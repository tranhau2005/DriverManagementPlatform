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

## Authoritative engineering guide

The authoritative engineering guide is [docs/agent-guide.md in dmp-docs](https://github.com/tranhau2005/dmp-docs/blob/main/docs/agent-guide.md). It lives in dmp-docs and defines the pinned stack, migration integrity rules, the MVP slice (M1–M5), NEEDS-OWNER rules, and the decision log. Read it before changing code in any component repository.

## Commit and branch conventions

- Commits: Conventional Commits 1.0, `<type>[(<scope>)][!]: <description>`. Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Imperative, lowercase description, no trailing period, header of 72 characters or fewer. Mark breaking changes with `!` or a `BREAKING CHANGE:` footer.
- Branches: `<type>/<short-kebab-description>` using the same types (for example `feat/m2-schema-migrations`). Never commit directly to `main`; work through pull requests.

The full wording is in [CLAUDE.md](CLAUDE.md#commit-and-branch-conventions).
