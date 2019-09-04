"""
author: cnk700i
blog: ljr.im
tested simplely On HA version: 0.97.2
"""
import asyncio
import logging
import voluptuous as vol
import re
import time,json
from datetime import datetime,timedelta
import operator

from homeassistant import loader
from homeassistant import setup
from homeassistant.core import callback, Context, Event

from homeassistant.components.template.sensor import SensorTemplate, PLATFORM_SCHEMA as SENSOR_TEMPLATE_PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, CONF_ICON, CONF_NAME, CONF_MODE, EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP, EVENT_STATE_CHANGED, SERVICE_SELECT_OPTION, SERVICE_TURN_ON, SERVICE_TURN_OFF,
    ATTR_SERVICE_DATA, ATTR_DOMAIN, ATTR_SERVICE, EVENT_CALL_SERVICE)

from homeassistant.helpers.config_validation import time_period_str
from homeassistant.helpers.event import async_track_time_change,async_call_later
from homeassistant.util.async_ import (run_coroutine_threadsafe, run_callback_threadsafe)
from homeassistant.helpers import config_per_platform, discovery
from homeassistant.helpers import discovery
from homeassistant.helpers.template import Template
import homeassistant.helpers.config_validation as cv
from homeassistant.auth.const import GROUP_ID_ADMIN

from ..input_select import InputSelect
from ..input_boolean import InputBoolean
from ..input_text import InputText

_LOGGER = logging.getLogger(__name__)

TIME_BETWEEN_UPDATES = timedelta(seconds=1)
STORAGE_VERSION = 1
STORAGE_KEY = 'common_timer_tasks'

DOMAIN = 'common_timer'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

SERVICE_SET_OPTIONS = 'set_options'
SERVICE_SET_VALUE = 'set_value'
SERVICE_SELECT_OPTION = 'select_option'

DOMAIN_SERVICE_WITHOUT_ENTITY_ID = ['climate']

UI_INPUT_DOMAIN = 'input_domain'
UI_INPUT_ENTITY = 'input_entity'
UI_INPUT_OPERATION = 'input_operation'
UI_INPUT_DURATION = 'input_duration'
UI_SWITCH = 'switch'

SERVICE_SET = 'set'
SERVICE_CANCEL = 'cancel'

CONF_OBJECT_ID = 'object_id'
CONF_UI = 'ui'
CONF_VISIBLE = 'visible'
CONF_VIEW = 'view'
CONF_INITIAL = 'initial'
CONF_PATTERN = 'pattern'
CONF_OPTIONS = 'options'
CONF_USE_FOR = 'use_for'
CONF_MIN = 'min'
CONF_MAX = 'max'
CONF_INFO_NUM_MIN = 'info_num_min'
CONF_INFO_NUM_MAX = 'info_num_max'
CONF_DOMAINS = 'domains'
CONF_EXCLUDE = 'exclude'
CONF_PATTERN = 'pattern'
CONF_FRIENDLY_NAME = 'friendly_name'
CONF_INFO_PANEL = 'info_panel'
CONF_RATIO = 'ratio'
CONF_LOOP_FLAG = '⟳'
CONF_LINKED_USER = 'linked_user'
CONF_INTERRUPT_LOOP = 'interrupt_loop'

ATTR_OBJECT_ID = 'object_id'
ATTR_NAME ='name'
ATTR_ENTITIES = 'entities'
ATTR_CALLER = 'caller'

DEFAULT_OPERATION_OPTIONS =  ['开','关','开⇌关 [1:5]','关⇌开 [1:5]', '调服务']

PLATFORM_KEY = ('template', None, 'common_timer')
CONTEXT = None
CONTEXT_IGNORE = Context()

INFO_PANEL_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default='ct_info_panel'): cv.string,
    vol.Optional(CONF_FRIENDLY_NAME, default='定时任务列表'): cv.string,
    vol.Optional(CONF_INFO_NUM_MIN, default=1): cv.positive_int,
    vol.Optional(CONF_INFO_NUM_MAX, default=10): cv.positive_int
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_NAME, default='ct_control_panel'): cv.string,
        vol.Optional(CONF_DOMAINS, default=['light', 'switch', 'input_boolean', 'automation', 'script']): vol.All(cv.ensure_list, vol.Length(min=1), [cv.string]),
        vol.Optional(CONF_EXCLUDE, default=[]): vol.All(cv.ensure_list, vol.Length(min=0), [cv.string]),
        vol.Optional(CONF_FRIENDLY_NAME, default='通用定时器'): cv.string,
        vol.Optional(CONF_INFO_PANEL, default={'name': 'ct_info_panel','friendly_name': '定时任务列表','info_num_min': 1,'info_num_max': 10}): INFO_PANEL_SCHEMA,
        vol.Optional(CONF_PATTERN, default='[\u4e00-\u9fa5]+'): cv.string,
        vol.Optional(CONF_RATIO, default=5): cv.positive_int,
        vol.Optional(CONF_LINKED_USER, default='common_timer_linked_user'): cv.string,
        vol.Optional(CONF_INTERRUPT_LOOP, default=False): cv.boolean,
    })
}, extra=vol.ALLOW_EXTRA)

ATTR_DURATION = 'duration'
ATTR_OPERATION = 'operation'
ATTR_IS_LOOP = 'is_loop'

COMMON_TIMER_SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    vol.Optional(ATTR_DURATION, default=timedelta(minutes = 30)): cv.time_period,
    vol.Optional(ATTR_OPERATION, default='off'): cv.string,
    vol.Optional(ATTR_IS_LOOP, default=False): cv.boolean
})



BUILT_IN_CONFIG = {
    'ui': {
        'input_select': {
            'ct_domain': {
                'name': '设备类型',
                'options': ['---请选择设备类型---'],
                'initial': '---请选择设备类型---',
                'icon': 'mdi:format-list-bulleted-type',
                'use_for': 'input_domain'
            },
            'ct_entity': {
                'name': '设备名称',
                'options': ['---请选择设备---'],
                'initial': '---请选择设备---',
                'icon': 'mdi:format-list-checkbox',
                'use_for': 'input_entity'
            },
            'ct_operation': {
                'name': '操作',
                'options': DEFAULT_OPERATION_OPTIONS,
                'initial': '关',
                'icon': 'mdi:nintendo-switch',
                'use_for': 'input_operation'
            }
        },
        'input_text': {
            'ct_duration': {
                'name': '延迟时间',
                'initial': '0:00:00',
                'pattern': '([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]',
                'min': 0,
                'max': 8,
                'use_for': 'input_duration'
            }
        },
        'input_boolean': {
            'ct_switch': {
                'name': '启用/暂停',
                'initial': False,
                'icon': 'mdi:switch',
                'use_for': 'switch'
            }
        },
        'sensor': [{
            'platform': 'template',
            'entity_namespace': "common_timer",
            'sensors': {
                'ct_record_0': {
                    'friendly_name': "无定时任务",
                    'value_template': "-",
                    'icon_template': "mdi:calendar-check"
                }
            }
        }]
    },
    # 'domains': ['light', 'switch', 'automation', 'script', 'input_boolean'],
    # 'exclude': [],
    # 'pattern': '[\u4e00-\u9fa5]+',
    # 'name': 'ct_control_panel',
    # 'friendly_name': '通用定时器',
    # 'info_panel': {
    #     'name': 'ct_info_panel',
    #     'friendly_name': '定时任务列表',
    #     'info_num_min': 1,
    #     'info_num_max': 10,
    # }
}

@asyncio.coroutine
def async_setup(hass, config):
    _LOGGER.debug("-------%s--------",config[DOMAIN])
    """ setup up common_timer component """
    ui ={}    #save params of input components for getting input
    VALIDATED_CONF = BUILT_IN_CONFIG[CONF_UI]
    info_ui = []
    #remove CONF_USE_FOR from BUILT_IN_CONFIG, otherwise raise a validate failure
    for domain in VALIDATED_CONF:
        if isinstance(VALIDATED_CONF[domain], list):
            for object_id in VALIDATED_CONF[domain][0]['sensors']:
                info_ui.append('{}.{}'.format(domain, object_id))
        else:
            for object_id in VALIDATED_CONF[domain]:        
                if CONF_USE_FOR in VALIDATED_CONF[domain][object_id]:
                    user_for = VALIDATED_CONF[domain][object_id][CONF_USE_FOR]
                    ui[user_for] = '{}.{}'.format(domain, object_id)
                    VALIDATED_CONF[domain][object_id].pop(CONF_USE_FOR)

    components = set(key.split(' ')[0] for key in config.keys())
    for setup_domain in ['input_select', 'input_text', 'input_boolean', 'sensor']:
        #config file contains info, let HA initailize 
        if setup_domain in components:
            _LOGGER.debug('initialize component[%s]: config has this component', setup_domain)
            #wait for HA initialize component
            #maybe it can use discovery.discover(hass, service='load_component.{}'.format(setup_domain), discovered={}, component=setup_domain, hass_config=config) instead
            while setup_domain not in hass.config.components:
                yield from asyncio.sleep(1)
                _LOGGER.debug("initialize component[%s]: wait for HA initialization.", setup_domain)

            if setup_domain in ['input_select', 'input_text', 'input_boolean']: #entity belongs to component
                _LOGGER.debug("initialize component[%s]: component is ready, use component's method.", setup_domain)
                #add entity in component
                entities = []
                for object_id, conf in VALIDATED_CONF.get(setup_domain, {}).items():
                    # _LOGGER.debug("setup %s.%s", setup_domain, object_id)
                    if setup_domain == 'input_select':
                        # InputSelect(object_id, name, initial, options, icon)
                        entity = InputSelect(object_id, conf.get(CONF_NAME, object_id), conf.get(CONF_INITIAL), conf.get(CONF_OPTIONS) or [], conf.get(CONF_ICON))
                    elif setup_domain == 'input_text':
                        # InputText(object_id, name, initial, minimum, maximum, icon, unit, pattern, mode)
                        entity = InputText(object_id, conf.get(CONF_NAME, object_id), conf.get(CONF_INITIAL), conf.get(CONF_MIN), conf.get(CONF_MAX), conf.get(CONF_ICON), conf.get(ATTR_UNIT_OF_MEASUREMENT), conf.get(CONF_PATTERN), conf.get(CONF_MODE))
                    elif setup_domain == 'input_boolean':
                        # InputBoolean(object_id, name, initial, icon)
                        entity = InputBoolean(object_id, conf.get(CONF_NAME), conf.get(CONF_INITIAL), conf.get(CONF_ICON))
                        _LOGGER.debug("input_boolean.timer_button:%s,%s,%s,%s", object_id, conf.get(CONF_NAME), conf.get(CONF_INITIAL), conf.get(CONF_ICON))
                    else:
                        pass
                        # _LOGGER.debug("illegal component:%s", object_id, conf.get(CONF_NAME), conf.get(CONF_INITIAL), conf.get(CONF_ICON))
                    entities.append(entity)
                # _LOGGER.debug("entities:%s", entities)
                yield from hass.data[setup_domain].async_add_entities(entities)        
                _LOGGER.debug('initialize component[%s]: entities added.', setup_domain)
            # sensor should set a unique namespace to ensure it's a new platform and don't affect other entities using template platform which have been initialized.
            elif setup_domain in ['sensor']:   #entity belongs to component.platform 
                _LOGGER.debug("initialize component.platform[%s]: component is ready, use EntityComponent's method to initialize entity.", setup_domain)
                # SCHEMA
                p_validated = SENSOR_TEMPLATE_PLATFORM_SCHEMA(VALIDATED_CONF.get(setup_domain, {})[0])
                # _LOGGER.debug('sensor_conf: %s', VALIDATED_CONF.get(setup_domain, {})[0])
                # _LOGGER.debug('p_validated: %s', p_validated)
                yield from hass.data[setup_domain].async_setup({setup_domain: p_validated})
            else:
                _LOGGER.debug("initialize component[%s]: undefined initialize method.", setup_domain)

        #add config for HA to initailize
        else:
            _LOGGER.debug('initialize component[%s]: config hasn\'t %s component , use HA\'s setup method to initialize entity.', setup_domain, setup_domain)
            # _LOGGER.debug('conf: %s', VALIDATED_CONF)
            # hass.async_create_task(setup.async_setup_component(hass, setup_domain, VALIDATED_CONF))
            yield from setup.async_setup_component(hass, setup_domain, VALIDATED_CONF)

    #add group through service since HA initialize group by defalut
    data = {
        ATTR_OBJECT_ID: config[DOMAIN][CONF_NAME],
        ATTR_NAME: config[DOMAIN][CONF_FRIENDLY_NAME],
        ATTR_ENTITIES: [entity_id for param, entity_id in ui.items()]
        }
    # data[ATTR_ENTITIES].append('timer.laundry')
    yield from hass.services.async_call('group', SERVICE_SET, data)
    # hass.async_add_job(hass.services.async_call('group', SERVICE_SET, data))
    _LOGGER.info('---control planel initialized---')

    #info panel inital
    info_config = config[DOMAIN].get(CONF_INFO_PANEL)
    if info_config:
        entities = []
        for num in range(1, info_config[CONF_INFO_NUM_MIN]):
            object_id = 'ct_record_{}'.format(num)
            state_template = Template('-')
            state_template.hass = hass
            icon_template = Template('mdi:calendar-check')
            icon_template.hass = hass
            entity = SensorTemplate(hass = hass,
                                    device_id = object_id,
                                    friendly_name = '无定时任务',
                                    friendly_name_template = None,
                                    unit_of_measurement = None,
                                    state_template = state_template,
                                    icon_template = icon_template,
                                    entity_picture_template = None,
                                    entity_ids = set(),
                                    device_class = None)

            entities.append(entity)
            info_ui.append(entity.entity_id)
        yield from hass.data['sensor']._platforms[PLATFORM_KEY].async_add_entities(entities)
        data = {
            ATTR_OBJECT_ID: info_config[CONF_NAME],
            ATTR_NAME: info_config[CONF_FRIENDLY_NAME],
            ATTR_ENTITIES: [entity_id for entity_id in info_ui]
            }
        yield from hass.services.async_call('group', SERVICE_SET, data)
        _LOGGER.info('---info planel initialized---')

    domains = config[DOMAIN].get(CONF_DOMAINS)
    exclude = config[DOMAIN].get(CONF_EXCLUDE)
    pattern = config[DOMAIN].get(CONF_PATTERN)
    ratio = config[DOMAIN].get(CONF_RATIO)
    exclude.append(ui['switch']) # ignore ui input_boolean

    @asyncio.coroutine
    def start_common_timer(event):
        """ initialize common_timer. """
        _LOGGER.debug('try to get a linked user.')
        global CONTEXT
        username = config[DOMAIN].get(CONF_LINKED_USER)
        users = yield from hass.auth.async_get_users()
        for user in users:
            if user.name == username:
                CONTEXT = Context(user.id)
                _LOGGER.info("get a linked user.")
                break
        if CONTEXT is None:
            user = yield from  hass.auth.async_create_system_user(username, [GROUP_ID_ADMIN])
            CONTEXT = Context(user.id)
            _LOGGER.info("create a linked user for component.")

        _LOGGER.info('start initialize common_timer.')
        common_timer = CommonTimer(domains, exclude, pattern, ratio, ui, hass, info_config)
        yield from common_timer.start()
        
        interrupt_loop = config[DOMAIN].get(CONF_INTERRUPT_LOOP)
        @callback
        def common_timer_handle(event):
            """Listen for state changed events and refresh ui. """
            # _LOGGER.debug('---common_timer_handle()---')
            if event.data[ATTR_ENTITY_ID] == ui[UI_INPUT_DOMAIN]:
                # _LOGGER.debug('set domain from %s to %s',event.data['old_state'].as_dict()['state'] ,event.data['new_state'].as_dict()['state'])
                common_timer.choose_domain(event.data['new_state'].as_dict()['state'])
            elif event.data[ATTR_ENTITY_ID] == ui[UI_INPUT_ENTITY]:
                # _LOGGER.debug('set entity')
                common_timer.choose_entity(event.data['new_state'].as_dict()['state'])
            elif event.data[ATTR_ENTITY_ID] == ui[UI_INPUT_OPERATION]:
                # _LOGGER.debug('set operation')
                common_timer.choose_operation(event.data['new_state'].as_dict()['state'], context = event.context)
            elif event.data[ATTR_ENTITY_ID] == ui[UI_INPUT_DURATION]:
                pass
                # _LOGGER.debug('set time')
                # common_timer.input_duration(event.data['new_state'].as_dict()['state'])
            elif event.data[ATTR_ENTITY_ID] == ui[UI_SWITCH]:
                # _LOGGER.debug('start/stop')
                common_timer.switch(event.data['new_state'].as_dict()['state'], context = event.context)
            else:
                # _LOGGER.debug('stop_loop_task')
                if interrupt_loop and common_timer.stop_loop_task(event.data[ATTR_ENTITY_ID], context = event.context):
                    hass.async_add_job(common_timer.update_info)
        hass.bus.async_listen(EVENT_STATE_CHANGED, common_timer_handle)

        @asyncio.coroutine
        def async_handler_service(service):
            """ Handle calls to the common timer services. """
            entity_id = service.data[ATTR_ENTITY_ID]
            duration = str(service.data[ATTR_DURATION])
            operation = service.data[ATTR_OPERATION]
            is_loop = service.data[ATTR_IS_LOOP]
            if service.service == SERVICE_SET:
                common_timer.set_task(entity_id, operation, duration, is_loop)
                pass
            elif service.service == SERVICE_CANCEL:
                common_timer.cancel_task(entity_id)
                pass
        hass.services.async_register(DOMAIN, SERVICE_SET, async_handler_service, schema=COMMON_TIMER_SERVICE_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_CANCEL, async_handler_service, schema=COMMON_TIMER_SERVICE_SCHEMA)
        

        @asyncio.coroutine
        def stop_common_timer(event):
            """save task config to disk when ha stop."""
            _LOGGER.info("Shutting down common timer")
            yield from common_timer.save_tasks()
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_common_timer)

        # for test

        # service_events = {}
        # @asyncio.coroutine
        # def event_to_service_call(event: Event) -> None:
        #     if event.context.user_id == CONTEXT.id:
        #         service_events[event.data.get(ATTR_SERVICE_CALL_ID)] = event.data
        # hass.bus.async_listen(EVENT_CALL_SERVICE, event_to_service_call)

        # @callback
        # def service_executed(event: Event) -> None:
        #     call_id = event.data.get(ATTR_SERVICE_CALL_ID)
        #     s_event = service_events.get(call_id)
        #     if s_event is not None:
        #         service_data = s_event.get(ATTR_SERVICE_DATA) or {}
        #         domain = s_event.get(ATTR_DOMAIN).lower()  # type: ignore
        #         service = s_event.get(ATTR_SERVICE).lower()  # type: ignore
        #         # _LOGGER.debug("-----common_timer调用服务完毕！-----context = %s", CONTEXT)
        #         _LOGGER.debug("service_executed:%s/%s; service_call_id=%s", domain, service,call_id)
        #         _LOGGER.debug('data:%s', service_data)
        #         if service_data.get('entity_id') == 'input_select.ct_operation' and service == 'set_options':
        #             common_timer.refresh_ui()
        #         service_events.pop(call_id)

        # hass.bus.async_listen(EVENT_SERVICE_EXECUTED, service_executed)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_common_timer)

    return True


class CommonTimer:
    """Representation of a common timer."""
    def __init__(self, domains, exclude, pattern, ratio, ui, hass = None, info_config = None):
        _LOGGER.debug('--------------CONTEXT: %s', CONTEXT)
        """Initialize a common timer."""
        self._domains = domains
        self._exclude = exclude
        self._pattern = pattern
        self._ratio = ratio
        self._hass = hass
        self._ui = ui
        self._tasks = {}
        self._store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
        self._dic_friendly_name = {}
        self._dic_operation_en_to_cn = {
            'on':'开',
            'off':'关',
            'temporary_on':'关⇌开',
            'temporary_off': '开⇌关',
            'custom:*': '调服务'
        }
        self._dic_operation_cn_to_en = {v : k for k, v in self._dic_operation_en_to_cn.items()}
        self._dic_domain_en_to_cn = {
            'light': '灯',
            'switch': '开关',
            'input_boolean': '二元选择器',
            'automation': '自动化',
            'script': '脚本'
        }
        self._dic_domain_cn_to_en = {v : k for k, v in self._dic_domain_en_to_cn.items()}
        self._dic_icon = {'light': 'mdi:lightbulb', 'switch': 'mdi:toggle-switch', 'automation': 'mdi:playlist-play', 'script': 'mdi:script', 'input_boolean': 'mdi:toggle-switch'}
        self._domain = None
        self._entity_id = None
        self._queue = DelayQueue(60)  # create a queue
        self._running_tasks = None
        self._running_tasks_ids = None
        self._info_config = info_config
    
    def refresh_ui(self):        
        _LOGGER.debug('refresh_ui()')
        if self._entity_id is None:
            return
        task = self._get_task(self._entity_id)
        self.set_state(self._ui[UI_INPUT_OPERATION], state = {'option': '开'}, service = 'select_option', context = CONTEXT_IGNORE)
        self.set_state(self._ui[UI_INPUT_OPERATION], state = {'option': self.get_operation(task = task)}, service = 'select_option', context = CONTEXT_IGNORE)

    @asyncio.coroutine
    def start(self):
        """prepare task list and default ui. """
        pattern = re.compile(self._pattern)
        states = self._hass.states.async_all()
        data =  yield from self._store.async_load()  # load task config from disk
        tasks = {
            user_dict['entity_id']: {'entity_id':user_dict['entity_id'],'duration':user_dict.get('duration','0:00:00'),'operation':user_dict.get('operation','off'),'count':user_dict.get('count',0),'ratio':user_dict.get('ratio',self._ratio)} for user_dict in data['tasks'] if 'entity_id' in user_dict
        } if data else {}
        # _LOGGER.debug('[start()] load task config: <tasks=%s>',tasks)

        for state in states:
            domain = state.domain
            object_id = state.object_id
            entity_id = '{}.{}'.format(domain, object_id)
            if domain not in self._domains or entity_id in self._exclude:
                pass
            else:
                friendly_name = state.name
                if not self._pattern or pattern.search(friendly_name):
                    _LOGGER.debug("添加设备:{}（{}）".format(friendly_name, entity_id))
                    self._dic_friendly_name.setdefault(friendly_name, entity_id)
                    self._tasks.setdefault(domain,{}).setdefault(entity_id,{})
                    self._tasks[domain][entity_id]['friendly_name'] = friendly_name                 
                    self._tasks[domain][entity_id]['icon'] = self.get_attributes(entity_id).get('icon', self._dic_icon[domain])
                    self._tasks[domain][entity_id]['entity_id'] = entity_id
                    self._tasks[domain][entity_id]['remaining'] = '0:00:00'
                    self._tasks[domain][entity_id]['handle'] = None
                    self._tasks[domain][entity_id]['next_operation'] = None
                    if tasks.get(entity_id) is not None:
                        self._tasks[domain][entity_id]['duration'] = tasks.get(entity_id).get('duration')
                        self._tasks[domain][entity_id]['operation'] = tasks.get(entity_id).get('operation')
                        self._tasks[domain][entity_id]['count'] = tasks.get(entity_id).get('count')
                        self._tasks[domain][entity_id]['ratio'] = tasks.get(entity_id).get('ratio')
                    else:
                        self._tasks[domain][entity_id]['duration'] = '0:00:00'
                        self._tasks[domain][entity_id]['operation'] = 'on' if domain == 'autonmation' or domain == 'script' else 'off'
                        self._tasks[domain][entity_id]['count'] = 0
                        self._tasks[domain][entity_id]['ratio'] = self._ratio
                else:
                    _LOGGER.debug("忽略设备：{}（{}）".format(friendly_name, entity_id))
        options = [self._dic_domain_en_to_cn.get(d) for d in self._tasks.keys()]
        options.insert(0,'---请选择设备类型---')
        data = {
            'entity_id':self._ui[UI_INPUT_DOMAIN],
            'options': options
        }
        self._hass.async_add_job(self._hass.services.async_call('input_select', SERVICE_SET_OPTIONS, data))
        
        async_track_time_change(self._hass, self.update) # update every second

    @asyncio.coroutine
    def save_tasks(self):
        """save task config to disk"""
        tasks = [
            {
                'entity_id': attrs['entity_id'],
                'duration': attrs['duration'],
                'operation': attrs['operation'],
                'count': attrs['count'],
                'ratio': attrs['ratio']
            } 
            for entities in self._tasks.values() for entity_id, attrs in entities.items() if attrs['duration'] != '0:00:00' or attrs['count'] != 0
        ]
        # _LOGGER.debug('[stop()] save task config: <tasks=%s>',tasks)
        if not tasks:
            return
        data = {
            'tasks':tasks
        }
        yield from self._store.async_save(data)

    def choose_domain(self, domain):
        """refresh entity input list """

        domain = self._dic_domain_cn_to_en.get(domain, domain)
        self._domain = domain
        if domain == '---请选择设备类型---':
            options = ['---请选择设备---']
        else:
            entities = [attrs for entity_id, attrs in self._tasks[domain].items() ]
            options = [self._get_task(entity['entity_id'])['friendly_name'] for entity in sorted(entities, key = operator.itemgetter('count'), reverse = True)]  #show friendly_name
            options.insert(0,'---请选择设备---')
        self.set_options(self._ui[UI_INPUT_ENTITY], options)
        # self.set_options(self._ui[UI_INPUT_OPERATION], DEFAULT_OPERATION_OPTIONS)
    
    def choose_entity(self, friendly_name):
        """ load entity task params and set ui."""
        # self.set_state(self._ui[UI_INPUT_OPERATION], state = '-', force_update = True, context = CONTEXT_IGNORE)
        if friendly_name == '---请选择设备---':
            self._entity_id = None
            self.set_state(self._ui[UI_INPUT_DURATION], state= '0:00:00')
            self.set_state(self._ui[UI_SWITCH], state = 'off')
            self.set_options(self._ui[UI_INPUT_OPERATION], DEFAULT_OPERATION_OPTIONS)
            self.set_state(self._ui[UI_INPUT_OPERATION], state = {'option': '关'}, service = 'select_option', context = CONTEXT_IGNORE)
        else:
            entity_id = self._entity_id = self._dic_friendly_name.get(friendly_name, None)
            task = self._get_task(entity_id)
            if task is None:
                _LOGGER.info("Function choose_entity: friendly_name not found in dic !")
                return
            remaining_time = self._queue.get_remaining_time(task['handle'])
            # task's running
            if remaining_time is not None:
                duration = str(remaining_time)
                self.set_state(self._ui[UI_INPUT_DURATION], state= duration)
                self.set_state(self._ui[UI_SWITCH], state = 'on')
            else:
                duration = task['remaining'] if task['remaining'] != '0:00:00' else task['duration']
                self.set_state(self._ui[UI_INPUT_DURATION], state= duration)
                self.set_state(self._ui[UI_SWITCH], state = 'off')

            options = ['开','关','开⇌关 [1:{}]'.format(task['ratio']),'关⇌开 [1:{}]'.format(task['ratio']), '调服务']
            self.set_options(self._ui[UI_INPUT_OPERATION], options)
            self.set_state(self._ui[UI_INPUT_OPERATION], state = {'option': self.get_operation(task = task)}, service = 'select_option', context = CONTEXT_IGNORE)

    def choose_operation(self, operation, context = None):
        """ set operation param """
        task = self._get_task(self._entity_id)
        if task is None:
            _LOGGER.debug("no entity selected, pass.")
            return

        # save operation if task is not running, besides setting options will cause a operation change.
        if self.get_state(self._ui[UI_SWITCH]) == 'off' and context != CONTEXT_IGNORE:
            task['operation'] = self.get_operation(ui_operation = operation)
    
    def switch(self, state, context = None):
        """ start or stop task """
        # _LOGGER.debug('switch()')
        if self._domain != '---请选择设备类型---':
            entity_id = self._entity_id
            task = self._get_task(self._entity_id)
            if task is None:
                _LOGGER.debug("未选择设备/未找到对应entity_id")
                self.set_state(self._ui[UI_SWITCH], state = 'off')
                return
            else:
                duration = self.get_state(self._ui[UI_INPUT_DURATION])
                operation = self.get_operation(ui_operation = self.get_state(self._ui[UI_INPUT_OPERATION]))

                if duration == '0:00:00':
                    return
                # start timer
                if state == 'on':
                    task['count'] += 1
                    if task['handle'] is None:
                        if task['remaining'] != duration:
                            task['duration'] = duration  # set duration attr
                        task['handle'] = self._queue.insert(entity_id, duration, self.handle_task, operation = operation)  # initialize queue task
                        task['operation'] = operation #set operation attr                            

                        # sync state for loop task
                        if 'temporary' in operation:
                            task['next_operation'] = operation.split('_')[1]  # set next_operation attr, used in info panenl to show state
                            state = 'off' if task['next_operation'] == 'on' else 'on'
                            self.set_state(entity_id, service = 'turn_'+state, force_update = True) 
                            #service.call()
                        else:
                            task['next_operation'] = operation
                        task['exec_time'] = datetime.now() + self._queue.get_remaining_time(task['handle'])
                # stop timer
                else:
                    self._queue.remove(task['handle'])
                    task['handle'] = None
                    task['next_operation'] = None
                    if 'temporary' in task['operation']:
                        task['remaining'] = '0:00:00'
                    else:
                        task['remaining'] = duration
                        self.set_state(self._ui[UI_INPUT_DURATION], state = task['duration'])  # reset control panel ui
                    _LOGGER.debug("---switch---")
                    self.set_state(self._ui[UI_INPUT_OPERATION], state = self.get_operation(task = task))  # reset control panel ui

        else:
            _LOGGER.debug("no device type selected")
            self.set_state(self._ui[UI_SWITCH], state = 'off')
        if context != CONTEXT_IGNORE: # UI_SWITCH will be reset after a task finish, this shouldn't trigger a update twice
            self._hass.async_add_job(self.update_info)  # refresh info panel

    def _get_task(self, entity_id):
        """ return task base info  """
        if entity_id is None:
            return None
        domain = entity_id.split('.')[0]
        if self._tasks.get(domain, None) is not None:
            return self._tasks.get(domain, None).get(entity_id, None)
        else:
            return None
    
    def get_operation(self,ui_operation = None, task = None):
        """ transform operation string between ui and task"""
        if ui_operation is not None:
            # _LOGGER.debug("get_operation from ui:{}|{}".format(ui_operation,self._dic_operation.get(ui_operation.split(' ')[0])))
            return self._dic_operation_cn_to_en.get(ui_operation.split(' ')[0])
        if task is not None:
            if 'custom:' in task['operation']:
                return '调服务'
            if task['operation'] in ['on','off']:
                # _LOGGER.debug("get_operation from task:{}|{}".format(task['operation'],self._dic_operation.get(task['operation'])))
                return self._dic_operation_en_to_cn.get(task['operation'])
            else:
                # _LOGGER.debug("get_operation from task:{}|{}".format(task['operation'],'{} [1:{}]'.format(self._dic_operation.get(task['operation']),task['ratio'])))
                return '{} [1:{}]'.format(self._dic_operation_en_to_cn.get(task['operation']),task['ratio'])
        else:
            return '关'

    def get_state(self, entity_id):
        """ return entity state. """
        state = self._hass.states.get(entity_id)
        if state:
            return state.as_dict()['state']
        else:
            return None
    
    def get_attributes(self, entity_id):
        """ return entity attributes. """
        state = self._hass.states.get(entity_id)
        if state:
            return state.as_dict().get('attributes',{})
        else:
            return None

    def set_state(self, entity_id, state = None, attributes = None, service = None, force_update = False, context = None):
        """ set entity state. """
        if context is None:
            context = CONTEXT
        if service is None:
            _LOGGER.debug("[set_state] state machine: entity_id= {}, from {} to {}, context = {}".format(entity_id, self.get_state(entity_id), state, context))
            attr = self.get_attributes(entity_id)
            if attributes is not None:
                attr.update(attributes)
            self._hass.states.async_set(entity_id, state, attr, force_update = force_update, context = context)
        else:
            domain = entity_id.split('.')[0]
            _LOGGER.debug('[set_state] call service: entity_id =%s, context = %s',entity_id, context)
            # unused, after 0.78.0 fixed.
            # attr = self.get_attributes(entity_id)
            # if attributes is not None:
            #     attr.update(attributes)
            # change state directly with a context identification since call service can't pass context in code.
            # self._hass.states.async_set(entity_id, state, attr, force_update = force_update, context = CONTEXT)
            data = {'entity_id': entity_id}
            if state is not None:
                data.update(state)
            # call service to controll device
            self._hass.async_add_job(self._hass.services.async_call(domain, service, data, context = context ))

    def set_options(self, entity_id, options, current_option = None, context = CONTEXT_IGNORE):
        """ set options for input select  """
        domain = entity_id.split('.')[0]
        if domain != 'input_select':
            _LOGGER.debug('wrong service')
            return
        data = {'entity_id': entity_id,'options': options}
        if current_option is not None:
            data['current_option'] = current_option
        self._hass.async_add_job(self._hass.services.async_call(domain, SERVICE_SET_OPTIONS, data , blocking = True, context = context)) # set blocking to wait till service is executed

    @callback
    def update(self, time):
        """ queue step forward and refresh timer display. 
            define callback to run in main thread.
        """
        self._queue.next()  # queue handler
        # refresh timer display when task is running
        if self.get_state(self._ui[UI_SWITCH]) == 'on':
            entity_id = self._entity_id
            if entity_id is None:
                _LOGGER.info("Function task: friendly_name(%s) not found in dic !", entity_id)
                return
            task = self._get_task(entity_id)
            remaining_time = self._queue.get_remaining_time(task['handle'])
            # task finish
            if remaining_time is None:
                remaining_time = task['remaining']
                if remaining_time == '0:00:00':
                    self.set_state(self._ui[UI_INPUT_DURATION], state = task['duration'])
                else:
                    self.set_state(self._ui[UI_INPUT_DURATION], state = str(remaining_time))
                self.set_state(self._ui[UI_SWITCH], state = 'off', context = CONTEXT_IGNORE)
            # task waite
            else:
                self.set_state(self._ui[UI_INPUT_DURATION], state = str(remaining_time))

    # @asyncio.coroutine
    def handle_task(self, entity_id, command, **kwargs):
        """ handle task when time arrive.
            if handler take long time, use hass.async_add_job(func) to exec in another thread. 
        """
        _LOGGER.debug("[handle_task] start: entity_id = %s, command = %s.", entity_id, command)
        task = self._get_task(entity_id)
        task['handle'] = None
        task['remaining'] = '0:00:00'
        if 'custom:' not in command:
            command = 'standard:'+command
        mode = command.split(':')[0]
        operation = command.split(':')[1]

        if mode == 'custom':
            try:
                if operation == '*':
                    _LOGGER.debug('[handle_task] custom mode: entity has no custom command, skip')
                    return
                try:
                    cmnds = self.get_attributes(entity_id)
                    for attr in operation.split('/'):
                        cmnds = cmnds[attr]
                    _LOGGER.debug('[handle_task] custom mode: get custom command %s', cmnds)
                except:
                    _LOGGER.error('[handle_task] custom mode: entity has no attr %s', operation)
                    return
                if not isinstance(cmnds, list) or len(cmnds[0]) != 3:
                    _LOGGER.error('[handle_task] custom mode: service command format error %s', cmnds)
                    return
                translation = lambda cmnds:([cmnd[0] for cmnd in cmnds], [cmnd[1] for cmnd in cmnds], [json.loads(cmnd[2]) for cmnd in cmnds])
                domain_list, service_list, data_list = translation(cmnds)
                _LOGGER.debug('domain_list: %s', domain_list)
                _LOGGER.debug('service_list: %s', service_list)
                _LOGGER.debug('data_list: %s', data_list)
                for i,d in enumerate(data_list):
                    if 'entity_id' not in d and domain_list[i] not in DOMAIN_SERVICE_WITHOUT_ENTITY_ID:
                        d.update({"entity_id": entity_id })
                for i in range(len(domain_list)):
                    _LOGGER.debug('domain: %s, servcie: %s, data: %s', domain_list[i], service_list[i], data_list[i])
                    self._hass.async_add_job(self._hass.services.async_call(domain_list[i], service_list[i], data_list[i], context = CONTEXT))
                _LOGGER.debug("[handle_task] with aihome_actions finish.")
            except:
                import traceback
                _LOGGER.error('[handle_task] %s', traceback.format_exc())
        else:
            if operation == 'temporary_on':
                ratio = self._ratio if task['operation'] == operation else 1
                delay =int(time_period_str(task['duration']).total_seconds()*ratio)
                task['handle'] = self._queue.insert(entity_id, str(timedelta(seconds = delay)), self.handle_task, 'temporary_off')
                task['next_operation'] = 'off'
                task['exec_time'] = datetime.now() + self._queue.get_remaining_time(task['handle'])
                operation = 'on'
            elif operation == 'temporary_off':
                ratio = self._ratio if task['operation'] == operation else 1
                delay =int(time_period_str(task['duration']).total_seconds()*ratio)
                task['handle'] = self._queue.insert(entity_id, str(timedelta(seconds = delay)), self.handle_task, 'temporary_on')
                task['next_operation'] = 'on'
                task['exec_time'] = datetime.now() + self._queue.get_remaining_time(task['handle'])
                operation = 'off'
            service = 'turn_'+operation
            state = operation
            self.set_state(entity_id, service = service, force_update = True)
            _LOGGER.debug("[handle_task] finish:{}({})".format(service,entity_id))
        self._hass.async_add_job(self.update_info)
        # self._hass.async_add_job(self.long_time_task)  # for test

    def long_time_task(self):
        """ for test. """
        _LOGGER.debug("handle long time task, start")
        time.sleep(5)
        _LOGGER.debug("handle long time task, finish")
    
    def _get_index_of_running_tasks(self, entity_id):
        """ return index of running_tasks. """
        if entity_id is None or self._running_tasks_ids is None:
            return None
        try:
            row = self._running_tasks_ids.index(entity_id)
            return row
        except ValueError:
            return None

    def stop_loop_task(self, entity_id, context):
        """ if entity operated by other method, stop loop task.
            according context to identify who changes state of entity.
        """
        info_config = self._info_config
        if info_config is None:
            return False

        #if entity in running tasks list
        if self._get_index_of_running_tasks(entity_id) is not None:
            task = self._get_task(entity_id)
            #if loop task and who operated
            if 'temporary' in task['operation'] and context.user_id != CONTEXT.user_id:
                _LOGGER.debug("operated by other method. <entity_id = %s, context = %s, common_timer context = %s>", entity_id, context, CONTEXT)
                #clear task info
                self._queue.remove(task['handle'])
                task['handle'] = None
                task['remaining'] = '0:00:00'
                #reset frontend
                if self._entity_id == entity_id:
                    self.set_state(self._ui[UI_SWITCH], state = 'off')
                    self.set_state(self._ui[UI_INPUT_DURATION], state = task['duration'])                
            else:
                _LOGGER.debug("operated by common_timer.py. <entity_id = %s, context = %s>", entity_id, context)
            return True
        return False

    def _get_running_tasks(self):
        """get running tasks order by exec_time"""
        tasks = [attrs for domain_entities in self._tasks.values() for entity_id, attrs in domain_entities.items() if attrs['handle'] is not None]
        return sorted(tasks, key=operator.itemgetter('exec_time'))

    @asyncio.coroutine
    def update_info(self):
        """update info and refresh info panel."""
        info_config = self._info_config
        if info_config is None:
            return
        _LOGGER.debug("↓↓↓↓↓_update_info()↓↓↓↓↓")
        running_tasks = self._get_running_tasks()
        self._running_tasks_ids = [entity['entity_id'] for entity in running_tasks]
        info_row_num = len(running_tasks) if len(running_tasks) < info_config[CONF_INFO_NUM_MAX] else info_config[CONF_INFO_NUM_MAX]
        new_rows = []
        info_ui = []
        default_state = Template('-')
        default_state.hass = self._hass
        default_icon = Template('mdi:calendar-check')
        default_icon.hass = self._hass
        # refresh every row
        for row in range(0, info_config[CONF_INFO_NUM_MAX]):
            info_entity_id = 'sensor.ct_record_{}'.format(row)
            info_entity = self._hass.data['sensor'].get_entity(info_entity_id)
            # rows show record
            if row < info_row_num:
                _LOGGER.debug("info_entity:%s, row=%s",info_entity, row)
                # info1 = '{0:{2}<12}{1:{2}>20}'.format(running_tasks[row]['friendly_name'], running_tasks[row]['exec_time'].strftime("%Y-%m-%d %H:%M:%S"),chr(12288))  # for test
                info1 = '{}{}'.format(align(running_tasks[row]['friendly_name'],20), align(running_tasks[row]['exec_time'].strftime("%Y-%m-%d %H:%M:%S"),20))  # name+time info template
                if 'custom:' in running_tasks[row]['operation']:
                    info2 = Template('call service')  # operation info template
                else:
                    loop_flag = CONF_LOOP_FLAG if 'temporary' in running_tasks[row]['operation'] else ''
                    info2 = Template('{} {} → {}'.format(loop_flag, self.get_state(running_tasks[row]['entity_id']), running_tasks[row]['next_operation']))  # operation info template
                info2.hass = self._hass
                # info3 = Template('{{{{states.{}.{}.{}}}}}'.format(running_tasks[row]['entity_id'] ,'attributes' ,'icon'))  # for test
                info3 = Template(running_tasks[row]['icon'])  # icon template
                info3.hass = self._hass
                # row has record, update
                if info_entity is not None:
                    _LOGGER.debug("row%s, record exist. <info_entity_id= %s >",row,info_entity_id)
                    info_entity._name = info1
                    info_entity._template = info2
                    info_entity._icon_template = info3
                    info_entity.schedule_update_ha_state(True)  # force_refresh = True to call device_update to update sensor.template
                # row has record, add   
                else:
                    _LOGGER.debug("row%s, no record. <info_entity_id = %s, state = %s>",row,info_entity_id, self.get_operation(running_tasks[row]['operation']))
                    object_id = 'ct_record_{}'.format(row)
                    sensor = SensorTemplate(hass = self._hass,
                                            device_id = object_id,
                                            friendly_name = info1,
                                            friendly_name_template = None,
                                            unit_of_measurement = None,
                                            state_template = info2,
                                            icon_template = info3,
                                            entity_picture_template = None,
                                            entity_ids = set(),
                                            device_class = None)
                    new_rows.append(sensor)
                info_ui.append(info_entity_id)
            # rows show blank or should be remove
            else:
                if not any([info_row_num, row]) or row < info_config[CONF_INFO_NUM_MIN] or info_config[CONF_INFO_NUM_MAX] == info_config[CONF_INFO_NUM_MIN]:
                    info1 = '无定时任务'
                    info_entity._name = info1
                    info_entity._template = default_state
                    info_entity._icon_template = default_icon
                    info_entity.schedule_update_ha_state(True)  # force_refresh = True to call device_update to update sensor.template
                    info_ui.append(info_entity_id)
                else:
                    yield from self._hass.data['sensor'].async_remove_entity(info_entity_id)
        if new_rows:
            yield from self._hass.data['sensor']._platforms[PLATFORM_KEY].async_add_entities(new_rows, update_before_add = True)

        data = {
            ATTR_OBJECT_ID: info_config[CONF_NAME],
            ATTR_NAME: info_config[CONF_FRIENDLY_NAME],
            ATTR_ENTITIES: [entity_id for entity_id in info_ui]
            }
        yield from self._hass.services.async_call('group', SERVICE_SET, data)
        _LOGGER.debug("↑↑↑↑↑_update_info()↑↑↑↑↑")

    def set_task(self, entity_id, operation, duration, is_loop):
        """ create new task, will overwrite previous task. """
        _LOGGER.debug('----set_task()-----')
        task = self._get_task(entity_id)
        if task is not None:
            self._queue.remove(task['handle'])
            task['duration'] = duration
            task['next_operation'] = operation
            if is_loop and 'custom:' not in operation:
                operation = 'temporary_' + operation
                state = 'off' if task['next_operation'] == 'on' else 'on'
                self.set_state(entity_id, service = 'turn_'+state, force_update = True)
            task['operation'] = operation
            task['handle'] = self._queue.insert(entity_id, duration, self.handle_task, operation = operation)  # initialize queue task
            task['exec_time'] = datetime.now() + self._queue.get_remaining_time(task['handle'])
            self._hass.async_add_job(self.update_info)  # refresh info panel
            if self._entity_id == entity_id:
                _LOGGER.debug("---set_task---")
                self.set_state(self._ui[UI_INPUT_OPERATION], state = self.get_operation(task = task))  # reset control panel ui
                self.set_state(self._ui[UI_INPUT_DURATION], state = task['duration'])
                self.set_state(self._ui[UI_SWITCH], state = 'on')
        else:
            _LOGGER.info('set up task for %s failure', entity_id)
    
    def cancel_task(self, entity_id):
        """ cancel task. """
        task = self._get_task(entity_id)
        if task is not None:
            self._queue.remove(task['handle'])
            task['handle'] = None
            task['remaining'] = '0:00:00'
            #reset frontend
            if self._entity_id == entity_id:
                self.set_state(self._ui[UI_SWITCH], state = 'off')
                self.set_state(self._ui[UI_INPUT_DURATION], state = task['duration'])
            self._hass.async_add_job(self.update_info)  # refresh info panel
        else:
            _LOGGER.info('cancel task of %s failure', entity_id)

class DelayQueue(object):
    """Representation of a queue. """
    __current_slot = 1

    def __init__(self, slots_per_loop, **kwargs):
        """initailize a queue. """
        self.__slots_per_loop = slots_per_loop
        self.__queue = [[] for i in range(slots_per_loop)]
    
    def insert(self, task_id, duration, callback, operation = 'turn_off', **kwargs):
        """ add new task into queue """
        if duration == "0:00:00":
            return None
        second = time_period_str(duration).total_seconds()
        loop = second / len(self.__queue)
        slot = (second + self.__current_slot - 1) % len(self.__queue)
        delayQueueTask = DelayQueueTask(task_id, operation, int(slot), loop, callback, kwargs = kwargs)
        self.__queue[delayQueueTask.slot].append(delayQueueTask)
        _LOGGER.debug("create task:{}/{}".format(delayQueueTask.slot, delayQueueTask.loop))
        return delayQueueTask

    def remove(self, delayQueueTask):
        """ remove task from queue """
        if delayQueueTask is not None:
            _LOGGER.debug("remove task: in slot {}.".format(delayQueueTask.slot))
            self.__queue[delayQueueTask.slot].remove(delayQueueTask)
        else:
            _LOGGER.debug("remove task: task has been removed.")

    
    def get_remaining_time(self, delayQueueTask):
        """ return remaining time of task"""
        if delayQueueTask:
            if self.__current_slot - 1 > delayQueueTask.slot and self.__current_slot - 1 < 60:
                second = self.__slots_per_loop * (delayQueueTask.loop + 1) + delayQueueTask.slot - (self.__current_slot - 1)
            else:
                second = self.__slots_per_loop * delayQueueTask.loop + delayQueueTask.slot - (self.__current_slot - 1)
            return timedelta(seconds = second)
        else:
            return None
   
    def next(self):
        """ queue read tasks of current slot, and execute task when loop count of task arrives 0 """
        if len(self.__queue) >= self.__current_slot:
            tasks = self.__queue[self.__current_slot - 1]
            # _LOGGER.debug("current slot：{}(has {} tasks)".format(self.__current_slot - 1,len(tasks)))
            if tasks:
                executed_task = []
                for task in tasks:
                    # _LOGGER.debug("find {} at loop:{}/{}, exec = {}".format(task.task_id, task.slot, task.loop, task.should_exec))
                    if task.should_exec:
                        task.exec_task()
                        executed_task.append(task)
                    else:
                        task.nextLoop()
                for task in executed_task:
                    # _LOGGER.debug("remove task in slot {}".format(task.slot))
                    tasks.remove(task)  #删除slot的任务，不是调用DelayQueue对象方法；因为引用同一对象，会同步删除
            self.__current_slot += 1
            if self.__current_slot > len(self.__queue):
                self.__current_slot = 1

class DelayQueueTask(object):
    """Representation of a queue task."""

    def __init__(self, task_id, operation:str = 'turn_off', slot:int = 0 , loop:int = 0 , exec_task = None, **kwargs):
        """initialize a queue task."""
        self._task_id = task_id
        self._operation = operation
        self._slot = int(slot)
        self._loop = int(loop)
        self._exec_task = exec_task
        self._kwargs = kwargs

    @property
    def slot(self) -> int:
        """ return slot """
        return int(self._slot)

    @property
    def loop(self) -> int:
        """ return loop """
        return int(self._loop)

    @property
    def task_id(self):
        """ return entity_id of task """
        return self._task_id

    @property
    def operation(self):
        """ return operatrion of task """
        return self._operation

    def nextLoop(self):
        """ update after queue finish a loop """
        self._loop -= 1

    @property
    def should_exec(self) -> bool:
        """ return true when loop count """
        if self._loop == 0:
            return True
        else:
            return False
    
    def exec_task(self):
        """ handle task"""
        self._exec_task(self._task_id, self._operation, kwargs = self._kwargs)


def is_chinese(uchar):
    """ return True if a unicode char is chinese. """
    if uchar >= u'\u4e00' and uchar <= u'\u9fa5':
        return True
    else:
        return False

def align( text, width, just = "left"):
    """ align strings mixed with english and chinese """
    utext = stext = str(text)
    # utext = stext.decode("utf-8")
    cn_count = 0
    for u in utext:
        if is_chinese(u):
            cn_count += 2 # count chinese chars width
        else:
            cn_count += 1  # count english chars width
    num =int( (width - cn_count) / 2 )
    blank =int( (width - cn_count) % 2)
    if just == "right":
        return chr(12288) * num + " " * blank + stext
    elif just == "left":
        return stext + " " * blank + chr(12288) * num