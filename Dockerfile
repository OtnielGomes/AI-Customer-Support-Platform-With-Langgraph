# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .python-version README.md ./
RUN uv sync --no-dev --no-install-project

COPY app ./app
RUN uv sync --no-dev

FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app
COPY alembic.ini ./
COPY migrations ./migrations
COPY data ./data
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
