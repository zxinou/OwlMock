# syntax=docker/dockerfile:1.7

FROM node:22.18.0-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.8.4 AS uv

FROM python:3.13.5-slim-bookworm AS backend-deps
COPY --from=uv /uv /uvx /bin/
WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.13.5-slim-bookworm AS production
RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates git tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 owlmock \
    && useradd --uid 10001 --gid owlmock --create-home --home-dir /home/owlmock owlmock

WORKDIR /app/backend
COPY --from=backend-deps --chown=owlmock:owlmock /app/backend/.venv ./.venv
COPY --chown=owlmock:owlmock backend/ ./
COPY --from=frontend-build --chown=owlmock:owlmock /build/frontend/dist /app/frontend/dist
COPY --chown=root:root docker/entrypoint.sh /usr/local/bin/owlmock-entrypoint

RUN mkdir -p /data \
    && chown owlmock:owlmock /data \
    && chmod 0755 /usr/local/bin/owlmock-entrypoint

ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OWLMOCK_DATA_DIR=/data \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/live', timeout=3)"]

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/owlmock-entrypoint"]
CMD ["sh", "-c", "exec uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*' --timeout-graceful-shutdown 30"]
