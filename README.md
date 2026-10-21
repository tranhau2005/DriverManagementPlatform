# DriverManagementPlatform

Starter monorepo for a driver management platform. The current repository contains only the initial directory scaffold; the frontend, backend, and infrastructure will be added incrementally.

See [AGENTS.md](AGENTS.md) for the project structure, module boundaries, and contribution conventions.

Target architecture and draw.io diagram: [docs/architecture/system-architecture.md](docs/architecture/system-architecture.md).

## Planned components

- `apps/web`: React web app
- `apps/mobile`: React Native mobile app
- `services/api`: domain-oriented FastAPI backend
- `services/agent-orchestrator`: agent orchestration and workflows
- `services/event-consumer`: Kafka event processing
- `services/data-processing`: data processing
- `infra/`: Docker, Kafka, database, and monitoring

Build and test commands will be added once the applications and their configuration are initialized.

## Agent orchestrator

A local Python dispatcher for Codex, Antigravity (`agy`), and OpenCode is available at [services/agent-orchestrator](services/agent-orchestrator/README.md). It requires the relevant CLI to be installed and authenticated separately. OpenRouter can be used through OpenCode's provider configuration.
