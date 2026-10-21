# Requirements Document

## Introduction

This spec defines the **Driver Management Platform MVP (M1–M5)**: the **authoritative MVP** for the Driver Management Platform — a synchronous
FastAPI + PostgreSQL modular monolith plus a React admin web app that implement the authoritative
data model in `docs/schema.dbml`. The MVP is delivered as five independently shippable slices
(M1–M5 from `AGENTS.md` Section 7). Work stops after M5 for human review.

This document is authoritative together with `docs/schema.dbml` and `AGENTS.md`. The existing
`.kiro/specs/driver-management-dashboard` spec is **not** authoritative for this platform and must
not be used as a source of requirements.

### Scope

In scope (MVP):
- M1 — Project scaffold + health check.
- M2 — Database schema + migrations + integrity constraints (all 17 tables).
- M3 — Accounts + authentication (JWT, roles).
- M4 — Drivers + licenses + employment history.
- M5 — Vehicles + driver–vehicle assignment.

### Non-Goals

- Kafka, event-consumer, data-processing, and the analytics lakehouse (MinIO/Spark/Trino/Superset).
- Multi-tenancy (the ERD has no tenant table; the system is single-organization).
- Business rules marked `[NEEDS-OWNER]`: booking lifecycle & fare calculation, leave-approval
  effects, timekeeping aggregation, payroll formula, report definitions, and any permission rule
  beyond "ADMIN manages; DRIVER/CUSTOMER see their own". For tables in these areas, build storage/CRUD
  only, stub the rules, and raise `NotImplementedError` with a `# NEEDS-OWNER:` comment.

## Glossary

- **API**: The FastAPI modular-monolith backend in `services/api`.
- **Account**: A login identity in `accounts` with a role (ADMIN/DRIVER/CUSTOMER) and status.
- **Driver**: A workforce record in `drivers` with profile, licenses, and employment history.
- **Employment History**: Time-bounded status records for a driver in `employment_history`.
- **Vehicle**: A vehicle record in `vehicles`.
- **Assignment**: A time-bounded driver–vehicle link in `driver_vehicles`.
- **Validity Interval**: A `[valid_from, valid_to)` range; an open `valid_to` means currently active.
- **JWT**: A bearer token carrying the account identity and role claim.
- **PII**: Personal data on `drivers` (date_of_birth, phone, address, citizen_id, emergency_contact).

## Requirements

### Requirement 1: Project scaffold and health check (M1)

**User Story:** As a developer, I want a runnable skeleton, so that every later slice has a working baseline.

#### Acceptance Criteria
1. WHEN `docker compose up -d db` is run, THE system SHALL start PostgreSQL 16 reachable on localhost:5432.
2. WHEN the API receives `GET /health`, THE API SHALL respond with HTTP 200 and body `{"status":"ok"}`.
3. WHEN `uv run pytest` is run from `services/api`, THE suite SHALL execute at least one test and pass.
4. THE API SHALL read `DATABASE_URL` from the environment and SHALL NOT hardcode credentials.

### Requirement 2: Database schema and migrations (M2)

**User Story:** As a developer, I want the full schema with integrity constraints, so that invalid data is rejected at the database.

#### Acceptance Criteria
1. WHEN `uv run alembic upgrade head` is run, THE migration SHALL create all 17 tables defined in `docs/schema.dbml` with the PK/unique constraints and foreign keys specified there.
2. THE migration SHALL add enum/CHECK constraints for every status/role/type column using the allowed values in the DBML notes (account role/status, employment status, booking status, leave type/status/action, vehicle type, adjustment type).
3. THE migration SHALL add a CHECK on `accounts` so that `driver_id` and `customer_id` are not both set and the set link matches `role` (DRIVER→driver_id, CUSTOMER→customer_id, ADMIN→neither).
4. THE migration SHALL add a CHECK `date_trunc('month', month) = month` on `income_policies.month` and `payroll_periods.month`.
5. THE migration SHALL prevent overlapping validity intervals per driver on `employment_history` and `driver_vehicles` via an `EXCLUDE` constraint (btree_gist) or an equivalent enforced service-level rule.
6. THE migration SHALL declare FK delete behavior as `ON DELETE RESTRICT` and SHALL provide soft-archive via `archived_at` on `drivers`/`customers` (no hard-delete of PII).
7. WHEN a round-trip test inserts and reads one `account` and one `driver`, THE test SHALL succeed.
8. IF data violating any added constraint is inserted, THEN the database SHALL reject it, and a test SHALL prove the rejection.
9. THE `payrolls.policy_id` 1:1 ambiguity SHALL be preserved as-is and flagged `[NEEDS-OWNER]`; it SHALL NOT be silently changed.

### Requirement 3: Accounts and authentication (M3)

**User Story:** As an administrator, I want secure login and account management, so that only authorized users act in the system.

#### Acceptance Criteria
1. WHEN an Account submits a valid username + password to `POST /auth/login`, THE API SHALL return a JWT carrying the account id and role claim.
2. IF the credentials are invalid, THEN THE API SHALL reject login with an authentication error and SHALL NOT disclose which field was wrong.
3. WHEN a request to `GET /auth/me` carries a valid JWT, THE API SHALL return the authenticated account's non-sensitive profile and SHALL NOT include `password_hash`.
4. THE API SHALL store passwords only as argon2 or bcrypt hashes and SHALL NOT return or log the hash or raw password.
5. WHERE the caller's role is ADMIN, THE API SHALL allow account CRUD under `/accounts`.
6. IF a non-ADMIN token is used for account management, THEN THE API SHALL respond 403 and leave data unchanged.
7. WHEN an account is created, THE API SHALL enforce the account/role/link CHECK from Requirement 2.3.

### Requirement 4: Drivers, licenses, and employment history (M4)

**User Story:** As an administrator, I want to manage drivers and their licenses, so that the workforce records stay accurate and attributable.

#### Acceptance Criteria
1. WHERE the caller is ADMIN, THE API SHALL support create/read/update for `drivers`.
2. WHEN listing drivers, THE API SHALL support pagination and filtering by `area_id` and employment status.
3. WHERE the caller is ADMIN, THE API SHALL support create/read/list for `areas` (code, name) to back the driver area filter.
4. THE API SHALL manage `driver_licenses` for a driver and SHALL enforce unique `license_number`.
5. WHEN a driver's employment status changes, THE API SHALL write an `employment_history` row with `changed_by` (an `accounts.id`), a `reason`, and a validity interval.
6. IF a new employment-history interval overlaps an existing one for the same driver, THEN THE API SHALL reject it.
7. THE API SHALL NOT log PII fields (date_of_birth, phone, address, citizen_id, emergency_contact).
8. THE API SHALL support soft-archive of a driver via `archived_at` and SHALL NOT hard-delete the record.

### Requirement 5: Vehicles and driver–vehicle assignment (M5)

**User Story:** As an administrator, I want to assign drivers to vehicles over time, so that assignment history is consistent and non-overlapping.

#### Acceptance Criteria
1. WHERE the caller is ADMIN, THE API SHALL support create/read/update for `vehicles` with unique `plate_number` and a valid `vehicle_type` (MOTORBIKE or CAR).
2. WHEN a driver is assigned to a vehicle, THE API SHALL create a `driver_vehicles` row with a validity interval.
3. WHEN a driver is re-assigned, THE API SHALL close the prior active interval before opening the new one.
4. IF a new assignment overlaps an existing active assignment for the same driver (or the same vehicle), THEN THE API SHALL reject it.

### Requirement 6: Cross-cutting non-functional requirements

**User Story:** As a developer, I want consistent cross-cutting conventions (layering, schemas, errors, attribution, done-definition), so that every slice is built and verified the same way.

#### Acceptance Criteria
1. THE API SHALL follow one-directional layering (router → service → repository); routers SHALL NOT access the DB directly and services SHALL NOT build HTTP responses.
2. THE API SHALL use Pydantic request/response models at every endpoint and SHALL NOT serialize SQLAlchemy ORM objects to clients.
3. THE API SHALL raise typed domain exceptions (NotFound/Conflict/ValidationError/Forbidden) mapped by a single handler to HTTP 404/409/422/403.
4. THE API SHALL store timestamps as `timestamptz` in UTC and SHALL represent money as `numeric(14,0)` integer minor units.
5. THE API SHALL populate attribution columns (`changed_by`/`decided_by`/`actor_id`/`created_by`) referencing `accounts.id` on every applicable write.
6. A task SHALL be considered done only when backend `pytest`/`ruff` and web `build`/`lint` pass, endpoints have happy-path + auth + validation tests, each added constraint has a rejection test, and no PII/secrets appear in logs or fixtures.
