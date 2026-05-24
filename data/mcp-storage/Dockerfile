FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml .
COPY src/ ./src/
RUN uv sync --no-dev --frozen
ENV R2_ACCOUNT_ID="" R2_ACCESS_KEY_ID="" R2_SECRET_ACCESS_KEY="" R2_DEFAULT_BUCKET="mmiri28-private" R2_PUBLIC_DOMAIN=""
ENTRYPOINT ["uv", "run", "mcp-storage"]
