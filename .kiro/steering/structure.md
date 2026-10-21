# Structure Steering — Driver Management Platform

> Sources: `AGENTS.md` §1, §3, §5; the actual directory tree surveyed in the repository.

## Current actual state

The repo is a **scaffold** — most leaf directories contain only a `.gitkeep`. The only files with real content:
`AGENTS.md`, `kiro-system-architecture-handoff.md`, `docs/schema.dbml`,
`docs/architecture/system-architecture.md` (+ `.drawio`/`.png`),
`services/agent-orchestrator/orchestrator.py` (+ README), `bootstrap-self-hosted.sh`,
`README.md`, and the specs under `.kiro/specs/`.
Scaffold directories are **intent**, not implemented code.

## Target monorepo layout (AGENTS.md §3)

```
apps/web            # React + Vite + TS (Admin)
apps/mobile         # React Native + TS (Driver) [later]
packages/{ui, api-client, contracts}   # api-client generated from OpenAPI
services/api        # FastAPI modular monolith (pyproject.toml, alembic.ini, alembic/versions, app/)
services/{event-consumer, data-processing, agent-orchestrator}  # DEFERRED / out of MVP
infra/{compose, docker, kafka, databases, monitoring}
data/{schemas, pipelines, seeds, notebooks}
docs/{schema.dbml, architecture, decisions(ADR), api, data}
```

## `services/api/app` convention

```
app/
  main.py                 # FastAPI app factory
  core/                   # config, db session, security
  domains/<name>/         # <name>: accounts, areas, drivers, licenses, vehicles,
                          #          customers, bookings, leave, scheduling, payroll
```

Each `domains/<name>/` folder (strict):

- `router.py` — FastAPI routes; validate input, call service, map errors to HTTP.
- `service.py` — business rules; the only place rules live.
- `repository.py` — DB access; returns ORM/domain objects, no HTTP concerns.
- `models.py` — SQLAlchemy ORM models.
- `schemas.py` — Pydantic request/response models (NOT ORM).
- `tests/` — unit + integration tests for the domain.

Rules: routers never touch the DB directly; services never build HTTP responses; ORM is never serialized to clients.

## Reconciliation note

The current scaffold uses `services/api/app/domains/{drivers,vehicles,assignments,auth}`, which diverges from §3.
When implementing: use `accounts`/`auth`, add `licenses/bookings/leave/scheduling/payroll`;
"assignments" actually belongs under `vehicles` (the `driver_vehicles` relationship).

## General rules

- Fill in by MVP order; do not spread half-finished domains.
- One migration per schema change; keep `docs/schema.dbml` **identical** to handoff Section 14.
- ADRs live in `docs/decisions` for: DB, Kafka-adoption decision, identity/authz, deployment, analytics.

## Naming hazard

"agent-orchestrator" is overloaded:
(a) the local CLI dispatcher in `services/agent-orchestrator/orchestrator.py`;
(b) the AO control-plane spec in `.kiro/specs/agent-orchestrator-multi-agent`.
Keep the two concepts distinct; do not confuse ownership.
