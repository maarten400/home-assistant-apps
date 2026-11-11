# Nod

Nod is a self-hosted personal agent. This add-on runs the Nod server and exposes
its web interface through Home Assistant Ingress.

## Configuration

- **Model provider**: Provider identifier, for example `openai`.
- **Model API key**: API key for the selected model provider.
- **Public URL**: Optional externally reachable URL used by Nod.

## Important

Nod requires its workspace and browser containers. Run them on the Home Assistant
host or another always-on Docker host using the repository's `compose.yaml`.

Do not expose this add-on directly to the internet. Use Home Assistant Ingress,
a reverse proxy with authentication, or a VPN.
