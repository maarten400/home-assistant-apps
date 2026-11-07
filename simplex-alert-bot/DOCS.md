# SimpleX Alert Bot: full guide

## Requirements and status

Home Assistant OS with Supervisor/app store on ARM64, such as Raspberry Pi 5. Home Assistant Container alone does not provide apps. Initial experimental release: source prepared from official documentation, but not built or hardware-tested by the authoring assistant. Protect your existing working alert path until testing succeeds.

The build uses Ubuntu 24.04 and distribution-provided Python/aiohttp packages. Only the official SimpleX CLI is downloaded; v7.0.3 and its ARM64 SHA-256 are pinned in Dockerfile. No unrelated third-party bot image is used. Existing Docker host bot is not modified.

## Installation

1. Settings > Apps > App store > menu > Repositories. Older interfaces call Apps Add-ons.
2. Add https://github.com/maarten400/home-assistant-apps
3. Refresh the store and install SimpleX Alert Bot. Image builds locally; wait for completion.
4. Configure before starting. If port 8080 is already occupied on your Home Assistant host, change the host-side port in Network (for example 8088) and use that port in all URLs below.

Generate TWO different secrets on a trusted terminal, using `openssl rand -hex 32` twice. Set:

```yaml
bot_name: HomeAlerts
bot_token: "REPLACE_WITH_FIRST_RANDOM_SECRET"
recipient: ""
allowed_recipients: []
admin_enabled: true
admin_token: "REPLACE_WITH_SECOND_RANDOM_SECRET"
```

Never use the placeholder values in production. Tokens must have at least 32 characters and differ. bot_name must have no whitespace. Name is for first creation; changing it later does not create another identity.

5. Start the app and inspect Logs. Startup creates a new bot profile in /data/simplex/bot*; no database import is needed. If it fails, retain the logs with sensitive details redacted.

## Pair the NEW identity

Use a trusted LAN computer. Replace HA_IP and secrets. The admin endpoint allows full SimpleX slash commands; enable only during setup and keep its secret separate from the alert token. Do not port-forward this service.

Create a one-time invitation:

```bash
curl --fail-with-body -sS http://HA_IP:8080/admin/command \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: YOUR_ADMIN_SECRET' \
  -d '{"command":"/connect"}'
```

Find the SimpleX invitation URI in the JSON response. Open it in SimpleX on your phone/desktop to connect to the bot. A one-time bot invitation avoids publishing a reusable address or enabling automatic acceptance of strangers.

List connected contacts:

```bash
curl --fail-with-body -sS http://HA_IP:8080/admin/command \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: YOUR_ADMIN_SECRET' \
  -d '{"command":"/contacts"}'
```

Use the contact's LOCAL display name from this response. It is your phone user's name as seen by the bot, NOT the bot's HomeAlerts profile name. For example, if localDisplayName is Maarten, configure recipient: "@Maarten". Names with whitespace are intentionally rejected in this first release; use a simple local alias/name.

If you need a reusable contact address, send `/address` through the same admin endpoint. Incoming address contact requests must be reviewed/accepted via `/ac ContactName`; do not enable unrestricted auto-accept.

Set recipient and set admin_enabled: false, save, restart. Leave admin disabled during normal operation. Enable Start on boot and Watchdog after successful first pairing/testing. Do not run a second CLI process against the same databases.

## Send a test

```bash
curl --fail-with-body -i http://HA_IP:8080/alert \
  -H 'Content-Type: application/json' \
  -H 'X-Bot-Token: YOUR_BOT_SECRET' \
  -d '{"text":"SimpleX alert test from Home Assistant"}'
```

HTTP 200 means the SimpleX client ACCEPTED the message for sending; it does not prove delivery to the recipient. Verify arrival on your phone. Do not automatically retry timed-out POST requests unless duplicate messages are acceptable. This version has no durable webhook queue or idempotency store; the sender must handle failures. No delivery receipts are tracked by the bridge.

GET /health verifies an active CLI profile, not end-to-end network delivery. A failing CLI terminates the app. Supervisor watchdog can restart unhealthy apps when enabled. No built-in TLS: use a trusted LAN/VPN or a TLS reverse proxy. Only port 8080 is exposed; unauthenticated CLI WebSocket 5225 stays on container loopback.

## Multiple projects and destinations

Projects may all use the same /alert endpoint and token with identifying text. For approved per-request routing:

```yaml
recipient: "@Maarten"
allowed_recipients:
  - "@OtherContact"
  - "#ServerAlerts"
```

Then send `{"recipient":"#ServerAlerts","text":"Project X alert"}`. Recipient must be the configured default or explicitly allowlisted; otherwise HTTP 400. Group must already be joined by the bot. Use admin commands `/connect GROUP_INVITATION_URI` and `/groups` if setting up a group, inspecting responses and completing any group approval in the regular app. The HTTP API does not create contacts/groups on demand. All allowed destinations share one alert token; this is not per-project access isolation. Separate installations/data directories are needed for independent identities. One Home Assistant app slug installs once; independent clones need distinct slugs and host ports.

## Zabbix

Create a Webhook media type named SimpleX. Parameters:

| Name | Value |
|---|---|
| URL | http://HA_IP:8080/alert |
| HTTPProxy | leave empty |
| To | {ALERT.SENDTO} |
| Subject | {ALERT.SUBJECT} |
| Message | {ALERT.MESSAGE} |
| Token | your bot_token |

Script:

```javascript
var params = JSON.parse(value);
var request = new HttpRequest();
if (params.HTTPProxy) { request.setProxy(params.HTTPProxy); }
request.addHeader('Content-Type: application/json');
request.addHeader('X-Bot-Token: ' + params.Token);
var response = request.post(params.URL, JSON.stringify({text: params.Subject + '\n\n' + params.Message}));
var status = request.getStatus();
if (status < 200 || status >= 300) { throw 'SimpleX HTTP ' + status + ': ' + response; }
return 'OK';
```

Timeout 30s. Leave Process tags and Include event menu entry off. To is not used for routing by this script.

IMPORTANT: Message templates tab > Add > Problem. Subject: `[{EVENT.SEVERITY}] {EVENT.NAME}`. Body:

```text
Host: {HOST.NAME}
Event: {EVENT.NAME}
Severity: {EVENT.SEVERITY}
Time: {EVENT.DATE} {EVENT.TIME}
Operational data: {EVENT.OPDATA}
Event ID: {EVENT.ID}
```

Also add Problem recovery. Subject: `[RESOLVED] {EVENT.NAME}`. Body:

```text
Host: {HOST.NAME}
Event: {EVENT.NAME}
Recovered: {EVENT.RECOVERY.DATE} {EVENT.RECOVERY.TIME}
Duration: {EVENT.DURATION}
Event ID: {EVENT.ID}
```

Save the media type. Missing templates cause 'No message defined for media type'. Add SimpleX media to the notification user (Send to: simplex-alerts, chosen severities, enabled). Configure trigger action operations/recovery operations to send to that user via SimpleX. When testing a webhook media type directly, fill its parameter values with literal test text if the test dialog does not resolve macros. Test from the Zabbix SERVER's network, not just your browser computer.

## Alertmanager

Use a webhook receiver pointing to http://HA_IP:8080/alert with X-Bot-Token set to your bot token. Recent Alertmanager versions support custom headers:

```yaml
receivers:
  - name: simplex
    webhook_configs:
      - url: http://HA_IP:8080/alert
        send_resolved: true
        http_config:
          http_headers:
            X-Bot-Token:
              secrets:
                - YOUR_BOT_SECRET
```

Connect this receiver through your existing route configuration; do not replace unrelated routing. Verify header support against your installed Alertmanager version and validate configuration with amtool. Bridge accepts standard alerts arrays. For older versions lacking custom headers, use a trusted reverse proxy to inject the header; never put secrets in URL query strings.

## Backups and security

/data/options.json holds app options; /data/simplex holds identity and chat databases. Use Home Assistant backups including this app. Cold backup is requested to stop the process while copying SQLite files. Backups contain secrets and cryptographic identity material: encrypt and protect them. Uninstalling/deleting app data may lose the identity. Never commit /data, tokens, invitations or backups to GitHub. No Docker socket, host networking or Home Assistant administrator API access is requested. Container uses its default root user internally; it is not a privileged container. Do not disable protection mode.

This bridge has bounded request size (64 KiB) and text length (12000 characters), but no rate limiter. Restrict network access to trusted alert senders. /admin/command exposes broad account control when enabled. Do not share its token with webhook clients. Body validation and SimpleX errors return 400/502; error responses can contain account details, so treat them as sensitive. Access logs are disabled to avoid logging headers/payloads, but upstream CLI logs may include connection metadata.

## Troubleshooting

- Build fails: inspect install/build logs. SHA mismatch intentionally stops installation. Do not bypass checksum verification.
- Startup fails: check tokens >=32 characters, distinct admin secret, bot_name without spaces, ARM64 installation.
- HTTP 401: token/header mismatch.
- HTTP 400: unset/not-allowlisted recipient, invalid body, empty/oversized text.
- HTTP 404 on admin: admin_enabled is false (expected after setup).
- HTTP 502: inspect response and app logs; verify paired local contact name and network connectivity. An unexpected successful response type may require adaptation to the pinned CLI version.
- Connection refused: verify app running, host-side port mapping, Home Assistant IP and firewall.
- HTTP 200 but no notification: accepted is not delivered; check SimpleX connectivity and phone notifications.
- Watchdog restart loop: disable Watchdog while troubleshooting; do not erase the data.

## Official references

- https://developers.home-assistant.io/docs/apps/configuration/
- https://developers.home-assistant.io/docs/apps/repository/
- https://github.com/simplex-chat/simplex-chat/blob/stable/bots/README.md
- https://github.com/simplex-chat/simplex-chat/releases/tag/v7.0.3
- https://www.zabbix.com/documentation/current/en/manual/config/notifications/media/webhook
