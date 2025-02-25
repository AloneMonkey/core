"""Support for MySensors sensors."""
from __future__ import annotations

from awesomeversion import AwesomeVersion

from homeassistant.components import mysensors
from homeassistant.components.sensor import DOMAIN, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONDUCTIVITY,
    DEGREE,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    ELECTRIC_POTENTIAL_MILLIVOLT,
    ELECTRICAL_CURRENT_AMPERE,
    ELECTRICAL_VOLT_AMPERE,
    ENERGY_KILO_WATT_HOUR,
    FREQUENCY_HERTZ,
    LENGTH_METERS,
    LIGHT_LUX,
    MASS_KILOGRAMS,
    PERCENTAGE,
    POWER_WATT,
    SOUND_PRESSURE_DB,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    VOLT,
    VOLUME_CUBIC_METERS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MYSENSORS_DISCOVERY, DiscoveryInfo
from .helpers import on_unload

SENSORS: dict[str, list[str | None] | dict[str, list[str | None]]] = {
    "V_TEMP": [None, None, DEVICE_CLASS_TEMPERATURE],
    "V_HUM": [PERCENTAGE, "mdi:water-percent", DEVICE_CLASS_HUMIDITY],
    "V_DIMMER": [PERCENTAGE, "mdi:percent", None],
    "V_PERCENTAGE": [PERCENTAGE, "mdi:percent", None],
    "V_PRESSURE": [None, "mdi:gauge", None],
    "V_FORECAST": [None, "mdi:weather-partly-cloudy", None],
    "V_RAIN": [None, "mdi:weather-rainy", None],
    "V_RAINRATE": [None, "mdi:weather-rainy", None],
    "V_WIND": [None, "mdi:weather-windy", None],
    "V_GUST": [None, "mdi:weather-windy", None],
    "V_DIRECTION": [DEGREE, "mdi:compass", None],
    "V_WEIGHT": [MASS_KILOGRAMS, "mdi:weight-kilogram", None],
    "V_DISTANCE": [LENGTH_METERS, "mdi:ruler", None],
    "V_IMPEDANCE": ["ohm", None, None],
    "V_WATT": [POWER_WATT, None, None],
    "V_KWH": [ENERGY_KILO_WATT_HOUR, None, None],
    "V_LIGHT_LEVEL": [PERCENTAGE, "mdi:white-balance-sunny", None],
    "V_FLOW": [LENGTH_METERS, "mdi:gauge", None],
    "V_VOLUME": [f"{VOLUME_CUBIC_METERS}", None, None],
    "V_LEVEL": {
        "S_SOUND": [SOUND_PRESSURE_DB, "mdi:volume-high", None],
        "S_VIBRATION": [FREQUENCY_HERTZ, None, None],
        "S_LIGHT_LEVEL": [LIGHT_LUX, "mdi:white-balance-sunny", None],
    },
    "V_VOLTAGE": [VOLT, "mdi:flash", None],
    "V_CURRENT": [ELECTRICAL_CURRENT_AMPERE, "mdi:flash-auto", None],
    "V_PH": ["pH", None, None],
    "V_ORP": [ELECTRIC_POTENTIAL_MILLIVOLT, None, None],
    "V_EC": [CONDUCTIVITY, None, None],
    "V_VAR": ["var", None, None],
    "V_VA": [ELECTRICAL_VOLT_AMPERE, None, None],
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up this platform for a specific ConfigEntry(==Gateway)."""

    async def async_discover(discovery_info: DiscoveryInfo) -> None:
        """Discover and add a MySensors sensor."""
        mysensors.setup_mysensors_platform(
            hass,
            DOMAIN,
            discovery_info,
            MySensorsSensor,
            async_add_entities=async_add_entities,
        )

    on_unload(
        hass,
        config_entry.entry_id,
        async_dispatcher_connect(
            hass,
            MYSENSORS_DISCOVERY.format(config_entry.entry_id, DOMAIN),
            async_discover,
        ),
    )


class MySensorsSensor(mysensors.device.MySensorsEntity, SensorEntity):
    """Representation of a MySensors Sensor child node."""

    @property
    def force_update(self) -> bool:
        """Return True if state updates should be forced.

        If True, a state change will be triggered anytime the state property is
        updated, not just when the value changes.
        """
        return True

    @property
    def state(self) -> str | None:
        """Return the state of this entity."""
        return self._values.get(self.value_type)

    @property
    def device_class(self) -> str | None:
        """Return the device class of this entity."""
        return self._get_sensor_type()[2]

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend, if any."""
        return self._get_sensor_type()[1]

    @property
    def unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of this entity."""
        set_req = self.gateway.const.SetReq
        if (
            AwesomeVersion(self.gateway.protocol_version) >= AwesomeVersion("1.5")
            and set_req.V_UNIT_PREFIX in self._values
        ):
            custom_unit: str = self._values[set_req.V_UNIT_PREFIX]
            return custom_unit

        if set_req(self.value_type) == set_req.V_TEMP:
            if self.hass.config.units.is_metric:
                return TEMP_CELSIUS
            return TEMP_FAHRENHEIT

        unit = self._get_sensor_type()[0]
        return unit

    def _get_sensor_type(self) -> list[str | None]:
        """Return list with unit and icon of sensor type."""
        pres = self.gateway.const.Presentation
        set_req = self.gateway.const.SetReq

        _sensor_type = SENSORS.get(set_req(self.value_type).name, [None, None, None])
        if isinstance(_sensor_type, dict):
            sensor_type = _sensor_type.get(
                pres(self.child_type).name, [None, None, None]
            )
        else:
            sensor_type = _sensor_type
        return sensor_type
