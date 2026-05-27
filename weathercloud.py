from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import requests

__version__ = "0.1.0"
__all__ = [
    "WeathercloudClient",
    "WeathercloudError",
    "VariableCode",
    "CurrentConditions",
    "StationInfo",
]

_BASE_URL = "https://app.weathercloud.net"
_DEFAULT_TIMEOUT = 10
_STATUS_MAP = {"1": "online", "2": "recently_online", "3": "offline"}


class WeathercloudError(Exception):
    """Raised when the Weathercloud API returns an unexpected response."""


class VariableCode(IntEnum):
    """Sensor variable codes used by the /device/evolution endpoint."""
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
    """Live sensor readings from /device/values — maps directly to HA sensor entities."""
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
    """Station metadata combining /device/info and a scraped station name."""
    device_id: str
    name: str            # scraped from HTML — not available via JSON API
    city: str
    altitude: str        # metres (as string from API)
    status: str          # "online" | "recently_online" | "offline"
    seconds_since_update: int
    account_type: int    # 0 = free, >0 = premium


class WeathercloudClient:
    """Unofficial Python client for app.weathercloud.net.

    All public methods raise :exc:`WeathercloudError` on network or parse failures.
    """

    def __init__(
        self,
        base_url: str = _BASE_URL,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise WeathercloudError(f"Request failed: {exc}") from exc
        return self._parse_json(resp)

    def _post(self, path: str, data: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        try:
            resp = self._session.post(url, data=data, timeout=self._timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise WeathercloudError(f"Request failed: {exc}") from exc
        return self._parse_json(resp)

    @staticmethod
    def _parse_json(resp: requests.Response) -> Any:
        try:
            return resp.json()
        except ValueError as exc:
            snippet = resp.text[:120]
            raise WeathercloudError(f"Expected JSON, got: {snippet!r}") from exc

    # ------------------------------------------------------------------
    # High-level convenience methods (HA-ready)
    # ------------------------------------------------------------------

    def get_current_conditions(self, device_id: str) -> CurrentConditions:
        """Return typed live sensor readings — primary endpoint for HA integration."""
        raw = self._get(f"/device/values/{device_id}")
        try:
            return CurrentConditions(
                epoch=raw["epoch"],
                temperature=float(raw["temp"]),
                dew_point=float(raw["dew"]),
                wind_chill=float(raw["chill"]),
                heat_index=float(raw["heat"]),
                humidity=int(raw["hum"]),
                pressure=float(raw["bar"]),
                wind_direction=int(raw["wdir"]),
                wind_direction_avg=int(raw["wdiravg"]),
                wind_speed=float(raw["wspd"]),
                wind_speed_avg=float(raw["wspdavg"]),
                wind_gust=float(raw["wspdhi"]),
                rain_rate=float(raw["rainrate"]),
                rain=float(raw["rain"]),
                solar_radiation=float(raw["solarrad"]),
                uv_index=int(raw["uvi"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WeathercloudError(f"Unexpected /device/values response: {exc}") from exc

    def get_station_info(self, device_id: str, scrape_name: bool = True) -> StationInfo:
        """Return typed station metadata.

        Args:
            device_id: Station ID.
            scrape_name: Fetch the station name from HTML (one extra request).
                Set to False to skip and use the device_id as the name instead.
        """
        raw = self._get(f"/device/info/{device_id}")
        dev = raw.get("device", {})
        name = self.get_station_name(device_id) if scrape_name else device_id
        return StationInfo(
            device_id=device_id,
            name=name,
            city=dev.get("city", ""),
            altitude=dev.get("altitude", ""),
            status=_STATUS_MAP.get(str(dev.get("status", "")), "unknown"),
            seconds_since_update=int(dev.get("update", 0)),
            account_type=int(dev.get("account", 0)),
        )

    def get_station_name(self, device_id: str) -> str:
        """Scrape the station name from the HTML page.

        The name is not available via any JSON endpoint — it only appears in
        the page ``<title>``. Returns *device_id* if the title cannot be found.
        """
        url = f"{self._base_url}/d{device_id}"
        try:
            resp = requests.get(
                url,
                timeout=self._timeout,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise WeathercloudError(f"Failed to fetch station page: {exc}") from exc

        match = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE)
        if match:
            return match.group(1).split(" - Weathercloud")[0].strip()
        return device_id

    # ------------------------------------------------------------------
    # Raw API methods — return dicts for full access to the API response
    # ------------------------------------------------------------------

    def get_device_values(self, device_id: str) -> dict:
        """Raw /device/values response. Prefer get_current_conditions() for typed access."""
        return self._get(f"/device/values/{device_id}")

    def get_device_stats(self, device_id: str) -> dict:
        """Current readings + day/month/year min–max.

        Each value is a ``[unix_timestamp, value]`` tuple.
        Key pattern: ``{sensor}_{period}_{type}`` e.g. ``temp_day_max``.
        """
        return self._get("/device/stats", params={"code": device_id})

    def get_device_info(self, device_id: str) -> dict:
        """Raw /device/info response (device metadata + current values as strings)."""
        return self._get(f"/device/info/{device_id}")

    def get_wind_rose(self, device_id: str) -> dict:
        """Wind direction distribution data for the wind rose chart."""
        return self._get("/device/wind", params={"code": device_id})

    def get_update_status(self, device_id: str) -> dict:
        """Seconds since last update and online status."""
        return self._post("/device/ajaxupdatedate", data={"d": device_id})

    def get_owner_profile(self, device_id: str) -> dict:
        """Station owner name, nickname, follower count, and hardware brand/model."""
        return self._post("/device/ajaxprofile", data={"d": device_id})

    def get_evolution(
        self,
        device_id: str,
        variable: VariableCode | int,
        period: str = "day",
    ) -> dict:
        """Time-series history (hourly buckets) for one sensor variable.

        Args:
            device_id: Station ID.
            variable: Sensor code — use :class:`VariableCode` or a raw integer.
            period: One of ``"day"``, ``"week"``, ``"month"``, ``"year"``.
        """
        return self._post("/device/evolution", data={
            "device": device_id,
            "variable": int(variable),
            "period": period,
        })

    def get_forecast(self, device_id: str) -> dict:
        """6-day WMO daily forecast for the station's location."""
        return self._get("/forecast/daily", params={"id": device_id})

    def get_nearby_stations(
        self,
        lat: float,
        lon: float,
        distance_km: int = 5,
    ) -> dict:
        """Stations within *distance_km* of a coordinate.

        Note: sensor values inside each device's ``"values"`` dict are scaled
        ×10 — divide by 10 to get the real unit (e.g. ``temp: 281`` → 28.1 °C).
        """
        return self._get(
            f"/page/coordinates/latitude/{lat}/longitude/{lon}/distance/{distance_km}"
        )
