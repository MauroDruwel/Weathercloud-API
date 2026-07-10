from __future__ import annotations

import pytest
import responses

from weathercloud import (
    CurrentConditions,
    StationInfo,
    VariableCode,
    WeathercloudClient,
    WeathercloudError,
)

BASE = "https://app.weathercloud.net"
DEVICE_ID = "5726468552"

VALUES_PAYLOAD = {
    "epoch": 1748358122,
    "temp": "22.8",
    "dew": "15.1",
    "chill": "22.8",
    "heat": "23.0",
    "hum": "62",
    "bar": "1013.2",
    "wdir": "180",
    "wdiravg": "175",
    "wspd": "1.0",
    "wspdavg": "0.8",
    "wspdhi": "1.4",
    "rainrate": "0.0",
    "rain": "2.4",
    "solarrad": "320.0",
    "uvi": "3",
    "tempin": "21.5",
    "humin": "55",
    "heatin": "22.0",
}


@pytest.fixture
def client():
    with WeathercloudClient() as c:
        yield c


@responses.activate
def test_get_current_conditions_returns_typed_dataclass(client):
    responses.get(f"{BASE}/device/values/{DEVICE_ID}", json=VALUES_PAYLOAD)

    cond = client.get_current_conditions(DEVICE_ID)

    assert isinstance(cond, CurrentConditions)
    assert cond.temperature == 22.8
    assert cond.humidity == 62
    assert cond.wind_gust == 1.4
    assert cond.uv_index == 3
    assert cond.epoch == 1748358122
    assert cond.inside_temperature == 21.5
    assert cond.inside_humidity == 55
    assert cond.inside_heat_index == 22.0


@responses.activate
def test_get_current_conditions_missing_keys_become_none(client):
    payload = {"epoch": 1748358122, "temp": "22.8", "hum": "62"}
    responses.get(f"{BASE}/device/values/{DEVICE_ID}", json=payload)

    cond = client.get_current_conditions(DEVICE_ID)

    assert cond.temperature == 22.8
    assert cond.humidity == 62
    # Sensors the station doesn't report are None, not errors.
    assert cond.pressure is None
    assert cond.wind_gust is None
    assert cond.uv_index is None
    assert cond.rain is None


@responses.activate
def test_get_current_conditions_unparseable_values_become_none(client):
    payload = dict(VALUES_PAYLOAD, temp="", hum="n/a", uvi=None)
    responses.get(f"{BASE}/device/values/{DEVICE_ID}", json=payload)

    cond = client.get_current_conditions(DEVICE_ID)

    assert cond.temperature is None
    assert cond.humidity is None
    assert cond.uv_index is None
    # Other valid readings still parse.
    assert cond.wind_gust == 1.4


@responses.activate
def test_get_current_conditions_non_object_raises(client):
    responses.get(f"{BASE}/device/values/{DEVICE_ID}", json=["unexpected"])

    with pytest.raises(WeathercloudError, match="Expected a JSON object"):
        client.get_current_conditions(DEVICE_ID)


@responses.activate
def test_http_error_wrapped(client):
    responses.get(f"{BASE}/device/values/{DEVICE_ID}", status=500)

    with pytest.raises(WeathercloudError, match="Request failed"):
        client.get_current_conditions(DEVICE_ID)


@responses.activate
def test_non_json_response_wrapped(client):
    responses.get(
        f"{BASE}/device/values/{DEVICE_ID}",
        body="<html>nope</html>",
        content_type="text/html",
    )

    with pytest.raises(WeathercloudError, match="Expected JSON"):
        client.get_current_conditions(DEVICE_ID)


@responses.activate
def test_get_station_info_without_scrape(client):
    responses.get(
        f"{BASE}/device/info/{DEVICE_ID}",
        json={"device": {"city": "Ingelmunster", "altitude": "18.0",
                         "status": "1", "update": "42", "account": "0"}},
    )

    info = client.get_station_info(DEVICE_ID, scrape_name=False)

    assert isinstance(info, StationInfo)
    assert info.name == DEVICE_ID
    assert info.city == "Ingelmunster"
    assert info.status == "online"
    assert info.seconds_since_update == 42
    assert info.account_type == 0


@responses.activate
def test_get_station_info_with_scrape(client):
    responses.get(
        f"{BASE}/device/info/{DEVICE_ID}",
        json={"device": {"city": "Ingelmunster", "altitude": "18.0",
                         "status": "3", "update": "0", "account": "1"}},
    )
    responses.get(
        f"{BASE}/d{DEVICE_ID}",
        body="<html><head><title>Ginometeo - Weathercloud</title></head></html>",
        content_type="text/html",
    )

    info = client.get_station_info(DEVICE_ID)

    assert info.name == "Ginometeo"
    assert info.status == "offline"
    assert info.account_type == 1


@responses.activate
def test_get_station_info_unknown_status(client):
    responses.get(
        f"{BASE}/device/info/{DEVICE_ID}",
        json={"device": {"status": "9"}},
    )

    info = client.get_station_info(DEVICE_ID, scrape_name=False)
    assert info.status == "unknown"


@responses.activate
def test_get_station_info_missing_device_fields_dont_fail(client):
    responses.get(f"{BASE}/device/info/{DEVICE_ID}", json={})

    info = client.get_station_info(DEVICE_ID, scrape_name=False)

    assert info.city == ""
    assert info.altitude == ""
    assert info.status == "unknown"
    assert info.seconds_since_update == 0
    assert info.account_type == 0


@responses.activate
def test_get_station_info_bad_numeric_fields_dont_fail(client):
    responses.get(
        f"{BASE}/device/info/{DEVICE_ID}",
        json={"device": {"update": "n/a", "account": "", "city": None}},
    )

    info = client.get_station_info(DEVICE_ID, scrape_name=False)

    assert info.seconds_since_update == 0
    assert info.account_type == 0
    assert info.city == ""


@responses.activate
def test_get_station_name_parsed(client):
    responses.get(
        f"{BASE}/d{DEVICE_ID}",
        body="<TITLE>My Station - Weathercloud - extra</TITLE>",
        content_type="text/html",
    )

    assert client.get_station_name(DEVICE_ID) == "My Station"


@responses.activate
def test_get_station_name_no_title_falls_back_to_id(client):
    responses.get(f"{BASE}/d{DEVICE_ID}", body="<html>no title here</html>")

    assert client.get_station_name(DEVICE_ID) == DEVICE_ID


@responses.activate
def test_get_station_name_network_error_wrapped(client):
    responses.get(f"{BASE}/d{DEVICE_ID}", status=404)

    with pytest.raises(WeathercloudError, match="Failed to fetch station page"):
        client.get_station_name(DEVICE_ID)


@responses.activate
def test_get_device_stats_uses_code_param(client):
    responses.get(f"{BASE}/device/stats", json={"temp_day_max": [1, 30.9]})

    result = client.get_device_stats(DEVICE_ID)

    assert result["temp_day_max"] == [1, 30.9]
    assert responses.calls[0].request.params["code"] == DEVICE_ID


@responses.activate
def test_get_evolution_posts_expected_body(client):
    responses.post(f"{BASE}/device/evolution", json={"data": {}})

    client.get_evolution(DEVICE_ID, VariableCode.TEMPERATURE, period="week")

    body = responses.calls[0].request.body
    assert "variable=101" in body
    assert "period=week" in body
    assert f"device={DEVICE_ID}" in body


@responses.activate
def test_get_evolution_accepts_raw_int(client):
    responses.post(f"{BASE}/device/evolution", json={})

    client.get_evolution(DEVICE_ID, 201)

    assert "variable=201" in responses.calls[0].request.body


@responses.activate
def test_get_nearby_stations_builds_url(client):
    url = f"{BASE}/page/coordinates/latitude/50.9/longitude/3.1/distance/10"
    responses.get(url, json={"devices": []})

    result = client.get_nearby_stations(lat=50.9, lon=3.1, distance_km=10)

    assert result == {"devices": []}


@responses.activate
def test_post_endpoints(client):
    responses.post(f"{BASE}/device/ajaxupdatedate", json={"update": 30})
    responses.post(f"{BASE}/device/ajaxprofile", json={"name": "owner"})

    assert client.get_update_status(DEVICE_ID) == {"update": 30}
    assert client.get_owner_profile(DEVICE_ID) == {"name": "owner"}


def test_base_url_trailing_slash_stripped():
    c = WeathercloudClient(base_url="https://example.com/")
    assert c._base_url == "https://example.com"
    c.close()


def test_default_headers_set():
    c = WeathercloudClient()
    assert c._session.headers["X-Requested-With"] == "XMLHttpRequest"
    assert "User-Agent" in c._session.headers
    c.close()


def test_context_manager_closes_session():
    with WeathercloudClient() as c:
        session = c._session
    # close() on a requests.Session is idempotent; just ensure no error.
    session.close()


# ------------------------------------------------------------------
# ICAO / METAR routing
# ------------------------------------------------------------------

ICAO_ID = "LEPA"
METAR_PAYLOAD = {
    "epoch": 1780687800,
    "temp": 21,
    "dew": 13,
    "chill": 21,
    "heat": 20,
    "hum": 60,
    "wspdavg": 4,
    "wspdhi": 0,
    "wdiravg": 70,
    "bar": 1016,
    "rain": 0,
    "vis": 100,
    "rainrate": 0,
}


@responses.activate
def test_get_device_values_uses_metar_endpoint_for_icao(client):
    responses.get(f"{BASE}/metar/values/{ICAO_ID}", json=METAR_PAYLOAD)

    result = client.get_device_values(ICAO_ID)

    assert result["epoch"] == 1780687800
    assert result["temp"] == 21
    assert len(responses.calls) == 1
    assert f"/metar/values/{ICAO_ID}" in responses.calls[0].request.url


@responses.activate
def test_get_current_conditions_uses_metar_endpoint_for_icao(client):
    responses.get(f"{BASE}/metar/values/{ICAO_ID}", json=METAR_PAYLOAD)

    cond = client.get_current_conditions(ICAO_ID)

    assert isinstance(cond, CurrentConditions)
    assert cond.temperature == 21.0
    assert cond.humidity == 60
    assert cond.epoch == 1780687800
    assert f"/metar/values/{ICAO_ID}" in responses.calls[0].request.url


@responses.activate
def test_get_device_values_uses_device_endpoint_for_numeric_id(client):
    responses.get(f"{BASE}/device/values/{DEVICE_ID}", json=VALUES_PAYLOAD)

    client.get_device_values(DEVICE_ID)

    assert f"/device/values/{DEVICE_ID}" in responses.calls[0].request.url


def test_values_path_icao_detection(client):
    assert client._values_path("LEPA") == "/metar/values/LEPA"
    assert client._values_path("EGLL") == "/metar/values/EGLL"
    assert client._values_path("KJFK") == "/metar/values/KJFK"
    assert client._values_path("5726468552") == "/device/values/5726468552"
    assert client._values_path("lepa") == "/device/values/lepa"  # lowercase not ICAO
    assert client._values_path("LEP") == "/device/values/LEP"    # 3 chars not ICAO


@responses.activate
def test_login_success():
    with WeathercloudClient(username="testuser", password="testpassword") as client:
        # Mock GET / to initialize cookies
        responses.get(f"{BASE}/", status=200)
        # Mock POST /signin to authenticate
        responses.post(f"{BASE}/signin", status=302, headers={"Location": "/"})
        # Mock actual request
        responses.get(f"{BASE}/device/values/{DEVICE_ID}", json=VALUES_PAYLOAD)

        cond = client.get_current_conditions(DEVICE_ID)
        assert cond.inside_temperature == 21.5
        assert len(responses.calls) == 3


@responses.activate
def test_login_failure():
    with WeathercloudClient(username="testuser", password="testpassword") as client:
        responses.get(f"{BASE}/", status=200)
        # Mock login failed (e.g. returns 200 instead of 302 redirect)
        responses.post(f"{BASE}/signin", status=200)

        with pytest.raises(WeathercloudError, match="Login failed"):
            client.get_current_conditions(DEVICE_ID)
