FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml .
COPY src/ ./src/
RUN uv sync --no-dev --frozen
ENV REDIS_URL="" KEY_PREFIX="mmiri28"
ENTRYPOINT ["uv", "run", "mcp-redis"]
