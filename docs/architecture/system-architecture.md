# Driver Management Platform Architecture

Editable diagram: [driver-management-architecture.drawio](driver-management-architecture.drawio).

This is the **target architecture**. The repository currently contains a directory scaffold; the services and integrations shown in the diagram have not yet been implemented.

| Layer | Components | Responsibility |
| --- | --- | --- |
| Sources | React Web (Admin), React Native (Driver) | Provide admin and driver workflows over HTTPS/REST. |
| Ingestion and operations | FastAPI, PostgreSQL | Authenticate users, handle the Driver, Leave, Attendance, and Payroll domains, and store operational data. |
| Event ingestion | Outbox Publisher, Kafka | Publish business events after the corresponding database transaction commits. |
| Processing | Event Consumer, Spark/PySpark | Persist raw events and produce analytics data. |
| Data lake | MinIO Bronze / Silver / Gold | Store raw events, cleaned data, and aggregated metrics. |
| Analytics | Trino, Superset | Query Gold data through SQL and display dashboards. |

## Sources → Ingestion flow

1. An admin or driver sends an HTTPS/REST request to FastAPI.
2. FastAPI checks authorization and business rules, then writes the operational data and an outbox record in **the same PostgreSQL transaction**.
3. The Outbox Publisher reads pending records and publishes events to Kafka. After Kafka acknowledges an event, the publisher marks it as sent. Consumers must handle duplicate delivery using `event_id` and idempotent processing.
4. The Event Consumer reads Kafka events and stores the originals in MinIO Bronze. Spark/PySpark reads the Kafka stream to produce Silver data, then derives Gold data from Silver. Bronze can be used to reprocess the pipeline when needed.
5. Trino provides SQL access to Gold data for Superset reports.

Initial topics can follow the business domains: `driver.events.v1`, `leave.events.v1`, `attendance.events.v1`, and `payroll.events.v1`. Each event should include `event_id`, `event_type`, `event_version`, `occurred_at`, `aggregate_id`, and a versioned payload. Events should contain only the data consumers need; they must not include tokens, passwords, or unnecessary personal information.

## Implementation boundaries

- `apps/web`, `apps/mobile`: client applications.
- `services/api`: FastAPI, business domains, and outbox writes.
- `services/event-consumer`: the Outbox Publisher and Event Consumer, which can run as separate processes when implemented.
- `services/data-processing`: Spark/PySpark jobs.
- `data/schemas`: event contracts; `data/pipelines`: Bronze, Silver, and Gold pipeline definitions.
- `infra/`: PostgreSQL, Kafka, MinIO, Trino, and Superset.

Trino is included so Superset can query Gold data in MinIO through SQL. The Gold table format and Trino catalog configuration must be decided when the pipeline is implemented.
