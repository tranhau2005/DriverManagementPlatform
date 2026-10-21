# Product Steering — Driver Management Platform

> Sources: `AGENTS.md`, `kiro-system-architecture-handoff.md`, `docs/schema.dbml`.
> This is the product-direction document. On conflict with older descriptions, this file + the DBML + AGENTS.md win.

## What the product is

A platform to manage the driver-workforce lifecycle for a **single organization**, covering:

- Accounts & access control (accounts).
- Area catalog (areas).
- Driver profiles, employment history, driving licenses (drivers, employment_history, driver_licenses).
- Vehicles and driver–vehicle assignment (vehicles, driver_vehicles).
- Customers and bookings (customers, bookings).
- Leave / approval (leave_requests, leave_actions).
- Work schedule & timekeeping (work_schedule, activity_sessions).
- Income policy & payroll (income_policies, payroll_periods, payrolls, payroll_adjustments).
- Three named reports: monthly driver status, workforce composition, payroll PDF.

## Actors (from the data model only)

- **ADMIN** — administrative account. Detailed permission matrix is `[NEEDS-OWNER]`.
- **DRIVER** — account optionally linked 1:1 to a driver profile.
- **CUSTOMER** — account optionally linked 1:1 to a customer profile.

Do not invent manager/dispatcher/team-leader roles — the ERD has none
(the DBML explicitly states there is no team leader or driver-team table).

## Scope discipline

- **MVP = AGENTS.md Section 7 (M1–M5):** scaffold + health, schema + migrations, accounts + auth,
  drivers + licenses, vehicles + assignment. Build the synchronous path, then **stop for review**.
- **Out of MVP:** Kafka, event-consumer, data-processing, analytics lakehouse (D-04 = No for now).
- **`[NEEDS-OWNER]` — do NOT invent (stub + raise NotImplementedError):** booking lifecycle & fare,
  leave-approval effects, timekeeping aggregation, payroll formula, report definitions,
  any permission rule beyond "ADMIN manages; DRIVER/CUSTOMER see their own".
- **Single-organization only.** No multi-tenancy (the ERD has no tenant table).

## Source-of-truth hierarchy

1. `docs/schema.dbml` + `AGENTS.md` — **authoritative** (data + conventions + MVP).
2. `docs/architecture/system-architecture.md` — **target architecture / roadmap** (NOT the MVP).
3. `.kiro/specs/driver-management-dashboard` — **non-authoritative** (a different, simpler model with Viewer/Manager roles). Treat as archived.

## Non-functional intent (unquantified — `[NEEDS-OWNER]` for concrete targets)

PII protection, auditability, availability, and backup/restore all matter; no SLA/SLO
numbers are confirmed. Do not invent them.

## Open decision log (from AGENTS.md §10 / handoff §10)

| ID | Decision | Current default | Status |
|---|---|---|---|
| D-01 | MVP scope | M1–M5 | ASSUMPTION |
| D-02 | Multi-tenant? | Single-org, no tenant table | ASSUMPTION |
| D-03 | DB ops / backup | dev compose only | NEEDS-OWNER (prod) |
| D-04 | Kafka in MVP? | No | ASSUMPTION |
| D-05 | Booking/leave/timekeeping/assignment lifecycle | storage only, rules stubbed | NEEDS-OWNER |
| D-06 | Identity / authz model | JWT + role claim | ASSUMPTION |
| D-07 | Cloud/region/topology | undecided | NEEDS-OWNER |
| D-08 | Report definitions | undecided | NEEDS-OWNER |
| D-09 | AI/agent capabilities | none in MVP | ASSUMPTION |
