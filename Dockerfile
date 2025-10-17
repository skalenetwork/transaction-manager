FROM python:3.13.8-slim-trixie AS builder

RUN apt update && apt install -y --no-install-recommends build-essential libssl-dev --yes

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN mkdir app
WORKDIR /app

COPY pyproject.toml ./
RUN uv pip install --prerelease=allow --system --no-cache .


FROM python:3.13.8-slim-trixie

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY transaction_manager transaction_manager

ENV PYTHONPATH="/app"
CMD ["python3", "-m", "transaction_manager.main"]
