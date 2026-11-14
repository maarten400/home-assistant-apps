ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache bash curl git nodejs npm

WORKDIR /opt/nod

RUN git clone --depth 1 https://github.com/n8n-io/nod.git . \
 && corepack enable \
 && pnpm install --frozen-lockfile

# Claude Code is required for subscription-based authentication.
RUN npm install -g @anthropic-ai/claude-code

# OCP provides a local OpenAI-compatible endpoint backed by Claude Code.
# Pin this to a specific upstream release after validating it in your environment.
RUN git clone --depth 1 https://github.com/dtzp555-max/ocp.git /opt/ocp \
 && chmod +x /opt/ocp/ocp

COPY rootfs /

CMD ["/usr/bin/with-contenv", "bash", "/run.sh"]
