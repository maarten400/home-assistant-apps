# Maarten400 Home Assistant Apps

## SimpleX Alert Bot

One container with the official SimpleX CLI and an authenticated HTTP webhook for Zabbix, Alertmanager and other projects. ARM64/aarch64, including Raspberry Pi 5. Creates a NEW identity; no migration from another bot is required.

Initial release: experimental, not hardware-tested. Requires Home Assistant with an app store/Supervisor (normally Home Assistant OS); Home Assistant Container alone cannot install apps.

## Install

In Settings > Apps (called Add-ons in older versions) > App store > menu > Repositories, add:

```text
https://github.com/maarten400/home-assistant-apps
```

Refresh the store, open SimpleX Alert Bot and install. Supervisor builds the image locally; allow several minutes. Configure it BEFORE starting. Read [the full guide](simplex-alert-bot/DOCS.md).

No prebuilt third-party bot images are used. The official SimpleX ARM64 release is checksum-verified at build time. Repository code is new custom integration code, not an audited upstream product.
