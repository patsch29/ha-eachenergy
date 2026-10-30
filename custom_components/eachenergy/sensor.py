"""Sensors for the Each Energy inverter."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EachEnergyCoordinator
from .const import DOMAIN

Data = dict[int, bytes]


def _raw(d: Data, cmd: int, pos: int, length: int, signed: bool = False) -> int | None:
    """Read a big-endian field; pos is the 1-based byte number from the protocol document."""
    frame = d.get(cmd)
    if frame is None or len(frame) < pos - 1 + length:
        return None
    return int.from_bytes(frame[pos - 1 : pos - 1 + length], "big", signed=signed)


def field(cmd: int, pos: int, length: int, scale: float = 1, signed: bool = False) -> Callable[[Data], Any]:
    def fn(d: Data):
        v = _raw(d, cmd, pos, length, signed)
        return None if v is None else round(v * scale, 3)

    return fn


def total(*fns: Callable[[Data], Any], factor: float = 1) -> Callable[[Data], Any]:
    def fn(d: Data):
        vals = [f(d) for f in fns]
        return None if any(v is None for v in vals) else round(sum(vals) * factor, 3)

    return fn


INVERTER_STATE = {0: "ready", 1: "running", 2: "warning", 3: "fault", 4: "updating", 5: "off_grid", 7: "ac_coupling"}
BATTERY_STATE = {0: "idle", 1: "charging", 2: "discharging", 3: "standby", 4: "no_battery"}


def inverter_state(d: Data):
    v = _raw(d, 0x02, 8, 2)
    return None if v is None else INVERTER_STATE.get(v, "other")


def battery_state(d: Data):
    v = _raw(d, 0xB0, 8, 2)
    if v is None:
        return None
    v &= 0x07
    return BATTERY_STATE.get(v, "no_battery")


@dataclass(frozen=True, kw_only=True)
class EESensorDescription(SensorEntityDescription):
    value_fn: Callable[[Data], Any]


W, KWH, WH = UnitOfPower.WATT, UnitOfEnergy.KILO_WATT_HOUR, UnitOfEnergy.WATT_HOUR
V, A, HZ, C = (
    UnitOfElectricPotential.VOLT,
    UnitOfElectricCurrent.AMPERE,
    UnitOfFrequency.HERTZ,
    UnitOfTemperature.CELSIUS,
)
MEAS, TOTAL_INC = SensorStateClass.MEASUREMENT, SensorStateClass.TOTAL_INCREASING
DIAG = EntityCategory.DIAGNOSTIC


def power(key, fn, **kw):
    return EESensorDescription(key=key, translation_key=key, value_fn=fn, native_unit_of_measurement=W,
                               device_class=SensorDeviceClass.POWER, state_class=MEAS, **kw)


def energy(key, fn, **kw):
    return EESensorDescription(key=key, translation_key=key, value_fn=fn, native_unit_of_measurement=KWH,
                               device_class=SensorDeviceClass.ENERGY, state_class=TOTAL_INC,
                               suggested_display_precision=2, **kw)


def voltage(key, fn, **kw):
    return EESensorDescription(key=key, translation_key=key, value_fn=fn, native_unit_of_measurement=V,
                               device_class=SensorDeviceClass.VOLTAGE, state_class=MEAS, **kw)


def current(key, fn, **kw):
    return EESensorDescription(key=key, translation_key=key, value_fn=fn, native_unit_of_measurement=A,
                               device_class=SensorDeviceClass.CURRENT, state_class=MEAS, **kw)


def temperature(key, fn, **kw):
    return EESensorDescription(key=key, translation_key=key, value_fn=fn, native_unit_of_measurement=C,
                               device_class=SensorDeviceClass.TEMPERATURE, state_class=MEAS, **kw)


PV_POWER = [field(0x34, 12 + i * 8, 4, 0.1) for i in range(3)]
GRID_FEED = [field(0x09, 8 + i * 6, 4, 0.1, True) for i in range(3)]  # + Einspeisung / - Bezug

SENSORS: tuple[EESensorDescription, ...] = (
    # Status
    EESensorDescription(key="inverter_state", translation_key="inverter_state", value_fn=inverter_state,
                        device_class=SensorDeviceClass.ENUM,
                        options=[*INVERTER_STATE.values(), "other"]),
    temperature("inverter_temperature", field(0x02, 32, 2, 0.1, True)),
    temperature("heatsink_temperature", field(0x02, 34, 2, 0.1, True), entity_category=DIAG),
    EESensorDescription(key="iso", translation_key="iso", value_fn=field(0x02, 30, 2),
                        native_unit_of_measurement="kΩ", state_class=MEAS, entity_category=DIAG),
    EESensorDescription(key="output_limit", translation_key="output_limit", value_fn=field(0x02, 12, 2, 0.01),
                        native_unit_of_measurement=PERCENTAGE, state_class=MEAS, entity_category=DIAG),
    EESensorDescription(key="warning_code", translation_key="warning_code", value_fn=field(0x02, 36, 4), entity_category=DIAG),
    EESensorDescription(key="error_code", translation_key="error_code", value_fn=field(0x02, 40, 4), entity_category=DIAG),
    # PV
    power("pv_power", total(*PV_POWER)),
    *(voltage(f"pv{i+1}_voltage", field(0x34, 8 + i * 8, 2, 0.1)) for i in range(3)),
    *(current(f"pv{i+1}_current", field(0x34, 10 + i * 8, 2, 0.1)) for i in range(3)),
    *(power(f"pv{i+1}_power", PV_POWER[i]) for i in range(3)),
    energy("pv_energy_today", field(0x03, 26, 4, 0.001)),
    energy("pv_energy_total", field(0x03, 30, 4, 0.001)),
    # Netz
    power("grid_power", total(*GRID_FEED, factor=-1)),  # + Bezug / - Einspeisung
    *(power(f"grid_power_l{i+1}", total(GRID_FEED[i], factor=-1)) for i in range(3)),
    power("grid_import_power", field(0x0A, 44, 4, 0.1, True)),
    energy("grid_import_today", field(0x0A, 48, 4, 0.001)),
    energy("grid_import_total", field(0x0A, 52, 4, 0.001)),
    energy("grid_export_today", field(0x03, 10, 4, 0.001)),
    energy("grid_export_total", field(0x03, 18, 4, 0.001)),
    *(voltage(f"ac_voltage_l{i+1}", field(0x36, 8 + i * 6, 2, 0.1)) for i in range(3)),
    *(current(f"ac_current_l{i+1}", field(0x36, 12 + i * 6, 2, 0.01, True),
              entity_category=DIAG) for i in range(3)),
    EESensorDescription(key="grid_frequency", translation_key="grid_frequency", value_fn=field(0x36, 10, 2, 0.01),
                        native_unit_of_measurement=HZ, device_class=SensorDeviceClass.FREQUENCY, state_class=MEAS),
    # Hausverbrauch
    power("load_power", field(0x08, 44, 4, 0.1, True)),
    *(power(f"load_power_l{i+1}", field(0x08, 8 + i * 12, 4, 0.1, True)) for i in range(3)),
    energy("load_energy_today", field(0x08, 48, 4, 0.001)),
    energy("load_energy_total", field(0x08, 52, 4, 0.001)),
    # Batterie
    EESensorDescription(key="battery_state", translation_key="battery_state", value_fn=battery_state,
                        device_class=SensorDeviceClass.ENUM, options=[*BATTERY_STATE.values()]),
    EESensorDescription(key="battery_soc", translation_key="battery_soc", value_fn=field(0xB0, 10, 2),
                        native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=MEAS),
    power("battery_power", field(0xB1, 8, 4, 1, True)),
    voltage("battery_voltage", field(0xB0, 12, 2)),
    current("battery_current", field(0xB0, 16, 2, 0.1, True)),
    temperature("battery_temperature", field(0xB0, 14, 2, 0.1, True)),
    EESensorDescription(key="battery_soh", translation_key="battery_soh", value_fn=field(0xB0, 26, 2),
                        native_unit_of_measurement=PERCENTAGE, state_class=MEAS, entity_category=DIAG),
    EESensorDescription(key="battery_cycles", translation_key="battery_cycles", value_fn=field(0xB0, 18, 2),
                        state_class=TOTAL_INC, entity_category=DIAG),
    energy("battery_charge_today", field(0xB1, 12, 4, 0.001)),
    energy("battery_discharge_today", field(0xB1, 16, 4, 0.001)),
    energy("battery_charge_total", field(0xB1, 20, 4, 0.001)),
    energy("battery_discharge_total", field(0xB1, 24, 4, 0.001)),
    # Backup
    power("backup_power", field(0xB5, 20, 4, 0.1, True)),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: EachEnergyCoordinator = entry.runtime_data
    async_add_entities(EESensor(coordinator, entry, desc) for desc in SENSORS)


class EESensor(CoordinatorEntity[EachEnergyCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: EESensorDescription

    def __init__(self, coordinator: EachEnergyCoordinator, entry: ConfigEntry, desc: EESensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = desc
        info = coordinator.info
        uid = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_{desc.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            manufacturer="Each Energy",
            model=info.get("model"),
            serial_number=info.get("serial"),
            sw_version=info.get("firmware"),
            translation_key="inverter",
        )

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data or {})
