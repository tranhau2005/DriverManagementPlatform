# Design Document — Driver Management Platform MVP (M1–M5)

## Overview

The MVP is a single deployable backend (`services/api`) — a FastAPI modular monolith backed by
PostgreSQL 16 — plus a React admin web app (`apps/web`). All business writes go through the API
synchronously; there is no Kafka, outbox, or analytics pipeline in the MVP. The design implements
the authoritative schema in `docs/schema.dbml` and the conventions in `AGENTS.md`.

This design satisfies `requirements.md`. Where a table belongs to a `[NEEDS-OWNER]` domain
(bookings, leave, scheduling/timekeeping, payroll), the MVP creates storage + migrations only;
lifecycle logic is stubbed with `NotImplementedError` and a `# NEEDS-OWNER:` comment.

## Architecture

```
apps/web (React+Vite+TS, Admin)
        │  HTTPS / REST (JSON)
        ▼
services/api  (FastAPI modular monolith)
  app/main.py            app factory, exception handler, router registration
  app/core/              config (DATABASE_URL from env), db session, security (JWT, hashing)
  app/domains/<name>/    router → service → repository → models/schemas
        │
        ▼
PostgreSQL 16  (operational data; integrity enforced by constraints)
```

Principles (from steering `tech.md` / `structure.md`):
- One-directional layering: router → service → repository. ORM never serialized; Pydantic at the boundary.
- The API is the only write path for business data.
- Integrity is enforced in the database (CHECK/enum/EXCLUDE/FK), not just in app code.

## Components and Interfaces

### Core (`app/core/`)
- `config.py` — settings from env; `DATABASE_URL` default `postgresql+psycopg://postgres:postgres@localhost:5432/dmp`.
- `db.py` — async SQLAlchemy 2.x engine + session dependency.
- `security.py` — JWT encode/decode, password hashing (argon2/bcrypt), current-account dependency, role guard.
- `errors.py` — typed exceptions (`NotFound`, `Conflict`, `ValidationError`, `Forbidden`) + single FastAPI handler → 404/409/422/403.

### Domains (MVP active)
| Domain | Tables | MVP responsibility |
|---|---|---|
| `accounts` (auth) | accounts | login, me, account CRUD (ADMIN), role/link CHECK |
| `areas` | areas | simple catalog CRUD (supports driver area filter) |
| `drivers` | drivers, employment_history, driver_licenses | driver CRUD, license CRUD, status-change history, overlap rejection, soft-archive |
| `vehicles` | vehicles, driver_vehicles | vehicle CRUD, assignment with non-overlapping intervals |

### Domains (storage-only / stubbed in MVP)
`customers`, `bookings`, `leave` (leave_requests, leave_actions), `scheduling`
(work_schedule, activity_sessions), `payroll` (income_policies, payroll_periods, payrolls,
payroll_adjustments): models + migration only; service methods raise `NotImplementedError` with
`# NEEDS-OWNER:` comments.

### Representative endpoints (MVP)
- `GET /health` → `{"status":"ok"}`
- `POST /auth/login` → `{access_token, token_type}`; `GET /auth/me`
- `GET/POST/PATCH /accounts` (ADMIN only)
- `GET/POST/PATCH /drivers`, `GET /drivers?area_id=&status=&page=&page_size=`
- `POST /drivers/{id}/licenses`, `POST /drivers/{id}/status` (writes employment_history)
- `GET/POST/PATCH /vehicles`, `POST /vehicles/{id}/assignments` / `POST /drivers/{id}/assignments`

## Data Models

Authoritative source: `docs/schema.dbml` (identical to handoff Section 14), 17 tables, every table
with a `bigint` identity PK. Uniqueness and keys preserved exactly:
`accounts.username`, `drivers.driver_code`, `drivers.citizen_id`, `driver_licenses.license_number`,
`vehicles.plate_number`, `bookings.booking_code`, `customers.phone`, `activity_sessions.source_key`;
`work_schedule(driver_id, work_date)`, `income_policies(driver_id, month)`,
`payrolls(period_id, driver_id)`, `payroll_periods.month`, `payrolls.policy_id` (all unique).

### Integrity added via migration (closing DBML gaps)
1. Enum/CHECK for every status/role/type column.
2. `accounts` driver/customer XOR + role-match CHECK.
3. `EXCLUDE` (btree_gist) against overlapping intervals on `employment_history` and `driver_vehicles`.
4. `date_trunc('month', month) = month` CHECK on month columns.
5. `ON DELETE RESTRICT` on FKs + soft-archive via `archived_at`.

### Flagged ambiguity (do not silently fix)
`payrolls.policy_id` UNIQUE / 1:1 to `income_policies` vs. the `(driver_id, month)` and
`(period_id, driver_id)` keys. Preserved as-is; resolution is `[NEEDS-OWNER]` before payroll logic.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

These properties capture the database-enforced invariants the MVP relies on. They are universally quantified and suitable for property-based testing against a disposable Postgres instance.

### Property 1: Employment-history intervals never overlap per driver

*For any* driver and *any* set of accepted `employment_history` rows for that driver, no two validity intervals `[valid_from, valid_to)` overlap.

**Validates: Requirements 2.5, 4.6**

### Property 2: Active assignments never overlap per driver or per vehicle

*For any* set of accepted active `driver_vehicles` assignments, no two active intervals overlap for the same driver, and no two active intervals overlap for the same vehicle.

**Validates: Requirements 2.5, 5.4**

### Property 3: Month columns are always the first day of the month

*For any* accepted `income_policies.month` or `payroll_periods.month` value, `date_trunc('month', month) = month` holds; any value that is not the first day of its month is rejected.

**Validates: Requirements 2.4**

### Property 4: Account driver/customer link is exclusive and role-matched

*For any* `accounts` row, `driver_id` and `customer_id` are never both set, and the set link matches the role (DRIVER → `driver_id` only, CUSTOMER → `customer_id` only, ADMIN → neither). Any row violating this is rejected.

**Validates: Requirements 2.3, 3.7**

### Property 5: password_hash is never exposed in API responses

*For any* account rendered by any endpoint that returns account data, the response body contains no `password_hash` field (and no raw password).

**Validates: Requirements 3.3, 3.4**

### Property 6: Re-assignment keeps at most one active assignment per driver

*For any* sequence of assign/re-assign operations on a driver, re-assignment closes the prior active interval, so at most one active `driver_vehicles` interval (open `valid_to`) exists for that driver at any time.

**Validates: Requirements 5.3**

## Error Handling

Services raise typed domain exceptions; a single FastAPI exception handler maps:
`NotFound`→404, `Conflict`→409 (e.g., overlap/unique), `ValidationError`→422, `Forbidden`→403.
Auth failures return a generic message that does not reveal which credential field was wrong.

## Security & PII

- JWT bearer with a role claim; role guard dependency enforces ADMIN-only routes. The server is the
  sole authorization enforcer; the web app only hides/disables actions.
- Passwords stored as argon2/bcrypt hashes; never returned or logged.
- PII on `drivers` is never logged; sensitive-field read/change should record an audit entry
  (exact masking/retention is `[NEEDS-OWNER]`).

## Testing Strategy

- `pytest` + `pytest-asyncio` against a disposable Postgres (dev compose).
- Each endpoint: happy-path, auth/permission (403), validation/error tests.
- Each migration constraint: a rejection test proving bad data is refused (overlaps, bad enum, both
  account links set, non-first-of-month).
- Round-trip test for one account + one driver (M2).
- Fixtures use fake data only — no real PII or secrets.
- Web: `npm run build` + `npm run lint` must pass; typed API client, no `any` at the boundary.
