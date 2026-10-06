# Agentic Software Engineering System — URL Shortener

A self-contained prototype for the interview assignment: **transform a software requirement into a reviewable engineering outcome using controlled agentic execution**.

The project intentionally demonstrates more than a prompt chain. It implements a **stateful dependency graph (DAG)** with sequential and parallel execution, synchronization, human approval, policy guardrails, bounded retries, safe-stop, rollback, audit events, metrics and dynamic re-planning.

## 1. What is included

### Working URL shortener
- `POST /api/v1/shorten` — create a short URL
- `GET /{code}` — redirect and increment click count
- `GET /api/v1/analytics/{code}` — click analytics
- URL scheme validation (`http` / `https`)
- custom aliases with collision protection
- expiry support
- SQLite persistence for a zero-dependency local demo

### Agentic SDLC orchestrator
Agents are represented as bounded, testable execution units:

- Requirements Agent
- Architecture Agent
- Brownfield Analysis Agent
- Implementation Agent
- Test Agent
- Security Agent
- Documentation Agent
- Release Agent

The orchestrator provides:

| Assignment requirement | Implementation |
|---|---|
| Requirement understanding | Requirements agent + normalized acceptance criteria |
| Task decomposition | Explicit DAG nodes + dependency sets |
| Brownfield reasoning | Dedicated brownfield-analysis node |
| Sequential + parallel execution | ThreadPoolExecutor for independent nodes |
| Synchronization | Release waits for tests + security + docs |
| Cross-stage context | Versioned shared run context |
| Human checkpoints | Approval endpoint for high-impact stages |
| Policy guardrails | Forbidden-action checks + release security gate |
| Bounded retries | Per-node retry limit |
| Safe stop | Policy rejection / human rejection |
| Rollback | Explicit rollback operation + audit event |
| Auditability | Persistent SQLite audit events |
| Reliability metrics | success rate, retries, rollback count, latency, MTTR proxy |
| Dynamic re-plan | `/replan` invalidates affected downstream nodes |

## 2. Architecture

See [`docs/architecture.md`](docs/architecture.md).

The core principle is:

> **Agents execute inside predefined autonomy boundaries; humans own high-impact approval and final quality control.**

## 3. Run locally

Requirements: Python 3.12+

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open Swagger at `http://localhost:8000/docs`.

### Docker

```bash
docker compose up --build
```

## 4. Try the URL shortener

```bash
curl -X POST http://localhost:8000/api/v1/shorten \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com/products/123"}'
```

Then call the returned `short_url`. Finally:

```bash
curl http://localhost:8000/api/v1/analytics/<code>
```

## 5. Try the agentic workflow

### Greenfield

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs \
  -H 'content-type: application/json' \
  -d '{"scenario":"greenfield","requirement":"Build a URL shortener with click analytics","auto_approve_low_risk":true}'
```

The response contains the full graph state, node outputs, context version and reliability metrics.

### Brownfield

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs \
  -H 'content-type: application/json' \
  -d '{"scenario":"brownfield","requirement":"Add analytics to an existing shortener without breaking redirects","auto_approve_low_risk":true}'
```

The graph inserts `brownfield_analysis` before implementation.

### Ambiguous requirement + human gate

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs \
  -H 'content-type: application/json' \
  -d '{"scenario":"ambiguous","requirement":"Build a shortener with analytics; retention is unclear","auto_approve_low_risk":false}'
```

The run pauses at an approval checkpoint. Resume it with:

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs/<run_id>/approve \
  -H 'content-type: application/json' \
  -d '{"approved":true,"comment":"Reviewed ambiguity and approved bounded implementation"}'
```

### Dynamic re-planning

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs/<run_id>/replan \
  -H 'content-type: application/json' \
  -d '{"scenario":"greenfield","requirement":"Also support expiry and document analytics retention","auto_approve_low_risk":true}'
```

The context version changes and affected downstream nodes are re-executed.

### Audit trail

```bash
curl http://localhost:8000/api/v1/agent/runs/<run_id>/audit
```

### Rollback / safe change control

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs/<run_id>/rollback
```

## 6. Testing

```bash
pytest -q
```

Tests cover:
- create → redirect → analytics flow
- duplicate custom alias
- invalid scheme
- expiry validation
- greenfield DAG completion
- brownfield dependency behavior
- ambiguous requirement approval gate
- dynamic re-planning/context versioning

CI is included under `.github/workflows/ci.yml`.

## 7. Three assignment scenarios

- [`scenarios/greenfield.md`](scenarios/greenfield.md)
- [`scenarios/brownfield.md`](scenarios/brownfield.md)
- [`scenarios/ambiguous.md`](scenarios/ambiguous.md)

## 8. Key engineering decisions

### SQLite for the prototype
SQLite makes the assignment reproducible with one command. Production would use PostgreSQL with unique constraints, connection pooling and migrations.

### DAG + state machine
A simple list of prompts cannot model fan-out, synchronization, pause/resume, retries or re-planning safely. The explicit graph makes dependencies reviewable and execution deterministic.

### Deterministic agents
The prototype does not require an LLM key. In a real system, each agent would be an adapter around an LLM/tool runtime, but the orchestrator—not the model—would own state transitions, policy and approvals.

### Human-in-the-loop
High-impact implementation/release operations can pause for approval. A model never gets unrestricted production authority.

## 9. Production hardening roadmap

1. Replace in-memory run state with PostgreSQL/Redis or a durable workflow engine.
2. Use Temporal/Camunda/Step Functions for durable execution if workflow scale warrants it.
3. Add OpenTelemetry traces, Prometheus metrics and centralized logs.
4. Add OAuth2/RBAC and signed approval records.
5. Store secrets in a cloud secret manager; never expose them to agents.
6. Add SAST, dependency scanning, SBOM and container image scanning.
7. Add a real artifact workspace / Git branch / pull-request adapter with protected branches.
8. Add contract tests and load tests for the URL API.
9. Add idempotency keys for create operations.
10. Replace the MTTR proxy with incident/recovery timestamps from production telemetry.

## 10. Limitations and trade-offs

- Agent implementations are deterministic stubs rather than external LLM calls.
- Run state is in memory; audit events are durable in SQLite.
- Rollback demonstrates governance semantics but does not deploy a real previous artifact.
- Metrics are prototype-level and should be connected to operational telemetry in production.
- Parallel execution uses a local thread pool; production should use durable workers.
