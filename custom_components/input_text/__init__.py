"""Support to enter a value into a text box."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.const import (
    ATTR_EDITABLE,
    ATTR_MODE,
    CONF_ICON,
    CONF_ID,
    CONF_MODE,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    SERVICE_RELOAD,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import collection
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
import homeassistant.helpers.service
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType, ServiceCallType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "input_text"

CONF_INITIAL = "initial"
CONF_MIN = "min"
CONF_MIN_VALUE = 0
CONF_MAX = "max"
CONF_MAX_VALUE = 100
CONF_PATTERN = "pattern"
CONF_VALUE = "value"

MODE_TEXT = "text"
MODE_PASSWORD = "password"

ATTR_VALUE = CONF_VALUE
ATTR_MIN = "min"
ATTR_MAX = "max"
ATTR_PATTERN = CONF_PATTERN

SERVICE_SET_VALUE = "set_value"
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

CREATE_FIELDS = {
    vol.Required(CONF_NAME): vol.All(str, vol.Length(min=1)),
    vol.Optional(CONF_MIN, default=CONF_MIN_VALUE): vol.Coerce(int),
    vol.Optional(CONF_MAX, default=CONF_MAX_VALUE): vol.Coerce(int),
    vol.Optional(CONF_INITIAL, ""): cv.string,
    vol.Optional(CONF_ICON): cv.icon,
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    vol.Optional(CONF_PATTERN): cv.string,
    vol.Optional(CONF_MODE, default=MODE_TEXT): vol.In([MODE_TEXT, MODE_PASSWORD]),
}
UPDATE_FIELDS = {
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_MIN): vol.Coerce(int),
    vol.Optional(CONF_MAX): vol.Coerce(int),
    vol.Optional(CONF_INITIAL): cv.string,
    vol.Optional(CONF_ICON): cv.icon,
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    vol.Optional(CONF_PATTERN): cv.string,
    vol.Optional(CONF_MODE): vol.In([MODE_TEXT, MODE_PASSWORD]),
}


def _cv_input_text(cfg):
    """Configure validation helper for input box (voluptuous)."""
    minimum = cfg.get(CONF_MIN)
    maximum = cfg.get(CONF_MAX)
    if minimum > maximum:
        raise vol.Invalid(
            f"Max len ({minimum}) is not greater than min len ({maximum})"
        )
    state = cfg.get(CONF_INITIAL)
    if state is not None and (len(state) < minimum or len(state) > maximum):
        raise vol.Invalid(
            f"Initial value {state} length not in range {minimum}-{maximum}"
        )
    return cfg


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: cv.schema_with_slug_keys(
            vol.All(
                lambda value: value or {},
                {
                    vol.Optional(CONF_NAME): cv.string,
                    vol.Optional(CONF_MIN, default=CONF_MIN_VALUE): vol.Coerce(int),
                    vol.Optional(CONF_MAX, default=CONF_MAX_VALUE): vol.Coerce(int),
                    vol.Optional(CONF_INITIAL, ""): cv.string,
                    vol.Optional(CONF_ICON): cv.icon,
                    vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
                    vol.Optional(CONF_PATTERN): cv.string,
                    vol.Optional(CONF_MODE, default=MODE_TEXT): vol.In(
                        [MODE_TEXT, MODE_PASSWORD]
                    ),
                },
                _cv_input_text,
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)
RELOAD_SERVICE_SCHEMA = vol.Schema({})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up an input text."""
    component = hass.data[DOMAIN] = EntityComponent(_LOGGER, DOMAIN, hass)
    id_manager = collection.IDManager()

    yaml_collection = collection.YamlCollection(
        logging.getLogger(f"{__name__}.yaml_collection"), id_manager
    )
    collection.sync_entity_lifecycle(
        hass, DOMAIN, DOMAIN, component, yaml_collection, InputText.from_yaml
    )

    storage_collection = InputTextStorageCollection(
        Store(hass, STORAGE_VERSION, STORAGE_KEY),
        logging.getLogger(f"{__name__}.storage_collection"),
        id_manager,
    )
    collection.sync_entity_lifecycle(
        hass, DOMAIN, DOMAIN, component, storage_collection, InputText
    )

    await yaml_collection.async_load(
        [{CONF_ID: id_, **(conf or {})} for id_, conf in config.get(DOMAIN, {}).items()]
    )
    await storage_collection.async_load()

    collection.StorageCollectionWebsocket(
        storage_collection, DOMAIN, DOMAIN, CREATE_FIELDS, UPDATE_FIELDS
    ).async_setup(hass)

    async def reload_service_handler(service_call: ServiceCallType) -> None:
        """Reload yaml entities."""
        conf = await component.async_prepare_reload(skip_reset=True)
        if conf is None:
            conf = {DOMAIN: {}}
        await yaml_collection.async_load(
            [{CONF_ID: id_, **(cfg or {})} for id_, cfg in conf.get(DOMAIN, {}).items()]
        )

    homeassistant.helpers.service.async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        reload_service_handler,
        schema=RELOAD_SERVICE_SCHEMA,
    )

    component.async_register_entity_service(
        SERVICE_SET_VALUE, {vol.Required(ATTR_VALUE): cv.string}, "async_set_value"
    )

    return True


class InputTextStorageCollection(collection.StorageCollection):
    """Input storage based collection."""

    CREATE_SCHEMA = vol.Schema(vol.All(CREATE_FIELDS, _cv_input_text))
    UPDATE_SCHEMA = vol.Schema(UPDATE_FIELDS)

    async def _process_create_data(self, data: dict) -> dict:
        """Validate the config is valid."""
        return self.CREATE_SCHEMA(data)

    @callback
    def _get_suggested_id(self, info: dict) -> str:
        """Suggest an ID based on the config."""
        return info[CONF_NAME]

    async def _update_data(self, data: dict, update_data: dict) -> dict:
        """Return a new updated data object."""
        update_data = self.UPDATE_SCHEMA(update_data)
        return _cv_input_text({**data, **update_data})


class InputText(RestoreEntity):
    """Represent a text box."""

    def __init__(self, config: dict):
        """Initialize a text input."""
        self._config = config
        self.editable = True
        self._current_value = config.get(CONF_INITIAL)

    @classmethod
    def from_yaml(cls, config: dict) -> InputText:
        """Return entity instance initialized from yaml storage."""
        input_text = cls(config)
        input_text.entity_id = f"{DOMAIN}.{config[CONF_ID]}"
        input_text.editable = False
        return input_text

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return the name of the text input entity."""
        return self._config.get(CONF_NAME)

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._config.get(CONF_ICON)

    @property
    def _maximum(self) -> int:
        """Return max len of the text."""
        return self._config[CONF_MAX]

    @property
    def _minimum(self) -> int:
        """Return min len of the text."""
        return self._config[CONF_MIN]

    @property
    def state(self):
        """Return the state of the component."""
        return self._current_value

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._config.get(CONF_UNIT_OF_MEASUREMENT)

    @property
    def unique_id(self) -> str | None:
        """Return unique id for the entity."""
        return self._config[CONF_ID]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_EDITABLE: self.editable,
            ATTR_MIN: self._minimum,
            ATTR_MAX: self._maximum,
            ATTR_PATTERN: self._config.get(CONF_PATTERN),
            ATTR_MODE: self._config[CONF_MODE],
        }

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        if self._current_value is not None:
            return

        state = await self.async_get_last_state()
        value = state and state.state

        # Check against None because value can be 0
        if value is not None and self._minimum <= len(value) <= self._maximum:
            self._current_value = value

    async def async_set_value(self, value):
        """Select new value."""
        if len(value) < self._minimum or len(value) > self._maximum:
            _LOGGER.warning(
                "Invalid value: %s (length range %s - %s)",
                value,
                self._minimum,
                self._maximum,
            )
            return
        self._current_value = value
        self.async_write_ha_state()

    async def async_update_config(self, config: dict) -> None:
        """Handle when the config is updated."""
        self._config = config
        self.async_write_ha_state()
