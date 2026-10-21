# Requirements Document

## Introduction

The Agent Orchestrator (AO) is a control-plane service for coordinating heterogeneous coding agents against a Git repository that may exist only on a remote SSH server. AO shall coordinate Kiro, Claude, Codex, Agy, and OpenCode through provider-specific adapters rather than assuming a common command-line interface, API, or protocol. AO shall own job and task lifecycle, dependency scheduling, execution policy, validation, review, approvals, artifacts, and audit records.

The first implementation slice is an AO skeleton with PostgreSQL durable state, Redis queue/lock support, Git worktree isolation, sequential execution, validation gates, and two adapters, preferably Kiro and Claude or Codex. The first slice shall support a repository registered by SSH and shall execute against the remote host without requiring the source repository to be present in the local AO workspace.

This document defines requirements only. It does not define the implementation design, database migration plan, deployment manifest, or task breakdown.

### Scope

The feature includes:

- Remote repository registration and SSH-host execution.
- Job creation, task dependency graphs, scheduling, state transitions, retries, cancellation, and timeouts.
- A common adapter contract for Kiro, Claude, Codex, Agy, and OpenCode.
- Immutable context packages, isolated Git worktrees and branches, structured run results, event streaming, validation, review, approval, merge, artifact persistence, audit, security controls, and observability.
- A sequential MVP with two adapters that can be extended to additional providers and parallel execution.

### Non-Goals

The feature does not define a universal agent CLI, provider-specific command syntax, a new Git hosting service, direct database access for workers, a Kafka-based event architecture, autonomous production deployment, a business-domain workflow for DriverManagementPlatform, or undocumented payroll, booking, leave, or authorization policies. The DriverManagementPlatform handoff and `AGENTS.md` provide architectural context only; the existing `driver-management-dashboard` spec is not authoritative for this feature.

## Glossary

- **Agent Orchestrator (AO)**: The control-plane service that owns orchestration state, policy, scheduling, execution coordination, validation, review, approval, artifacts, and audit.
- **Job**: A user-requested orchestration unit containing repository identity, one or more Tasks, execution policy, and an overall outcome.
- **Task**: A unit of work in a Job with instructions, dependencies, allowed scope, validation requirements, and one or more Runs.
- **Run**: One attempt by one Worker to execute one Task in an isolated Worktree.
- **Worker**: A provider process or remote execution endpoint that performs a Run on behalf of AO.
- **Adapter**: A provider-specific integration that exposes a common AO contract for capabilities, starting a Run, streaming events, cancelling a Run, and collecting a result.
- **Provider**: An agent implementation coordinated by AO, including Kiro, Claude, Codex, Agy, or OpenCode.
- **Worktree**: A Git working tree created for one Run, isolated from every other active Run and associated with a dedicated branch.
- **Context Package**: An immutable, hashed input package sent to a Worker. The package contains repository identity, base commit SHA, Job and Task identity, specification references, allowed paths, allowed commands, constraints, and context hash.
- **Artifact**: A persisted output associated with a Job, Task, or Run, such as a patch, structured result, test report, log bundle, review report, or generated file.
- **Approval Gate**: A policy-controlled checkpoint requiring an authorized human decision before a protected action can continue.
- **Validation Gate**: A required automated or independent review check that must pass before a Task or Job can advance.
- **Task Graph**: The directed acyclic graph of Tasks and dependency edges within a Job.
- **Event**: A timestamped, ordered execution observation emitted by AO or a Worker, such as status, output, command, test, finding, or heartbeat.
- **Structured Run Result**: A machine-readable result containing status, changed files, test results, findings, artifacts, and failure information.
- **Context Hash**: A cryptographic digest of the canonical Context Package contents.
- **Repository Identity**: The immutable or verifiable combination of repository URL, SSH host identity, repository path, and selected revision information used to identify a source repository.
- **AO Operator**: An authenticated human or service principal authorized to configure AO, submit Jobs, inspect Runs, or perform permitted operational actions.
- **Human Approver**: An authenticated human authorized by policy to approve a protected action.
- **Secret Reference**: An indirect identifier for a credential stored in an approved secret store; a Secret Reference is not the secret value.

## Requirements

### Requirement 1: Control-Plane Ownership and Scope

**User Story:** As an AO Operator, I want AO to own orchestration state and policy, so that heterogeneous Workers remain replaceable and execution remains auditable.

#### Acceptance Criteria

1. WHEN AO accepts a Job, Task, or Run change, THE AO SHALL persist lifecycle state, dependencies, execution policy, validation outcome, approval outcome, Artifact metadata, and audit history for the affected object.
2. WHEN AO creates a Job, Task, or Run, THE AO SHALL assign a stable identifier and SHALL expose the identifier through the machine-readable operator interface.
3. WHEN a Worker emits output or an execution decision, THE AO SHALL store the output as policy input and SHALL determine the resulting lifecycle transition through AO policy.
4. IF a Worker submits a state mutation outside the Adapter contract, THEN THE AO SHALL reject the mutation, preserve the prior AO state, and append a security audit record.
5. THE AO SHALL represent Kiro, Claude, Codex, Agy, and OpenCode as distinct Provider identities and SHALL retain the selected Provider identity on every Run.

### Requirement 2: Remote Repository Registration and SSH Execution

**User Story:** As an AO Operator, I want to register a Git repository hosted on an SSH server, so that AO can coordinate Runs without assuming the source repository is locally visible.

#### Acceptance Criteria

1. WHEN an AO Operator registers a Remote Repository, THE AO SHALL persist Repository Identity, SSH endpoint, canonical repository path, default branch, host-key verification policy, and Secret References without persisting raw credentials in Job or Run records.
2. WHEN AO prepares a Run, THE AO SHALL verify the SSH host identity, repository path, requested revision, and base commit SHA before Worker execution.
3. WHEN AO executes a repository command for a Run, THE AO SHALL record remote host identity, command classification, command start time, command end time, exit status, and Run identifier.
4. IF SSH host verification, repository verification, revision verification, or base SHA verification fails, THEN THE AO SHALL block Worker execution and SHALL record a machine-readable setup failure.
5. IF the local AO workspace lacks the source repository, THEN THE AO SHALL support repository registration, Context Package creation, and remote Run preparation from Remote Repository metadata.
6. WHEN AO creates a Context Package, THE AO SHALL bind the Run to the verified Repository Identity and base commit SHA, and SHALL reject any later repository identity or base SHA change for that Run.
7. [ASSUMPTION] THE AO SHALL use a configured managed Remote Workspace root and SHALL persist the selected root configuration for each remote execution environment.
8. [NEEDS-OWNER] The production deployment topology, SSH transport, credential source, bastion or proxy requirements, and host-key enrollment process SHALL remain explicit configuration confirmed before production enablement.

### Requirement 3: Job, Task, and Dependency Graph Management

**User Story:** As an AO Operator, I want to express work as dependent Tasks inside a Job, so that AO can execute work in a deterministic order.

#### Acceptance Criteria

1. WHEN an AO Operator submits a Job, THE AO SHALL require a Remote Repository, base revision or branch, Job objective, execution policy, and at least one Task.
2. IF a Job is incomplete or its Task Graph contains a cycle, missing dependency, duplicate Task identifier, or cross-Job dependency, THEN THE AO SHALL reject the submission and SHALL persist no partial Job, Task, or dependency record.
3. WHEN an AO Operator creates a Task, THE AO SHALL persist instructions, specification references, allowed paths, allowed commands, Validation Gates, retry policy, timeout policy, and dependency references.
4. WHEN all dependencies of a Task satisfy the configured policy-accepted successful outcomes, THE AO SHALL assign the Task the `ready` state.
5. WHILE a dependency remains incomplete or has an outcome rejected by policy, THE AO SHALL assign the dependent Task `blocked` or `queued` according to scheduling policy and SHALL expose each blocking dependency identifier and outcome.
6. THE AO SHALL support exactly these Task states: `queued`, `ready`, `running`, `blocked`, `validation_failed`, `review_required`, `approved`, `merged`, and `cancelled`.
7. IF a requested Task transition is not permitted by the configured state machine, THEN THE AO SHALL reject the transition, preserve the prior state, and record the attempted transition.
8. [ASSUMPTION] During the MVP, THE AO SHALL allow at most one running Task per Job while retaining the Task Graph model for later parallel execution.
9. [NEEDS-OWNER] Dependency-failure overrides, manual graph overrides, multiple independent roots, and the set of terminal outcomes accepted by dependent Tasks SHALL remain explicit configuration confirmed by the owner.

### Requirement 4: Immutable Context Packaging

**User Story:** As a Worker, I want a complete immutable Context Package, so that a Run is reproducible and bounded by explicit instructions and permissions.

#### Acceptance Criteria

1. WHEN AO creates a Run, THE AO SHALL create a Context Package containing Repository Identity, base commit SHA, Job identifier, Task identifier, specification references, allowed paths, allowed commands, constraints, execution policy, and Context Hash.
2. WHEN AO serializes a Context Package, THE AO SHALL use a canonical representation in which identical content produces the same SHA-256 Context Hash and any included-content change produces a different Context Hash.
3. WHEN AO starts a Run, THE AO SHALL persist and expose the Context Hash to the Worker, Adapter, and audit record.
4. IF a Context Package mutation is requested after Run start, THEN THE AO SHALL reject the mutation and SHALL require a new Run with a newly computed Context Hash.
5. IF a Task omits allowed paths, allowed commands, or constraints, THEN THE AO SHALL apply configured policy defaults and SHALL record each applied default in the Context Package and audit history.
6. WHEN a Context Package contains a specification reference, THE AO SHALL resolve the reference by an immutable identifier or revision that does not depend on access to the local AO IDE workspace.
7. IF a Worker requests a path or command outside the Context Package policy, THEN THE AO SHALL deny the request and SHALL emit a policy-violation Event.
8. [ASSUMPTION] THE AO SHALL use SHA-256 as the initial Context Hash algorithm.

### Requirement 5: Adapter Registry and Provider Capability Contract

**User Story:** As an AO Operator, I want provider-specific adapters behind one contract, so that AO can add or replace agents without changing orchestration logic.

#### Acceptance Criteria

1. WHEN an Adapter is registered, THE AO SHALL require Provider identity, Adapter version, protocol version, execution mode, declared capabilities, configuration reference, result schema version, and health state.
2. THE AO SHALL represent at least these Adapter capabilities: start Run, stream Events, cancel Run, collect Structured Run Result, and report health.
3. WHEN AO schedules a Run, THE AO SHALL select an Adapter only when Provider identity, protocol version, execution mode, required capabilities, configuration compatibility, and result schema compatibility satisfy the Task policy.
4. IF no registered Adapter satisfies the Task policy or compatibility requirements, THEN THE AO SHALL leave the Task unstarted, record a typed capability or configuration outcome, and expose the missing requirement.
5. WHEN AO selects an Adapter, THE AO SHALL persist Provider identity, Adapter version, protocol version, and Worker version when available on the Run.
6. THE AO SHALL support Kiro through a provider-specific CLI, ACP, or headless Adapter without treating any Kiro integration as the AO itself.
7. THE AO SHALL provide separate Adapter identities and implementations for Claude, Codex, Agy, and OpenCode rather than requiring a shared provider command or protocol.
8. [NEEDS-OWNER] Preferred Kiro integration mode, provider authentication, provider command or API versions, supported models, and production enablement criteria SHALL remain explicit Adapter configuration confirmed per deployment.

### Requirement 6: Worker Process and API Execution

**User Story:** As an AO Operator, I want AO to start Workers through controlled process or API adapters, so that each provider can run using its native integration safely.

#### Acceptance Criteria

1. WHEN AO starts a Run, THE selected Adapter SHALL receive the Run identifier, immutable Context Package, remote Worktree reference, execution policy, and timeout policy.
2. IF any required Adapter input is missing or invalid, THEN THE Adapter SHALL block Worker execution and SHALL return a typed setup failure to AO.
3. WHEN a Worker runs as a local process on an SSH host, THE Adapter SHALL use an explicit executable or endpoint, Worktree directory, environment-variable allowlist, input reference, and output-capture policy.
4. WHEN a Worker runs through a provider API, THE Adapter SHALL record the provider request identifier, model or agent version when available, and API response status without recording provider secrets.
5. WHEN a Worker starts, THE Adapter SHALL emit a Run-start Event containing Provider identity, Adapter version, Worktree reference, and Context Hash.
6. IF a Worker exits without a valid Structured Run Result, THEN THE Adapter SHALL return a typed adapter failure and SHALL persist captured diagnostics as an Artifact.
7. THE AO SHALL prevent Workers from directly accessing AO PostgreSQL data, Redis data, or the secret store.
8. [NEEDS-OWNER] Provider executable names, flags, endpoints, authentication mechanisms, model selection, network egress, and provider-specific result formats SHALL remain Adapter-specific configuration confirmed before production use.

### Requirement 7: Event Streaming and Structured Results

**User Story:** As an AO Operator, I want live execution Events and structured results, so that I can monitor progress and automate gates without parsing free-form agent prose.

#### Acceptance Criteria

1. WHILE a Run is active, THE AO SHALL emit Events for lifecycle changes, Worker output, command execution, validation checks, findings, heartbeats, cancellation, and failures, and SHALL assign each Event a monotonic Run sequence number.
2. WHEN AO persists an Event, THE AO SHALL store Run identifier, sequence number, Event type, timestamp, source, redacted payload, and correlation identifier.
3. WHEN a Worker completes a Run, THE Adapter SHALL return a Structured Run Result containing result status, changed files, test results, findings, Artifacts, and failure information when applicable.
4. WHEN a Structured Run Result lists changed files, THE AO SHALL persist each path, change kind, and diff or commit reference when available.
5. IF a Worker returns malformed, incomplete, or schema-incompatible output, THEN THE AO SHALL classify the Run as an adapter or result-validation failure and SHALL prevent a successful outcome.
6. THE AO SHALL retain free-form Worker output only as bounded, redacted diagnostic data and SHALL require structured evidence for validation or merge decisions.
7. WHEN an operator reconnects to a Run stream with a sequence number, THE AO SHALL replay retained Events after that sequence or SHALL report the earliest retained sequence when earlier Events are unavailable.
8. [ASSUMPTION] THE initial Event stream SHALL provide at-least-once delivery with sequence-based deduplication for reconnecting clients.

### Requirement 8: Worktree and Branch Isolation

**User Story:** As an AO Operator, I want every Run isolated in Git, so that concurrent or retried Workers cannot corrupt one another's mutable files.

#### Acceptance Criteria

1. WHEN AO prepares a Run, THE AO SHALL create or verify exactly one dedicated Git Worktree and branch for that Run from the recorded base commit SHA.
2. IF a Run requests a Worktree or branch already assigned to another Run, THEN THE AO SHALL reject the request and SHALL block Worker execution.
3. WHEN a Run ends, THE AO SHALL persist Worktree path, branch name, base SHA, resulting commit SHA when available, cleanup status, and cleanup failure reason when applicable.
4. IF Worktree creation, branch creation, or base SHA verification fails, THEN THE AO SHALL block Worker execution and SHALL record a setup failure.
5. IF the execution environment can detect a Worker change outside its Worktree, THEN THE AO SHALL exclude the change from the Run result and SHALL record a security finding.
6. WHEN AO creates a retry Run, THE AO SHALL assign a new Run identifier and new Worktree unless policy explicitly permits a clean, verified reconstruction of the prior Worktree.
7. WHEN AO removes a Worktree, THE AO SHALL first persist Run Artifacts, logs, and result metadata.
8. [ASSUMPTION] The MVP SHALL use one branch per Run and SHALL merge only a verified commit or patch produced from that Run's Worktree.

### Requirement 9: Cancellation, Retry, Timeout, and Failure Handling

**User Story:** As an AO Operator, I want to stop unsafe or stalled work and retry recoverable failures, so that execution remains controllable.

#### Acceptance Criteria

1. WHEN an authorized AO Operator requests cancellation of a queued or running Task, THE AO SHALL record cancellation-requested state, requester identity, and request time, and SHALL instruct the Adapter to cancel the Worker.
2. WHEN a Worker acknowledges cancellation or reaches a safe termination point, THE AO SHALL transition the Run and Task to `cancelled` and SHALL preserve partial Events and Artifacts.
3. IF a Worker remains active after the configured cancellation grace period, THEN THE AO SHALL escalate termination according to execution policy and SHALL record every escalation step.
4. WHEN a Run exceeds its configured timeout, THE AO SHALL record timeout metadata, request cancellation, and prevent the timed-out Run from entering validation or merge.
5. WHEN a Run has a retryable failure and retry budget remains, THE AO SHALL create exactly one new Run with a new Run identifier, retain the prior Run, and apply configured retry backoff.
6. IF retry budget is exhausted, THEN THE AO SHALL assign a terminal machine-readable failure outcome and SHALL leave dependent Tasks blocked.
7. THE AO SHALL classify failures as at least setup failure, adapter failure, Worker failure, validation failure, policy violation, cancellation, timeout, and approval rejection.
8. [ASSUMPTION] The default retry policy SHALL permit two retries with exponential backoff and a maximum per-Run timeout of 30 minutes.
9. [NEEDS-OWNER] Retry budgets, timeout limits, cancellation grace periods, escalation steps, and cost ceilings SHALL remain configurable and owner-confirmed for each environment and Provider.

### Requirement 10: Validation and Independent Review Gates

**User Story:** As an AO Operator, I want mandatory automated validation and independent review before merge, so that agent-generated changes receive objective checks.

#### Acceptance Criteria

1. WHEN a Worker reports a candidate result, THE AO SHALL execute every Validation Gate required by the Task policy before marking the Task eligible for approval or merge.
2. THE AO SHALL support Validation Gates for tests, lint, type-check, migration checks where applicable, repository status, and independent review.
3. WHEN a Validation Gate completes, THE AO SHALL persist gate name, gate type, command or reviewer reference, exit status or decision, output Artifact reference, gate version, and start and end timestamps.
4. IF a required Validation Gate fails, is unavailable, or returns invalid evidence, THEN THE AO SHALL transition the Task to `validation_failed`, preserve the gate evidence, and prevent merge approval for that result.
5. WHEN independent review is required, THE AO SHALL use a reviewer identity distinct from the producing Worker unless policy contains a recorded pre-approved exception.
6. IF changed files include migration, authentication, authorization, security, secret-handling, or deployment-sensitive paths, THEN THE AO SHALL apply the configured elevated Validation Gates and SHALL identify the affected paths.
7. WHEN all required Validation Gates pass, THE AO SHALL transition the Task to `review_required` or `approved` according to the configured approval policy.
8. [ASSUMPTION] The default gate set SHALL include repository tests, lint, type-check, applicable migration checks, repository status, and one independent review before protected-branch merge.
9. [NEEDS-OWNER] Exact commands, test environments, review independence definition, flaky-test policy, and repository-specific gate requirements SHALL remain repository-owned configuration confirmed by owners.

### Requirement 11: Approval, Protected Merge, and Sensitive Actions

**User Story:** As a Human Approver, I want explicit approval gates for high-impact actions, so that agents cannot independently perform irreversible or sensitive operations.

#### Acceptance Criteria

1. WHEN a Task targets a Protected Branch, THE AO SHALL create an Approval Gate before merge.
2. WHEN a Run requests production migration or deployment, THE AO SHALL create an Approval Gate before executing the protected action.
3. WHEN a Run changes authentication, authorization, security controls, or secret-handling behavior, THE AO SHALL create an Approval Gate before merge or deployment.
4. WHEN a Run requests a destructive action, Secret Reference access outside policy, or an unresolved business-policy decision, THE AO SHALL pause the affected Task in `review_required` and SHALL identify the action and required approver role.
5. WHEN a Human Approver approves or rejects an Approval Gate, THE AO SHALL persist approver identity, decision, timestamp, policy version, reason or comment, and affected Job, Task, Run, branch, and commit references.
6. IF an Approval Gate is rejected or expires, THEN THE AO SHALL prevent the protected action and SHALL transition the affected Task to the configured blocked or cancelled outcome.
7. IF the proposed approver is the Worker that produced the affected result, THEN THE AO SHALL deny self-approval and SHALL record the denial.
8. [NEEDS-OWNER] Approval roles, approval expiration, two-person approval, production environment definition, protected-branch patterns, and emergency override behavior SHALL remain explicit configuration confirmed by the owner.

### Requirement 12: Artifact, Audit, and Reproducibility Persistence

**User Story:** As an AO Operator, I want complete Run evidence preserved, so that results can be reproduced, reviewed, and investigated.

#### Acceptance Criteria

1. FOR EACH Run, THE AO SHALL persist Repository Identity, remote host identity, base SHA, Provider, Adapter version, Worker version, prompt or instruction hash, Context Hash, Worktree and branch, changed files, executed commands, test results, findings, approval identity, and lifecycle timestamps.
2. WHEN AO persists a Structured Run Result or Artifact, THE AO SHALL persist result schema version, content reference or checksum, producer identity, creation timestamp, and retention classification.
3. WHEN AO executes a state transition, policy decision, command classification, approval action, or security denial, THE AO SHALL append an audit record containing actor identity, target identity, decision or action, timestamp, correlation identifier, and reason when available.
4. THE AO SHALL make audit records append-only to ordinary AO Operators and SHALL permit correction or deletion only through an explicitly authorized retention operation.
5. WHEN AO reconstructs a Run summary, THE AO SHALL identify the exact repository revision, Context Hash, Provider and Worker version, validation evidence, and approval decision used for the outcome.
6. IF an Artifact contains a secret, credential, access token, or unredacted sensitive personal data, THEN THE AO SHALL redact or quarantine the Artifact before ordinary operator access.
7. [ASSUMPTION] The initial Artifact store SHALL use PostgreSQL metadata with content in an approved object or filesystem store referenced by checksum.
8. [NEEDS-OWNER] Artifact, Event, log, audit, and PII retention duration, legal hold behavior, encryption requirements, maximum log size, and deletion authority SHALL remain owner-confirmed configuration.

### Requirement 13: Security, Least Privilege, and PII Protection

**User Story:** As a security owner, I want Workers constrained to explicit permissions, so that agent execution cannot cause uncontrolled repository or infrastructure changes.

#### Acceptance Criteria

1. THE AO SHALL apply separate permission scopes for AO control operations, SSH repository access, Worker execution, validation commands, Artifact storage, and approvals.
2. THE AO SHALL enforce command allowlists, path allowlists, environment-variable allowlists, network egress policy, and resource limits for each Run.
3. IF a command, path, environment variable, network request, or file operation is outside the Run policy, THEN THE AO SHALL deny the operation and SHALL append a redacted security Event and audit record.
4. THE AO SHALL pass Secret References to Adapters only through approved secret retrieval mechanisms and SHALL prevent raw secret values from appearing in prompts, Events, command logs, Artifacts, or error messages.
5. THE AO SHALL prevent Workers from connecting directly to AO data stores and SHALL expose only the Adapter and execution interfaces required for the Run.
6. THE AO SHALL sanitize or redact credentials, tokens, private keys, and configured PII patterns from streamed output and persisted diagnostics.
7. WHEN a Run accesses repository content containing personal data, THE AO SHALL apply the configured PII handling policy to Worker context, logs, Artifacts, and operator views.
8. IF an agent or Adapter reports a security violation, THEN THE AO SHALL stop or isolate the affected Run according to policy and SHALL require human review before protected actions continue.
9. [ASSUMPTION] The initial security baseline SHALL deny commands and network destinations by default unless a Task policy explicitly allows them.
10. [NEEDS-OWNER] Threat model, identity provider, MFA, SSH key or certificate method, secret manager, network isolation, PII classification, and jurisdiction-specific retention rules SHALL remain owner-confirmed.

### Requirement 14: Observability and Operator Control

**User Story:** As an AO Operator, I want health, metrics, logs, and traceable execution status, so that I can operate AO on an SSH server and diagnose failures.

#### Acceptance Criteria

1. THE AO SHALL expose a health status for AO control components, PostgreSQL, Redis, remote SSH connectivity, Git availability, registered Adapters, and Artifact storage.
2. THE AO SHALL emit structured logs containing correlation identifier, Job identifier, Task identifier, Run identifier, Provider, Adapter, and outcome fields while excluding secrets and configured PII.
3. THE AO SHALL record metrics with defined units for queued Tasks (count), active Runs (count), Run duration (seconds), setup failures (count), Adapter failures (count), validation failures (count), retries (count), cancellations (count), timeouts (count), approval wait time (seconds), queue wait time (seconds), and Provider usage metadata when available.
4. WHEN an operator reconnects to an active Run stream, THE AO SHALL replay Events after the requested sequence or SHALL report the earliest retained sequence.
5. IF AO loses a Worker process, SSH connection, or Adapter connection, THEN THE AO SHALL classify the Run as recoverable or failed using persisted heartbeat, timeout, and connection evidence and SHALL expose that evidence with the classification.
6. THE AO SHALL provide an operator-visible explanation for every Task in `queued`, `blocked`, `validation_failed`, `review_required`, `cancelled`, or another state that prevents advancement.
7. [ASSUMPTION] The initial operational target SHALL be 99 percent AO control API availability per calendar month, excluding planned maintenance, and SHALL return health responses within 5 seconds.
8. [NEEDS-OWNER] Availability target, alert thresholds, log and metric backend, trace propagation standard, on-call ownership, and incident response objectives SHALL remain owner-confirmed.

### Requirement 15: Durable State, Queueing, Locking, and Consistency

**User Story:** As an AO Operator, I want orchestration state to survive process restarts, so that active Jobs are recoverable and duplicate execution is prevented.

#### Acceptance Criteria

1. THE AO SHALL persist authoritative Job, Task, Run, Event, Artifact metadata, Approval Gate, and audit state in PostgreSQL or another policy-approved durable store.
2. THE AO SHALL use a durable queue and distributed lock mechanism to coordinate scheduling and SHALL allow at most one active claim for a Task or Run.
3. WHEN AO restarts, THE AO SHALL recover queued and active execution records from durable state and SHALL reconcile active Runs within the configured recovery window before starting a duplicate Run.
4. IF two scheduler workers attempt to claim the same ready Task, THEN THE AO SHALL accept exactly one valid claim, reject the other claim, and record both the winning claim and rejected claim attempt.
5. WHEN a state transition and its audit record are accepted, THE AO SHALL persist both atomically or SHALL mark the transition uncertain and prevent downstream protected actions until reconciliation.
6. [ASSUMPTION] The MVP SHALL use PostgreSQL for durable state and Redis for queueing and locks, with synchronous execution before introducing Kafka.
7. IF no confirmed asynchronous, replay, or fan-out requirement exists, THEN THE AO SHALL omit Kafka from the MVP implementation.
8. [NEEDS-OWNER] PostgreSQL and Redis deployment mode, replication, backup, recovery objectives, lock lease duration, and future outbox requirements SHALL remain owner-confirmed.

### Requirement 16: MVP and Extensible Delivery Boundary

**User Story:** As a coding agent implementing the first slice, I want an explicit MVP boundary, so that I can implement and test the skeleton without inventing unresolved provider or business rules.

#### Acceptance Criteria

1. THE first implementation slice SHALL provide interfaces for Remote Repository registration, Job and Task creation, dependency validation, Run creation, Context Package creation, status inspection, Event streaming, cancellation, Validation Gate result recording, review recording, Approval Gate recording, and Artifact metadata.
2. THE first implementation slice SHALL provide PostgreSQL durable state, Redis queue or lock integration, SSH-based Remote Repository execution, Git Worktree isolation, sequential scheduling, mandatory Validation Gates, and audit records.
3. THE first implementation slice SHALL provide two working Adapters, including Kiro and one of Claude or Codex by default, while keeping Adapter Registry contracts extensible to Agy and OpenCode.
4. IF a required Adapter is unavailable or unconfigured, THEN THE AO SHALL return a typed capability or configuration error and SHALL leave the affected Task unstarted.
5. THE first implementation slice SHALL include tests for happy paths, graph validation, state transitions, Context Hash immutability, Worktree isolation, Adapter failure, cancellation or timeout, Validation Gate failure, Approval Gate denial, redaction, restart recovery, and duplicate claim handling.
6. THE first implementation slice SHALL omit Kafka, local visibility of the source repository, direct Worker access to AO data stores, autonomous protected-branch merge, and autonomous production deployment.
7. WHEN an unresolved provider, deployment, security, retention, cost, or business-policy decision affects implementation, THE AO SHALL expose the decision as configuration or a typed stub and SHALL label it `[NEEDS-OWNER]`.
8. [NEEDS-OWNER] The owner SHALL confirm the first two Providers, target SSH server operating system, packaging method, operator interface, and initial deployment environment before implementation begins.

## Non-Functional Requirements

### NFR-1: Performance Defaults

1. [ASSUMPTION] THE AO SHALL acknowledge Job and Task submission requests within 2 seconds under a target load of 20 concurrent AO Operators, excluding remote Worker execution time.
2. [ASSUMPTION] THE AO SHALL expose a newly persisted Event to a connected stream client within 5 seconds under normal operating conditions.
3. [ASSUMPTION] THE AO SHALL complete state and policy reads within 500 milliseconds at the 95th percentile under the target load, excluding artifact download time.
4. [NEEDS-OWNER] The owner SHALL confirm expected concurrent Jobs, concurrent Runs, repository size, event volume, artifact volume, and performance objectives before capacity planning.

### NFR-2: Reliability and Recovery

1. [ASSUMPTION] THE AO SHALL preserve committed durable state across an AO process restart and SHALL reconcile active Runs within 60 seconds after control-plane recovery.
2. [ASSUMPTION] The initial development environment SHALL target a recovery point objective of 24 hours and a recovery time objective of 4 hours for PostgreSQL state.
3. [NEEDS-OWNER] Production recovery point, recovery time, backup frequency, restore-test frequency, and data-loss tolerance SHALL be confirmed.

### NFR-3: Compatibility and Versioning

1. THE AO SHALL version Adapter contracts, Structured Run Results, Event payloads, Context Packages, and policy schemas.
2. WHEN a Worker or Adapter reports an unsupported contract version, THE AO SHALL reject the Run before execution or classify the result as incompatible without treating it as successful.
3. THE AO SHALL preserve provider name and version separately from Adapter version so that provider upgrades remain auditable.
4. [NEEDS-OWNER] Supported Python, PostgreSQL, Redis, Git, SSH, Kiro, Claude, Codex, Agy, and OpenCode versions SHALL be confirmed per deployment.

### NFR-4: Data Protection and Access

1. THE AO SHALL encrypt control-plane and artifact traffic in transit using the approved deployment transport.
2. THE AO SHALL encrypt durable state, logs, and Artifacts at rest when the deployment platform supports managed encryption.
3. THE AO SHALL enforce authenticated operator access and role-based authorization for repository registration, Job submission, cancellation, approval, artifact access, and audit access.
4. [NEEDS-OWNER] The identity provider, operator roles, service-to-service authentication, encryption key ownership, and access review frequency SHALL be confirmed.

### NFR-5: Cost and Resource Limits

1. THE AO SHALL support per-Job and per-Task limits for wall-clock duration, retry count, Worker concurrency, output size, Artifact size, and optional provider usage or token cost.
2. IF a configured resource or cost limit is reached, THEN THE AO SHALL stop or pause the affected Run according to policy and SHALL record the limit breach.
3. [ASSUMPTION] The initial default output limit SHALL be 10 MiB per Event payload and 100 MiB per single diagnostic Artifact, with configurable values.
4. [NEEDS-OWNER] Provider budget, token or API cost accounting, currency, cost ceiling, and billing owner SHALL be confirmed.

## Explicit Owner Decisions

The following decisions are intentionally unresolved. Implementations SHALL expose configuration or typed stubs for these decisions and SHALL not silently invent business rules:

- [NEEDS-OWNER] Exact CLI/API/protocol commands and supported versions for Kiro, Claude, Codex, Agy, and OpenCode.
- [NEEDS-OWNER] Whether Kiro integration should prefer Kiro CLI, ACP, headless mode, or a compatibility sequence; Kiro CLI is needed on the SSH host only when AO launches or controls Kiro there.
- [NEEDS-OWNER] Authentication and credential storage for each provider, including SSH keys/certificates, API tokens, SSO, MFA, and secret-manager choice.
- [NEEDS-OWNER] AO deployment topology, process supervisor/container strategy, SSH server operating system, network segmentation, bastion/proxy use, and public/private exposure.
- [NEEDS-OWNER] Operator UI versus API-only operation for the first release.
- [NEEDS-OWNER] Repository hosting providers, host-key enrollment, repository size limits, submodules, LFS, monorepo behavior, and protected-branch patterns.
- [NEEDS-OWNER] Task graph override rules, dependency failure behavior, manual retry behavior, and merge conflict resolution ownership.
- [NEEDS-OWNER] Validation command definitions and test environment provisioning for each registered repository.
- [NEEDS-OWNER] Human approval roles, two-person approval requirements, approval expiry, and emergency override policy.
- [NEEDS-OWNER] Artifact, Event, log, audit, and PII retention, deletion, legal hold, and export rules.
- [NEEDS-OWNER] Maximum concurrent Runs, per-provider concurrency, timeouts, retry budgets, cancellation grace periods, and cost/token limits.
- [NEEDS-OWNER] Availability, performance, backup, disaster recovery, alerting, and incident response objectives.
- [NEEDS-OWNER] Whether future asynchronous/replay requirements justify Kafka, an outbox, or another event transport after the synchronous MVP.

## Implementation Guidance for Coding Agents

Coding agents implementing this requirements document may choose implementation details for persistence, APIs, process supervision, and adapter internals only when those choices satisfy the requirements and do not resolve an `[NEEDS-OWNER]` item silently. Each implementation should include focused tests for the acceptance criteria it claims to satisfy, use fake repository identities and credentials in fixtures, redact secrets and PII from test output, and leave explicit typed configuration or `NotImplementedError` stubs for unresolved provider integrations.

The local workspace containing this specification is not the source repository. Implementations SHALL obtain repository source through the configured Remote Repository and SSH execution path, and SHALL treat any local source files as optional specification context rather than the runtime repository.
