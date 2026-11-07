import asyncio
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from browser import Browser, FetchError
from settings import enabled

KEY = os.getenv("API_KEY", "")
DATA = Path(os.getenv("DATA_DIR", "/data/diagnostics"))
lock = asyncio.Lock()
cache = {}
last_fetch = float("-inf")
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("finn-api")


@asynccontextmanager
async def lifespan(app):
    if len(KEY) < 24:
        raise RuntimeError("Configure an API key of at least 24 characters")
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    app.state.browser = Browser()
    await app.state.browser.start()
    try:
        yield
    finally:
        await app.state.browser.close()


app = FastAPI(title="FINN browser API", version="0.2.0", lifespan=lifespan)


def record(meta):
    for path in DATA.iterdir():
        if path.is_file() and path.suffix in {".json", ".html", ".png", ".zip"} and path.stat().st_mtime < time.time() - 86400:
            path.unlink(missing_ok=True)
    DATA.joinpath(meta["request_id"] + ".json").write_text(json.dumps(meta), encoding="utf-8")
    log.info(json.dumps(meta))


@app.get("/healthz")
def health():
    ready = hasattr(app.state, "browser") and not app.state.browser.closed
    return JSONResponse({"status": "ok" if ready else "error", "version": "0.2.0", "browser_setup_enabled": enabled("BROWSER_SETUP_ENABLED"), "live_verified": False}, status_code=200 if ready else 503)


@app.get("/api/finn/v1/eiendom/search")
async def search(sub: Literal["homes"] = "homes", page: int = Query(1, ge=1, le=100), price_to: int = Query(6000000, gt=0), sort: Literal["PUBLISHED_DESC"] = "PUBLISHED_DESC", x_api_key: str = Header("")):
    global last_fetch
    if not hmac.compare_digest(x_api_key.encode(), KEY.encode()):
        raise HTTPException(401, "Invalid API key")
    if not enabled("FINN_PERMISSION_CONFIRMED"):
        raise HTTPException(403, "Confirm FINN permission in app configuration")
    request_id = uuid.uuid4().hex
    headers = {"X-Request-ID": request_id}
    if enabled("BROWSER_SETUP_ENABLED"):
        return JSONResponse({"request_id": request_id, "error": {"code": "BROWSER_SETUP_ACTIVE", "message": "Finish browser setup, disable browser_setup_enabled and restart"}}, status_code=409, headers=headers)
    async with lock:
        key = (page, price_to, sort)
        cached = cache.get(key)
        if cached and time.monotonic() - cached[0] < 900:
            return JSONResponse(cached[1], headers={**headers, "X-Cache": "HIT"})
        remaining = 60 - (time.monotonic() - last_fetch)
        if remaining > 0:
            return JSONResponse({"request_id": request_id, "error": {"code": "LOCAL_RATE_LIMIT"}}, status_code=429, headers={**headers, "Retry-After": str(int(remaining)+1)})
        last_fetch = time.monotonic()
        started = time.monotonic()
        meta = {"request_id": request_id, "parameters": {"page": page, "price_to": price_to, "sort": sort}, "parser_version": "0.1.0", "fetcher_version": "0.2.0"}
        try:
            properties = await app.state.browser.fetch(meta["parameters"], meta, DATA)
            properties = [p for p in properties if p["price_nok"] <= price_to]
            for old, entry in list(cache.items()):
                if time.monotonic() - entry[0] >= 900:
                    del cache[old]
            if len(cache) >= 100:
                cache.clear()
            cache[key] = (time.monotonic(), properties)
            meta.update(outcome="success", count=len(properties), elapsed_ms=round((time.monotonic()-started)*1000))
            record(meta)
            return JSONResponse(properties, headers={**headers, "X-Cache": "MISS"})
        except FetchError as exc:
            meta.update(outcome="error", code=exc.code, elapsed_ms=round((time.monotonic()-started)*1000))
            record(meta)
            return JSONResponse({"request_id": request_id, "error": {"code": exc.code, "message": "Inspect app logs and optional diagnostics; browser access and parsing are not live-verified"}}, status_code=504 if exc.code == "BROWSER_TIMEOUT" else 502, headers=headers)
