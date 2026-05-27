# Weathercloud Unofficial API

Reverse-engineered OpenAPI 3.0 spec for [app.weathercloud.net](https://app.weathercloud.net).

> **No authentication required** — all endpoints work without any CSRF token or login (verified by testing).

---

## Browse the docs

Open `index.html` in any static file server, or visit the hosted version:

→ **[View swagger](https://weathercloud-api.maurodruwel.be)**

---

## Try it out locally

The Swagger UI's **Try it out** feature requires a local proxy to avoid CORS restrictions from the browser.

**Requirements:** Python 3.8+ and Flask

```bash
pip install flask
python proxy.py
```

Then open **[http://localhost:8765](http://localhost:8765)**.

The proxy forwards requests to `https://app.weathercloud.net` and adds the required CORS headers.

---

## Import into Postman

1. Open Postman → **File → Import**
2. Upload `openapi.yaml` (or paste its raw GitHub URL)
3. All endpoints are imported with examples and descriptions

---

## File overview

| File | Purpose |
|------|---------|
| `openapi.yaml` | The API spec — single source of truth |
| `index.html` | Swagger UI shell — loads `openapi.yaml` at runtime |
| `proxy.py` | Local CORS proxy (Flask) for Try it out |

---

## Device ID

The numeric ID in the URL: `app.weathercloud.net/d`**`5726468552`**
