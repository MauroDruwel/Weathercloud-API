# weathercloud

[![PyPI](https://img.shields.io/pypi/v/weathercloud.svg)](https://pypi.org/project/weathercloud/)
[![Python](https://img.shields.io/pypi/pyversions/weathercloud.svg)](https://pypi.org/project/weathercloud/)
[![CI](https://github.com/MauroDruwel/Weathercloud-API/actions/workflows/ci.yml/badge.svg)](https://github.com/MauroDruwel/Weathercloud-API/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Unofficial, fully-typed Python client for [Weathercloud](https://app.weathercloud.net).
Read live conditions, station metadata, history, and forecasts from any public
station — **no account, no API key**.

> ⚠️ Reverse-engineered from the public web app. Not affiliated with or endorsed
> by Weathercloud, and the upstream endpoints may change without notice.

## ✨ Highlights

- 🌡️ **Typed results** — `get_current_conditions()` returns a `CurrentConditions`
  dataclass, not a bag of stringly-typed JSON.
- 🧱 **Raw access too** — every endpoint also has a `dict`-returning method when
  you need the full payload.
- 🧯 **One exception to catch** — every failure (network, HTTP, bad JSON) raises
  `WeathercloudError`.
- 🧪 **Tested & type-checked** — ships `py.typed`, runs on Python 3.10–3.13.

## 📦 Installation

```sh
pip install weathercloud
```

## 🚀 Quick start

```python
from weathercloud import WeathercloudClient

with WeathercloudClient() as client:
    cond = client.get_current_conditions("5726468552")

print(cond.temperature)   # 22.8
print(cond.humidity)      # 62
print(cond.wind_gust)     # 1.4
```

The client owns a `requests.Session`, so use it as a context manager (or call
`client.close()`) to release connections. You can also tune the request timeout:

```python
client = WeathercloudClient(timeout=30)   # seconds; default is 10
```

## 📖 API

### `get_current_conditions(device_id)` → `CurrentConditions`

Live sensor readings as a typed dataclass — the one you'll call most.

| Field | Type | Unit | Field | Type | Unit |
|---|---|---|---|---|---|
| `temperature` | `float` | °C | `pressure` | `float` | hPa |
| `dew_point` | `float` | °C | `wind_speed` | `float` | m/s |
| `wind_chill` | `float` | °C | `wind_speed_avg` | `float` | m/s |
| `heat_index` | `float` | °C | `wind_gust` | `float` | m/s |
| `humidity` | `int` | % | `wind_direction` | `int` | ° |
| `rain` | `float` | mm | `rain_rate` | `float` | mm/h |
| `solar_radiation` | `float` | W/m² | `uv_index` | `int` | — |
| `epoch` | `int` | unix ts | | | |

### `get_station_info(device_id, scrape_name=True)` → `StationInfo`

Station metadata. The name isn't exposed by any JSON endpoint, so it's scraped
from the page `<title>` (one extra request). Pass `scrape_name=False` to skip it
and use the `device_id` as the name instead.

```python
info = client.get_station_info("5726468552")
info.name                   # "Ginometeo"
info.city                   # "Ingelmunster"
info.altitude               # "18.0"  (metres, as string)
info.status                 # "online" | "recently_online" | "offline" | "unknown"
info.seconds_since_update   # int
info.account_type           # 0 = free, >0 = premium
```

### `get_device_stats(device_id)` → `dict`

Current readings plus day / month / year min–max. Each value is a
`[unix_timestamp, value]` pair, keyed as `{sensor}_{period}_{type}`.

```python
stats = client.get_device_stats("5726468552")
stats["temp_day_max"]       # [1748358122, 30.9]
stats["rain_month_total"]   # [1748358122, 12.4]
```

### `get_evolution(device_id, variable, period="day")` → `dict`

Hourly history for a single sensor. `period` is `"day"`, `"week"`, `"month"`, or
`"year"`.

```python
from weathercloud import VariableCode

evo = client.get_evolution("5726468552", VariableCode.TEMPERATURE, "week")
```

Available codes: `TEMPERATURE`, `HUMIDITY`, `DEW_POINT`, `PRESSURE`, `WIND_SPEED`,
`WIND_DIRECTION`, `WIND_GUST`, `RAIN`, `RAIN_RATE`, `SOLAR_RADIATION`, `UV_INDEX`.

### `get_forecast(device_id)` → `dict`

6-day WMO daily forecast for the station's location.

### `get_nearby_stations(lat, lon, distance_km=5)` → `dict`

Stations within a radius of a coordinate. ⚠️ Sensor values inside each result are
**×10 integers** — divide by 10 (e.g. `temp: 281` → 28.1 °C).

### Other raw methods

```python
client.get_device_values(device_id)    # same data as get_current_conditions, raw
client.get_device_info(device_id)       # metadata + current values as strings
client.get_wind_rose(device_id)         # wind direction distribution
client.get_update_status(device_id)     # seconds since last update
client.get_owner_profile(device_id)     # observer name, hardware brand/model
client.get_station_name(device_id)      # scrape the station name only
```

## 🧯 Error handling

Every method raises `WeathercloudError` on failure — network error, HTTP error,
non-JSON body, or an unexpected response shape. Catch the one type and you're
covered.

```python
from weathercloud import WeathercloudClient, WeathercloudError

try:
    cond = client.get_current_conditions(device_id)
except WeathercloudError as exc:
    ...  # set unavailable, log it, retry — your call
```

## 🔎 Finding a device ID

It's the number at the end of the station URL:

```
app.weathercloud.net/d5726468552  →  device_id = "5726468552"
```

METAR (airport) stations use ICAO codes (`EBBR`, `EGLL`, …) and work on most
`device/*` endpoints — just swap the prefix to `metar/*`.

## 💡 Notes

- 🔓 No authentication required for any endpoint.
- ⏱️ Poll at most every 10 minutes — that's how often free stations update.
- 🧭 Based on the [reverse-engineered OpenAPI spec](./docs/openapi.yaml) in this repo.

## 🛠️ Development

```sh
git clone https://github.com/MauroDruwel/Weathercloud-API
cd Weathercloud-API
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

ruff check .      # lint
mypy              # type-check
pytest            # tests
python -m build   # build sdist + wheel
```

CI runs the linter, type checker, and the test matrix (Python 3.10–3.13) on every
push and pull request.

### Local API explorer (Swagger UI)

A Swagger UI is hosted at
**[weathercloud-api.maurodruwel.be](https://weathercloud-api.maurodruwel.be)**, or
run it locally against a small CORS proxy:

```sh
pip install flask
python docs/proxy.py   # serves the proxy + Swagger UI on :8765
# then open docs/index.html
```

## 📄 License

[MIT](LICENSE)
