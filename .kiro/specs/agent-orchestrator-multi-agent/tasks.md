# Implementation Plan: Agent Orchestrator (AO) — MVP Slice

## Overview

This plan implements the MVP slice (Requirement 16) of the Agent Orchestrator: a Python 3.12 / FastAPI async control-plane service under `services/agent-orchestrator/`, with PostgreSQL 16 durable state, Redis queue/locks, Git worktree isolation on remote SSH hosts, sequential execution, mandatory validation and approval gates, audit records, and two working Adapters (Kiro plus one of Claude/Codex) while keeping the Adapter Registry extensible to Agy/OpenCode.

The build order is: project scaffold → core (config, DB, Redis, exceptions, enums, redaction) → ORM models + migration → Pydantic schemas → repositories → context packaging & hashing → graph validation & state machine → scheduler/claiming → worktree & SSH execution → adapter contract & registry (Kiro + Claude/Codex concrete, Agy/OpenCode stubs) → run lifecycle, events, structured results → validation gates → approval gates → artifacts/audit → routers & exception handler → observability/health → integration wiring. Each step builds on the previous and ends by wiring new components into the running application.

Property-based tests (Hypothesis, min 100 examples each) implement the 25 correctness properties from the design and are placed next to the implementation they validate. Unit, edge-case, and integration/example tests cover the remaining Req 16.5 scenarios. All test sub-tasks are optional (`*`) and use fake repository identities/credentials with redacted output.

Conventions (from `AGENTS.md`): strict `router -> service -> repository` layering, Pydantic v2 schemas separate from SQLAlchemy 2.x typed ORM models, typed domain exceptions mapped by a single FastAPI exception handler, Alembic migrations, `uv`, `pytest` + `pytest-asyncio`, `ruff`. `[NEEDS-OWNER]` items stay as typed config or `NotImplementedError` stubs with a `# NEEDS-OWNER:` marker — never invented.

## Tasks

- [ ] 1. Project scaffold, dependencies, and settings
  - Create `pyproject.toml` (uv) for `services/agent-orchestrator/` pinning Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic, Pydantic v2, psycopg, redis, Hypothesis, pytest, pytest-asyncio, ruff
  - Add `app/main.py` FastAPI app factory and package `__init__.py` files across `app/core`, `app/routers`, `app/schemas`, `app/services`, `app/tools`, `app/workflows`, and `app/tests`
  - Add `ruff` config and a `pytest`/`pytest-asyncio` config (asyncio mode)
  - _Requirements: 16.1, 16.2_

  - [ ] 1.1 Implement typed settings/config module
    - Create `app/core/config.py` with a Pydantic-settings model exposing all MVP config plus typed placeholders for `[NEEDS-OWNER]`/`[ASSUMPTION]` values: `DATABASE_URL`, `REDIS_URL`, Redis lock lease TTL, remote workspace root, policy defaults (allowed paths/commands/constraints), default retry policy (2 retries, exponential backoff, 30-min timeout), deny-by-default security baseline, output limits (10 MiB event / 100 MiB artifact), recovery window (60s)
    - Mark each assumption with `# ASSUMPTION:` and each unresolved decision with `# NEEDS-OWNER:`
    - _Requirements: 2.7, 3.9, 9.8, 9.9, 13.9, 15.6, 15.8, 16.7, NFR-5.3_

- [ ] 2. Core enumerations and typed exception hierarchy
  - [ ] 2.1 Define versioned StrEnums in `app/core/enums.py`
    - `TaskState` (exactly: queued, ready, running, blocked, validation_failed, review_required, approved, merged, cancelled), `RunStatus`, `FailureClass` (setup, adapter, worker, validation, policy_violation, cancellation, timeout, approval_rejection), `ProviderIdentity` (Kiro, Claude, Codex, Agy, OpenCode), `ExecutionMode`, `AdapterCapability`, `GateType`, `ApprovalGateKind`, `ApprovalDecision`, `ArtifactKind`, `RedactionStatus`
    - _Requirements: 3.6, 9.7, 1.5, 5.2, NFR-3.1_

  - [ ] 2.2 Implement the AOError exception hierarchy in `app/core/exceptions.py`
    - Base `AOError` with `error_code` + `correlation_id`; subclasses `SetupFailure`, `CapabilityError`, `ConfigurationError`, `GraphValidationError`, `IllegalTransitionError`, `ContractViolationError`, `ImmutabilityError`, `PolicyViolationError`, `ResultValidationError`, `AdapterFailure`, `ValidationGateFailure`, `ApprovalDenied`, `ClaimRejected`, `LimitExceeded`, `TimeoutExceeded`, `UncertainTransition`
    - _Requirements: 2.4, 5.4, 3.2, 3.7, 1.4, 2.6, 4.4, 4.7, 13.3, 7.5, 6.6, 10.4, 11.6, 11.7, 8.2, 15.4, 9.4, 15.5, 16.4_

  - [ ]* 2.3 Write unit tests for enums and exceptions
    - Assert `TaskState` contains exactly the nine required states and no others; assert each exception carries `error_code`/`correlation_id`
    - _Requirements: 3.6, 9.7_

- [ ] 3. Redaction utility (deny-by-default secret/PII scrubbing)
  - [ ] 3.1 Implement `Redactor` in `app/core/redaction.py`
    - Scrub configured credential, token, private-key, and PII patterns from arbitrary strings/structured payloads; return redacted copies; expose a single entry point used by event, diagnostic, and artifact persistence
    - _Requirements: 13.4, 13.6, 13.7_

  - [ ]* 3.2 Write property test for redaction
    - **Property 22: Redaction removes all configured secret and PII patterns and is idempotent**
    - **Validates: Requirements 13.6**

- [ ] 4. Database session, Redis client, and base ORM
  - Implement `app/core/db.py` (async SQLAlchemy 2.x engine + session factory from `DATABASE_URL`) and `app/core/redis.py` (async Redis client from `REDIS_URL`)
  - Add a typed SQLAlchemy `DeclarativeBase` with UTC `timestamptz` and server-assigned identifier conventions
  - _Requirements: 15.1, 1.2_

- [ ] 5. ORM models and initial Alembic migration
  - [ ] 5.1 Implement SQLAlchemy ORM models in `app/core/models.py`
    - `RemoteRepository`, `Job`, `Task`, `TaskDependency`, `Run`, `ContextPackage`, `Event`, `ValidationGateResult`, `ApprovalGate`, `Artifact`, `AdapterRegistry`, `AuditRecord` with all fields from the design Data Models
    - Constraints: unique `(job_id, task_key)` on Task; unique `(run_id, sequence_no)` on Event; same-Job-only TaskDependency edges; 1:1 Run↔ContextPackage; `transition_certainty` on AuditRecord
    - _Requirements: 1.1, 1.2, 3.2, 3.6, 4.1, 5.1, 7.2, 10.3, 11.5, 12.1, 12.2, 15.1, 15.5_

  - [ ] 5.2 Create the initial Alembic migration
    - Configure `alembic.ini` + `alembic/env.py` against the async engine; generate the migration creating every table, unique constraint, and CHECK (Task state enum, same-Job dependency) from 5.1
    - _Requirements: 3.2, 3.6, 7.1, 15.1_

  - [ ]* 5.3 Write an integration round-trip test for the schema
    - Apply migrations against a test PostgreSQL, insert and read one RemoteRepository + Job + Task, and assert unique/CHECK constraints reject duplicate Task identifiers and cross-Job dependency edges
    - _Requirements: 3.2, 15.1_

- [ ] 6. Pydantic v2 schemas (API + Context Package)
  - Implement request/response schemas in `app/schemas/` for repository registration, Job/Task submission, Run creation/status, Event payloads, validation gate results, approval decisions, and artifact metadata, plus the `ContextPackage` content model
  - Version Context Package, Event payload, Structured Run Result, and policy schemas (`schema_version` fields)
  - _Requirements: 16.1, 4.1, 7.2, 7.3, NFR-3.1_

- [ ] 7. Repository layer
  - Implement SQLAlchemy-backed repositories (`app/services/<domain>/repository.py` or `app/core/repositories.py`) for repositories, jobs/tasks/dependencies, runs, context packages, events, gate results, approval gates, artifacts, adapter registry, and audit records; return ORM/domain objects only
  - _Requirements: 1.1, 15.1_

- [ ] 8. Context Packager: canonicalization and hashing
  - [ ] 8.1 Implement `ContextPackager` in `app/tools/context.py`
    - `build()` assembles Repository Identity, base commit SHA, Job/Task ids, spec references, allowed paths/commands, constraints, execution policy; `canonicalize()` produces a deterministic byte representation (sorted keys, normalized encoding); `context_hash()` returns SHA-256 hex
    - Apply configured policy defaults for omitted allowed paths/commands/constraints and record them in `applied_defaults`
    - _Requirements: 4.1, 4.2, 4.5, 4.6, 4.8_

  - [ ]* 8.2 Write property test for context hashing
    - **Property 1: Context Hash is canonical, order-invariant, and change-sensitive**
    - **Validates: Requirements 4.2, 4.8**

  - [ ]* 8.3 Write property test for applied policy defaults
    - **Property 3: Omitted policy fields are filled with defaults and recorded exactly**
    - **Validates: Requirements 4.5**

- [ ] 9. Graph validation and Job/Task submission service
  - [ ] 9.1 Implement graph validation in `app/services/jobs/service.py`
    - Validate `>=1 Task`, DAG (no cycles), no missing dependency, no duplicate Task identifier, no cross-Job edge; raise `GraphValidationError` and persist no partial Job/Task/dependency on rejection; persist atomically on acceptance and assign stable identifiers
    - _Requirements: 3.1, 3.2, 1.1, 1.2_

  - [ ]* 9.2 Write property test for graph acceptance and no-partial-persistence
    - **Property 4: Job graph is accepted iff it is a valid same-Job DAG, with no partial persistence on rejection**
    - **Validates: Requirements 3.1, 3.2**

- [ ] 10. Task state machine and readiness
  - [ ] 10.1 Implement the transition table and readiness logic in `app/workflows/state_machine.py`
    - Accept a transition iff `(source, target)` is in the configured table, else raise `IllegalTransitionError`, preserve prior state, and record the attempt; compute `ready` iff all dependency outcomes are in the policy-accepted set, else expose the exact blocking set (dependency id + outcome)
    - _Requirements: 3.4, 3.5, 3.7_

  - [ ]* 10.2 Write property test for readiness and blocking set
    - **Property 5: Task readiness and blocking set are exact**
    - **Validates: Requirements 3.4, 3.5**

  - [ ]* 10.3 Write property test for permitted transitions only
    - **Property 6: Only permitted state-machine transitions are accepted**
    - **Validates: Requirements 3.7**

- [ ] 11. Worker contract-boundary enforcement
  - [ ] 11.1 Enforce out-of-contract mutation rejection in the run/service layer
    - Treat worker output as policy input only; reject any state mutation outside the Adapter contract, preserve prior AO state, and append a security audit record (`ContractViolationError`)
    - _Requirements: 1.3, 1.4_

  - [ ]* 11.2 Write property test for out-of-contract mutation rejection
    - **Property 7: Out-of-contract Worker mutations are rejected without state change**
    - **Validates: Requirements 1.4**

- [ ] 12. Checkpoint — core logic validated
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Immutable Run binding
  - [ ] 13.1 Enforce Run binding/context immutability after Run start
    - Reject any post-start change to bound repository identity, base commit SHA, or Context Package content (`ImmutabilityError`); require a new Run with a newly computed hash
    - _Requirements: 2.6, 4.3, 4.4_

  - [ ]* 13.2 Write property test for post-start immutability
    - **Property 2: Run binding and Context Package are immutable after Run start**
    - **Validates: Requirements 2.6, 4.4**

- [ ] 14. SSH executor and Remote Repository registration/verification
  - [ ] 14.1 Implement the `SSHExecutor` protocol and a default implementation in `app/core/ssh.py`
    - `verify_host_identity`, `resolve_revision`, `run_repo_command` recording remote host identity, command classification, start/end time, exit status, and Run id; registration persists Repository Identity, SSH endpoint, canonical path, default branch, host-key policy, and Secret References (never raw credentials)
    - Before execution, verify host/path/revision/base SHA; on failure raise `SetupFailure` and record a machine-readable setup failure; keep production transport/credential/bastion/host-key enrollment as `# NEEDS-OWNER:` typed config
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.8_

  - [ ]* 14.2 Write unit/integration tests for setup verification failures
    - Mock SSH to assert host/repo/revision/base-SHA failures block execution and record a setup failure with no usable worktree or Context Package
    - _Requirements: 2.2, 2.4_

- [ ] 15. Worktree Manager (isolation and cleanup ordering)
  - [ ] 15.1 Implement `WorktreeManager` in `app/tools/worktree.py`
    - `create_for_run` creates exactly one dedicated worktree + branch from the recorded base SHA; `verify_exclusive` rejects a worktree/branch already assigned to another active Run (`ClaimRejected`) and blocks execution; `persist_and_cleanup` persists worktree path, branch, base SHA, resulting commit SHA, cleanup status/failure reason, and persists Artifacts/logs/result metadata before removal
    - Record out-of-worktree changes as excluded security findings; use one branch per Run
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.7, 8.8_

  - [ ]* 15.2 Write property test for worktree/branch injectivity and collision rejection
    - **Property 12: Worktree and branch assignment is injective and collisions are rejected**
    - **Validates: Requirements 8.1, 8.2**

  - [ ]* 15.3 Write property test for artifact-before-cleanup ordering
    - **Property 13: Artifacts are persisted before worktree removal**
    - **Validates: Requirements 8.7**

- [ ] 16. Adapter contract, registry, and concrete/stub adapters
  - [ ] 16.1 Define the Adapter contract and schemas in `app/services/adapters/contract.py`
    - `Adapter` Protocol (`report_health`, `start_run`, `stream_events`, `cancel_run`, `collect_result`), `AdapterRunInput` (Run id, immutable Context Package, remote worktree ref, execution policy, timeout policy), `RunStartAck`, `RunEvent`, `CancelAck`, `StructuredRunResult`, `AdapterHealth`; validate required inputs or raise `SetupFailure`
    - _Requirements: 5.2, 6.1, 6.2, 6.4, 6.7_

  - [ ] 16.2 Implement the Adapter Registry and `select_adapter`
    - Persist/registers provider identity, adapter version, protocol version, execution mode, declared capabilities, config reference, result schema version, health state; `select_adapter(task_policy)` returns an Adapter iff all compatibility dimensions match, else returns a typed `CapabilityError`/`ConfigurationError` exposing the missing requirement and leaves the Task unstarted
    - _Requirements: 5.1, 5.3, 5.4, 5.5, 16.4_

  - [ ] 16.3 Implement the Kiro adapter and one of Claude/Codex adapter
    - Concrete `KiroAdapter` (provider-specific CLI/ACP/headless, never AO itself) and one of `ClaudeAdapter`/`CodexAdapter`; emit a Run-start Event (provider identity, adapter version, worktree ref, Context Hash); pass Secret References only, never raw secrets; keep executables/flags/endpoints/auth/model selection as `# NEEDS-OWNER:` config
    - _Requirements: 5.6, 6.3, 6.4, 6.5, 16.3, 5.8, 6.8_

  - [ ] 16.4 Register Agy and OpenCode as contract-only stubs
    - `AgyAdapter`/`OpenCodeAdapter` registered in the registry but raising `NotImplementedError` with a `# NEEDS-OWNER:` marker
    - _Requirements: 5.7, 16.3, 16.7_

  - [ ]* 16.5 Write property test for adapter selection compatibility
    - **Property 8: Adapter selection matches full compatibility, else typed error with Task unstarted**
    - **Validates: Requirements 5.3, 5.4, 16.4**

- [ ] 17. Event streaming, sequencing, and structured results
  - [ ] 17.1 Implement event emission, sequencing, and persistence in `app/services/runs/events.py`
    - Emit Events for lifecycle changes, worker output, command execution, validation checks, findings, heartbeats, cancellation, failures; assign a monotonic, unique, contiguous per-Run sequence number; persist Run id, sequence, type, timestamp, source, redacted payload, correlation id; at-least-once delivery with sequence-based dedup
    - _Requirements: 7.1, 7.2, 7.8_

  - [ ] 17.2 Implement structured result collection and validation in `app/services/runs/result.py`
    - Collect `StructuredRunResult` (status, changed files with path/change-kind/diff-or-commit-ref, test results, findings, artifacts, failure info); classify malformed/incomplete/schema-incompatible output as adapter/result-validation failure (`ResultValidationError`/`AdapterFailure`) that can never produce a successful outcome; retain free-form output only as bounded, redacted diagnostics
    - _Requirements: 7.3, 7.4, 7.5, 7.6, 6.6_

  - [ ] 17.3 Implement event replay on reconnect
    - Replay retained Events with sequence > requested s, or report the earliest retained sequence when earlier Events are unavailable
    - _Requirements: 7.7, 14.4_

  - [ ]* 17.4 Write property test for event sequence integrity
    - **Property 9: Event sequence numbers are strictly increasing, unique, and contiguous per Run**
    - **Validates: Requirements 7.1**

  - [ ]* 17.5 Write property test for invalid-result classification
    - **Property 10: Invalid structured results never produce a successful outcome**
    - **Validates: Requirements 7.5**

  - [ ]* 17.6 Write property test for event replay suffix/earliest-retained
    - **Property 11: Event replay returns the correct suffix or reports earliest retained**
    - **Validates: Requirements 7.7, 14.4**

- [ ] 18. Scheduler loop and Redis claim exclusivity
  - [ ] 18.1 Implement the scheduler in `app/workflows/scheduler.py`
    - Maintain the per-Job Task Graph and readiness; claim a ready Task via a leased Redis lock so exactly one claim wins, the loser is rejected (`ClaimRejected`), and both winning and rejected claim attempts are recorded; enforce at most one running Task per Job (MVP) while retaining the full graph model
    - _Requirements: 3.8, 15.2, 15.4_

  - [ ]* 18.2 Write property test for single-winner claim
    - **Property 23: Exactly one scheduler claim wins for a ready Task**
    - **Validates: Requirements 15.4**

- [ ] 19. Atomic transition + audit and restart recovery
  - [ ] 19.1 Implement atomic transition+audit and reconciliation in `app/services/audit/service.py` and `app/workflows/recovery.py`
    - Commit each accepted state transition and its audit record in one PostgreSQL transaction; if atomicity cannot be guaranteed, mark the transition `uncertain` and block downstream protected actions until reconciliation; on startup, load queued/active records and reconcile active Runs within the recovery window before starting any duplicate Run
    - _Requirements: 15.3, 15.5_

  - [ ]* 19.2 Write property test for transition/audit atomicity
    - **Property 24: State transition and its audit record are atomic or marked uncertain**
    - **Validates: Requirements 15.5**

  - [ ]* 19.3 Write property test for restart recovery without duplicate Runs
    - **Property 25: Restart recovery reproduces active work without duplicate Runs**
    - **Validates: Requirements 15.3**

- [ ] 20. Checkpoint — execution/scheduling validated
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 21. Cancellation, retry, timeout, and failure handling
  - [ ] 21.1 Implement cancellation/retry/timeout in `app/services/runs/lifecycle.py`
    - Record cancellation-requested state/requester/time and instruct the Adapter to cancel; on ack/safe termination move Run+Task to `cancelled` preserving partial Events/Artifacts; escalate after grace period recording each step; on timeout record metadata, request cancellation, and prevent validation/merge; on retryable failure with budget create exactly one new Run (new id) retaining the prior, applying non-decreasing backoff; on exhausted budget assign a terminal failure and leave dependents blocked
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [ ]* 21.2 Write property test for retryable-failure new-Run creation
    - **Property 14: Retryable failure with remaining budget creates exactly one new Run**
    - **Validates: Requirements 9.5**

  - [ ]* 21.3 Write property test for exhausted-budget terminal failure
    - **Property 15: Exhausted retry budget yields a terminal failure and blocks dependents**
    - **Validates: Requirements 9.6**

  - [ ]* 21.4 Write example tests for cancellation and timeout flows
    - Cover `TimeoutExceeded` and the cancellation request→ack→cancelled path with escalation recording
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 22. Validation and independent review gates
  - [ ] 22.1 Implement validation gate execution in `app/services/validation/service.py`
    - Run every required gate (tests, lint, type-check, migration checks, repository status, independent review) before approval/merge eligibility; persist name, type, command/reviewer ref, exit status/decision, output artifact ref, gate version, start/end timestamps; a failed/unavailable/invalid-evidence gate moves the Task to `validation_failed`, preserves evidence, and prevents merge; apply elevated gates when changed files intersect sensitive path patterns and identify exactly the affected paths; independent review uses an identity distinct from the producing Worker; keep exact commands/environments/independence as `# NEEDS-OWNER:` config
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.9_

  - [ ]* 22.2 Write property test for gate-pass eligibility
    - **Property 16: A Task is eligible for approval/merge iff all required gates pass**
    - **Validates: Requirements 10.1, 10.4**

  - [ ]* 22.3 Write property test for sensitive-path elevated gates
    - **Property 17: Sensitive changed paths trigger elevated gates and exact path identification**
    - **Validates: Requirements 10.6**

- [ ] 23. Approval and protected-merge gates
  - [ ] 23.1 Implement approval gates in `app/services/approvals/service.py`
    - Create Approval Gates before protected-branch merge, production migration/deploy, and auth/authorization/security/secret-handling changes; pause destructive/out-of-policy-secret/unresolved-business-policy Tasks in `review_required` identifying the action and required approver role; persist approver identity, decision, timestamp, policy version, reason, and affected job/task/run/branch/commit refs; rejection/expiry prevents the action and moves the Task to the configured blocked/cancelled outcome; deny and record self-approval when the approver is the producing Worker; keep roles/expiry/two-person/protected-branch patterns/override as `# NEEDS-OWNER:` config
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

  - [ ]* 23.2 Write property test for rejected/expired approval prevention
    - **Property 18: Rejected or expired approval prevents the protected action**
    - **Validates: Requirements 11.6**

  - [ ]* 23.3 Write property test for self-approval denial
    - **Property 19: Self-approval is denied and recorded**
    - **Validates: Requirements 11.7**

- [ ] 24. Security policy enforcement (allowlists, egress, deny-by-default)
  - [ ] 24.1 Implement the per-Run policy engine in `app/core/policy.py`
    - Enforce command/path/environment-variable allowlists, network-egress policy, and resource limits with deny-by-default; permit an operation iff within the configured allowlists/egress, else deny (`PolicyViolationError`) and append a redacted security Event + audit record; apply separate permission scopes for control/SSH/worker/validation/artifact/approval; prevent workers from reaching AO data stores
    - _Requirements: 4.7, 13.1, 13.2, 13.3, 13.5, 13.9, 6.7_

  - [ ]* 24.2 Write property test for policy permit/deny with redacted evidence
    - **Property 21: Operations are permitted iff within Run policy, else denied with redacted evidence**
    - **Validates: Requirements 13.3, 13.9**

- [ ] 25. Artifact and audit persistence (reproducibility + append-only)
  - [ ] 25.1 Implement artifact store and audit persistence in `app/services/artifacts/service.py`
    - Persist per-Run reproducibility record (repository identity, remote host, base SHA, provider, adapter/worker version, instruction hash, Context Hash, worktree/branch, changed files, executed commands, test results, findings, approval identity, lifecycle timestamps); store artifact metadata (schema version, checksum, content ref, producer identity, retention classification, redaction status) in PostgreSQL with content in the approved object/FS store by checksum; redact/quarantine secret/PII artifacts before ordinary operator access; make audit records append-only for ordinary operators with correction/deletion only via an authorized retention operation; build a Run summary reconstructing revision/Context Hash/provider+worker version/validation evidence/approval decision
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

  - [ ]* 25.2 Write property test for append-only audit log
    - **Property 20: Audit log is append-only for ordinary operators**
    - **Validates: Requirements 12.3, 12.4**

- [ ] 26. Routers and single exception handler
  - [ ] 26.1 Implement FastAPI routers in `app/routers/`
    - Routers for repos, jobs, tasks, runs, events (stream + reconnect-by-sequence), approvals, artifacts, and health; validate Pydantic input, call services, never touch DB/Redis directly; register a single exception handler mapping each `AOError` subclass to a machine-readable HTTP response; wire routers into the app factory
    - _Requirements: 16.1, 1.2, 7.7, 14.4_

  - [ ]* 26.2 Write router tests (happy path, auth/permission, validation/error)
    - Per `AGENTS.md` done-definition: at least one happy-path, one auth/permission, and one validation/error test per new endpoint group
    - _Requirements: 16.1, NFR-4.3_

- [ ] 27. Observability, health, and operator explanations
  - [ ] 27.1 Implement health, structured logging, and metrics in `app/core/observability.py`
    - Health endpoint reports AO control components, PostgreSQL, Redis, remote SSH connectivity, Git availability, registered Adapters, and Artifact storage within 5 seconds; structured logs carry correlation/job/task/run/provider/adapter/outcome and exclude secrets/PII; emit metrics with defined units (queued tasks, active runs, run duration, setup/adapter/validation failures, retries, cancellations, timeouts, approval/queue wait); classify lost worker/SSH/adapter connections recoverable vs failed from heartbeat/timeout/connection evidence; attach an operator-visible explanation to every non-advancing Task state
    - _Requirements: 14.1, 14.2, 14.3, 14.5, 14.6, NFR-1.3_

  - [ ]* 27.2 Write smoke tests for health and startup/configuration
    - Assert health responds within the budget and reports each component; assert the app starts with valid config
    - _Requirements: 14.1_

- [ ] 28. End-to-end wiring and MVP integration
  - [ ] 28.1 Wire the full happy-path flow through the app factory
    - Connect routers → services → scheduler → context packager → worktree manager → adapter registry → run lifecycle → events → validation gates → approval gate → merge of a verified commit, so submitting a Job runs a Task end to end with gates and audit; ensure no orphaned components remain
    - _Requirements: 16.1, 16.2, 16.6, 8.8_

  - [ ]* 28.2 Write the end-to-end integration/example test for the happy path
    - End-to-end job submission → run → gates → approval → merge using mocked SSH/Git/adapter boundaries with fake identities and redacted output
    - _Requirements: 16.1, 16.5_

  - [ ]* 28.3 Write integration tests confirming MVP exclusions and store isolation
    - Assert Kafka is absent, the source repo is not required locally, Workers cannot reach AO data stores, Secret References never resolve to raw values in captured output, and unsupported contract versions are rejected before execution
    - _Requirements: 16.6, 13.5, 13.4, NFR-3.2_

- [ ] 29. Final checkpoint — ensure all tests pass
  - Ensure all tests pass (`uv run pytest`) and `uv run ruff check . && uv run ruff format .` are clean; ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP; all test sub-tasks are optional per the workflow convention.
- Each correctness property (1–25) is implemented by exactly one property-based test (Hypothesis, `@settings(max_examples=100)` or higher), placed next to the implementation it validates and tagged `# Feature: agent-orchestrator-multi-agent, Property {n}: {text}`.
- Property-to-scenario coverage for Req 16.5: happy path (28.2), graph validation (9.2 / Property 4), state transitions (10.3 / Property 6, plus 11.2 / Property 7), Context Hash immutability (8.2, 13.2 / Properties 1, 2, plus 8.3 / Property 3), worktree isolation (15.2 / Property 12, plus 15.3 / Property 13), adapter failure (16.5, 17.5 / Properties 8, 10), cancellation/timeout (21.4), validation gate failure (22.2, 22.3 / Properties 16, 17), approval gate denial (23.2, 23.3 / Properties 18, 19), redaction (24.2, 3.2 / Properties 21, 22), restart recovery (19.3 / Property 25), duplicate claim handling (18.2, 19.2 / Properties 23, 24).
- `[NEEDS-OWNER]` items remain typed config or `NotImplementedError` stubs with `# NEEDS-OWNER:` markers (Agy/OpenCode adapters, provider auth/commands, prod SSH topology, approval roles, validation commands, retention, cost limits) and are never invented.
- Checkpoints (12, 20, 29) ensure incremental validation; the legacy `orchestrator.py` local CLI dispatcher is unrelated to this control-plane service.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "2.2", "3.1"] },
    { "id": 1, "tasks": ["2.3", "3.2", "5.1", "8.1"] },
    { "id": 2, "tasks": ["5.2", "6", "8.2", "8.3"] },
    { "id": 3, "tasks": ["5.3", "7", "9.1", "10.1", "14.1"] },
    { "id": 4, "tasks": ["9.2", "10.2", "10.3", "11.1", "13.1", "14.2", "15.1"] },
    { "id": 5, "tasks": ["11.2", "13.2", "15.2", "15.3", "16.1", "24.1"] },
    { "id": 6, "tasks": ["16.2", "16.3", "16.4", "17.1", "24.2"] },
    { "id": 7, "tasks": ["16.5", "17.2", "17.3", "18.1"] },
    { "id": 8, "tasks": ["17.4", "17.5", "17.6", "18.2", "19.1"] },
    { "id": 9, "tasks": ["19.2", "19.3", "21.1", "22.1", "23.1", "25.1"] },
    { "id": 10, "tasks": ["21.2", "21.3", "21.4", "22.2", "22.3", "23.2", "23.3", "25.2", "27.1"] },
    { "id": 11, "tasks": ["26.1", "27.2"] },
    { "id": 12, "tasks": ["26.2", "28.1"] },
    { "id": 13, "tasks": ["28.2", "28.3"] }
  ]
}
```
``