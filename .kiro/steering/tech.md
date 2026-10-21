# Tech Steering — Driver Management Platform

> Sources: `AGENTS.md` §2–§6, `kiro-system-architecture-handoff.md`, `docs/schema.dbml`, `.gitignore`.

## Pinned stack (AGENTS.md §2)

| Layer | Choice | Version target | Notes |
|---|---|---|---|
| Backend language | Python | 3.12 | |
| Backend framework | FastAPI | latest 0.11x | async routers |
| ASGI server | Uvicorn | latest | |
| ORM | SQLAlchemy | 2.x (typed) | never return ORM models directly as responses |
| Migrations | Alembic | latest | every schema change = one migration |
| Validation/schemas | Pydantic | v2 | request/response separate from ORM |
| Database | PostgreSQL | 16 | source of truth = DBML |
| Package manager (py) | uv | latest | installs/locking via `uv` |
| Web | React + TypeScript + Vite | React 18 | |
| Mobile | React Native + TypeScript | latest stable | Expo-managed (ASSUMPTION) |
| Backend tests | pytest + pytest-asyncio | latest | |
| Lint/format (py) | ruff | latest | lint + format |
| Lint/format (ts) | eslint + prettier | latest | |
| Container | Docker + docker-compose | latest | dev Postgres via compose |

**Deferred (target architecture only):** Kafka, Spark/PySpark, MinIO (Bronze/Silver/Gold), Trino, Superset.
Do not add Kafka until a `[NEEDS-OWNER]` async use case is confirmed (D-04).

## Backend rules (strict)

- **One-directional layering:** router → service → repository. Routers never touch the DB; services never build HTTP;
  **ORM models are never serialized to clients** — always map to a Pydantic schema.
- **Errors:** services raise typed domain exceptions (`NotFound`/`Conflict`/`ValidationError`/`Forbidden`);
  a single FastAPI exception handler maps them to HTTP (404/409/422/403). Do not scatter `HTTPException` through services.
- **Money:** `numeric(14,0)` → integer minor units; currency VND, 0 decimals (ASSUMPTION — confirm, mark `# ASSUMPTION:`).
- **Time:** store `timestamptz` in UTC; `*.month` columns are **always the first day of the month** — enforce via CHECK in the migration.
- **Auth:** JWT bearer, role claim; `password_hash` via argon2 or bcrypt. Never store raw passwords. Never log tokens or PII.
- **Attribution:** `changed_by`/`decided_by`/`actor_id`/`created_by` always reference `accounts.id`;
  populate them on every write that has such a column.

## Data integrity encoded in migrations (not only app code)

Add these as Alembic migrations with constraint SQL, since the raw DBML lacks them:

1. `accounts`: CHECK that `driver_id` and `customer_id` are not both set, and that the set link matches `role`
   (DRIVER → driver_id, CUSTOMER → customer_id, ADMIN → neither). (ASSUMPTION)
2. `employment_history` and `driver_vehicles`: prevent **overlapping validity intervals** per driver — use a
   PostgreSQL `EXCLUDE` constraint (btree_gist) or enforce in the service inside a serializable transaction. (ASSUMPTION)
3. Enum/CHECK constraints for every status/role/type column, using the allowed values in the DBML notes.
4. `*.month` columns: CHECK `date_trunc('month', month) = month`.
5. FK delete behavior: `ON DELETE RESTRICT` everywhere + soft-archive via `archived_at` on `drivers`/`customers`.
   Do not hard-delete PII. (ASSUMPTION — confirm)

**FLAG (do not silently fix):** `payrolls.policy_id` is UNIQUE and 1:1 to `income_policies`, while `income_policies`
is keyed `(driver_id, month)` and `payrolls` by `(period_id, driver_id)`. If a payroll period's month can differ
from the policy month, this 1:1 is ambiguous → `[NEEDS-OWNER]`.

## Config & secrets

- `DATABASE_URL` from env; dev default: `postgresql+psycopg://postgres:postgres@localhost:5432/dmp`.
- Never hardcode secrets; honor `.gitignore` (`.env`, `*.pem/key`, `credentials/`, etc.).

## Standard commands (AGENTS.md §4)

```bash
# dev database
docker compose up -d db

# backend (from services/api)
uv sync
uv run alembic upgrade head
uv run pytest
uv run ruff check . && uv run ruff format .

# web (from apps/web)
npm install
npm run build
npm run lint
```
Do not run the dev server / watch mode as a blocking step in automation; a human runs those manually.

## Definition of "Done" (AGENTS.md §8)

- `uv run pytest` passes (backend); `npm run build` + `npm run lint` pass (web).
- Each new endpoint has ≥1 happy-path test, 1 auth/permission test, 1 validation/error test.
- Any constraint added in a migration has a test proving it rejects bad data.
- No PII or secrets in logs or fixtures (use fake data).
- Every `[ASSUMPTION]` relied upon has a `# ASSUMPTION:` comment at the point of use.
