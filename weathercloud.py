import re
import requests

class WeathercloudClient:
    """
    An unofficial Python client library for app.weathercloud.net
    Based on the reverse-engineered OpenAPI specification.
    """
    
    def __init__(self, base_url: str = "https://app.weathercloud.net"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # CRITICAL: Weathercloud's backend requires this header to return JSON data.
        self.session.headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Internal helper to execute requests securely."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        
        # Guard against endpoints that return text/html containing JSON strings
        try:
            return response.json()
        except ValueError:
            raise RuntimeError(f"API failed to return JSON. Response snippet: {response.text[:100]}")

    # ==========================================
    # TAG: Device (Live) Endpoints
    # ==========================================

    def get_device_values(self, device_id: str) -> dict:
        """Get live real-time sensor metrics for a specific device ID."""
        return self._request("GET", f"/device/values/{device_id}")

    def get_device_stats(self, device_id: str) -> dict:
        """Get current readings + daily, monthly, and yearly min/max stats."""
        return self._request("GET", "/device/stats", params={"code": device_id})

    def get_device_info(self, device_id: str) -> dict:
        """Get general station metadata (elevation, city, status) and values."""
        return self._request("GET", f"/device/info/{device_id}")

    def get_wind_rose(self, device_id: str) -> dict:
        """Get direction distributions for wind rose mapping."""
        return self._request("GET", "/device/wind", params={"code": device_id})

    def get_update_status(self, device_id: str) -> dict:
        """Get seconds passed since the last update and connection status code."""
        # The spec indicates this must be url-encoded form data via POST
        return self._request("POST", "/device/ajaxupdatedate", data={"d": device_id})

    def get_owner_profile(self, device_id: str) -> dict:
        """Fetch the weather station owner's public profile information."""
        return self._request("POST", "/device/ajaxprofile", data={"d": device_id})

    # ==========================================
    # TAG: History & Forecasts
    # ==========================================

    def get_historical_evolution(self, device_id: str, variable_code: int, period: str = "day") -> dict:
        """
        Fetch time-series data for individual metrics.
        Common variable_codes: Temperature=101, Humidity=201, Barometer=641, Rain=801
        Periods allowed: 'day', 'week', 'month', 'year'
        """
        payload = {
            "device": device_id,
            "variable": variable_code,
            "period": period
        }
        return self._request("POST", "/device/evolution", data=payload)

    def get_daily_forecast(self, device_id: str) -> dict:
        """Fetch a 6-day localized WMO weather forecast for the device area."""
        return self._request("GET", "/forecast/daily", params={"id": device_id})

    # ==========================================
    # TAG: Nearby & Discovery (Pages)
    # ==========================================

    def get_nearby_stations(self, lat: float, lon: float, distance_km: int = 5) -> dict:
        """Find active stations within a specific radius of a coordinate point."""
        endpoint = f"/page/coordinates/latitude/{lat}/longitude/{lon}/distance/{distance_km}"
        return self._request("GET", endpoint)

    # ==========================================
    # TAG: Miscellaneous (Scraping Tricks)
    # ==========================================

    def scrape_station_name(self, device_id: str) -> str:
        """
        The JSON APIs lack the user-facing station name. 
        This helper parses it from the web presentation wrapper directly.
        """
        url = f"{self.base_url}/d{device_id}"
        
        # Temporarily drop AJAX header so we don't confuse standard HTML page load
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        
        # Regex pull out the page title
        match = re.search(r"<title>(.*?)</title>", res.text, re.IGNORECASE)
        if match:
            clean_title = match.group(1)
            # Remove trailing string branding template
            return clean_title.split(" - Weathercloud")[0].strip()
        return "Unknown Station"