# AGENTS.md — DriverManagementPlatform

> **Audience:** autonomous coding agents (Codex, Claude, Gemini, Kiro, etc.).
> **Purpose:** everything you need to vibe code this project without blocking on questions.
> Read this file top to bottom before writing code. When a rule here conflicts with your defaults, this file wins.

---

## 0. TL\;DR for agents

- This is a **driver management platform**: accounts, drivers, vehicles, customers, bookings, leave/approval, timekeeping, and payroll.
- Stack: **FastAPI + PostgreSQL** backend (modular monolith), **React** web, **React Native** mobile. Monorepo.
- The schema in `docs/schema.dbml` / Appendix A is the **authoritative data model**. Do not rename tables, columns, roles, or statuses.
- Build the **MVP slice in Section 7 first**. It is fully specified - you can build it end to end without asking anyone.
- Anything marked **[ASSUMPTION]** is a reasonable default chosen so you can proceed. It is safe to build on, but leave a `# ASSUMPTION:` code comment so a human can confirm later.
- Anything marked **[NEEDS-OWNER]** is a business rule that is *not* decided. Do **not** invent it. Stub it, raise `NotImplementedError`, and add a `# NEEDS-OWNER:` comment. See Section 9.

---

## 1. Current repository state (read this - the repo is almost empty)

As of now the repository contains only:

- `kiro-system-architecture-handoff.md` - the architecture review/handoff doc (reference, not instructions).
- `.kiro/` - Kiro spec workspace.
- this `AGENTS.md`.

There is **no** application code, no `apps/`, no `services/`, no `infra/`, no `README.md` yet. Earlier docs describe these as if they exist - they do not. **You are creating them.** Scaffold the structure in Section 3 before writing feature code.

> WARNING: Do not confuse this with `.kiro/specs/driver-management-dashboard/`. That spec describes a *different, simpler* system (roles `Viewer`/`Manager`, a trimmed model). It is **not authoritative** for this platform. Use only this AGENTS.md and Appendix A.

---

## 2. Tech stack (pinned)

| Layer | Choice | Version target | Notes |
|---|---|---|---|
| Backend language | Python | 3.12 | |
| Backend framework | FastAPI | latest 0.11x | async routers |
| ASGI server | Uvicorn | latest | |
| ORM | SQLAlchemy | 2.x (typed) | models never returned directly as API responses |
| Migrations | Alembic | latest | every schema change = one migration |
| Validation/schemas | Pydantic | v2 | request/response models separate from ORM |
| Database | PostgreSQL | 16 | source of truth = Appendix A DBML |
| Package manager (py) | uv | latest | `uv` for installs/locking |
| Web | React + TypeScript + Vite | React 18 | |
| Mobile | React Native + TypeScript | latest stable | **[ASSUMPTION]** Expo-managed |
| Backend tests | pytest + pytest-asyncio | latest | |
| Lint/format (py) | ruff | latest | lint + format |
| Lint/format (ts) | eslint + prettier | latest | |
| Container | Docker + docker-compose | latest | dev Postgres via compose |

**[ASSUMPTION]** Kafka, event-consumer, data-processing, and agent-orchestrator services are **out of MVP scope**. Build the synchronous API path first. Do not add Kafka until a [NEEDS-OWNER] async use case is confirmed.

---

## 3. Monorepo layout (create this)

```
/
  AGENTS.md
  README.md                     # short: how to run; link here for details
  docker-compose.yml            # dev postgres (+ api once it exists)
  docs/
    schema.dbml                 # copy of Appendix A - keep in sync
  apps/
    web/                        # React + Vite + TS
    mobile/                     # React Native + TS   [later]
  services/
    api/
      pyproject.toml
      alembic.ini
      alembic/versions/
      app/
        main.py                 # FastAPI app factory
        core/                   # config, db session, security
        domains/
          accounts/ areas/ drivers/ licenses/ vehicles/
          customers/ bookings/ leave/ scheduling/ payroll/
        tests/
```

**Per-domain module convention (strict).** Each `domains/<name>/` folder contains:

- `router.py` - FastAPI routes; validate input, call service, map errors to HTTP.
- `service.py` - business rules; the only place rules live.
- `repository.py` - DB access; returns ORM/domain objects, no HTTP concerns.
- `models.py` - SQLAlchemy ORM models.
- `schemas.py` - Pydantic request/response models (NOT ORM).
- `tests/` - unit + integration tests for the domain.

Rules: routers never touch the DB directly; services never build HTTP responses; **ORM models are never serialized to clients** - always map to a Pydantic schema.

---

## 4. Setup and commands (make these work, then keep them working)

Agents must ensure these commands succeed. If a command does not exist yet, create the config that makes it work. Start the DB, apply migrations, then run tests. Do not run the backend dev server or any watch mode as a blocking step in automation; a human runs those manually.

```bash
# dev database
docker compose up -d db                 # Postgres 16 on localhost:5432

# backend (run from services/api)
uv sync                                  # install deps
uv run alembic upgrade head              # apply migrations
uv run pytest                            # tests must pass before a task is done
uv run ruff check . && uv run ruff format .
# backend dev server (run manually in a terminal, not in automation)

# web (run from apps/web)
npm install
npm run build
npm run lint
# web dev server (run manually in a terminal)
```

**[ASSUMPTION]** Local dev DB URL: `postgresql+psycopg://postgres:postgres@localhost:5432/dmp`. Read it from the `DATABASE_URL` env var; never hardcode secrets.

---

## 5. Backend conventions

- **Layering:** router -> service -> repository. One direction only.
- **Schemas vs models:** every endpoint takes a Pydantic request model and returns a Pydantic response model. Never return a SQLAlchemy object.
- **Errors:** services raise typed domain exceptions (`NotFound`, `Conflict`, `ValidationError`, `Forbidden`); a single FastAPI exception handler maps them to HTTP (404/409/422/403). Do not scatter `HTTPException` through services.
- **Money:** all amounts are `numeric(14,0)` -> integer minor units. **[ASSUMPTION]** currency is VND with 0 decimal places. Mark with `# ASSUMPTION:` and confirm.
- **Time:** store `timestamptz` in UTC. `month` columns are **always the first day of the month** - enforce with a CHECK constraint in the migration.
- **Auth:** **[ASSUMPTION]** JWT bearer tokens; `password_hash` via argon2 or bcrypt. Never store raw passwords. Never log tokens or PII.
- **PII:** `drivers` holds DOB, phone, address, citizen_id, emergency_contact. Restrict read access by role, never log these fields, and add an audit entry on read/change of sensitive fields. **[NEEDS-OWNER]** exact masking/retention rules.
- **Attribution:** `changed_by`, `decided_by`, `actor_id`, `created_by` always reference the acting `accounts.id`. Populate them on every write that has such a column.

### Data-integrity rules to encode in migrations (not just the app)

These close real gaps in the raw DBML. Add them as Alembic migrations with CHECK/constraint SQL:

1. `accounts`: CHECK that `driver_id` and `customer_id` are not both set, and that the set link matches `role` (DRIVER -> driver_id, CUSTOMER -> customer_id, ADMIN -> neither). **[ASSUMPTION]**
2. `employment_history` and `driver_vehicles`: prevent **overlapping validity intervals** per driver. Use a PostgreSQL `EXCLUDE` constraint (btree_gist) or enforce in the service inside a serializable transaction. **[ASSUMPTION]** overlaps are not allowed.
3. Enum/CHECK constraints for every status/role/type column, using the allowed values in the DBML notes (account role/status, employment status, booking status, leave type/status, leave action, vehicle type, adjustment type).
4. `*.month` columns: CHECK `date_trunc('month', month) = month`.
5. FK delete behavior: **[ASSUMPTION]** use `ON DELETE RESTRICT` everywhere, plus soft-archive via `archived_at` on `drivers`/`customers`. Do not hard-delete PII. **[NEEDS-OWNER]** confirm.

---

## 6. Frontend conventions

- React + TS + Vite; function components + hooks.
- Typed API client aligned to the backend OpenAPI; no `any` on API boundaries.
- Keep business rules on the server. The web app renders state and surfaces server errors; it does not re-implement payroll/booking logic.
- Role-aware UI: hide/disable actions the current role cannot perform, but **never** rely on the client for authorization - the API enforces it.

---

## 7. MVP slice - BUILD THIS FIRST (fully specified, no owner input needed)

Deliver these in order. Each is independently shippable and testable.

**M1. Project scaffold + health check**
- Create the layout in Section 3, `docker-compose.yml` with Postgres 16, a FastAPI app factory, and `GET /health` returning `{"status":"ok"}`.
- Acceptance: the DB starts, the API serves `GET /health` as 200, and `uv run pytest` runs (at least one trivial test).

**M2. Database schema + migrations**
- Translate **all** of Appendix A into SQLAlchemy models + an initial Alembic migration, including the integrity rules in Section 5.
- Acceptance: `uv run alembic upgrade head` creates every table and constraint; a round-trip test inserts and reads one `account` and one `driver`.

**M3. Accounts + auth**
- `POST /auth/login` (username + password -> JWT), `GET /auth/me`, password hashing, role on the token.
- CRUD for `accounts` restricted to `ADMIN`. Enforce the account/role/link CHECK.
- Acceptance: login succeeds/fails correctly; a non-ADMIN token gets 403 on account management; passwords are hashed and never returned.

**M4. Drivers + licenses (core domain)**
- CRUD `drivers`; list with pagination + filter by `area_id` and status; manage `driver_licenses` (unique `license_number`).
- Record an `employment_history` row on status change with `changed_by` + reason; reject overlapping intervals.
- Acceptance: create/read/update a driver; add a license; a status change writes history; overlapping history is rejected; PII fields are not logged.

**M5. Vehicles + assignment**
- CRUD `vehicles`; assign a driver to a vehicle over a validity interval via `driver_vehicles`; reject overlapping active assignments.
- Acceptance: assigning, then re-assigning closes the prior interval; an overlap is rejected.

> Stop after M5 and ask for review. M6+ (bookings lifecycle, leave approval, timekeeping aggregation, payroll calculation, reports/PDF) depend on **[NEEDS-OWNER]** business rules - see Section 9. Build CRUD/storage for those tables, but do not invent their lifecycle or formulas.

---

## 8. Testing and done-definition

A task is **done** only when:

- `uv run pytest` passes (backend) and `npm run build` + `npm run lint` pass (web).
- New endpoints have at least one happy-path test, one auth/permission test, and one validation/error test.
- Any constraint added in a migration has a test proving it rejects bad data.
- No PII or secrets appear in logs or test fixtures (use fake data).
- Every `[ASSUMPTION]` you relied on has a `# ASSUMPTION:` comment at the point of use.

---

## 9. Business rules you must NOT invent ([NEEDS-OWNER])

Stub these; raise `NotImplementedError`; add a `# NEEDS-OWNER:` comment. Do not guess.

- **Booking lifecycle:** assignment, state transitions (PENDING -> ASSIGNED -> IN_PROGRESS -> COMPLETED/CANCELLED), fare calculation, currency, cancellation fees, concurrency.
- **Leave/approval:** who may approve which request type, date limits, and the exact effect of approval on `employment_history` and schedules.
- **Timekeeping:** who or what creates `activity_sessions` (app? booking? device?), overnight/overlap/correction rules, and how sessions aggregate against `work_schedule.planned_minutes`.
- **Payroll formula:** how `net_amount` is derived from base/trip/bonus/allowance/deduction; the source of `completed_bookings`; rounding; recalculation; period locking; who may finalize; PDF template.
- **Reports:** exact metrics, filters, permissions, and templates for the three named reports.
- **Permission matrix:** anything beyond "ADMIN manages, DRIVER/CUSTOMER see their own" is unconfirmed.
- **Multi-tenancy:** the ERD has **no** organization/tenant table. Treat the system as **single-organization**. Do not add tenancy.

If you need one of these to proceed, implement storage/CRUD only, leave the rule as a stub, and surface it in your summary.

---

## 10. Open decisions (carry forward)

| ID | Decision | Default taken here | Status |
|---|---|---|---|
| D-01 | MVP scope | Section 7 (M1-M5) | [ASSUMPTION] |
| D-02 | Multi-tenant? | Single-org, no tenant table | [ASSUMPTION] |
| D-03 | DB ops / backup | dev compose only | [NEEDS-OWNER] prod |
| D-04 | Kafka in MVP? | No | [ASSUMPTION] |
| D-05 | Booking/leave/timekeeping/assignment lifecycle | storage only, rules stubbed | [NEEDS-OWNER] |
| D-06 | Identity / authz model | JWT + role claim | [ASSUMPTION] |
| D-07 | Cloud/region/topology | undecided | [NEEDS-OWNER] |
| D-08 | Report definitions | undecided | [NEEDS-OWNER] |
| D-09 | AI/agent capabilities | none in MVP | [ASSUMPTION] |

---

## Appendix A: Authoritative schema (DBML)

The canonical copy lives at `docs/schema.dbml`. Keep it identical to the DBML in `kiro-system-architecture-handoff.md` Section 14. Table names, column names, roles (`ADMIN`/`DRIVER`/`CUSTOMER`), statuses, and cardinalities are **fixed** - propose changes via a migration + comment, never silently.

Key invariants to preserve from the DBML:

- Every table has a `bigint` identity PK.
- Unique: `accounts.username`, `drivers.driver_code`, `drivers.citizen_id`, `driver_licenses.license_number`, `vehicles.plate_number`, `bookings.booking_code`, `customers.phone`, `activity_sessions.source_key`.
- `work_schedule (driver_id, work_date)` unique; `income_policies (driver_id, month)` unique; `payrolls (period_id, driver_id)` unique; `payroll_periods.month` unique; `payrolls.policy_id` unique.
- `accounts` links to at most one of driver/customer (see Section 5 rule 1).
- `*.month` = first day of the month.

> Known schema question (flag, do not silently fix): `payrolls.policy_id` is UNIQUE and FKs to `income_policies`, while `income_policies` is keyed by `(driver_id, month)` and `payrolls` by `(period_id, driver_id)`. If a payroll period's month can differ from the policy month, this 1:1 is ambiguous. Treat as **[NEEDS-OWNER]**.
