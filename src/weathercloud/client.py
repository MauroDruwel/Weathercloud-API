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
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
}

# ICAO airport codes are 4 uppercase ASCII letters (e.g. LEPA, EGLL, KJFK).
# Regular Weathercloud station IDs are numeric strings.
_ICAO_RE = re.compile(r"^[A-Z]{4}$")

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
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self.username = username
        self.password = password
        self._logged_in = False
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

    def login(self) -> None:
        """Log in to app.weathercloud.net using the configured credentials."""
        if not self.username or not self.password:
            raise WeathercloudError("Username and password are required to log in")

        # 1. GET base URL to initialize cookies
        url = f"{self._base_url}/"
        try:
            resp = self._session.get(url, headers=_BROWSER_HEADERS, timeout=self._timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise WeathercloudError(f"Failed to initialize session for login: {exc}") from exc

        # 2. POST signin
        signin_url = f"{self._base_url}/signin"
        data = {
            "LoginForm[entity]": self.username,
            "LoginForm[password]": self.password,
            "LoginForm[rememberMe]": "1",
        }
        try:
            resp = self._session.post(
                signin_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self._timeout,
                allow_redirects=False,
            )
            # A successful login redirects (status 302)
            if resp.status_code != 302:
                raise WeathercloudError(
                    f"Login failed: invalid username or password (status: {resp.status_code})"
                )
        except requests.RequestException as exc:
            raise WeathercloudError(f"Login request failed: {exc}") from exc

        self._logged_in = True

    def _ensure_logged_in(self) -> None:
        if self.username and self.password and not self._logged_in:
            self.login()

    def _is_session_expired(
        self,
        resp: requests.Response | None,
        exc: Exception | None = None,
    ) -> bool:
        if resp is not None:
            if resp.status_code == 401:
                return True
            if "/signin" in resp.url or any("/signin" in r.url for r in resp.history):
                return True
            # Check for non-JSON sign-in responses (HTML sign-in page)
            content_type = resp.headers.get("content-type", "").lower()
            if "text/html" in content_type and ("signin" in resp.url or "LoginForm" in resp.text):
                return True
        if exc is not None and isinstance(exc, WeathercloudError):
            err_msg = str(exc)
            if "Expected JSON" in err_msg and ("signin" in err_msg or "login" in err_msg.lower()):
                return True
        return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        _retry: bool = True,
    ) -> Any:
        self._ensure_logged_in()
        url = f"{self._base_url}{path}"
        resp = None
        try:
            resp = self._session.request(
                method,
                url,
                params=params,
                data=data,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            if (
                self.username
                and self.password
                and self._logged_in
                and self._is_session_expired(resp)
            ):
                raise WeathercloudError("Expected JSON, session likely expired")
            return self._parse_json(resp)
        except (requests.RequestException, WeathercloudError) as exc:
            r = resp or (
                exc.response if isinstance(exc, requests.RequestException) else None
            )
            if (
                _retry
                and self.username
                and self.password
                and self._logged_in
                and self._is_session_expired(r, exc)
            ):
                self._logged_in = False
                self._ensure_logged_in()
                return self._request(
                    method,
                    path,
                    params=params,
                    data=data,
                    _retry=False,
                )
            if isinstance(exc, WeathercloudError):
                raise
            raise WeathercloudError(f"Request failed: {exc}") from exc

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict[str, Any]) -> Any:
        return self._request("POST", path, data=data)

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

    @staticmethod
    def _values_path(device_id: str) -> str:
        """Return the correct values endpoint path for a given station ID."""
        if _ICAO_RE.match(device_id):
            return f"/metar/values/{device_id}"
        return f"/device/values/{device_id}"

    def get_current_conditions(self, device_id: str) -> CurrentConditions:
        """Return typed live sensor readings — primary endpoint for HA integration.

        Stations only report the sensors they have, so any reading the station
        does not provide is returned as ``None`` instead of raising.

        Automatically uses the METAR endpoint for ICAO airport codes
        (4 uppercase letters, e.g. ``LEPA``).
        """
        raw = self._get_dict(self._values_path(device_id))
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
            inside_temperature=_to_float(raw.get("tempin")),
            inside_humidity=_to_int(raw.get("humin")),
            inside_heat_index=_to_float(raw.get("heatin")),
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
        """Raw values response. Prefer get_current_conditions() for typed access.

        Automatically uses ``/metar/values/{id}`` for ICAO airport codes
        (4 uppercase letters, e.g. ``LEPA``) and ``/device/values/{id}``
        for regular numeric station IDs.
        """
        return self._get_dict(self._values_path(device_id))

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
