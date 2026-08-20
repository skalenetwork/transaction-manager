ARG PYTHON_VERSION=3.13.8

FROM ubuntu:24.04 AS builder

ARG PYTHON_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_MANAGED_PYTHON=1 \
    UV_PYTHON_INSTALL_DIR=/opt/python

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
RUN uv python install "${PYTHON_VERSION}" --no-bin \
    && uv sync --no-cache --no-dev --no-install-project --python "${PYTHON_VERSION}"


FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/python /opt/python
COPY --from=builder /app/.venv /app/.venv
COPY transaction_manager ./transaction_manager

CMD ["python", "-m", "transaction_manager.main"]
