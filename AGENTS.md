# Instructions for AI Agents and Contributors

## Project overview

DriverManagementPlatform is a monorepo for a driver management platform. The planned stack includes React for web, React Native for mobile, Python/FastAPI for the backend, Docker for running services, and Kafka for event streaming. This repository currently contains only the initial directory scaffold. Check the actual configuration before running commands or assuming a technology has been installed.

## Main structure

- `apps/web`: React application for browsers.
- `apps/mobile`: React Native application.
- `packages/`: code shared by applications, such as UI components, the API client, and contracts.
- `services/api`: FastAPI API. Each domain under `app/domains/<domain>/` contains `repositories`, `services`, `routers`, `schemas`, and `models`.
- `services/agent-orchestrator`: agent orchestration, workflows, and tools.
- `services/event-consumer`: Kafka consumers and event handlers.
- `services/data-processing`: data processing jobs and pipelines.
- `data/`: schemas, pipeline definitions, seed data, and notebooks. Do not store sensitive or generated data here.
- `infra/`: Docker, Kafka, database, and monitoring configuration.
- `docs/`: architecture, API, data, and architecture decision records (ADRs).

## Backend conventions

- Routers handle HTTP requests, validate input at the boundary, and call services. Avoid putting business logic in routers.
- Use Pydantic schemas for API request and response data. Do not return ORM models directly as API responses.
- Services contain business rules and coordinate work across repositories or infrastructure.
- Repositories handle data queries and writes; they do not contain business rules.
- Models contain ORM mappings. Keep database migrations with the service that owns the corresponding database.
- Put infrastructure dependencies such as Kafka, databases, caches, and LLM integrations in `infrastructure` or dedicated adapters. Keep domain logic from depending directly on vendor frameworks.
- Add new domains under `services/api/app/domains/` and keep each domain's components together.

## Frontend and data conventions

- Each app owns its UI, navigation, and state. Put code in `packages/` only when it is genuinely shared.
- Keep API and event contract changes consistent across the backend, frontend, and relevant schemas in `packages/contracts/` or `data/schemas/`.
- Give Kafka topics and events clear names and versions. Do not put secrets in events or in the repository.

## Change guidelines

1. Read the README and the relevant component configuration before making changes.
2. Keep changes within the requested scope; do not add dependencies or services unless needed.
3. Do not commit secrets, tokens, real personal data, or environment files. If needed, provide an `.env.example` containing variable names and non-sensitive sample values only.
4. Use clear names when adding directories or modules, and update documentation when the structure or architecture changes.
5. Before finishing, report the files changed and the relevant verification commands. Run checks only when requested by the user or required by the project workflow.

## Project commands

No build, lint, or test commands are configured in this scaffold yet. When adding configuration for an app or service, update this section with the exact commands and the working directory for each.
