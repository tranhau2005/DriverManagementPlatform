# DriverManagementPlatform umbrella

This repository is the landing page and coordination point for the independently versioned DriverManagementPlatform repositories. Application code, infrastructure, specifications, schemas, data assets, and contracts live in the linked component repositories in [README.md](README.md).

`packages/ui` and `packages/api-client` are hosted in dmp-web as frontend-facing shared packages. System specifications and shared contracts live in dmp-docs. Coordinate changes across affected repositories and keep contracts aligned.

## Commit and branch conventions

- Commits MUST follow Conventional Commits 1.0: `<type>[(<scope>)][!]: <description>`. Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Use an imperative, lowercase description with no trailing period; keep the header at 72 characters or fewer. A body/footer is optional; mark breaking changes with `!` or a `BREAKING CHANGE:` footer.
- Branches MUST follow `<type>/<short-kebab-description>`, using one of the same types (for example `feat/m2-schema-migrations`, `fix/auth-token-expiry`, `docs/update-readme`). Never commit directly to `main`; work through pull requests.
