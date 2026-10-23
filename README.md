# DriverManagementPlatform

DriverManagementPlatform is maintained as a set of independently versioned repositories. This umbrella repository documents the layout and links to each component; it does not contain application implementations.

## Repositories

| Repository | Scope |
| --- | --- |
| [dmp-api](https://github.com/tranhau2005/dmp-api) | FastAPI backend and domain services |
| [dmp-web](https://github.com/tranhau2005/dmp-web) | Browser application plus shared `packages/ui` and `packages/api-client` |
| [dmp-mobile](https://github.com/tranhau2005/dmp-mobile) | React Native application |
| [dmp-agent-orchestrator](https://github.com/tranhau2005/dmp-agent-orchestrator) | Agent orchestration, workflows, and tools |
| [dmp-event-consumer](https://github.com/tranhau2005/dmp-event-consumer) | Kafka consumers and event handlers |
| [dmp-data-processing](https://github.com/tranhau2005/dmp-data-processing) | Data processing jobs and pipelines |
| [dmp-infra](https://github.com/tranhau2005/dmp-infra) | Docker, Compose, databases, Kafka, monitoring, and scripts |
| [dmp-docs](https://github.com/tranhau2005/dmp-docs) | Kiro specifications, architecture, schemas, data assets, and shared contracts |

The former `packages/ui` and `packages/api-client` paths live in dmp-web because they are frontend-facing shared packages and there is no separate cross-platform package host yet. Specs and shared contracts live in dmp-docs. Each new repository retains the history for its paths from the original repository.

Clone repositories side by side when working locally. For example, dmp-api's development instructions start PostgreSQL using the Compose file in `../dmp-infra`. See each repository's `CLAUDE.md` and `AGENTS.md` for scoped contribution conventions. Cross-repository contract changes should be coordinated with affected repositories and documented in dmp-docs.
