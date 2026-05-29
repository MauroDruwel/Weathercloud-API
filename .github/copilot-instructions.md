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

## Refactoring history (context for future sessions)

This section captures decisions made during the initial overhaul session so future sessions don't re-litigate them.

### Structure

The library was originally a single `weathercloud.py` at the repo root. It was converted to a `src/` layout package (`src/weathercloud/`) to:
- prevent accidental imports of the source tree instead of the installed package
- match the PyPI-standard package structure
- allow clean split of concerns across `exceptions.py`, `models.py`, `client.py`

Public import paths are **unchanged** — consumers still do `from weathercloud import WeathercloudClient, ...`. All public names are re-exported from `__init__.py`.

### Session/HTTP

- `get_station_name` used to call bare `requests.get()`; it now uses `self._session` so the connection pool and headers are reused.
- The session carries `X-Requested-With: XMLHttpRequest`, `Accept: application/json`, and `User-Agent: Mozilla/5.0`. The last header matters — the station page scrape needs it.
- `close()` and `__enter__`/`__exit__` were added so callers can manage the connection pool.

### Partial station handling

Stations vary widely in which sensors they expose. The original code raised `WeathercloudError` on any missing key. After the overhaul:
- All `CurrentConditions` fields are `T | None`.
- `_to_float` and `_to_int` in `client.py` silently return `None` for missing, empty, `null`, or unparseable values.
- `get_station_info` similarly falls back to empty string / 0 for missing device fields.
- A genuinely broken response (e.g. the API returns a JSON array instead of an object) still raises `WeathercloudError`.

### CI

Two workflows:
- `ci.yml` — runs on every push/PR: ruff → mypy → pytest matrix (3.10–3.13) → build + twine check + wheel smoke-test
- `publish.yml` — runs on GitHub release published: build → twine check → PyPI upload via OIDC trusted publishing (no stored secrets)

Publish workflow uses `permissions: contents: read` at the top level and `id-token: write` only in the publish job.

### README style

The README targets developers, not end users. Light emoji on section headers only. Badges at the top (PyPI version, Python versions, CI, license). Includes a table of `CurrentConditions` fields with types and units. Does not list every method in exhaustive detail — links to the OpenAPI spec at `docs/openapi.yaml` and the hosted Swagger UI instead.

