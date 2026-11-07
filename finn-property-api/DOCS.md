# FINN browser setup (0.2.0)

## Install and set up cookies

Refresh the app repository and update to 0.2.0. Keep your existing api_key and
API host port (default 8089). Browser downloads make this build larger.

1. Set finn_permission_confirmed=true only if you have FINN permission.
2. Enable browser_setup_enabled in Configuration, save and restart.
3. On the app Info page enable Home Assistant's native Show in sidebar toggle.
4. Open FINN Browser Setup in the sidebar, or Open Web UI. Chromium opens FINN
   when permission is confirmed. If connection is early, reopen the panel.
5. Review consent and perform any verification yourself. No CAPTCHA solver,
   stealth patches, proxy rotation or acceptance guarantee is included.
6. Disable browser_setup_enabled, save and restart GRACEFULLY. Optionally hide
   the sidebar. Do not uninstall the app: uninstalling can delete profile data.
7. Test /healthz and one n8n request before activating your schedule.

These are TWO controls: the configuration option enables browser interaction
and pauses API searches with 409 BROWSER_SETUP_ACTIVE. Home Assistant's native
Show in sidebar toggle only changes visibility. Hiding it does not disable
control. Both manual setup and automation use the SAME persistent profile and
headed Chromium under Xvfb. Configuration changes require a restart.

## Options and security

api_key: random secret, at least 24 characters; send it as x-api-key.
finn_permission_confirmed: permission acknowledgement, not a grant; false by default.
browser_setup_enabled: interactive setup, false by default.
save_failure_html: opt-in HTML, PNG and trace ZIP failure captures; not redacted.
chromium_sandbox: true by default. Some hosts/Supervisor policies prevent the
sandbox from starting. Prefer a browser-compatible host if logs show namespace/
sandbox failures. Setting this false explicitly weakens browser isolation under
untrusted website content; it is NOT a bot-protection fix. No automatic fallback,
SYS_ADMIN grant or disabled Home Assistant protection is included.

Browser/API run as UID/GID 10001. Browser child environment omits API_KEY and
SUPERVISOR_TOKEN, but desktop access is powerful: use only for this dedicated
profile, not unrelated accounts. Anyone granted Ingress access can control it.
The sidebar is admin-only by default; hiding it is not authorization.

/data/browser-profile holds sensitive cookies and is never removed by diagnostic
cleanup. /data/options.json holds the API secret. Cold backups stop the app for
profile consistency: protect backups and never share profiles/cookies publicly.
/data/diagnostics/REQUEST_ID.json stores metadata; debug captures add .html,
.png and .zip. They may contain personal data or tokens, are never served by the
API, and need host-level inspection. Files older than 24h are cleaned on the next
uncached fetch, not on a timer. No file-download UI is added.

API remains TCP 8000 / host 8089 with x-api-key. Browser UI is private Ingress
8099, restricted to Supervisor 172.30.32.2. VNC 5900 and WebSocket 6080 bind to
loopback. None of those browser-control ports is published. No new privileged
capabilities or host networking are requested in the Home Assistant manifest.

## Operation and limits

Existing n8n URL, parameters and array fields remain unchanged. Keep scheduling
in n8n. On slow hardware raise its request timeout from 60000 to 90000 ms, allowing
the API to return diagnostics. Requests are serialized, locally throttled to one
per minute and cached for 15 minutes (100 entries). Restart clears this memory
state, not the cookie profile. Do not add workers/instances sharing the profile.

/healthz checks browser context readiness, NOT FINN access. Errors include
UPSTREAM_BOT_PROTECTION, UPSTREAM_HTTP_ERROR, PARSE_FAILED, BROWSER_TIMEOUT,
BROWSER_ERROR, BROWSER_CLOSED and LOCAL_RATE_LIMIT. A closed browser requires
restart. Captures are optional. Do not continuously retry challenges.

Playwright executes JS but cookies do NOT guarantee DataDome acceptance. The
parser is UNCHANGED and synthetic-fixture-based. Successful browsing can still
produce PARSE_FAILED. Live access, fields, coverage, sorting and pagination remain
unverified. Retain a working data source until scheduled runs and restarts pass.

Standalone Compose uses the same launcher, API loopback publishing and a new
named data volume for profile+diagnostics. Old diagnostics volumes are not
migrated/deleted. Browser setup Ingress is Home Assistant only. Compose briefly
grants CHOWN/SETUID/SETGID to initialize storage, then drops user. Resource limits
are starting values, not capacity guarantees. Configure .env from .env.example.

## Validation

Python/YAML syntax and four helper tests passed: challenge detection, defaults,
setup enabling and invalid option rejection. Docker builds, Chromium launch,
noVNC/WebSockets, Supervisor/Ingress, cookies and live FINN were NOT tested.
Run python -m unittest -v test_browser.py test_parser.py for available helper
and synthetic parser tests. Test installation and all integrations before use.
