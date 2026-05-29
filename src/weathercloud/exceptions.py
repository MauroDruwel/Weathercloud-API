from __future__ import annotations

__all__ = ["WeathercloudError"]


class WeathercloudError(Exception):
    """Raised when the Weathercloud API returns an unexpected response."""
