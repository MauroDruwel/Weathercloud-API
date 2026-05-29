"""
Weathercloud API proxy + Swagger UI server.
Runs on http://localhost:8765

- GET /           → Swagger UI
- GET /openapi.yaml → OpenAPI spec
- ANY /proxy/*    → proxied to https://app.weathercloud.net/*
"""

import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, Response, request, send_from_directory

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
UPSTREAM = "https://app.weathercloud.net"

PROXY_REQUEST_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://app.weathercloud.net/",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

# Headers from upstream that we pass back (blocklist approach)
SKIP_RESPONSE_HEADERS = {
    "transfer-encoding", "connection", "content-encoding",
    "content-length", "keep-alive",
}


def add_cors(response: Response) -> Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, X-Requested-With, Authorization"
    )
    return response


@app.after_request
def cors_after(response: Response) -> Response:
    return add_cors(response)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def static_files(path):
    if path == "" or path == "index.html":
        return send_from_directory(BASE_DIR, "index.html")
    if path == "openapi.yaml":
        return send_from_directory(BASE_DIR, "openapi.yaml")
    return "Not found", 404


@app.route("/proxy/", defaults={"upstream_path": ""}, methods=["GET", "POST", "OPTIONS"])
@app.route("/proxy/<path:upstream_path>", methods=["GET", "POST", "OPTIONS"])
def proxy(upstream_path):
    if request.method == "OPTIONS":
        return Response(status=204)

    # Reconstruct upstream URL including query string
    query = request.query_string.decode()
    url = f"{UPSTREAM}/{upstream_path}"
    if query:
        url = f"{url}?{query}"

    headers = dict(PROXY_REQUEST_HEADERS)

    # Forward the body for POST requests
    body = None
    if request.method == "POST":
        body = request.get_data()
        content_type = request.content_type or "application/x-www-form-urlencoded"
        headers["Content-Type"] = content_type

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=request.method)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
            status = resp.status
            resp_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in SKIP_RESPONSE_HEADERS
            }
    except urllib.error.HTTPError as e:
        content = e.read()
        status = e.code
        resp_headers = {}
    except Exception as e:
        return Response(f"Proxy error: {e}", status=502)

    return Response(content, status=status, headers=resp_headers)


if __name__ == "__main__":
    print("Weathercloud Swagger UI → http://localhost:8765")
    app.run(host="0.0.0.0", port=8765, debug=False)
