# Copilot instructions for weathercloud

Unofficial, fully-typed Python client for the Weathercloud API, published on PyPI as `weathercloud`.

## Commands

```sh
# Install in editable mode with all dev tools
pip install -e ".[dev]"

# Lint
ruff check .

# Type-check
mypy

# Full test suite
pytest

# Single test
pytest tests/test_client.py::test_get_current_conditions_returns_typed_dataclass

# Build + verify package
python -m build && twine check dist/*
```

## Architecture

`src/weathercloud/` is a src-layout package with four files:

- `exceptions.py` — `WeathercloudError` (single exception for all failures)
- `models.py` — `CurrentConditions`, `StationInfo` dataclasses; `VariableCode` IntEnum
- `client.py` — `WeathercloudClient` and module-level `_to_float`/`_to_int` coercion helpers
- `__init__.py` — re-exports everything; defines `__version__`

`WeathercloudClient` wraps a `requests.Session`. Every public method raises `WeathercloudError` on network, HTTP, or parse failure — nothing else escapes. The session is shared across all requests; the client is a context manager (`with WeathercloudClient() as c`).

The two-layer call pattern in `client.py`:
- `_get`/`_post` → returns `Any`, wraps all `requests.RequestException`
- `_get_dict`/`_post_dict` → calls the above and validates the result is a `dict`; used by all raw public methods

## Key conventions

**Optional sensor fields** — `CurrentConditions` fields are all `float | None` or `int | None`. Stations only report the sensors they have. The `_to_float`/`_to_int` helpers in `client.py` absorb missing keys, empty strings, `None`, and unparseable values silently. Never raise on a missing sensor.

**One exception type** — all failures (network, HTTP 4xx/5xx, non-JSON body, unexpected response shape) raise `WeathercloudError`. Don't introduce other exception types.

**Raw API key mapping** — the upstream API uses short keys (`temp`, `hum`, `bar`, `wspd`, `wspdhi`, etc.). The mapping to human names lives in `get_current_conditions` in `client.py`. When adding a new field, add it to the dataclass in `models.py` and map it from the raw key in `client.py`.

**`StationInfo.name` is scraped** — it isn't in any JSON endpoint; `get_station_name` GETs `/d{device_id}` and regex-parses the `<title>`. Pass `scrape_name=False` to skip it.

**Nearby stations ×10 scaling** — `get_nearby_stations` returns sensor values multiplied by 10 (upstream convention). This is intentional and documented; do not silently correct it in the library.

**Tests use `responses` for HTTP mocking** — no live network calls in tests. Register mocks with `@responses.activate` and `responses.get()`/`responses.post()`. The `VALUES_PAYLOAD` fixture in `test_client.py` holds a realistic full response; mutate a copy for partial/error cases.

**Type checking is strict** — `mypy --strict` is enforced in CI. All new code must pass without `# type: ignore` suppressions.

**`__version__` is the single source of truth** — defined in `src/weathercloud/__init__.py`; `pyproject.toml` reads it via `dynamic = ["version"]` + `attr = "weathercloud.__version__"`.
