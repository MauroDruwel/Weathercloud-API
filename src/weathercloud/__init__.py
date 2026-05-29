"""Unofficial Python client for the Weathercloud API.

Public API::

    from weathercloud import (
        WeathercloudClient,
        WeathercloudError,
        VariableCode,
        CurrentConditions,
        StationInfo,
    )
"""
from __future__ import annotations

from .client import WeathercloudClient
from .exceptions import WeathercloudError
from .models import CurrentConditions, StationInfo, VariableCode

__version__ = "0.1.1"
__all__ = [
    "WeathercloudClient",
    "WeathercloudError",
    "VariableCode",
    "CurrentConditions",
    "StationInfo",
    "__version__",
]
