FROM ghcr.io/astral-sh/uv:0.12.3 AS uv

FROM python:3.13-slim AS base

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project

COPY src ./src

RUN uv sync --locked --no-dev --no-editable

FROM base AS migrate

COPY alembic.ini ./
COPY migrations ./migrations

RUN uv sync --locked --dev --no-editable

CMD ["alembic", "upgrade", "head"]

FROM base AS runtime

EXPOSE 8000

CMD ["uvicorn", "ledgerlab.main:app", "--host", "0.0.0.0", "--port", "8000"]
