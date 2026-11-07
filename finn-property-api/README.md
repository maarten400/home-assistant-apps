# FINN Property API

Experimental Home Assistant app: a browser-backed property API plus an optional
interactive Chromium desktop in Home Assistant Ingress. The desktop and API use
the SAME dedicated persistent profile. The n8n request URL/key remain unchanged.

Version 0.2.0 adds Playwright, Chromium, Xvfb and an internal noVNC setup UI.
See DOCS.md for installation, sidebar controls, cookies and security limitations.

This is NOT a verified Scrappa replacement. Browser access through FINN's
protection and extraction from real listings remain unverified. No automated
CAPTCHA solver, proxy rotation or fingerprint-spoofing mechanism is included.
The existing parser is unchanged. Cookies do not guarantee future acceptance.

Your n8n workflow and private credentials are intentionally not included here.
