from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

__all__ = ["VariableCode", "CurrentConditions", "StationInfo"]


class VariableCode(IntEnum):
    """Sensor variable codes used by the ``/device/evolution`` endpoint."""

    TEMPERATURE = 101
    HUMIDITY = 201
    DEW_POINT = 541
    PRESSURE = 641
    WIND_SPEED = 701
    WIND_DIRECTION = 6001
    WIND_GUST = 6501
    RAIN = 801
    RAIN_RATE = 811
    SOLAR_RADIATION = 1001
    UV_INDEX = 1101


@dataclass
class CurrentConditions:
    """Live sensor readings from ``/device/values`` — maps directly to HA sensor entities.

    Every field is optional: a station only reports the sensors it actually has,
    so any missing or unparseable reading is returned as ``None`` rather than
    raising.
    """

    epoch: int | None              # unix timestamp
    temperature: float | None      # °C
    dew_point: float | None        # °C
    wind_chill: float | None       # °C
    heat_index: float | None       # °C
    humidity: int | None           # %
    pressure: float | None         # hPa
    wind_direction: int | None     # ° instantaneous
    wind_direction_avg: int | None  # ° averaged
    wind_speed: float | None       # m/s instantaneous
    wind_speed_avg: float | None   # m/s averaged
    wind_gust: float | None        # m/s
    rain_rate: float | None        # mm/h
    rain: float | None             # mm total
    solar_radiation: float | None  # W/m²
    uv_index: int | None


@dataclass
class StationInfo:
    """Station metadata combining ``/device/info`` and a scraped station name."""

    device_id: str
    name: str            # scraped from HTML — not available via JSON API
    city: str
    altitude: str        # metres (as string from API)
    status: str          # "online" | "recently_online" | "offline"
    seconds_since_update: int
    account_type: int    # 0 = free, >0 = premium
