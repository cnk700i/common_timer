"""
Component to 
"""
import asyncio
import logging

import re
from homeassistant import loader
from homeassistant import setup
from homeassistant.core import callback
from homeassistant.components.input_select import InputSelect
from homeassistant.components.input_boolean import InputBoolean
from homeassistant.components.input_text import InputText



from homeassistant.components.sensor.template import SensorTemplate
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, CONF_ICON, CONF_NAME, CONF_MODE, EVENT_HOMEASSISTANT_START, EVENT_STATE_CHANGED, SERVICE_SELECT_OPTION, SERVICE_TURN_ON, SERVICE_TURN_OFF)

from homeassistant.helpers.config_validation import time_period_str
from datetime import datetime,timedelta
from homeassistant.helpers.event import async_track_time_change

from homeassistant.util.async_ import (
    run_coroutine_threadsafe, run_callback_threadsafe)

import time
from datetime import datetime
import operator
from homeassistant.helpers import config_per_platform, discovery
from homeassistant.helpers import discovery
from homeassistant.helpers.template import Template

TIME_BETWEEN_UPDATES = timedelta(seconds=1)

_LOGGER = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)

DOMAIN = 'common_timer'
DEPENDENCIES = ['group']
ENTITY_ID_FORMAT = DOMAIN + '.{}'

SERVICE_SET_OPTIONS = 'set_options'
SERVICE_SET_VALUE = 'set_value'
SERVICE_SELECT_OPTION = 'select_option'

UI_INPUT_DOMAIN = 'input_domain'
UI_INPUT_ENTITY = 'input_entity'
UI_INPUT_OPERATION = 'input_operation'
UI_INPUT_DURATION = 'input_duration'
UI_SWITCH = 'switch'

SERVICE_SET = 'set'
CONF_OBJECT_ID = 'object_id'
CONF_ENTITIES = 'entities'
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
ATTR_OBJECT_ID = 'object_id'
ATTR_NAME ='name'
ATTR_ENTITIES = 'entities'

PLATFORM_KEY = ('template', None, 'common_timer')

COMMON_TIMER_CONF={
    'entities':
    {
        'input_select':
        {
            'domain':
            {
                'name': '设备类型',
                'options': ['请选择设备类型'],
                'initial': '请选择设备类型',
                'icon': 'mdi:format-list-bulleted-type',
                'use_for': 'input_domain'
            },
            'entity':
            {
                'name': '设备名称',
                'options': ['请选择设备'],
                'initial': '请选择设备',
                'icon': 'mdi:format-list-checkbox',
                'use_for': 'input_entity'
            },
            'operation':
            {
                'name': '操作',
                'options': ['开', '关'],
                'initial': '关',
                'icon': 'mdi:nintendo-switch',
                'use_for': 'input_operation'
            }
        },
        'input_text':
        {
            'common_timer':
            {
                'name': '延迟时间',
                'initial': '0:00:00',
                'pattern': '([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]',
                'min':0,
                'max':8,
                'use_for': 'input_duration'
            }
        },
        'input_boolean':
        {
            'timer_button':
            {
                'name': '启用/暂停',
                'initial': False,
                'icon': 'mdi:switch',
                'use_for': 'switch'
            }
        },

        'sensor':
        [{
            'platform': 'template',
            'entity_namespace': "common_timer",
            'sensors':
            {
                'ct_row_0':
                {
                    'friendly_name': "无定时任务",
                    'value_template': Template("-"),
                    'icon_template': Template("mdi:calendar-check")
                }
            }
        },
        {
            'platform': 'api_streams'
        }]
        
    },
    'domains': ['light', 'switch', 'automation', 'script', 'input_boolean'],
    'exclude': [],
    'pattern': '[\u4e00-\u9fa5]+',
    'name': 'common_timer_control_panel',
    'friendly_name': '通用定时器',
    'info_panel':{
        'name': 'common_timer_info_panel',
        'friendly_name': '定时任务列表',
        'info_num_min': 1,
        'info_num_max': 10,
    }
}
@asyncio.coroutine
def async_setup(hass, config):
    ui ={}    

    
    
    VALIDATED_CONF = COMMON_TIMER_CONF[CONF_ENTITIES]
    info_ui = []
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
        
        if setup_domain in components:
            _LOGGER.debug('initial component[%s]: config has this component', setup_domain)
            
            
            """
            setup_tasks = hass.data.get('setup_tasks')
            if setup_tasks is not None and setup_domain in setup_tasks:
                _LOGGER.debug("initial component[%s]: HA is initializing, wait.", setup_domain)
                yield from setup_tasks[setup_domain]
                _LOGGER.debug("initial component[%s]: HA finish initialization.", setup_domain)
            """
            while setup_domain not in hass.config.components:
                yield from asyncio.sleep(1)
                _LOGGER.debug("initial component[%s]: wait for HA initialization.", setup_domain)

            if setup_domain in ['input_select', 'input_text', 'input_boolean']: 
                _LOGGER.debug("initial component[%s]: component is ready, use component's method.", setup_domain)
                
                entities = []
                for object_id, conf in VALIDATED_CONF.get(setup_domain, {}).items():
                    
                    if setup_domain == 'input_select':
                        
                        entity = InputSelect(object_id, conf.get(CONF_NAME, object_id), conf.get(CONF_INITIAL), conf.get(CONF_OPTIONS) or [], conf.get(CONF_ICON))
                    elif setup_domain == 'input_text':
                        
                        entity = InputText(object_id, conf.get(CONF_NAME, object_id), conf.get(CONF_INITIAL), conf.get(CONF_MIN), conf.get(CONF_MAX), conf.get(CONF_ICON), conf.get(ATTR_UNIT_OF_MEASUREMENT), conf.get(CONF_PATTERN), conf.get(CONF_MODE))
                    elif setup_domain == 'input_boolean':
                        
                        entity = InputBoolean(object_id, conf.get(CONF_NAME), conf.get(CONF_INITIAL), conf.get(CONF_ICON))
                        _LOGGER.debug("input_boolean.timer_button:%s,%s,%s,%s", object_id, conf.get(CONF_NAME), conf.get(CONF_INITIAL), conf.get(CONF_ICON))
                    else:
                        pass
                        
                    entities.append(entity)
                
                yield from hass.data[setup_domain].async_add_entities(entities)        
                _LOGGER.debug('initial component[%s]: entities added.', setup_domain)
            elif setup_domain in ['sensor']:   
                _LOGGER.debug("initial component.platform[%s]: component is ready, use custom method.", setup_domain)
                """
                for p_type, p_config in config_per_platform({setup_domain: VALIDATED_CONF.get(setup_domain, {})}, setup_domain): 
                    
                    key = (p_type, None, 'common_timer')
                    if '{}.{}'.format(setup_domain,p_type) in hass.config.components:
                        _LOGGER.debug("initial component.platform[%s]: platform is ready",p_type)
                        entities = []
                        for :
                            entity = SensorTemplate
                            entities.append(entity)                        
                        yield from hass.data[setup_domain]._platforms[PLATFORM_KEY]._async_schedule_add_entities(entities)
                    else:
                        _LOGGER.debug("initial component.platform[%s]: platform isn't ready",p_type)
                        yield from hass.data[setup_domain].async_setup(p_config)
                """
                yield from hass.data[setup_domain].async_setup({setup_domain: VALIDATED_CONF.get(setup_domain, {})})

                
                
                
                
                
                
                
                
                
            else:
                _LOGGER.debug("initial component[%s]: undefined initialize method.", setup_domain)

        
        else:
            _LOGGER.debug('initial component[%s]: config hasn\'t this componet , use HA\'s setup method to initialize entity.', setup_domain)
            hass.async_create_task(setup.async_setup_component(hass, setup_domain, VALIDATED_CONF))

    
    data = {
        ATTR_OBJECT_ID: COMMON_TIMER_CONF[CONF_NAME],
        ATTR_NAME: COMMON_TIMER_CONF[CONF_FRIENDLY_NAME],
        ATTR_ENTITIES: [entity_id for param, entity_id in ui.items()]
        }
    
    yield from hass.services.async_call('group', SERVICE_SET, data)
    
    _LOGGER.debug('---control planel initialized---')

    
    
    info_config = COMMON_TIMER_CONF.get(CONF_INFO_PANEL)
    if info_config:
        entities = []
        for num in range(1, info_config[CONF_INFO_NUM_MIN]):
            object_id = 'ct_row_{}'.format(num)
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
        _LOGGER.debug('---info planel initialized---')

    domains = COMMON_TIMER_CONF.get('domains', ['light', 'switch'])   
    exclude = COMMON_TIMER_CONF.get('exclude', [])        
    pattern = COMMON_TIMER_CONF.get('pattern', '.*')  
    exclude.append(ui['switch'])    
    common_timer = CommonTimer(domains, exclude, pattern, ui, hass, info_config)

    @callback
    def initial(event):
        _LOGGER.debug('start initialize.')
        common_timer.prepare()
        for key in hass.data['sensor']._platforms:
            _LOGGER.debug("sensor platforms:%s", key)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, initial)

    @callback
    def common_timer_handle(event):
        if event.data[ATTR_ENTITY_ID] == ui[UI_INPUT_DOMAIN]:
            
            common_timer.choose_domain(event.data['new_state'].as_dict()['state'])
        elif event.data[ATTR_ENTITY_ID] == ui[UI_INPUT_ENTITY]:
            
            common_timer.choose_entity(event.data['new_state'].as_dict()['state'])
        elif event.data[ATTR_ENTITY_ID] == ui[UI_INPUT_OPERATION]:
            
            common_timer.choose_operation(event.data['new_state'].as_dict()['state'])
        elif event.data[ATTR_ENTITY_ID] == ui[UI_INPUT_DURATION]:
            pass
            
            
        elif event.data[ATTR_ENTITY_ID] == ui[UI_SWITCH]:
            
            common_timer.switch(event.data['new_state'].as_dict()['state'])
        else:
            
            hass.async_add_job(common_timer.update_info_panel(event.data[ATTR_ENTITY_ID]))
    hass.bus.async_listen(EVENT_STATE_CHANGED, common_timer_handle)

    return True
    
class CommonTimer:
    def __init__(self, domains, exclude, pattern, ui, hass = None, info_config = None):
        self._domains = domains
        self._exclude = exclude
        self._pattern = pattern
        self._hass = hass
        self._ui = ui
        self._store = {}
        self._dic_friendly_name = {}                    
        self._dic_operation = {'on':'开','off':'关','开':'on','关':'off'}                            
        self._dic_icon = {'light': 'mdi:lightbulb', 'switch': 'mdi:toggle-switch', 'automation': 'mdi:playlist-play', 'script': 'mdi:script', 'input_boolean': 'mdi:toggle-switch'}
        self._domain = None
        self._entity_id = None
        self._queue = DelayQueue(hass, 60)   
        self._tasks = None
        self._tasks_ids = None
        self._info_config = info_config
        
    def prepare(self):
        pattern = re.compile(self._pattern)
        states = self._hass.states.async_all()
        

        for state in states:
            domain = state.domain
            object_id = state.object_id
            entity_id = '{}.{}'.format(domain, object_id)
            if domain not in self._domains or entity_id in self._exclude:
                pass
            else:
                friendly_name = state.name 
                if not self._pattern or pattern.search(friendly_name):
                    _LOGGER.debug("添加设备:{}({})".format(friendly_name, entity_id))
                    self._dic_friendly_name.setdefault(friendly_name, entity_id)
                    self._store.setdefault(domain,{}).setdefault(entity_id,{}).setdefault('friendly_name', friendly_name)
                    
                    
                    
                    self._store[domain][entity_id]['icon'] = self.get_attributes(entity_id).get('icon', self._dic_icon[domain])
                    self._store[domain][entity_id]['entity_id'] = entity_id
                    self._store[domain][entity_id]['duration'] = '0:00:00'
                    self._store[domain][entity_id]['remaining'] = '0:00:00'
                    self._store[domain][entity_id]['handle'] = None
                    self._store[domain][entity_id]['operation'] = 'on' if domain == 'autonmation' or domain == 'script' else 'off'    
                else:
                    _LOGGER.debug("忽略{}({})".format(friendly_name, entity_id))
        options= list(self._store.keys())
        options.insert(0,'请选择设备类型')
        data = {
            'entity_id':self._ui[UI_INPUT_DOMAIN],
            'options': options
        }
        self._hass.async_add_job(self._hass.services.async_call('input_select', SERVICE_SET_OPTIONS, data))
        async_track_time_change(self._hass, self.update)


    def choose_domain(self, domain):
        self._domain = domain
        if domain == '请选择设备类型':
            options = '请选择设备'
        else:
            options = [self.get_entity_map(entity_id)['friendly_name'] for entity_id in self._store[domain]]
            
            options.insert(0,'请选择设备')
            
            
            
            
            
            self.set_options(self._ui[UI_INPUT_ENTITY], options)
    
    def choose_entity(self, friendly_name):
        _LOGGER.debug("choose_entity: %s",friendly_name)
        if friendly_name == '请选择设备':
            self._entity_id = None
            self.set_state(self._ui[UI_INPUT_DURATION], state= '0:00:00')
            self.set_state(self._ui[UI_SWITCH], state = 'off')
        else:       
            entity_id = self._entity_id = self._dic_friendly_name.get(friendly_name, None)
            entity_map = self.get_entity_map(entity_id)
            if entity_map is None:
                _LOGGER.debug("Function choose_entity: friendly_name not found in dic !")
                return
            remaining_time = self._queue.get_remaining_time(entity_map['handle'])
            if remaining_time is not None:
                duration = str(remaining_time)
                self.set_state(self._ui[UI_INPUT_DURATION], state= duration)
                self.set_state(self._ui[UI_SWITCH], state = 'on')
            else:
                duration = entity_map['remaining'] if entity_map['remaining'] != '0:00:00' else entity_map['duration']
                self.set_state(self._ui[UI_INPUT_DURATION], state= duration)
                self.set_state(self._ui[UI_SWITCH], state = 'off')
            
            self.set_state(self._ui[UI_INPUT_OPERATION], state = self._dic_operation.get(entity_map['operation']))

    def choose_operation(self, operation):
        entity_map = self.get_entity_map(self._entity_id)
        if entity_map is None:
            _LOGGER.debug("no entity selected, pass.")
            return
        if  self.get_state(self._ui[UI_SWITCH]) == 'off':            
            entity_map['operation'] = self._dic_operation.get(operation)
    
    def switch(self, state):
        if self._domain != '请选择设备类型':
            entity_id = self._entity_id
            entity_map = self.get_entity_map(self._entity_id)
            if entity_map is None:
                _LOGGER.debug("未选择设备/未找到对应entity_id")
                self.set_state(self._ui[UI_SWITCH], state = 'off')
                return
            else:
                duration = self.get_state(self._ui[UI_INPUT_DURATION])
                if duration == '0:00:00':
                    return
                if state == 'on': 
                    if entity_map['handle'] is None:
                        if entity_map['remaining'] != duration: 
                            entity_map['duration'] = duration
                        operation = self._dic_operation.get(self.get_state(self._ui[UI_INPUT_OPERATION]))
                        entity_map['handle'] = self._queue.insert(entity_id, duration, self.handle_task, operation = operation)   
                        entity_map['operation'] = operation             
                        
                        entity_map['exec_time'] = datetime.now() + self._queue.get_remaining_time(entity_map['handle'])
                else:           
                    self._queue.remove(entity_map['handle'])
                    entity_map['handle'] = None
                    entity_map['remaining'] = duration  
        else:
            _LOGGER.debug("未选设备类型")
            self.set_state(self._ui[UI_SWITCH], state = 'off')
        _LOGGER.debug("---switch---")
        self._hass.async_add_job(self.update_info_panel)

    def get_entity_map(self, entity_id):
        if entity_id is None:
            return None
        domain = entity_id.split('.')[0]
        if self._store.get(domain, None) is not None:
            return self._store.get(domain, None).get(entity_id, None)
        else:
            return None
    
    def get_state(self, entity_id):
        return self._hass.states.get(entity_id).as_dict()['state']
    def get_attributes(self, entity_id):
        return self._hass.states.get(entity_id).as_dict()['attributes']

    def set_state(self, entity_id, state = None, service = None ):
        _LOGGER.debug("handle set_state(): entity_id= {}, state= {}, service = {}".format(entity_id, state, service))
        domain = entity_id.split('.')[0]
        if domain == 'input_text':
            self._hass.async_add_job(self._hass.services.async_call(domain, SERVICE_SET_VALUE, {'entity_id': entity_id, 'value': state}))
        elif domain == 'input_select':
            self._hass.async_add_job(self._hass.services.async_call(domain, SERVICE_SELECT_OPTION, {'entity_id': entity_id,'option': state}))
        elif domain == 'input_boolean':
            if state == 'on':
                self._hass.async_add_job(self._hass.services.async_call(domain, SERVICE_TURN_ON, {'entity_id': entity_id}))
            elif state == 'off':
                self._hass.async_add_job(self._hass.services.async_call(domain, SERVICE_TURN_OFF, {'entity_id': entity_id}))
        elif domain in ['switch', 'light', 'automation', 'script']:
            self._hass.async_add_job(self._hass.services.async_call(domain, service, {'entity_id': entity_id}))
    
    def set_options(self, entity_id, options):
        domain = entity_id.split('.')[0]
        if domain != 'input_select':
            _LOGGER.debug('wrong service')
            return
        self._hass.async_add_job(self._hass.services.async_call(domain, SERVICE_SET_OPTIONS, {'entity_id': entity_id,'options': options}))

    
    @callback
    def update(self, time):
        
        
        
        self._queue.read()
        
        
        
        if self.get_state(self._ui[UI_SWITCH]) == 'on':
            entity_id = self._entity_id
            if entity_id is None:
                _LOGGER.debug("Function task: friendly_name(%s) not found in dic !", entity_id)
                return
            entity_map = self.get_entity_map(entity_id)
            remaining_time = self._queue.get_remaining_time(entity_map['handle'])
            
            if remaining_time is None:
                remaining_time = entity_map['remaining']
                if remaining_time == '0:00:00':
                    self.set_state(self._ui[UI_INPUT_DURATION], state = entity_map['duration'])
                else:
                    self.set_state(self._ui[UI_INPUT_DURATION], state = str(remaining_time))
                self.set_state(self._ui[UI_SWITCH], state = 'off')
            else:
                self.set_state(self._ui[UI_INPUT_DURATION], state = str(remaining_time))
    
    
    def handle_task(self, entity_id, operation, **kwargs):
        
        domain = entity_id.split('.')[0]
        _LOGGER.debug("handle_task: entity_id=%s.", entity_id)
        entity_map = self.get_entity_map(entity_id)
        entity_map['handle'] = None
        entity_map['remaining'] = '0:00:00'             

        if operation == 'custom':
            
            pass
        else:
            service = 'turn_'+operation
            state = operation
            self.set_state(entity_id, state = state, service = service)
            _LOGGER.debug("handle_task finish:{}({})".format(service,entity_id))
        
        
        self._hass.async_add_job(self.update_info_panel)
    def long_time_task(self):
        
        _LOGGER.debug("handle long time task, start")
        time.sleep(5)
        _LOGGER.debug("handle long time task, finish")
    
    def get_row(self, entity_id):
        
        if entity_id is None or self._tasks_ids is None:
            return None
        try:
            row = self._tasks_ids.index(entity_id)
            return row
        except ValueError:
            return None

    @asyncio.coroutine
    def update_info_panel(self, entity_id = None):
        info_config = self._info_config
        if info_config is None:
            return
        _LOGGER.debug("-----------update_info_panel()------------")

        if entity_id:
            row = self.get_row(entity_id)
            if row is not None:  
                _LOGGER.debug("%s状态被改变，进行更新(at row %s)",entity_id,row)
                info_entity_id = 'sensor.ct_row_{}'.format(row)
                info_entity = self._hass.data['sensor'].get_entity(info_entity_id)
                info2 = Template('{} -> {}'.format(self.get_state(self._tasks[row]['entity_id']), self._tasks[row]['operation']))
                info2.hass = self._hass
                info_entity._template = info2
                info_entity.async_schedule_update_ha_state(True)
            else:
                pass
                _LOGGER.debug("%s不在任务列表%s中，忽略",entity_id,self._tasks_ids)
            return

        tasks = [attrs for entities in self._store.values() for entity_id, attrs in entities.items() if attrs['handle'] is not None]
        sorted_tasks = sorted(tasks, key=operator.itemgetter('exec_time'))
        info_row_num = len(sorted_tasks) if len(sorted_tasks) < info_config[CONF_INFO_NUM_MAX] else info_config[CONF_INFO_NUM_MAX]
        info_entities = []
        info_ui = []
        default_state = Template('-')
        default_state.hass = self._hass
        default_icon = Template('mdi:calendar-check')
        default_icon.hass = self._hass
        for row in range(0, info_config[CONF_INFO_NUM_MAX]):
            info_entity_id = 'sensor.ct_row_{}'.format(row)
            info_entity = self._hass.data['sensor'].get_entity(info_entity_id)
            if row < info_row_num:
                _LOGGER.debug("info_entity:%s, row=%s",info_entity, row)
                
                info1 = '{}{}'.format(align(sorted_tasks[row]['friendly_name'],28), align(sorted_tasks[row]['exec_time'].strftime("%Y-%m-%d %H:%M:%S"),20))
                info2 = Template('{} -> {}'.format(self.get_state(sorted_tasks[row]['entity_id']), sorted_tasks[row]['operation']))
                info2.hass = self._hass
                
                info3 = Template(sorted_tasks[row]['icon'])
                info3.hass = self._hass
                if info_entity is not None:
                    _LOGGER.debug("row%s, exist. info_entity_id=%s",row,info_entity_id)
                    info_entity._name = info1
                    info_entity._template = info2
                    info_entity._icon_template = info3
                    info_entity.async_schedule_update_ha_state(True)
                else:
                    
                    object_id = 'ct_row_{}'.format(row)
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
                    info_entities.append(sensor)
                info_ui.append(info_entity_id)
            else:
                if not any([info_row_num, row]) or row < info_config[CONF_INFO_NUM_MIN] or info_config[CONF_INFO_NUM_MAX] == info_config[CONF_INFO_NUM_MIN]:
                    info1 = '无定时任务'
                    info_entity._name = info1
                    info_entity._template = default_state
                    info_entity._icon_template = default_icon
                    info_entity.async_schedule_update_ha_state(True)
                    info_ui.append(info_entity_id)
                else:
                    yield from self._hass.data['sensor'].async_remove_entity(info_entity_id)
        if info_entities:
            _LOGGER.debug("info: add entities")
            yield from self._hass.data['sensor']._platforms[PLATFORM_KEY].async_add_entities(info_entities, update_before_add = True)

        data = {
            ATTR_OBJECT_ID: info_config[CONF_NAME],
            ATTR_NAME: info_config[CONF_FRIENDLY_NAME],
            ATTR_ENTITIES: [entity_id for entity_id in info_ui]
            }
        self._info_ui = info_ui
        self._tasks = sorted_tasks
        self._tasks_ids = [entity['entity_id'] for entity in self._tasks[0:info_row_num]]
        _LOGGER.debug("info: update group:%s",data)
        yield from self._hass.services.async_call('group', SERVICE_SET, data)

class DelayQueue(object):
    __current_slot = 1

    def __init__(self, hass, slots_per_loop, **kwargs):
        self.__slots_per_loop = slots_per_loop
        self.__queue = [[] for i in range(slots_per_loop)]
        self._hass = hass
    
    def insert(self, task_id, duration, callback, operation = 'turn_off', **kwargs):
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
        if delayQueueTask is not None:
            _LOGGER.debug("remove task in slot {}.".format(delayQueueTask.slot))
            self.__queue[delayQueueTask.slot].remove(delayQueueTask)
        else:
            _LOGGER.debug("remove task, but not found.")

    
    def get_remaining_time(self, delayQueueTask):
        if delayQueueTask:
            if self.__current_slot - 1 > delayQueueTask.slot and self.__current_slot - 1 < 60:
                second = self.__slots_per_loop * (delayQueueTask.loop + 1) + delayQueueTask.slot - (self.__current_slot - 1)
            else:
                second = self.__slots_per_loop * delayQueueTask.loop + delayQueueTask.slot - (self.__current_slot - 1)
            return timedelta(seconds = second)
        else:
            return None
    
    
    def read(self):
        if len(self.__queue) >= self.__current_slot:
            tasks = self.__queue[self.__current_slot - 1]
            
            if tasks:
                executed_task = []
                for task in tasks:
                    _LOGGER.debug("===task:{}, loop:{}/{}, should_execute:{}===".format(task.task_id, task.slot, task.loop, task.should_exec))
                    if task.should_exec:
                        
                        task.exec_task()
                        
                        executed_task.append(task)
                    else:
                        task.nextLoop()
                for task in executed_task:
                    
                    tasks.remove(task)  
            self.__current_slot += 1
            if self.__current_slot > len(self.__queue):
                self.__current_slot = 1

class DelayQueueTask(object):
    def __init__(self, task_id, operation:str = 'turn_off', slot:int = 0 , loop:int = 0 , exec_task = None, **kwargs):
        self._task_id = task_id
        self._operation = operation
        self._slot = int(slot)
        self._loop = int(loop)
        self._exec_task = exec_task
        self._kwargs = kwargs

    @property
    def slot(self) -> int:
        return int(self._slot)

    @property
    def loop(self) -> int:
        return int(self._loop)

    @property
    def task_id(self):
        return self._task_id

    @property
    def operation(self):
        return self._operation

    def nextLoop(self):
        self._loop -= 1

    @property
    def should_exec(self) -> bool:
        if self._loop == 0:
            return True
        else:
            return False
    
    
    def exec_task(self):
        
        self._exec_task(self._task_id, self._operation, kwargs = self._kwargs)


def is_chinese(uchar):

    """判断一个unicode是否是汉字"""

    if uchar >= u'\u4e00' and uchar <= u'\u9fa5':

        return True

    else:

        return False

 

def align( text, width, just = "left" ):  
    utext = stext = str(text)
    
    cn_count = 0
    for u in utext:
        if is_chinese(u):
            cn_count += 2 
        else:
            cn_count += 1  
    num =int( (width - cn_count) / 2 )
    blank =int( (width - cn_count) % 2)
    if just == "right":
        return chr(12288) * num + " " * blank + stext
    elif just == "left":
        return stext + " " * blank + chr(12288) * num

def string_ljust( text, width ):
    return align( text, width, "left" )

def string_rjust( text, width ):
    return align( text, width, "right" )
