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

## Engineering guide

The authoritative engineering guide is [docs/agent-guide.md in dmp-docs](https://github.com/tranhau2005/dmp-docs/blob/main/docs/agent-guide.md). It lives in dmp-docs and covers the pinned stack, migration integrity rules, the MVP slice (M1–M5), NEEDS-OWNER rules, and the decision log.

## Local setup

Clone all repositories side by side in one parent directory:

```bash
mkdir dmp && cd dmp
for r in api web mobile agent-orchestrator event-consumer data-processing infra docs; do
  gh repo clone tranhau2005/dmp-$r
done
```

Keep the side-by-side layout: dmp-api depends on dmp-infra at `../dmp-infra`, because dmp-api's development instructions start PostgreSQL with `docker compose -f ../dmp-infra/docker-compose.yml up -d db`. dmp-infra's Compose file does not currently build application images.

## Contributing

See each repository's `CLAUDE.md` and `AGENTS.md` for scoped contribution conventions. Cross-repository contract changes should be coordinated with affected repositories and documented in dmp-docs.
