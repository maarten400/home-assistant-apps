# Nod Home Assistant add-on

Self-hosted Nod personal agent server for Home Assistant.

## Model providers

The add-on supports:

- `ollama`: local Ollama models through its OpenAI-compatible endpoint.
- `claude-subscription`: a local Claude Code-backed OpenAI-compatible proxy running inside this add-on.
- `openai-compatible`: any OpenAI-compatible endpoint, such as LM Studio, vLLM, LiteLLM, or OpenRouter.

## Claude Pro subscription

This option is intended for **personal use with your own Claude Pro subscription**. It runs a local proxy inside the add-on and uses Claude Code with a Claude subscription OAuth token.

1. On a computer where you can sign in interactively, run:

   ```bash
   claude setup-token
   ```

2. Copy the generated token into the add-on option `claude_subscription_token`.

3. Set:

   ```yaml
   model_provider: claude-subscription
   claude_subscription_enabled: true
   claude_model: claude-sonnet-4-5
   claude_proxy_port: 3457
   ```

4. Set `claude_proxy_command` to the command that starts your local subscription proxy. For example:

   ```yaml
   claude_proxy_command: "node /opt/ocp/ocp --host 127.0.0.1 --port 3457"
   ```

The proxy listens only on `127.0.0.1` inside the add-on container. Nod connects to:

```text
http://127.0.0.1:3457/v1
```

## Important notes

- This does **not** use an Anthropic API key and does not create Anthropic API billing.
- The Claude subscription token is a Claude Code OAuth token, not an Anthropic API key.
- Claude Pro usage limits and token expiry still apply.
- Anthropic’s terms restrict intermediating Claude.ai credentials and routing subscription usage on behalf of other users. Use this only for your own personal Nod instance and review Anthropic’s current terms before relying on it.
- The OCP startup command and health endpoint may need adjustment for the version installed by the Dockerfile.
