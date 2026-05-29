# weathercloud

Unofficial Python client for [Weathercloud](https://app.weathercloud.net). No account needed.

> Reverse-engineered from HAR captures. Not affiliated with Weathercloud.

```sh
pip install weathercloud   # not on PyPI yet — clone and pip install -e .
```

---

## Quick start

```python
from weathercloud import WeathercloudClient

client = WeathercloudClient()
cond = client.get_current_conditions("5726468552")

print(cond.temperature)   # 22.8
print(cond.humidity)      # 62
print(cond.wind_gust)     # 1.4
```

The client owns a `requests.Session`. Use it as a context manager (or call
`client.close()`) to release the connection pool when you're done:

```python
with WeathercloudClient(timeout=30) as client:
    cond = client.get_current_conditions("5726468552")
```

---

## API

### `get_current_conditions(device_id)` → `CurrentConditions`

Live sensor readings as a typed dataclass. The one you'll call most.

```python
cond = client.get_current_conditions("5726468552")
cond.temperature      # float °C
cond.dew_point        # float °C
cond.wind_chill       # float °C
cond.heat_index       # float °C
cond.humidity         # int %
cond.pressure         # float hPa
cond.wind_speed       # float m/s (instantaneous)
cond.wind_speed_avg   # float m/s
cond.wind_gust        # float m/s
cond.wind_direction   # int °
cond.rain             # float mm
cond.rain_rate        # float mm/h
cond.solar_radiation  # float W/m²
cond.uv_index         # int
cond.epoch            # int unix timestamp
```

### `get_station_info(device_id, scrape_name=True)` → `StationInfo`

Station metadata. The name isn't in any JSON endpoint, so it's scraped from HTML (one extra request). Pass `scrape_name=False` to skip it.

```python
info = client.get_station_info("5726468552")
info.name                   # "Ginometeo"
info.city                   # "Ingelmunster"
info.altitude               # "18.0"  (metres, as string)
info.status                 # "online" | "recently_online" | "offline"
info.seconds_since_update   # int
info.account_type           # 0 = free, >0 = premium
```

### `get_device_stats(device_id)` → `dict`

Current readings + day / month / year min–max. Each value is a `[unix_timestamp, value]` pair.

```python
stats = client.get_device_stats("5726468552")
stats["temp_day_max"]       # [1748358122, 30.9]
stats["rain_month_total"]   # [1748358122, 12.4]
```

Key pattern: `{sensor}_{period}_{type}` — e.g. `wspd_year_max`, `rain_day_total`.

### `get_evolution(device_id, variable, period)` → `dict`

Hourly history for one sensor. `period` is `"day"`, `"week"`, `"month"`, or `"year"`.

```python
from weathercloud import VariableCode

evo = client.get_evolution("5726468552", VariableCode.TEMPERATURE, "week")
```

Available codes: `TEMPERATURE`, `HUMIDITY`, `DEW_POINT`, `PRESSURE`, `WIND_SPEED`, `WIND_DIRECTION`, `WIND_GUST`, `RAIN`, `RAIN_RATE`, `SOLAR_RADIATION`, `UV_INDEX`.

### `get_forecast(device_id)` → `dict`

6-day WMO daily forecast for the station's location.

### `get_nearby_stations(lat, lon, distance_km=5)` → `dict`

Stations within radius. Note: sensor values inside each result are **×10 integers** — divide by 10.

### Other raw methods

```python
client.get_device_values(device_id)    # same data as get_current_conditions, as raw dict
client.get_device_info(device_id)      # metadata + current values as strings
client.get_wind_rose(device_id)        # wind direction distribution
client.get_update_status(device_id)    # seconds since last update
client.get_owner_profile(device_id)    # observer name, hardware brand/model
client.get_station_name(device_id)     # scrape name only
```

---

## Error handling

Everything raises `WeathercloudError` on failure (network error, bad JSON, HTTP error).

```python
from weathercloud import WeathercloudError

try:
    cond = client.get_current_conditions(device_id)
except WeathercloudError as exc:
    # handle it — set unavailable in HA, log it, whatever
    print(exc)
```

---

## Device IDs

The number at the end of the station URL:

```
app.weathercloud.net/d5726468552  →  device_id = "5726468552"
```

METAR (airport) stations use ICAO codes (`EBBR`, `EGLL`, …) and work on most `device/*` endpoints — just swap the prefix to `metar/*`.

---

## Notes

- **No auth required** for any of these endpoints
- **Poll at most every 10 minutes** — that's how often free stations update
- Default request timeout is 10 s — override with `WeathercloudClient(timeout=30)`
- Based on the [reverse-engineered OpenAPI spec](./docs/openapi.yaml) in this repo

---

## Development

The package is fully typed (ships `py.typed`) and lives under `src/weathercloud/`.

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

CI runs lint, type-check, and the test matrix (Python 3.10–3.13) on every push
and pull request.

---

## Swagger UI / OpenAPI docs

Hosted at **[weathercloud-api.maurodruwel.be](https://weathercloud-api.maurodruwel.be)** — or run locally:

```sh
pip install flask
python docs/proxy.py   # starts proxy on :8765
# open docs/index.html
```

