# Changelog

## 0.2.0

- Replace direct HTTP fetching with headed Playwright Chromium under Xvfb.
- Reuse a dedicated persistent /data/browser-profile for manual and API browsing.
- Add opt-in noVNC setup through Home Assistant Ingress; API searches pause in setup.
- Add Home Assistant sidebar metadata; native Show in sidebar is a separate toggle.
- Keep browser-control ports private; retain existing API path/key and host port.
- Add explicit bot-protection errors and optional HTML/PNG/trace failure captures.
- Default Chromium sandbox on; no automatic fallback or stealth/CAPTCHA solver.
- Bump app version; preserve old profile-independent diagnostics.
- WARNING: browser builds, Supervisor, cookies and live FINN extraction unverified.
- Standalone Compose now uses a new data volume; old diagnostics are not migrated.

## 0.1.0

- Initial experimental API and Home Assistant packaging with synthetic parser tests.
