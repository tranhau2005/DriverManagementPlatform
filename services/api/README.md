# Driver Management Platform API

The API uses Python 3.12, FastAPI, SQLAlchemy's async engine, and PostgreSQL 16.
The development database connection defaults to the local Compose database and can be
overridden with `DATABASE_URL`.

From the repository root, start PostgreSQL:

```bash
docker compose -f infra/compose/docker-compose.yml up -d db
```

From `services/api`, install dependencies and run checks:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

To run the API locally from `services/api`:

```bash
uv run uvicorn app.main:app --reload
```

Set `DATABASE_URL` in the environment or copy `.env.example` to `.env` for local
development. Alembic is configured for async PostgreSQL connections; schema models and
migrations are added in a later milestone.
