# mcp-postgres — GitHub Container Registry image
# Built by .github/workflows/build-images.yml
# Pushed to: ghcr.io/chaghadi/mcp-postgres

FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini .

# Install dependencies (no dev deps in image)
RUN uv sync --no-dev --frozen

# DATABASE_URL must be injected at runtime via environment variable
# Never bake credentials into the image
ENV DATABASE_URL=""

ENTRYPOINT ["uv", "run", "mcp-postgres"]
