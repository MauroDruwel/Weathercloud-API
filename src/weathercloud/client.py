from __future__ import annotations

import re
from types import TracebackType
from typing import Any

import requests

from .exceptions import WeathercloudError
from .models import CurrentConditions, StationInfo, VariableCode

__all__ = ["WeathercloudClient"]

_BASE_URL = "https://app.weathercloud.net"
_DEFAULT_TIMEOUT = 10.0
_STATUS_MAP = {"1": "online", "2": "recently_online", "3": "offline"}

# Timeout accepted by requests: a single value, a (connect, read) pair, or None.
Timeout = float | tuple[float, float] | None


def _to_float(value: Any) -> float | None:
    """Coerce an API value to ``float``, returning ``None`` if missing/invalid."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    """Coerce an API value to ``int``, returning ``None`` if missing/invalid.

    Accepts float-like strings (e.g. ``"62.0"``) by truncating.
    """
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class WeathercloudClient:
    """Unofficial Python client for app.weathercloud.net.

    All public methods raise :exc:`WeathercloudError` on network or parse failures.

    The client owns a :class:`requests.Session`. Use it as a context manager or
    call :meth:`close` to release the underlying connection pool::

        with WeathercloudClient() as client:
            conditions = client.get_current_conditions("5726468552")
    """

    def __init__(
        self,
        base_url: str = _BASE_URL,
        timeout: Timeout = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        })

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying :class:`requests.Session`."""
        self._session.close()

    def __enter__(self) -> WeathercloudClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

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

    def _get_dict(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        data = self._get(path, params)
        if not isinstance(data, dict):
            raise WeathercloudError(f"Expected a JSON object from {path}, got: {data!r}")
        return data

    def _post_dict(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        result = self._post(path, data)
        if not isinstance(result, dict):
            raise WeathercloudError(f"Expected a JSON object from {path}, got: {result!r}")
        return result

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
        """Return typed live sensor readings — primary endpoint for HA integration.

        Stations only report the sensors they have, so any reading the station
        does not provide is returned as ``None`` instead of raising.
        """
        raw = self._get_dict(f"/device/values/{device_id}")
        return CurrentConditions(
            epoch=_to_int(raw.get("epoch")),
            temperature=_to_float(raw.get("temp")),
            dew_point=_to_float(raw.get("dew")),
            wind_chill=_to_float(raw.get("chill")),
            heat_index=_to_float(raw.get("heat")),
            humidity=_to_int(raw.get("hum")),
            pressure=_to_float(raw.get("bar")),
            wind_direction=_to_int(raw.get("wdir")),
            wind_direction_avg=_to_int(raw.get("wdiravg")),
            wind_speed=_to_float(raw.get("wspd")),
            wind_speed_avg=_to_float(raw.get("wspdavg")),
            wind_gust=_to_float(raw.get("wspdhi")),
            rain_rate=_to_float(raw.get("rainrate")),
            rain=_to_float(raw.get("rain")),
            solar_radiation=_to_float(raw.get("solarrad")),
            uv_index=_to_int(raw.get("uvi")),
        )

    def get_station_info(self, device_id: str, scrape_name: bool = True) -> StationInfo:
        """Return typed station metadata.

        Args:
            device_id: Station ID.
            scrape_name: Fetch the station name from HTML (one extra request).
                Set to False to skip and use the device_id as the name instead.
        """
        raw = self._get_dict(f"/device/info/{device_id}")
        dev = raw.get("device") or {}
        if not isinstance(dev, dict):
            dev = {}
        name = self.get_station_name(device_id) if scrape_name else device_id
        return StationInfo(
            device_id=device_id,
            name=name,
            city=str(dev.get("city") or ""),
            altitude=str(dev.get("altitude") or ""),
            status=_STATUS_MAP.get(str(dev.get("status", "")), "unknown"),
            seconds_since_update=_to_int(dev.get("update")) or 0,
            account_type=_to_int(dev.get("account")) or 0,
        )

    def get_station_name(self, device_id: str) -> str:
        """Scrape the station name from the HTML page.

        The name is not available via any JSON endpoint — it only appears in
        the page ``<title>``. Returns *device_id* if the title cannot be found.
        """
        url = f"{self._base_url}/d{device_id}"
        try:
            resp = self._session.get(
                url,
                timeout=self._timeout,
                headers={"Accept": "text/html"},
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise WeathercloudError(f"Failed to fetch station page: {exc}") from exc

        match = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).split(" - Weathercloud")[0].strip()
        return device_id

    # ------------------------------------------------------------------
    # Raw API methods — return dicts for full access to the API response
    # ------------------------------------------------------------------

    def get_device_values(self, device_id: str) -> dict[str, Any]:
        """Raw /device/values response. Prefer get_current_conditions() for typed access."""
        return self._get_dict(f"/device/values/{device_id}")

    def get_device_stats(self, device_id: str) -> dict[str, Any]:
        """Current readings + day/month/year min–max.

        Each value is a ``[unix_timestamp, value]`` tuple.
        Key pattern: ``{sensor}_{period}_{type}`` e.g. ``temp_day_max``.
        """
        return self._get_dict("/device/stats", params={"code": device_id})

    def get_device_info(self, device_id: str) -> dict[str, Any]:
        """Raw /device/info response (device metadata + current values as strings)."""
        return self._get_dict(f"/device/info/{device_id}")

    def get_wind_rose(self, device_id: str) -> dict[str, Any]:
        """Wind direction distribution data for the wind rose chart."""
        return self._get_dict("/device/wind", params={"code": device_id})

    def get_update_status(self, device_id: str) -> dict[str, Any]:
        """Seconds since last update and online status."""
        return self._post_dict("/device/ajaxupdatedate", data={"d": device_id})

    def get_owner_profile(self, device_id: str) -> dict[str, Any]:
        """Station owner name, nickname, follower count, and hardware brand/model."""
        return self._post_dict("/device/ajaxprofile", data={"d": device_id})

    def get_evolution(
        self,
        device_id: str,
        variable: VariableCode | int,
        period: str = "day",
    ) -> dict[str, Any]:
        """Time-series history (hourly buckets) for one sensor variable.

        Args:
            device_id: Station ID.
            variable: Sensor code — use :class:`VariableCode` or a raw integer.
            period: One of ``"day"``, ``"week"``, ``"month"``, ``"year"``.
        """
        return self._post_dict("/device/evolution", data={
            "device": device_id,
            "variable": int(variable),
            "period": period,
        })

    def get_forecast(self, device_id: str) -> dict[str, Any]:
        """6-day WMO daily forecast for the station's location."""
        return self._get_dict("/forecast/daily", params={"id": device_id})

    def get_nearby_stations(
        self,
        lat: float,
        lon: float,
        distance_km: int = 5,
    ) -> dict[str, Any]:
        """Stations within *distance_km* of a coordinate.

        Note: sensor values inside each device's ``"values"`` dict are scaled
        ×10 — divide by 10 to get the real unit (e.g. ``temp: 281`` → 28.1 °C).
        """
        return self._get_dict(
            f"/page/coordinates/latitude/{lat}/longitude/{lon}/distance/{distance_km}"
        )
