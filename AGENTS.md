# DriverManagementPlatform umbrella repository

This repository is the directory and coordination point for the independently versioned DriverManagementPlatform repositories. Application, infrastructure, documentation, data, and contract sources live in the repositories listed below.

- [dmp-api](https://github.com/tranhau2005/dmp-api): FastAPI backend.
- [dmp-web](https://github.com/tranhau2005/dmp-web): web app and shared UI/API client packages.
- [dmp-mobile](https://github.com/tranhau2005/dmp-mobile): mobile app.
- [dmp-agent-orchestrator](https://github.com/tranhau2005/dmp-agent-orchestrator): agent orchestration.
- [dmp-event-consumer](https://github.com/tranhau2005/dmp-event-consumer): Kafka consumers.
- [dmp-data-processing](https://github.com/tranhau2005/dmp-data-processing): data jobs and pipelines.
- [dmp-infra](https://github.com/tranhau2005/dmp-infra): infrastructure and operational scripts.
- [dmp-docs](https://github.com/tranhau2005/dmp-docs): specifications, schemas, architecture, and shared contracts.

Use each repository's own `AGENTS.md` and `CLAUDE.md` for implementation guidance. Coordinate cross-repository changes through the affected maintainers and keep interface contracts in dmp-docs aligned. Keep secrets, local environment files, generated data, and real personal data out of commits. Do not use this umbrella repository as a substitute for component-level source control.
