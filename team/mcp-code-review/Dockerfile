FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml .
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini .
RUN uv sync --no-dev --frozen
ENTRYPOINT ["uv", "run", "mcp-code-review"]
