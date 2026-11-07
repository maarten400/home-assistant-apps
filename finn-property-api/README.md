# FINN Property API - Home Assistant app

Experimental API packaged for Home Assistant OS / Supervisor, amd64 and aarch64.
This adds an app, not a Home Assistant custom integration or automatic sensors.
Source copied from maarten400/finn-property-api commit fdec14093f4720da80f66d5e45591f86ed1dd40f.
The private n8n workflow and its LAN configuration are intentionally not included.

## Important status

The parser has passed synthetic unit tests ONLY. Live FINN extraction, image
builds and Supervisor installation have NOT been verified. It scans JSON-LD
and __NEXT_DATA__ for listing URLs, title, price and coordinates. Actual FINN
markup may require a new adapter. Unknown/incomplete recognized data raises
PARSE_FAILED; listings absent from the scripts cannot be detected. Explicitly
empty JSON-LD ItemList can return []. Pagination/sort semantics are unverified.
Do not replace a working monitor until actual results and completeness are tested.
No browser, access-control bypass, proxy rotation or private API is included.
FINN requires written crawling permission: https://www.finn.no/robots.txt .
The permission option acknowledges permission; it does not grant any rights.

## Install in Home Assistant

1. Add https://github.com/maarten400/home-assistant-apps to the app store's
   repository list, or refresh it if already added.
2. Find FINN Property API and install. The image is built locally; no registry
   image or private-repository token is needed.
3. In Configuration set api_key to a NEW random secret, at least 24 characters.
4. Leave finn_permission_confirmed false until permission is obtained.
5. save_failure_html defaults to false. Enable only temporarily for diagnostics.
6. Review Network: internal TCP 8000 maps to host port 8089 by default. Choose
   another free host port if necessary. Restrict access to trusted clients.
7. Start the app and inspect its Log tab. Enable start-on-boot/watchdog if wanted.

Options are read from /data/options.json. Startup creates /data/diagnostics
with mode 0700, then drops to UID/GID 10001 before running the API. No host
networking, hardware, Supervisor API or Home Assistant API access is requested.
Do not disable protection mode just to troubleshoot a failed build/start.

## n8n connection

Use http://YOUR_HA_HOST:8089/api/finn/v1/eiendom/search?sub=homes&page=1&price_to=6000000&sort=PUBLISHED_DESC
when the host port is 8089. YOUR_HA_HOST must be reachable from n8n; localhost
in an n8n container refers to n8n, not Home Assistant. Set a Header Auth
credential named x-api-key to the configured app api_key. Keep the six-hour
schedule in n8n. This app does not fix downstream routing, SQL or AI workflow
issues. Use trusted LAN/VPN transport or an HTTPS proxy; never publish the
plain HTTP port or API key to the Internet.

GET /healthz is unauthenticated and reports service health, not FINN availability.
GET /docs provides the generated API documentation. Searches require the key
and permission flag. Supported parameters: sub=homes; page=1..100; positive
price_to (default 6000000); sort=PUBLISHED_DESC. Successful output is an array:
id, title, url, price_nok, latitude, longitude. Price is also filtered locally.

## Diagnostics

Uncached fetches log JSON metadata and save it under /data/diagnostics. Errors
return request_id and a code, with X-Request-ID on fetch responses. Codes include
PARSE_FAILED, UPSTREAM_HTTP_ERROR, UPSTREAM_TIMEOUT, UPSTREAM_NETWORK_ERROR,
RESPONSE_TOO_LARGE, UNEXPECTED_CONTENT_TYPE and LOCAL_RATE_LIMIT. Authentication
and validation failures use the standard FastAPI error format. Cached responses
and local throttle/auth/validation failures do not create metadata files.

Failed HTML capture is opt-in and NOT redacted: it may include personal data
or site-generated tokens. It is never served over HTTP. Restrict backup/data
access and delete captures after investigation. Old diagnostic files are removed
after 24 hours on the next uncached fetch, not by a background timer. Options
are stored outside that cleanup directory and are not deleted. Supervisor
controls its own log retention. Options/backups contain your API key: protect them.

One worker; at most one upstream request per minute; 15-minute success cache
(up to 100 entries); 30-second network timeout; 5 MiB response limit; no automatic
retry or redirect following. A 3xx is reported as an upstream error for review.
A 429 includes Retry-After. Do not add workers/replicas without shared limiting.

## Standalone Docker (outside Home Assistant)

From this directory: copy .env.example to .env, replace API_KEY and configure
the permission flag only after permission. Run docker compose up -d --build.
Compose uses Dockerfile.standalone, not the app launcher. It publishes only
127.0.0.1:8000; attach n8n to a common Docker network or use a restricted proxy.
Standalone diagnostics use the named volume mounted at /data.

## Development

Run python -m unittest -v test_parser.py. The tests are synthetic, not live-site
compatibility tests. Python/YAML syntax and launcher option validation were checked
separately; Docker and Supervisor were not available for testing. Next validation:
install/build, verify health/auth, obtain an authorized FINN response, inspect
PARSE_FAILED diagnostics and update parser.py with sanitized regression fixtures.
Never commit .env, API keys, unredacted bodies or credential-bearing workflows.
The standalone and Home Assistant copies are separate; keep fixes synchronized.
