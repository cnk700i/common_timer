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
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, CONF_ICON, CONF_NAME, CONF_MODE, EVENT_HOMEASSISTANT_START, EVENT_STATE_CHANGED, SERVICE_SELECT_OPTION, SERVICE_TURN_ON, SERVICE_TURN_OFF)

from homeassistant.helpers.config_validation import time_period_str
from datetime import datetime,timedelta
from homeassistant.helpers.event import async_track_time_change

from homeassistant.util.async_ import (
    run_coroutine_threadsafe, run_callback_threadsafe)

import time
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

CONF_DOMAINS = 'domains'
CONF_EXCLUDE = 'exclude'
CONF_PATTERN = 'pattern'

ATTR_OBJECT_ID = 'object_id'
ATTR_NAME ='name'
ATTR_ENTITIES = 'entities'

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
        'group':
        {
            'common_timer':
            {
                'name': '通用定时器',
                'entities': ['input_select.domain', 'input_select.entity', 'input_select.operation']
            }
        }
    },
    
    'domains': ['light', 'switch', 'script', 'automation'],
    'exclude': [],
    # 'pattern': '[\u4e00-\u9fa5]+',
}
@asyncio.coroutine
def async_setup(hass, config):
    ui ={}    

    
    
    VALIDATED_CONF = COMMON_TIMER_CONF[CONF_ENTITIES]
    for domain in VALIDATED_CONF:
        for object_id in VALIDATED_CONF[domain]:
            if CONF_USE_FOR in VALIDATED_CONF[domain][object_id]:
                user_for = VALIDATED_CONF[domain][object_id][CONF_USE_FOR]
                ui[user_for] = '{}.{}'.format(domain, object_id)
                VALIDATED_CONF[domain][object_id].pop(CONF_USE_FOR)

    components = set(key.split(' ')[0] for key in config.keys())
    
    for setup_domain in ['input_select', 'input_text', 'input_boolean']:
        
        if setup_domain in components: 
            
            setup_tasks = hass.data.get('setup_tasks')
            if setup_tasks is not None and setup_domain in setup_tasks:
                _LOGGER.debug("wait for HA initial %s component.", setup_domain)
                yield from setup_tasks[setup_domain]
            
            entities = []
            for object_id, conf in VALIDATED_CONF.get(setup_domain, {}).items():
                _LOGGER.debug("initializing %s.%s", setup_domain, object_id)
                if setup_domain == 'input_select':
                    
                    entity = InputSelect(object_id, conf.get(CONF_NAME, object_id), conf.get(CONF_INITIAL), conf.get(CONF_OPTIONS) or [], conf.get(CONF_ICON))
                elif setup_domain == 'input_text':
                    
                    entity = InputText(object_id, conf.get(CONF_NAME, object_id), conf.get(CONF_INITIAL), conf.get(CONF_MIN), conf.get(CONF_MAX), conf.get(CONF_ICON), conf.get(ATTR_UNIT_OF_MEASUREMENT), conf.get(CONF_PATTERN), conf.get(CONF_MODE))
                else:
                    
                    entity = InputBoolean(object_id, conf.get(CONF_NAME), conf.get(CONF_INITIAL), conf.get(CONF_ICON))
                    _LOGGER.debug("input_boolean.timer_button:%s,%s,%s,%s", object_id, conf.get(CONF_NAME), conf.get(CONF_INITIAL), conf.get(CONF_ICON))
                entities.append(entity)
            _LOGGER.debug("entities:%s", entities)
            yield from hass.data[setup_domain].async_add_entities(entities)        
            _LOGGER.debug('add entity in %s component.', setup_domain)          
        
        else:
            hass.async_create_task(setup.async_setup_component(hass, setup_domain, VALIDATED_CONF))
            _LOGGER.debug('setup %s component.', setup_domain)
    
    data = {
        ATTR_OBJECT_ID: 'common_timer',
        ATTR_NAME: '通用定时器',
        ATTR_ENTITIES: [entity_id for param, entity_id in ui.items()]
        }
    
    yield from hass.services.async_call('group', SERVICE_SET, data)
    
    _LOGGER.debug('add group.')

    domains = COMMON_TIMER_CONF.get('domains', ['light', 'switch'])   
    exclude = COMMON_TIMER_CONF.get('exclude', [])        
    pattern = COMMON_TIMER_CONF.get('pattern', '.*')  
    exclude.append(ui['switch'])    
    common_timer = CommonTimer(domains, exclude, pattern, ui, hass)

    @callback
    def initial(event):
        _LOGGER.debug('start initialize.')
        common_timer.prepare()
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
    hass.bus.async_listen(EVENT_STATE_CHANGED, common_timer_handle)

    return True
    
class CommonTimer:
    def __init__(self, domains, exclude, pattern, ui, hass = None):
        self._domains = domains
        self._exclude = exclude
        self._pattern = pattern
        self._hass = hass
        self._ui = ui
        self._store = {}
        self._dic_friendly_name = {}                    
        self._dic_operation = {'turn_on':'开','turn_off':'关','开':'turn_on','关':'turn_off'}                            
        self._domain = None
        self._entity_id = None
        self._queue = DelayQueue(hass, 60)   
        
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
                    _LOGGER.debug("添加{}({})".format(friendly_name, entity_id))
                    self._dic_friendly_name.setdefault(friendly_name, entity_id)
                    self._store.setdefault(domain,{}).setdefault(entity_id,{}).setdefault('friendly_name', friendly_name)
                    self._store[domain][entity_id]['duration'] = '0:00:00'
                    self._store[domain][entity_id]['remaining'] = '0:00:00'
                    self._store[domain][entity_id]['handle'] = None
                    self._store[domain][entity_id]['operation'] = 'turn_on' if domain == 'autonmation' or domain == 'script' else 'turn_off'    
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
                duration = remaining_time
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
                else:           
                    self._queue.remove(entity_map['handle'])
                    entity_map['handle'] = None
                    entity_map['remaining'] = duration  
        else:
            _LOGGER.debug("未选设备类型")
            self.set_state(self._ui[UI_SWITCH], state = 'off')

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
    
    def set_state(self, entity_id, state = None, service = None):
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
                    self.set_state(self._ui[UI_INPUT_DURATION], state = remaining_time)
                self.set_state(self._ui[UI_SWITCH], state = 'off')
            else:
                self.set_state(self._ui[UI_INPUT_DURATION], state = remaining_time)
    
    
    def handle_task(self, entity_id, operation, **kwargs):
        
        domain = entity_id.split('.')[0]
        entity_map = self.get_entity_map(entity_id)
        entity_map['handle'] = None
        entity_map['remaining'] = '0:00:00'             

        if operation == 'custom':            
            pass
        else:
            service_name = domain+'.'+operation
            self.set_state(entity_id, service = operation)
            _LOGGER.debug("handle_task finish:{}({})".format(service_name,entity_id))        
        # self._hass.async_add_job(self.long_time_task)

    def long_time_task(self):
        """ 测试用的 """
        _LOGGER.debug("handle long time task, start")
        time.sleep(5)
        _LOGGER.debug("handle long time task, finish")

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
        _LOGGER.debug("remove task!!!")
        if delayQueueTask is not None:
            _LOGGER.debug("remove task in slot {}".format(delayQueueTask.slot))
            self.__queue[delayQueueTask.slot].remove(delayQueueTask)

    
    def get_remaining_time(self, delayQueueTask):
        if delayQueueTask:
            if self.__current_slot - 1 > delayQueueTask.slot and self.__current_slot - 1 < 60:
                second = self.__slots_per_loop * (delayQueueTask.loop + 1) + delayQueueTask.slot - (self.__current_slot - 1)
            else:
                second = self.__slots_per_loop * delayQueueTask.loop + delayQueueTask.slot - (self.__current_slot - 1)
            return str(timedelta(seconds = second))
        else:
            return None
    
    
    def read(self):
        if len(self.__queue) >= self.__current_slot:
            tasks = self.__queue[self.__current_slot - 1]
            _LOGGER.debug("current slot：{}(has {} tasks)".format(self.__current_slot - 1,len(tasks)))
            if tasks:
                executed_task = []
                for task in tasks:
                    _LOGGER.debug("task info:{}/{},should_execute:{}".format(task.slot, task.loop, task.should_exec))
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
