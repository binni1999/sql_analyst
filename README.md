# DataPilot — Multi-Agent SQL Data Analyst

DataPilot is a Python-based, natural-language interface for analytical queries over a PostgreSQL database. It uses LLM-powered agents, validation and security controls, and workflow orchestration to translate business questions into SQL, execute approved queries, analyze the results, and generate human-readable answers.

This repository is configured for **local, single-user development and demonstration**. It is suitable for experimenting with agent workflows and demonstrating engineering practices; it is not a fully production-hardened, multi-user service.

## Features

- Natural-language questions against structured business data.
- Multi-agent analytical workflow orchestrated with LangGraph.
- SQL generation, syntax validation, semantic validation, and repair.
- Schema metadata retrieval and Redis-backed caching.
- SQL execution through a controlled database execution boundary.
- SQL security guardrails, query-plan cost checks, row limits, and statement timeouts.
- Human-in-the-loop approval for queries that require approval.
- Conversation state and PostgreSQL-backed LangGraph checkpoints.
- Business-knowledge retrieval to support analytical responses.
- Structured logging, request IDs, health endpoints, and application metrics.
- Automated tests for agents, validation, security, workflow behavior, and provider failures.
- Local Docker Compose deployment using PostgreSQL, Redis, and the FastAPI backend.

## Technology stack

| Area | Technologies |
|---|---|
| Language | Python 3.11 |
| API | FastAPI, Uvicorn |
| Agent orchestration | LangGraph, LangChain |
| LLM integrations | Groq and OpenAI integrations |
| Database | PostgreSQL 16, SQLAlchemy, psycopg |
| SQL parsing and validation | SQLGlot and application-specific validators |
| Caching | Redis 7 |
| Data processing | Pandas, NumPy |
| Testing | Pytest |
| Deployment | Docker, Docker Compose |

The environment template contains additional optional provider and tracing settings. An integration being configurable does not necessarily mean it is enabled in the default workflow.

## Architecture

```text
Client
  |
  v
FastAPI API (/api/ask)
  |
  v
Data Analyst Service
  |
  v
LangGraph Workflow
  |
  +--> Intent and clarification handling
  |
  +--> Metadata and business-knowledge retrieval
  |
  +--> Analytical context and conversation memory
  |
  +--> SQL generation
  |      |
  |      v
  |    SQL syntax, semantic and security validation
  |      |
  |      v
  |    Query-plan cost checks and approval handling
  |      |
  |      v
  |    Controlled SQL execution
  |
  +--> Result analysis
  |
  +--> Answer generation
  |
  v
Structured response with SQL, results, answer and trace

Supporting services:
  PostgreSQL --> Business data and workflow checkpoints
  Redis      --> Metadata caching
```

The workflow may request clarification or human approval rather than immediately returning a final analytical answer.

## Prerequisites

Install the following tools:

- Docker Desktop with Docker Compose.
- Git, if you are cloning the repository.
- Python 3.11 for running the backend tests locally.
- A valid API key for the LLM provider used by your configured workflow.

You do not need a paid cloud-hosting account to run the Docker Compose setup locally. LLM API usage may still incur provider charges or be subject to rate limits.

## Local setup with Docker Compose

Run the following commands from the repository root.

### 1. Configure environment variables

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` locally using your preferred editor. Configure the database credentials, connection settings, and LLM provider key required by your environment.

The Compose configuration also requires these variables:

- `READONLY_DB_USER`
- `READONLY_DB_PASSWORD`

Add them to `.env` if they are not already present. Use a dedicated, restricted database role for generated analytical SQL.

Configure `DATABASE_URL`, `READONLY_DATABASE_URL`, and `LANGGRAPH_CHECKPOINT_DB_URL` consistently with your local setup. Docker Compose overrides the database and Redis service URLs for the backend container.

**Never commit `.env` or publish its contents.** Keep credentials and API keys out of screenshots, logs, issue reports, and source code.

### 2. Validate the Compose configuration

```powershell
docker compose config --quiet
```

If the command exits successfully, the Compose configuration is valid.

### 3. Build and start the services

```powershell
docker compose up --build -d
```

The stack contains:

| Service | Purpose | Host binding |
|---|---|---|
| `backend` | FastAPI application | `127.0.0.1:8000` |
| `postgres` | Analytical data and checkpoints | `127.0.0.1:5433` |
| `redis` | Metadata cache | Not published to the host |

The database and Redis use named Docker volumes so their data can persist across ordinary container recreation.

### 4. Verify service status

```powershell
docker compose ps
```

Check the backend readiness endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

A ready response should report PostgreSQL as healthy. Redis is an optional cache optimization, so the application can fall back to PostgreSQL if Redis is unavailable.

Inspect backend logs if necessary:

```powershell
docker compose logs --tail 100 backend
```

Follow logs continuously:

```powershell
docker compose logs -f backend
```

Press `Ctrl+C` to stop following the logs.

### 5. Open the API documentation

With the backend running, open:

- Swagger UI: http://127.0.0.1:8000/docs
- Root endpoint: http://127.0.0.1:8000/
- Readiness: http://127.0.0.1:8000/health/ready
- Liveness: http://127.0.0.1:8000/health/live
- Metrics: http://127.0.0.1:8000/metrics

## API usage

### Endpoint

`POST /api/ask`

The `question` field is required and must contain between 3 and 1,000 characters.

| Field | Type | Description |
|---|---|---|
| `question` | String | Natural-language analytical question |
| `conversation_id` | String or null | Identifies conversation state across requests |
| `human_approval` | Boolean or null | Approval decision for a query awaiting human approval |

### Example: ask a question

Run this PowerShell example:

```powershell
$body = @{
    question = "How many customers are in the database?"
    conversation_id = "readme-demo"
    human_approval = $false
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/ask" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

$response | ConvertTo-Json -Depth 10
```

Depending on the risk assessment, the response may contain a generated SQL statement and request human approval before execution.

### Example: approve a pending request

If the workflow indicates that approval is required, send the approval decision using the same conversation identifier:

```powershell
$approvalBody = @{
    question = "Approve"
    conversation_id = "readme-demo"
    human_approval = $true
} | ConvertTo-Json

$approvalResponse = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/ask" `
    -Method Post `
    -ContentType "application/json" `
    -Body $approvalBody

$approvalResponse | ConvertTo-Json -Depth 10
```

This illustrates the current approval interaction. Submit an approval response only when the application has actually requested approval for that conversation.

### Response fields

The response model can include:

- `success` — whether processing succeeded.
- `question` — the submitted question.
- `conversation_id` — conversation identifier.
- `answer` — natural-language answer.
- `sql` — generated SQL, when available.
- `result` — analytical result payload, when available.
- `error` — error details, when applicable.
- `needs_clarification` and `clarification_question` — clarification state.
- `needs_human_approval` and `human_approval_question` — approval state.
- `execution_trace` and `execution_summary` — workflow execution information.

Fields may be absent or null depending on the workflow outcome.

## Security and reliability controls

The implementation includes several layers intended to reduce the risk of unsafe analytical queries:

1. **Restricted table policy:** the configured SQL security policy limits access to the supported business tables.
2. **SQL guardrails:** SQL is checked before execution, including restrictions against unsafe query operations.
3. **Validation:** SQL syntax, semantic requirements, and analytical intent are checked before execution.
4. **Query-plan cost checks:** `EXPLAIN` plan metrics are inspected against configured limits.
5. **Execution controls:** each secure query runs in a read-only transaction (`SET TRANSACTION READ ONLY`); statement timeouts and result row limits are also enforced.
6. **Restricted database role:** the analytical execution connection is intended to use a dedicated role with limited privileges.
7. **Human approval:** higher-risk operations can be paused for an approval decision.
8. **Input guardrails:** prompt-injection and question-validation checks are part of the application workflow.
9. **Error handling:** user-facing LLM errors are sanitized, including rate-limit failures.
10. **Observability:** request IDs, structured logs, health checks, and metrics support diagnosis.

These controls reduce risk but do not guarantee that every possible malicious or expensive query will be prevented. Database permissions remain an important independent security boundary.

### Important deployment limitations

This repository's current configuration is intended for local, single-user use:

- The API does **not** provide authentication or user-level authorization.
- Do not expose the API publicly or deploy it as a multi-user service in its current form.
- The human-approval field is an application workflow mechanism, not a substitute for authenticated user identity or authorization.
- Secrets must be managed using an appropriate secret-management mechanism for any production deployment.
- Production use would require additional work, including authentication, authorization, stronger tenant isolation, operational monitoring, and deployment-specific security review.

## Running tests

Use Python 3.11 and activate your project virtual environment.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q --ignore=test_output.txt
```

The `--ignore=test_output.txt` option is intentional: this repository contains a captured test-output file that is not a normal Python test module.

Run a focused test file when debugging:

```powershell
python -m pytest .\app\tests\test_llm_errors.py -q
```

The test suite covers multiple areas, including SQL generation and validation, context handling, security controls, workflow behavior, and provider resilience. Test results should be rerun against the current working tree before claiming that all tests pass.

## Useful Docker commands

Check service status:

```powershell
docker compose ps
```

View backend logs:

```powershell
docker compose logs --tail 100 backend
```

Restart the backend:

```powershell
docker compose restart backend
```

Rebuild and recreate the backend after source or image changes:

```powershell
docker compose up --build -d --no-deps --force-recreate backend
```

Stop the services without deleting named volumes:

```powershell
docker compose down
```

**Do not add `-v` to the shutdown command unless you intentionally want to delete the Compose-managed data volumes.** Keep independent backups before performing database maintenance or recovery operations.

## Suggested next steps for production readiness

1. Add authentication and enforce authorization for every request.
2. Introduce user and tenant isolation before supporting multiple users.
3. Add API-level rate limiting and request quotas.
4. Expand adversarial SQL and prompt-injection testing.
5. Add database backup and restore procedures with recovery testing.
6. Add integration tests against a disposable database and Redis instance.
7. Establish CI checks for linting, type checking, automated tests, and dependency vulnerabilities.
8. Add deployment-specific secret management, monitoring, and alerting.
9. Measure latency, LLM cost, query-plan behavior, and failure rates using representative workloads.

## Project status

DataPilot is a local implementation of a multi-agent analytical workflow. The README documents the current architecture and safeguards, while the production-readiness items above remain additional engineering work rather than claims that those capabilities have already been delivered.
