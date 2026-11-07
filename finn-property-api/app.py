import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from parser import ParseError, parse_properties

KEY = os.getenv("API_KEY", "")
DATA = Path(os.getenv("DATA_DIR", "/data"))
TTL = 900
RETENTION = 86400
LIMIT = 5 * 1024 * 1024
lock = asyncio.Lock()
cache = {}
last_fetch = 0.0
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("finn-api")


@asynccontextmanager
async def lifespan(app):
    if len(KEY) < 24:
        raise RuntimeError("Set API_KEY to a random secret of at least 24 characters")
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False, headers={"User-Agent": "finn-property-api/0.1", "Accept": "text/html"}) as client:
        app.state.client = client
        yield


app = FastAPI(title="FINN property API", version="0.1.0", lifespan=lifespan)


def record(meta, body=None):
    now = time.time()
    for path in DATA.glob("*.*"):
        if path.is_file() and path.stat().st_mtime < now - RETENTION:
            path.unlink(missing_ok=True)
    DATA.joinpath(meta["request_id"] + ".json").write_text(json.dumps(meta), encoding="utf-8")
    if body is not None and os.getenv("SAVE_FAILURE_HTML", "false").lower() == "true":
        DATA.joinpath(meta["request_id"] + ".html").write_text(body, encoding="utf-8")
    log.info(json.dumps(meta))


@app.get("/healthz")
def health():
    return {"status": "ok", "parser": "experimental", "live_verified": False}


@app.get("/api/finn/v1/eiendom/search")
async def search(sub: Literal["homes"] = "homes", page: int = Query(1, ge=1, le=100), price_to: int = Query(6000000, gt=0), sort: Literal["PUBLISHED_DESC"] = "PUBLISHED_DESC", x_api_key: str = Header("")):
    global last_fetch
    if not hmac.compare_digest(x_api_key.encode(), KEY.encode()):
        raise HTTPException(401, "Invalid API key")
    if os.getenv("FINN_PERMISSION_CONFIRMED", "false").lower() != "true":
        raise HTTPException(403, "Obtain FINN permission, then set FINN_PERMISSION_CONFIRMED=true")
    request_id = uuid.uuid4().hex
    started = time.monotonic()
    params = {"page": page, "price_to": price_to, "sort": sort}
    meta = {"request_id": request_id, "parameters": params, "parser_version": "0.1.0"}
    body = None
    async with lock:
        cache_key = (page, price_to, sort)
        cached = cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < TTL:
            return JSONResponse(cached[1], headers={"X-Request-ID": request_id, "X-Cache": "HIT"})
        remaining = 60 - (time.monotonic() - last_fetch)
        if remaining > 0:
            return JSONResponse({"error": {"code": "LOCAL_RATE_LIMIT"}, "request_id": request_id}, status_code=429, headers={"Retry-After": str(int(remaining) + 1), "X-Request-ID": request_id})
        last_fetch = time.monotonic()
        status = 502
        code = "UPSTREAM_ERROR"
        try:
            async with app.state.client.stream("GET", "https://www.finn.no/realestate/homes/search.html", params=params) as response:
                meta["upstream_status"] = response.status_code
                meta["content_type"] = response.headers.get("content-type", "")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > LIMIT:
                        raise ValueError("RESPONSE_TOO_LARGE")
                body = content.decode("utf-8", errors="replace")
                if response.status_code != 200:
                    code = "UPSTREAM_HTTP_ERROR"
                    raise ValueError(code)
                if "text/html" not in meta["content_type"].lower():
                    raise ValueError("UNEXPECTED_CONTENT_TYPE")
            properties = parse_properties(body)
            properties = [p for p in properties if p["price_nok"] <= price_to]
            for key, entry in list(cache.items()):
                if time.monotonic() - entry[0] >= TTL:
                    del cache[key]
            if len(cache) >= 100:
                cache.clear()
            cache[cache_key] = (time.monotonic(), properties)
            meta.update(outcome="success", count=len(properties), elapsed_ms=round((time.monotonic() - started) * 1000))
            record(meta)
            return JSONResponse(properties, headers={"X-Request-ID": request_id, "X-Cache": "MISS"})
        except ParseError:
            code = "PARSE_FAILED"
        except httpx.TimeoutException:
            code, status = "UPSTREAM_TIMEOUT", 504
        except httpx.RequestError:
            code = "UPSTREAM_NETWORK_ERROR"
        except ValueError as exc:
            code = str(exc)
        meta.update(outcome="error", code=code, elapsed_ms=round((time.monotonic() - started) * 1000))
        if body is not None:
            meta["body_sha256"] = hashlib.sha256(body.encode()).hexdigest()
        record(meta, body)
        return JSONResponse({"request_id": request_id, "error": {"code": code, "message": "Check server diagnostics using request_id"}}, status_code=status, headers={"X-Request-ID": request_id})
