ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache bash curl git nodejs npm

WORKDIR /opt/nod

RUN git clone --depth 1 https://github.com/n8n-io/nod.git . \
 && corepack enable \
 && pnpm install --frozen-lockfile

COPY rootfs /

CMD ["/usr/bin/with-contenv", "bash", "/run.sh"]
