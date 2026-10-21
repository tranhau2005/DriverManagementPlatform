# Implementation Plan: Driver Management Dashboard

## Overview

This plan builds the Driver Management Dashboard incrementally, from the inside out. It starts with the project scaffold and the typed domain foundation (value types and the discriminated error/result model), then implements the pure domain layer one service area at a time, validating each with property-based tests (fast-check + Vitest) that cover the 37 correctness properties. Only after the domain logic is proven does the plan add repositories, service orchestration, the Fastify transport layer, and finally the React + Vite frontend, wiring each layer onto the one below so no code is left orphaned.

Implementation language: **TypeScript (Node.js 20+)**, as specified in the design.

## Tasks

- [ ] 1. Set up project structure, tooling, and shared types
  - [ ] 1.1 Scaffold the TypeScript monorepo and tooling
    - Create workspace layout: `backend/` (Fastify API) and `frontend/` (React + Vite), each with its own `package.json` and `tsconfig.json`
    - Add and configure Vitest and fast-check in the backend package, with a test script that runs a single pass (no watch mode)
    - Add shared `domain/` directory under `backend/src` for the pure layer, plus `services/`, `repositories/`, and `transport/` directories as empty placeholders
    - Configure linting/formatting and a `build`/`typecheck` script
    - _Requirements: 1.1, 3.1_

  - [ ] 1.2 Define core domain value types
    - Create `backend/src/domain/types.ts` with `DriverStatus`, `Availability`, `VerificationState`, `DocumentType`, `Role`, and the entity interfaces `Administrator`, `LockoutState`, `Session`, `Driver`, `Document`, `Vehicle` exactly as defined in the design Data Models section
    - _Requirements: 1.1, 2.3, 5.1, 6.1, 8.1, 10.1, 11.1_

  - [ ] 1.3 Define the typed Result and discriminated error model
    - Create `backend/src/domain/result.ts` with the `Result<T, E>` type (`{ ok: true, value }` / `{ ok: false, error }`) and helpers
    - Create `backend/src/domain/errors.ts` with the discriminated error union: `ValidationError` (per-field detail), `AuthenticationError`, `AccountLockedError`, `SessionInvalidError`, `AuthorizationError`, `NotFoundError`, `DuplicateEmailError`, `StatusTransitionError`, `AvailabilityError`, `UploadRejectedError`, `AssignmentConflictError`, `DependencyError`
    - _Requirements: 1.2, 2.5, 5.3, 6.2, 9.2, 10.4, 11.2_

- [ ] 2. Implement Admin_Service domain layer (authentication, lockout, session, authorization)
  - [ ] 2.1 Implement credential-format and login-decision pure functions
    - Create `backend/src/domain/admin/credentials.ts` with `validateCredentialFormat(email, password)` enforcing email 1–254 chars and password 8–128 chars
    - Implement `evaluateLogin(account, submittedPassword, now, lockoutState)` returning `Success` | `InvalidCredentials` | `AccountLocked`, with a uniform invalid-credentials error that does not disclose which field was wrong
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [ ]* 2.2 Write property test for credential-format rejection
    - **Property 4: Credential-format rejection leaves the counter untouched**
    - **Validates: Requirements 1.3**

  - [ ]* 2.3 Write property test for indistinguishable invalid-credential errors
    - **Property 3: Invalid-credential errors are indistinguishable**
    - **Validates: Requirements 1.2**

  - [ ]* 2.4 Write property test for active-lockout rejection
    - **Property 6: An active lockout rejects every login**
    - **Validates: Requirements 1.5**

  - [ ] 2.5 Implement the lockout state machine
    - Create `backend/src/domain/admin/lockout.ts` with `nextLockoutState(current, outcome, now)`: reset to zero on `Success`, increment by one on `InvalidCredentials`, open a 15-minute lockout on the 5th consecutive failure within a 15-minute window
    - _Requirements: 1.1, 1.2, 1.4_

  - [ ]* 2.6 Write property test for counter reset on success
    - **Property 1: Successful login resets the failed-attempt counter**
    - **Validates: Requirements 1.1**

  - [ ]* 2.7 Write property test for single-increment on failure
    - **Property 2: Each invalid-credential attempt increments the counter by exactly one**
    - **Validates: Requirements 1.2**

  - [ ]* 2.8 Write property test for lockout opening after five failures
    - **Property 5: Five failures within the window open a 15-minute lockout**
    - **Validates: Requirements 1.4**

  - [ ] 2.9 Implement session-expiry and authorization pure functions
    - Create `backend/src/domain/admin/session.ts` with `isSessionExpired(session, now)` true iff inactivity since `lastActivityAt` exceeds 30 minutes
    - Create `backend/src/domain/admin/authorization.ts` with `isActionAllowed(role, action)`: Viewer may `read`; Manager may `read | create | update | status-change`; unknown/undefined roles may do nothing
    - _Requirements: 1.6, 2.2, 2.3, 2.4, 2.6_

  - [ ]* 2.10 Write property test for session-expiry boundary
    - **Property 7: Session expiry tracks the 30-minute inactivity boundary**
    - **Validates: Requirements 1.6, 2.2**

  - [ ]* 2.11 Write property test for exact role permissions
    - **Property 8: Role permissions are exactly defined**
    - **Validates: Requirements 2.3, 2.4, 2.6**

- [ ] 3. Checkpoint - Ensure all Admin_Service domain tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement Driver_Service domain layer (validation, pagination, transitions, detail view)
  - [ ] 4.1 Implement driver input validation and duplicate-email detection
    - Create `backend/src/domain/driver/validation.ts` with `validateDriverInput(input, mode)` enforcing name 1–100, email 1–254 with format `local-part@domain`, phone 7–15 digits on create / 7–20 chars on edit, license 1–50, returning per-field errors
    - Implement `isDuplicateEmail(email, existing, excludeId?)` using case-insensitive comparison and excluding the record being edited
    - Implement `newDriverDefaults()` returning `{ status: Inactive, availability: Unavailable }`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.4_

  - [ ]* 4.2 Write property test for new-driver defaults
    - **Property 15: New drivers start Inactive and Unavailable**
    - **Validates: Requirements 6.1**

  - [ ]* 4.3 Write property test for missing-required-field reporting
    - **Property 16: Missing required fields are reported exactly**
    - **Validates: Requirements 6.2**

  - [ ]* 4.4 Write property test for case-insensitive duplicate-email detection
    - **Property 17: Duplicate emails are detected case-insensitively**
    - **Validates: Requirements 6.3**

  - [ ]* 4.5 Write property test for email-format validation
    - **Property 18: Email format validation accepts well-formed and rejects malformed addresses**
    - **Validates: Requirements 6.4**

  - [ ]* 4.6 Write property test for phone and license boundaries
    - **Property 19: Phone and license boundaries are enforced per field**
    - **Validates: Requirements 6.5**

  - [ ]* 4.7 Write property test for valid-edit round-trip
    - **Property 20: Valid edits round-trip through storage**
    - **Validates: Requirements 7.1**

  - [ ]* 4.8 Write property test for editing to another record's email
    - **Property 21: Editing to another record's email is rejected and leaves the record unchanged**
    - **Validates: Requirements 7.2**

  - [ ]* 4.9 Write property test for invalid edit fields
    - **Property 22: Invalid edit fields are rejected and leave the record unchanged**
    - **Validates: Requirements 7.4**

  - [ ] 4.10 Implement status and availability transition functions
    - Create `backend/src/domain/driver/transitions.ts` with `applyStatusChange(driver, target, now)`: target ∈ {Active, Inactive, Suspended}; Active requires at least one Verified driving-license Document; Inactive and Suspended force Availability to Unavailable
    - Implement `applyAvailabilityChange(driver, target, adminId, now)`: target ∈ {Available, Unavailable}; Available only when status is Active; on success record acting administrator id and change timestamp
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.5_

  - [ ]* 4.11 Write property test for activation requiring a Verified license
    - **Property 23: Activation succeeds exactly when a Verified license exists**
    - **Validates: Requirements 8.1, 8.4**

  - [ ]* 4.12 Write property test for Inactive/Suspended forcing Unavailable
    - **Property 24: Inactive and Suspended force Unavailable**
    - **Validates: Requirements 8.2, 8.3**

  - [ ]* 4.13 Write property test for invalid status values
    - **Property 25: Invalid status values are rejected**
    - **Validates: Requirements 8.5**

  - [ ]* 4.14 Write property test for Active drivers accepting any availability value
    - **Property 26: Active drivers accept any valid availability value**
    - **Validates: Requirements 9.1**

  - [ ]* 4.15 Write property test for Available rejected on non-Active drivers
    - **Property 27: Available is rejected for non-Active drivers**
    - **Validates: Requirements 9.2**

  - [ ]* 4.16 Write property test for invalid availability values
    - **Property 28: Invalid availability values are rejected**
    - **Validates: Requirements 9.3**

  - [ ]* 4.17 Write property test for recording actor and timestamp on availability change
    - **Property 29: Successful availability changes record actor and timestamp**
    - **Validates: Requirements 9.5**

  - [ ] 4.18 Implement pagination and detail-view fill functions
    - Create `backend/src/domain/driver/pagination.ts` with `paginate(records, pageSize=25, requestedPage)`: order by name ascending, 25 per page, clamp out-of-range requests to page 1 with an `outOfRange` flag
    - Create `backend/src/domain/driver/view.ts` with `fillEmptyFields(driver)` representing every unset field as an explicit empty indicator rather than omitting it
    - _Requirements: 3.2, 3.3, 3.4, 5.2_

  - [ ]* 4.19 Write property test for pagination ordering and preservation
    - **Property 10: Pagination preserves, orders, and bounds all records**
    - **Validates: Requirements 3.2, 3.3**

  - [ ]* 4.20 Write property test for out-of-range page clamping
    - **Property 11: Out-of-range page requests clamp to the first page**
    - **Validates: Requirements 3.4**

  - [ ]* 4.21 Write property test for explicit empty-field detail view
    - **Property 14: Detail views expose every field with explicit empties**
    - **Validates: Requirements 5.2**

- [ ] 5. Checkpoint - Ensure all Driver_Service domain tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement Search_Service, Document_Service, and Assignment_Service domain layers
  - [ ] 6.1 Implement search validation and matching functions
    - Create `backend/src/domain/search/search.ts` with `validateSearchTerm(term)` enforcing 1–100 chars and `matchesCriteria(driver, criteria)`: case-insensitive substring match of term against name or identifier, exact match on status and availability filters, all supplied criteria combined by logical AND
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 6.2 Write property test for search-criteria matching
    - **Property 12: Search returns exactly the records matching every criterion**
    - **Validates: Requirements 4.1, 4.3, 4.4, 4.5**

  - [ ]* 6.3 Write property test for search-term length validation
    - **Property 13: Search-term length validation tracks the 1–100 boundary**
    - **Validates: Requirements 4.2**

  - [ ] 6.4 Implement document upload validation and verification transitions
    - Create `backend/src/domain/document/document.ts` with `validateUpload(fileSizeBytes, mimeType)` rejecting size > 10 MiB and formats other than PDF/JPEG/PNG
    - Implement `applyVerify(document, adminId, now)` setting state Verified from Pending or Rejected and recording verifier id + timestamp
    - Implement `applyReject(document, reason, adminId, now)` requiring reason 1–500 chars; on success set state Rejected and store reason, rejecter id, and timestamp; otherwise leave state unchanged
    - _Requirements: 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ]* 6.5 Write property test for verify recording reviewer and state
    - **Property 30: Verifying a document records the reviewer and sets Verified**
    - **Validates: Requirements 10.2**

  - [ ]* 6.6 Write property test for reject storing details with a valid reason
    - **Property 31: Rejecting with a valid reason stores the rejection details**
    - **Validates: Requirements 10.3**

  - [ ]* 6.7 Write property test for reject leaving state unchanged on invalid reason
    - **Property 32: Rejecting without a valid reason leaves state unchanged**
    - **Validates: Requirements 10.4**

  - [ ]* 6.8 Write property test for upload size validation
    - **Property 33: Upload size validation tracks the 10 MB boundary**
    - **Validates: Requirements 10.5**

  - [ ]* 6.9 Write property test for upload format validation
    - **Property 34: Upload format validation accepts only PDF, JPEG, and PNG**
    - **Validates: Requirements 10.6**

  - [ ] 6.10 Implement assignment and unassignment constraint functions
    - Create `backend/src/domain/assignment/assignment.ts` with `canAssign(driver, vehicle)` permitting a link only when driver status is Active, the vehicle has no current driver, and the driver has no current vehicle
    - Implement `canUnassign(driver)` permitting removal only when the driver currently has a vehicle link
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]* 6.11 Write property test for assignment preconditions
    - **Property 35: Assignment forms a link only when all preconditions hold**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4**

  - [ ]* 6.12 Write property test for assign-then-unassign round-trip
    - **Property 36: Assign then unassign returns to the unlinked state**
    - **Validates: Requirements 11.1, 11.5**

  - [ ]* 6.13 Write property test for removing a non-existent assignment
    - **Property 37: Removing a non-existent assignment is rejected**
    - **Validates: Requirements 11.6**

- [ ] 7. Checkpoint - Ensure all domain tests across all services pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement the persistence layer (Prisma schema and repositories)
  - [ ] 8.1 Define the Prisma schema and persistence constraints
    - Create `backend/prisma/schema.prisma` with models for Administrator, Driver, Document, Vehicle mapping the domain types
    - Add case-insensitive unique indexes on `administrator.email` and `driver.email`, a unique constraint on `vehicle.driverId`, and an index on `driver.name` for ordered pagination
    - Generate the Prisma client and add a migration script
    - _Requirements: 6.3, 7.2, 11.3, 11.4, 3.2_

  - [ ] 8.2 Implement the driver repository
    - Create `backend/src/repositories/driverRepository.ts` with load-by-id, list (ordered by name), create, update, and persist-transition methods over Prisma; map rows to/from domain `Driver`
    - _Requirements: 3.1, 5.1, 6.1, 7.1, 8.1, 9.1_

  - [ ]* 8.3 Write unit tests for the driver repository mapping
    - Test row-to-domain and domain-to-row mapping including null/unset fields
    - _Requirements: 5.2_

  - [ ] 8.4 Implement document, vehicle/assignment, and object-storage repositories
    - Create `backend/src/repositories/documentRepository.ts` (metadata in PostgreSQL) and an object-storage adapter for S3-compatible blob writes/reads
    - Create `backend/src/repositories/assignmentRepository.ts` performing the driver-vehicle link transactionally, relying on the unique `vehicle.driverId` constraint
    - _Requirements: 10.1, 11.1, 11.3, 11.5_

  - [ ] 8.5 Implement the Redis session and lockout repository
    - Create `backend/src/repositories/sessionRepository.ts` for session storage with a sliding 30-minute TTL and lockout-counter reads/writes
    - _Requirements: 1.1, 1.4, 1.6_

- [ ] 9. Implement service orchestration layers
  - [ ] 9.1 Implement Admin_Service orchestration
    - Create `backend/src/services/adminService.ts` wiring login (read account + lockout from Redis, apply `evaluateLogin` + `nextLockoutState`, write counter, create session on success), logout (delete session key), and session resolution using the session repository
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.7, 2.1_

  - [ ] 9.2 Implement Driver_Service orchestration
    - Create `backend/src/services/driverService.ts` wiring list, detail (via `fillEmptyFields`), create, edit (duplicate-email check), status change, and availability change; persist only on domain success; record actor + timestamp on availability changes
    - _Requirements: 3.1, 5.1, 5.3, 6.1, 7.1, 7.3, 8.1, 8.6, 9.1, 9.4, 9.5_

  - [ ]* 9.3 Write unit tests for Driver_Service not-found and invalid-identifier handling
    - Lookup/edit/status/availability on an unknown identifier returns a not-found error; empty/malformed identifier returns an invalid-identifier error; no stored record changes
    - _Requirements: 5.3, 5.4, 7.3, 8.6, 9.4_

  - [ ] 9.4 Implement Search_Service, Document_Service, and Assignment_Service orchestration
    - Create `backend/src/services/searchService.ts` (validate term, return records satisfying `matchesCriteria`, preserve prior result set on invalid term)
    - Create `backend/src/services/documentService.ts` (validate upload, store blob then metadata with state Pending and upload timestamp; verify/reject using domain transitions)
    - Create `backend/src/services/assignmentService.ts` (apply `canAssign`/`canUnassign`, persist link transactionally)
    - _Requirements: 4.1, 4.2, 10.1, 10.2, 10.3, 11.1, 11.5_

  - [ ]* 9.5 Write unit test for denied-mutation invariance across services
    - **Property 9: Denied mutations leave records unchanged**
    - **Validates: Requirements 2.5**

- [ ] 10. Checkpoint - Ensure repository and service tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement the Fastify transport layer
  - [ ] 11.1 Implement session + role middleware and error-to-HTTP mapping
    - Create `backend/src/transport/middleware.ts` applying `isSessionExpired` and `isActionAllowed` on protected routes, sliding the inactivity window on valid sessions, and denying/redirecting to login otherwise
    - Create `backend/src/transport/errorMapper.ts` mapping each domain error to its HTTP status per the design Error Handling table (400/401/403/404/409/413/415/423/502-503)
    - _Requirements: 1.6, 2.1, 2.2, 2.5, 2.6_

  - [ ]* 11.2 Write unit tests for error-to-HTTP mapping
    - Assert each domain error maps to its specified status code
    - _Requirements: 1.2, 6.3, 8.4, 9.2, 10.5, 10.6, 11.2_

  - [ ] 11.3 Implement auth and driver routes
    - Create `backend/src/transport/routes/auth.ts` (`POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/session`)
    - Create `backend/src/transport/routes/drivers.ts` (`GET /api/drivers`, `GET /api/drivers/:id`, `POST /api/drivers`, `PUT /api/drivers/:id`, `PATCH /api/drivers/:id/status`, `PATCH /api/drivers/:id/availability`)
    - _Requirements: 1.1, 1.7, 3.1, 5.1, 6.1, 7.1, 8.1, 9.1_

  - [ ] 11.4 Implement search, document, and assignment routes and register the app
    - Create `backend/src/transport/routes/search.ts` (`GET /api/drivers/search`), `documents.ts` (`POST /api/drivers/:id/documents` multipart, `PATCH /api/documents/:docId/verify`, `PATCH /api/documents/:docId/reject`), and `assignment.ts` (`POST /api/drivers/:id/assignment`, `DELETE /api/drivers/:id/assignment`)
    - Create `backend/src/app.ts` registering all routes, middleware, and the error mapper into the Fastify instance
    - _Requirements: 4.1, 10.1, 10.2, 10.3, 11.1, 11.5_

  - [ ]* 11.5 Write integration tests for session lifecycle and latency budgets
    - Logout invalidates the session; a request with no/expired session is denied and redirected to login; list/detail/search/status/availability/upload/assignment meet their latency budgets against seeded data
    - _Requirements: 1.7, 2.1, 2.2, 3.1, 5.1, 10.1, 11.1_

  - [ ]* 11.6 Write integration tests for document storage and assignment conflicts
    - Upload stores the blob, links it to the driver, timestamps it, and sets state Pending; end-to-end assignment/removal including the unique-vehicle constraint under concurrent assignment
    - _Requirements: 10.1, 11.1, 11.3, 11.5_

- [ ] 12. Checkpoint - Ensure the backend API passes all tests
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Implement the React + Vite frontend
  - [ ] 13.1 Set up the frontend app shell, API client, and auth flow
    - Create the Vite React app entry, a typed API client wrapping the backend endpoints, and login/logout screens that establish and clear the session cookie and redirect to login on 401
    - _Requirements: 1.1, 1.7, 2.1_

  - [ ] 13.2 Implement the driver list view with pagination and states
    - Build the list view rendering identifier, name, status, and availability; 25 per page ordered by name; page navigation; out-of-range handling showing page 1 with an error; empty-state message; and retained records with an error on retrieval failure
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 13.3 Implement search and filter controls
    - Build search input (1–100 chars) with status and availability filters that call the search endpoint, show a no-match message for empty results, and preserve the current result set with an error on invalid term length
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ] 13.4 Implement the driver detail, create, and edit views
    - Build the detail view showing full record with explicit empty indicators; create and edit forms with client-side field validation surfacing per-field and duplicate-email errors; role-based hiding/disabling of create/update/status actions for Viewers
    - _Requirements: 2.3, 2.4, 5.1, 5.2, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.4_

  - [ ] 13.5 Implement status, availability, document, and assignment controls
    - Build status/availability controls surfacing license-required and non-Active errors; document upload (size/format validation feedback) with verify/reject actions and rejection-reason input; assign/unassign controls surfacing conflict and no-assignment errors
    - _Requirements: 8.1, 8.4, 9.1, 9.2, 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]* 13.6 Write component tests for list, search, and form states
    - Test pagination, empty/no-match states, out-of-range handling, per-field validation display, and role-based control visibility
    - _Requirements: 3.2, 3.4, 3.5, 4.6, 6.2, 2.3_

- [ ] 14. Final checkpoint - Ensure all backend and frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test sub-tasks and can be skipped for a faster MVP; core implementation tasks are never optional.
- Each of the 37 correctness properties maps to exactly one property-based test sub-task, placed next to the domain code it validates so errors surface early.
- Property tests run under fast-check + Vitest with a minimum of 100 iterations each; unit tests cover concrete example/edge-case scenarios; integration tests cover wiring, side effects, and latency budgets.
- Each task references specific requirements (and properties where applicable) for traceability.
- Checkpoints provide incremental validation at natural layer boundaries.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["1.3"] },
    { "id": 3, "tasks": ["2.1", "2.5", "2.9", "4.1", "4.10", "4.18", "6.1", "6.4", "6.10"] },
    { "id": 4, "tasks": ["2.2", "2.3", "2.4", "2.6", "2.7", "2.8", "2.10", "2.11", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8", "4.9", "4.11", "4.12", "4.13", "4.14", "4.15", "4.16", "4.17", "4.19", "4.20", "4.21", "6.2", "6.3", "6.5", "6.6", "6.7", "6.8", "6.9", "6.11", "6.12", "6.13"] },
    { "id": 5, "tasks": ["8.1"] },
    { "id": 6, "tasks": ["8.2", "8.4", "8.5"] },
    { "id": 7, "tasks": ["8.3", "9.1", "9.2", "9.4"] },
    { "id": 8, "tasks": ["9.3", "9.5"] },
    { "id": 9, "tasks": ["11.1"] },
    { "id": 10, "tasks": ["11.2", "11.3", "11.4"] },
    { "id": 11, "tasks": ["11.5", "11.6"] },
    { "id": 12, "tasks": ["13.1"] },
    { "id": 13, "tasks": ["13.2", "13.3", "13.4", "13.5"] },
    { "id": 14, "tasks": ["13.6"] }
  ]
}
```
