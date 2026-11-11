# Nod

Nod is a self-hosted personal agent. This add-on runs the Nod server and exposes
its web interface through Home Assistant Ingress.

## Model configuration

### Ollama

Set **Model provider** to `ollama` and provide the Ollama URL, for example:

```text
http://host.docker.internal:11434
```

If **Model name** is empty, the add-on queries Ollama's `/api/tags` endpoint and
uses the first installed model. If discovery fails, it uses **Fallback model**.

### OpenAI-compatible servers

Set **Model provider** to `openai-compatible`, then provide:

- **Model base URL**, for example `http://192.168.1.60:1234/v1`
- **Model name**, for example `mistral-small`
- **Model API key**, if required by the server

## Dry run

Enable **Dry run** to test the connection without starting Nod. The add-on will
report the selected provider, model, base URL, and whether the model-listing
endpoint is reachable.

## Important

Nod requires its workspace and browser containers. Run them on the Home Assistant
host or another always-on Docker host using the repository's `compose.yaml`.

Do not expose this add-on directly to the internet. Use Home Assistant Ingress,
a reverse proxy with authentication, or a VPN.
