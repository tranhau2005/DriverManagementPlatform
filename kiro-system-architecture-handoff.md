# DriverManagementPlatform — Architecture Handoff Spec for KIRO

> Purpose: give KIRO the project context, current design baseline, and review questions needed to continue the system design.
>
> Source status: the repository is a scaffold, but the project owner has provided the design report's table of contents and a PostgreSQL DBML schema in the conversation. The owner-provided design is the current business/ERD source of truth and takes precedence over any preliminary proposals in this document. Details that appear only as table-of-contents headings must be verified against the full report before they are treated as requirements.

## 1. Instructions for KIRO

Use this document as the starting point for an architecture review. Prioritize the design transcribed in Section 14. Earlier proposal sections remain applicable only where they do not conflict with Section 14. During review:

1. Compare against the owner's original business and design documents if they are provided later.
2. State assumptions, unresolved decisions, rationale, and consequences explicitly.
3. Do not invent business policies such as detailed authorization rules, payroll formulas, compliance rules, or booking lifecycles.
4. If more information is needed, provide a concise list of questions, prioritizing those that affect the data model, service boundaries, security, or operations.
5. Update the KIRO requirements, design, and tasks after the assumptions have been confirmed.

## 2. Project context and confirmed information

### Information in the repository

- The product is described as a driver management platform.
- The repository is intended to be a monorepo.
- The components planned for the monorepo (not yet created in the repository) are:
  - `apps/web`: React web app.
  - `apps/mobile`: React Native mobile app.
  - `services/api`: domain-oriented FastAPI backend.
  - `services/agent-orchestrator`: agent and workflow orchestration.
  - `services/event-consumer`: Kafka event processing.
  - `services/data-processing`: data processing.
  - `infra/`: Docker, Kafka, database, and monitoring.
- Planned backend conventions: routers validate requests at the boundary and call services; services contain business rules; repositories handle data access; Pydantic schemas define API boundaries; ORM models are not returned directly as API responses.
- The repository currently contains only this handoff document, the `.kiro/` spec workspace, and an `AGENTS.md` agent guide (added during review) with its `docs/schema.dbml`. There is no application code, no `apps/`/`services/`/`infra/` directories, no `README.md`, and no runtime configuration, migrations, API contracts, business diagrams, or ADRs. The monorepo structure described above is a plan to be created, not an existing layout.

### Additional design provided by the project owner

- The DBML specifies PostgreSQL.
- The current account roles are `ADMIN`, `DRIVER`, and `CUSTOMER`; the system includes customers and bookings.
- The data design covers accounts, areas, driver profiles/employment history/licenses, vehicles and driver–vehicle assignments, customers/bookings, leave requests and approval history, work schedules/activity sessions, income policies, payroll periods/payrolls/payroll adjustments.
- The report's table of contents includes a functional diagram, business permission matrix, grouped ERDs, integrity constraints, approval/state transitions, timekeeping/payroll, reports, and indexes.

### Not confirmed from the material currently available

The full body of the LaTeX report, functional/ERD diagram images, detailed table descriptions, permission matrix, payroll formula, timekeeping rules, report definitions, load estimates, SLA, jurisdiction, and production deployment model have not been provided. KIRO must use the supplied DBML as-is while marking rules mentioned only in report headings as requiring verification from the full source.

## 3. Design scope for KIRO to review

The target design should cover these layers. Priorities and business details should follow the owner's confirmed requirements:

1. Functional map and actors.
2. Web/mobile application architecture, API, and domain boundaries.
3. Operational data model, event data, and reporting data.
4. API and event contracts between components.
5. Security, authorization, audit, and personal-data protection.
6. Deployment, observability, backup/restore, and incident handling.
7. Phased delivery plan and acceptance criteria.

## 4. Functional map based on the current design

This scope is derived from the DBML and report table of contents provided by the project owner. The table of contents reveals section names only; it is not sufficient to reproduce the original functional diagram or detailed permission matrix.

| Functional area | Design evidence | What is currently known | KIRO must verify from the full report |
|---|---|---|---|
| Accounts and permissions | `accounts`; table of contents includes “Organization structure and roles” and “Business permission matrix” | An account optionally links to one driver or one customer; roles are ADMIN/DRIVER/CUSTOMER; usernames are unique; statuses are ACTIVE/LOCKED/DISABLED | Use cases/screens per role; detailed permission matrix; account creation, reset, and locking flows |
| Areas | `areas` | Area catalog with unique code and name | Are areas used for operational assignment, reporting, or permission scope? |
| Driver profile and lifecycle | `drivers`, `employment_history` | Personal profile, driver code, area, start date, archive timestamp; status history has validity intervals and the actor who changed it | Status transition rules; resignation/archive behavior; required/unique constraints for sensitive fields |
| Driver licenses | `driver_licenses` | A driver may have multiple licenses; license number is unique; class and issue/expiry dates are stored | License classes, validity rules, and expiration reminders |
| Vehicles and assignment | `vehicles`, `driver_vehicles` | Motorcycle/car catalog; driver–vehicle relationship over a validity interval | Can assignments overlap? What is the vehicle handover process? |
| Customers and bookings | `customers`, `bookings` | Customer profile; booking has pickup/drop-off, requested/scheduled times, optional driver, fare, status, and cancellation fields | Assignment, state transition, cancellation, fare calculation, and concurrency rules |
| Leave and approval | `leave_requests`, `leave_actions`, `employment_history` | Request types ANNUAL/SICK/LONG/SUSPEND/RESIGN; PENDING/APPROVED/REJECTED; actions SUBMIT/APPROVE/REJECT; request may be linked to employment history | Approval workflow, approver permissions, date limits, and effects on driver status/schedule |
| Work schedule and activity | `work_schedule`, `activity_sessions` | Planned minutes per driver/day; activity session start/end; unique source_key | Are sessions created by the app, booking, or device? Overnight, overlapping-session, and correction rules |
| Income policy and payroll | `income_policies`, `payroll_periods`, `payrolls`, `payroll_adjustments` | Per-driver/month base and trip rates; DRAFT/FINALIZED period; snapshots and bonus/allowance/deduction amounts; adjustments | Formula, timekeeping/booking sources, rounding, recalculation, period locking, permissions, and PDF export |
| Reports | Table of contents: monthly driver status, workforce composition, payroll PDF | Three report outputs are named | Exact metrics, filters, view permissions, data sources, and PDF template |

### Actors represented in the data design

- `ADMIN`: administrative role declared in `accounts`; its detailed permissions are not available.
- `DRIVER`: may have an account linked to a driver profile.
- `CUSTOMER`: may have an account linked to a customer profile.

The `changed_by`, `decided_by`, `actor_id`, and `created_by` fields indicate that operational actions should be attributable to an account. Do not infer additional manager/dispatcher roles without a source.

## 5. Preliminary logical architecture — proposal for review

```text
Web app (React) ─┐
                 ├── HTTPS / API ── FastAPI modular monolith
Mobile app ──────┘                       │
                                         ├── PostgreSQL (operational data; proposed)
                                         ├── Outbox / event publisher (if needed)
                                         └── Kafka (only if async/replay/scale use cases require it)
                                                  ├── Event consumer
                                                  └── Data processing → reporting store (not selected)

Agent orchestrator: separate component for agent workflows; integrate through controlled APIs/events.
Infrastructure: Docker for development; production topology, cloud, and monitoring are not yet specified.
```

### Proposed architecture principles

- Start with a modular monolith in `services/api`, organized by domain. Split services only when independent deployment, scaling, or ownership needs are demonstrated.
- Keep the API as the controlled write path for business data. Do not allow Kafka consumers to mutate business data without clear ownership and rules.
- Use Kafka only for flows that need asynchronous processing, multiple integrations/consumers, throughput, or replay. If adopted, define schema/versioning, idempotency, retries, dead-letter handling, and ordering requirements.
- Use a transactional outbox if database updates and event publication must remain consistent.
- Separate transactional data from reporting storage when actual needs or volume justify it; analytics technology is not selected.
- The agent orchestrator must not bypass authorization/business APIs to read or change the database directly.

These are starting recommendations and should be checked against actual scale and product goals.

## 6. Current database design

The source design specifies PostgreSQL and provides the complete DBML in Section 14. This section is a navigational summary; if anything differs, KIRO should use the source DBML as the baseline and propose changes with explicit rationale.

| Group | Tables | Responsibility shown by the schema |
|---|---|---|
| Accounts | `accounts` | Login identity, role, status; optional one-to-one link to a driver or customer |
| Catalog | `areas` | Area code and name |
| Driver workforce | `drivers`, `employment_history`, `driver_licenses` | Driver profile, time-bounded employment status history, licenses |
| Vehicles | `vehicles`, `driver_vehicles` | Vehicle catalog and time-bounded driver–vehicle history |
| Customer/booking | `customers`, `bookings` | Customer profile and booking lifecycle data |
| Leave/status changes | `leave_requests`, `leave_actions` | Leave/suspension/resignation requests and action audit history |
| Timekeeping/schedule | `work_schedule`, `activity_sessions` | Planned work minutes and actual activity intervals |
| Payroll | `income_policies`, `payroll_periods`, `payrolls`, `payroll_adjustments` | Monthly income policy, payroll period, result snapshots, and adjustments |

### Rules encoded in the DBML

- Every table uses an auto-incrementing `bigint` primary key.
- Username, driver_code, citizen_id, license_number, plate_number, booking_code, customer phone, and source_key have unique constraints. Some of these uniqueness rules may need business validation before being changed.
- An account can link to at most one driver or one customer through nullable unique FKs. Verify that it cannot link to both at once and that the link agrees with the account role.
- A driver can have multiple employment-history entries, licenses, vehicle links, leave requests, schedules, activity sessions, income policies, and payroll records over time.
- `employment_history.valid_from/valid_to` and `driver_vehicles.valid_from/valid_to` represent validity intervals. The DBML does not define exclusion constraints to prevent overlapping intervals.
- `work_schedule` is unique by `(driver_id, work_date)`; `income_policies` by `(driver_id, month)`; and `payrolls` by `(period_id, driver_id)`.
- `payroll_periods.month` and `income_policies.month` are intended to be the first day of the month. Consider a CHECK constraint or a dedicated month type to enforce this.
- Monetary amounts use `numeric(14,0)`. Confirm currency, rounding rules, and the formula against the full report.
- Most business timestamps use `timestamptz`; not every table has `created_at`. Review audit/lifecycle needs instead of adding timestamps mechanically.
- `drivers` contains PII (date of birth, phone, address, national ID, emergency contact); design access control, masking, retention, and audit. `password_hash` is intended to store a password hash, never a raw password.

### Schema review questions — do not change these assumptions silently

1. Add enum/check constraints for status, role, leave type, vehicle type, and adjustment type; current allowed values are recorded in DBML notes.
2. `employment_history.source_request_id` is nullable and references `leave_requests`. Verify whether every status change requires a request or whether there are other administrative sources.
3. `payrolls.policy_id` is unique and payroll rows snapshot pay components. Verify the intended business key and how recalculation history should work.
4. `activity_sessions` currently has no uniqueness or interval-overlap constraint. Verify session rules.
5. `driver_vehicles` has no unique key or interval-overlap constraint for vehicle/driver assignments. Verify assignment rules.
6. `bookings.fare_amount` is nullable and has no currency field. Verify when a fare is set, currency, and fare-finalization rules.
7. Account, driver, and customer deletion/archive rules are unspecified; FK delete behavior is not declared in the DBML.
8. Non-unique indexes, partitioning, concurrency/locking, and migration strategy are not described.

There is no organization/tenant entity in the current ERD. KIRO must not treat multi-tenancy as a default requirement; first confirm whether the product serves one transport organization or multiple organizations.

## 7. Main flows to document after business confirmation

KIRO should add sequence/activity diagrams for flows that are in scope. Suggested flows based on the current schema:

1. Create an account and link it to a driver or customer profile.
2. Create/update a driver and license; record employment-status history.
3. Assign or change a vehicle for a driver over time.
4. Customer creates a booking; assign a driver, complete the booking, or cancel it.
5. Driver submits a leave/suspension/resignation request; an authorized actor approves/rejects it and the system records `leave_actions` and, where applicable, an employment-status change.
6. Create a work schedule and record activity sessions; aggregate timekeeping.
7. Configure income policies, calculate monthly payroll, add adjustments, finalize the period, and generate reports/PDFs.

Flows 5–7 have corresponding tables in the design, but only their section headings were provided. KIRO must obtain the full report before defining exact business rules.

For each flow, specify the actor, preconditions, happy path, errors/recovery, access rules, data read/written, and events emitted.

## 8. API, events, and module boundaries

### API

- REST/JSON through FastAPI is the planned baseline in the README.
- Define versioning, pagination, filtering/sorting, error format, idempotency for important write commands, authentication/authorization, and rate limits.
- Keep request/response schemas separate from ORM models; generate and review OpenAPI documentation with API changes.
- Candidate domains to evaluate: accounts/access, areas, drivers, licenses, vehicles, customers/bookings, leave, scheduling/timekeeping, payroll, and reporting.

### Events

Kafka appears in the planned component list, but there are no defined topics or event contracts. Before creating topics, KIRO should identify:

- Which use cases actually need event-driven processing.
- Events as immutable facts with versions and unique identifiers.
- Partition keys, required ordering, retention, and PII policy.
- Consumer idempotency, retry/backoff, dead-letter handling, and replay.
- Producer/consumer schema coordination and backward-compatibility handling.

## 9. Security and operations — design requirements to clarify

- Authentication provider, session/token lifecycle, and MFA for sensitive roles.
- Authorization model and how tenant/data-scope isolation is tested, if applicable.
- Audit for access to/change of sensitive data and agent actions.
- Encryption in transit and at rest; keep secrets outside the repository.
- Rules for PII, location data, and identity documents based on the target jurisdiction.
- Logging with correlation/request IDs, metrics, tracing, health checks, and alerting.
- Backup, point-in-time recovery, retention, RPO/RTO, and restore drills.
- Load limits, availability targets, and incident response.

No quantitative targets or policies have been provided. KIRO must obtain input before assigning SLA/SLO values.

## 10. Open decisions (initial decision log)

| ID | Decision | Status | Required input |
|---|---|---|---|
| D-01 | MVP scope, out-of-scope items, and priority of modules already represented in the ERD | Open | Current workflows and prioritization criteria |
| D-02 | Single-organization or multi-organization product; whether organization/tenant is needed | Open; current ERD has no tenant | Business deployment model and data boundaries |
| D-03 | PostgreSQL operations, migration, and backup strategy | PostgreSQL selected in DBML; operations open | Hosting, scale, RPO/RTO, operational capabilities |
| D-04 | Whether Kafka is needed from the MVP | Open | Async use cases, integrations, throughput, replay requirements |
| D-05 | Exact lifecycle rules for bookings, work schedules, activity sessions, and vehicle assignments | Entities/tables exist; rules are unclear | Full business report and operational workflows |
| D-06 | Identity provider and authorization model | Open | SSO, MFA, roles, data scope, user devices |
| D-07 | Cloud/region and deployment topology | Open | Data jurisdiction, budget, operations, availability |
| D-08 | Definitions for driver, workforce, and payroll PDF reports; retention | Reports named in table of contents; definitions missing | Full report sections and output templates |
| D-09 | What AI/agents may do | Open | Use cases, automation level, human approval, audit |

## 11. Expected KIRO outputs after review

1. Actor/use-case requirements with verifiable acceptance criteria and non-functional requirements.
2. Functional and main-flow diagrams; distinguish MVP features from roadmap.
3. Context/container and deployment diagrams; explain module/service boundaries.
4. Draft logical and physical ERD, including keys, cardinality, data isolation, indexes, and retention.
5. API contracts and event catalog only for confirmed flows.
6. A concise threat model for authentication, multi-tenancy, PII, file uploads, agent actions, and event consumers.
7. ADRs for major choices: database, Kafka, identity, deployment, and analytics.
8. Remaining questions/blockers, the owner for each, and the impact of leaving each unresolved.
9. Phased implementation plan with acceptance criteria and dependencies for each item.

## 12. Design acceptance criteria

The design is ready for implementation when:

- Every MVP function maps to a confirmed actor and acceptance criteria.
- Important assumptions are explicit, have an owner, and are not presented as confirmed decisions.
- The ERD covers confirmed flows and explains data isolation, state, audit, PII, and retention.
- Every service, database, queue, or platform component has a use case and rationale.
- APIs/events define contracts, versioning, errors, idempotency, and required access control.
- Migration, backup/restore, observability, and security fit the confirmed goals.
- Risks and remaining questions are clear; no legal or SLA details are invented without evidence.

## 13. Sources and evidence level

- `README.md`, `AGENTS.md`: planned stack and repository structure; the repository remains a scaffold.
- LaTeX report supplied by the project owner in the conversation: only the table of contents/metadata is currently available. It reveals section, table, and diagram names but not their full content or figures.
- PostgreSQL DBML supplied by the project owner in the conversation: current detailed schema and relationships, transcribed in Section 14.

If the full report differs from the supplied excerpt, KIRO should describe the discrepancy and ask the project owner before changing the schema or business rules.

## 14. Source DBML — PostgreSQL

This is the schema supplied by the project owner. KIRO should load it as the current design, check consistency, and propose any additional migrations/constraints separately. Do not silently replace table names, column names, roles, statuses, or cardinalities. The DBML note explicitly says the ERD has no team leader or driver-team table.

```dbml
DB(Project driver_management_approval {
  database_type: 'PostgreSQL'
  Note: 'Current ERD design in bao-cao.tex. Customers and bookings were added; there is no team leader or driver-team table.'
}

Table accounts {
  id bigint [pk, increment]
  driver_id bigint [unique, null]
  customer_id bigint [unique, null]
  role varchar(20) [not null, note: 'ADMIN, DRIVER, or CUSTOMER']
  username varchar(100) [not null, unique]
  password_hash text [not null]
  status varchar(20) [not null, note: 'ACTIVE, LOCKED, or DISABLED']
  created_at timestamptz [not null]
}

Table areas {
  id bigint [pk, increment]
  code varchar(20) [not null, unique]
  name varchar(100) [not null]
}

Table drivers {
  id bigint [pk, increment]
  driver_code varchar(20) [not null, unique]
  full_name varchar(150) [not null]
  date_of_birth date [not null]
  phone varchar(20) [not null]
  email varchar(254)
  address text [not null]
  citizen_id varchar(20) [not null, unique]
  education_level varchar(50) [not null]
  area_id bigint [not null]
  start_date date [not null]
  emergency_contact varchar(255)
  created_at timestamptz [not null]
  archived_at timestamptz
}

Table employment_history {
  id bigint [pk, increment]
  driver_id bigint [not null]
  status varchar(20) [not null, note: 'WORKING, ON_LEAVE, SICK, LONG_LEAVE, SUSPENDED, RESIGNED']
  valid_from timestamptz [not null]
  valid_to timestamptz
  source_request_id bigint
  changed_by bigint [not null]
  reason text [not null]
}

Table driver_licenses {
  id bigint [pk, increment]
  driver_id bigint [not null]
  license_number varchar(30) [not null, unique]
  license_class varchar(20) [not null]
  issued_on date [not null]
  expires_on date
}

Table vehicles {
  id bigint [pk, increment]
  plate_number varchar(20) [not null, unique]
  vehicle_type varchar(20) [not null, note: 'MOTORBIKE or CAR']
  brand_model varchar(100)
}

Table driver_vehicles {
  id bigint [pk, increment]
  driver_id bigint [not null]
  vehicle_id bigint [not null]
  valid_from timestamptz [not null]
  valid_to timestamptz
}

Table customers {
  id bigint [pk, increment]
  full_name varchar(150) [not null]
  phone varchar(20) [not null, unique]
  email varchar(254)
  created_at timestamptz [not null]
  archived_at timestamptz
}

Table bookings {
  id bigint [pk, increment]
  booking_code varchar(24) [not null, unique]
  customer_id bigint [not null]
  driver_id bigint
  pickup_address text [not null]
  dropoff_address text [not null]
  requested_at timestamptz [not null]
  scheduled_at timestamptz
  completed_at timestamptz
  fare_amount numeric(14,0)
  status varchar(20) [not null, note: 'PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, CANCELLED']
  cancelled_at timestamptz
}

Table leave_requests {
  id bigint [pk, increment]
  driver_id bigint [not null]
  request_type varchar(20) [not null, note: 'ANNUAL, SICK, LONG, SUSPEND, or RESIGN']
  start_date date [not null]
  end_date date
  reason text [not null]
  status varchar(20) [not null, note: 'PENDING, APPROVED, or REJECTED']
  submitted_at timestamptz [not null]
  decided_by bigint
  decided_at timestamptz
  rejection_reason text
}

Table leave_actions {
  id bigint [pk, increment]
  request_id bigint [not null]
  actor_id bigint [not null]
  action varchar(30) [not null, note: 'SUBMIT, APPROVE, or REJECT']
  acted_at timestamptz [not null]
  comment text
}

Table work_schedule {
  id bigint [pk, increment]
  driver_id bigint [not null]
  work_date date [not null]
  planned_minutes int [not null]
  created_by bigint [not null]

  Indexes {
    (driver_id, work_date) [unique]
  }
}

Table activity_sessions {
  id bigint [pk, increment]
  driver_id bigint [not null]
  work_date date [not null]
  started_at timestamptz [not null]
  ended_at timestamptz
  source_key varchar(100) [not null, unique]
}

Table income_policies {
  id bigint [pk, increment]
  driver_id bigint [not null]
  month date [not null, note: 'Always the first day of the month']
  base_amount numeric(14,0) [not null, note: 'Monthly base salary']
  trip_rate numeric(14,0) [not null, note: 'Payment per completed booking']
  created_by bigint [not null]

  Indexes {
    (driver_id, month) [unique]
  }
}

Table payroll_periods {
  id bigint [pk, increment]
  month date [not null, unique, note: 'Always the first day of the month']
  status varchar(20) [not null, note: 'DRAFT or FINALIZED']
  created_by bigint [not null]
  created_at timestamptz [not null]
  finalized_by bigint
  finalized_at timestamptz
}

Table payrolls {
  id bigint [pk, increment]
  period_id bigint [not null]
  driver_id bigint [not null]
  policy_id bigint [not null, unique]
  driver_code_snapshot varchar(20) [not null]
  driver_name_snapshot varchar(150) [not null]
  completed_bookings int [not null]
  base_amount numeric(14,0) [not null]
  trip_rate numeric(14,0) [not null]
  trip_amount numeric(14,0) [not null]
  bonus_amount numeric(14,0) [not null]
  allowance_amount numeric(14,0) [not null]
  deduction_amount numeric(14,0) [not null]
  net_amount numeric(14,0) [not null]
  calculated_at timestamptz [not null]

  Indexes {
    (period_id, driver_id) [unique]
  }
}

Table payroll_adjustments {
  id bigint [pk, increment]
  payroll_id bigint [not null]
  adjustment_type varchar(20) [not null, note: 'BONUS, ALLOWANCE, or DEDUCTION']
  description text [not null]
  amount numeric(14,0) [not null]
  created_by bigint [not null]
  created_at timestamptz [not null]
}

Ref: accounts.driver_id - drivers.id
Ref: accounts.customer_id - customers.id
Ref: drivers.area_id > areas.id
Ref: employment_history.driver_id > drivers.id
Ref: employment_history.source_request_id > leave_requests.id
Ref: employment_history.changed_by > accounts.id
Ref: driver_licenses.driver_id > drivers.id
Ref: driver_vehicles.driver_id > drivers.id
Ref: driver_vehicles.vehicle_id > vehicles.id
Ref: bookings.customer_id > customers.id
Ref: bookings.driver_id > drivers.id
Ref: leave_requests.driver_id > drivers.id
Ref: leave_requests.decided_by > accounts.id
Ref: leave_actions.request_id > leave_requests.id
Ref: leave_actions.actor_id > accounts.id
Ref: work_schedule.driver_id > drivers.id
Ref: work_schedule.created_by > accounts.id
Ref: activity_sessions.driver_id > drivers.id
Ref: income_policies.driver_id > drivers.id
Ref: income_policies.created_by > accounts.id
Ref: payroll_periods.created_by > accounts.id
Ref: payroll_periods.finalized_by > accounts.id
Ref: payrolls.period_id > payroll_periods.id
Ref: payrolls.driver_id > drivers.id
Ref: payrolls.policy_id > income_policies.id
Ref: payroll_adjustments.payroll_id > payrolls.id
Ref: payroll_adjustments.created_by > accounts.id
}
```
