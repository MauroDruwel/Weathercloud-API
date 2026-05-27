# Weathercloud Unofficial API

Reverse-engineered OpenAPI 3.0 spec and unofficial Python library for [app.weathercloud.net](https://app.weathercloud.net).

> **No authentication required** — all endpoints work without any CSRF token or login (verified by testing).

---

## Repository structure

```
Weathercloud-API/
├── docs/               # Swagger UI + OpenAPI spec (served via GitHub Pages)
│   ├── openapi.yaml    # The API spec — single source of truth
│   ├── index.html      # Swagger UI shell
│   └── proxy.py        # Local CORS proxy for "Try it out"
├── weathercloud.py     # Unofficial Python client library
├── example.py          # Usage example for the Python library
└── README.md
```

---

## API Docs

Browse the interactive docs at:

→ **[weathercloud-api.maurodruwel.be](https://weathercloud-api.maurodruwel.be)**

Or import `docs/openapi.yaml` into Postman:
1. Open Postman → **File → Import**
2. Upload `docs/openapi.yaml` (or paste its raw GitHub URL)

---

## Python Library

A minimal client for the Weathercloud API — based on the OpenAPI spec above.

```python
from weathercloud import WeathercloudClient

client = WeathercloudClient()
info = client.get_device_info("5726468552")
```

See `example.py` for a full walkthrough of all endpoints.

---

## Try it out locally (Swagger UI)

The **Try it out** button in Swagger UI requires a local proxy due to browser CORS restrictions.

```bash
pip install flask
python docs/proxy.py
```

Then open **[http://localhost:8765](http://localhost:8765)**.

---

## Device ID

The numeric ID in the URL: `app.weathercloud.net/d`**`5726468552`**
