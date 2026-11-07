FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl python3 python3-aiohttp libgmp10 libssl3t64 zlib1g libtinfo6 libnuma1 libgssapi-krb5-2 libsqlite3-0 && rm -rf /var/lib/apt/lists/*
RUN test "$(dpkg --print-architecture)" = arm64 && curl --fail --location --retry 3 --output /usr/local/bin/simplex-chat https://github.com/simplex-chat/simplex-chat/releases/download/v7.0.3/simplex-chat-ubuntu-24_04-aarch64 && echo '2d2e62351f11bc51ae659618584722b38ea5a6796b806c9a388ee6e3124c90ac  /usr/local/bin/simplex-chat' | sha256sum -c - && chmod 755 /usr/local/bin/simplex-chat && simplex-chat --version
WORKDIR /app
COPY app.py /app/app.py
RUN python3 -m py_compile /app/app.py
EXPOSE 8080
CMD ["python3", "/app/app.py"]
