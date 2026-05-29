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
    """Live sensor readings from ``/device/values`` — maps directly to HA sensor entities."""

    epoch: int
    temperature: float       # °C
    dew_point: float         # °C
    wind_chill: float        # °C
    heat_index: float        # °C
    humidity: int            # %
    pressure: float          # hPa
    wind_direction: int      # ° instantaneous
    wind_direction_avg: int  # ° averaged
    wind_speed: float        # m/s instantaneous
    wind_speed_avg: float    # m/s averaged
    wind_gust: float         # m/s
    rain_rate: float         # mm/h
    rain: float              # mm total
    solar_radiation: float   # W/m²
    uv_index: int


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
