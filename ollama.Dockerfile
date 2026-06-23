FROM ubuntu:22.04

ARG OLLAMA_VERSION=0.7.1

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0:11434

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tgz" -o /tmp/ollama.tgz \
    && tar -C /usr -xzf /tmp/ollama.tgz \
    && rm -f /tmp/ollama.tgz

VOLUME ["/root/.ollama"]

EXPOSE 11434

ENTRYPOINT ["/usr/bin/ollama"]
CMD ["serve"]
