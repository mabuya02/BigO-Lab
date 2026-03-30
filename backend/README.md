# Big O Playground Backend

Phase 1 backend foundation for Big O Playground.

## Included

- FastAPI application bootstrapping
- JWT auth with register/login/current-user endpoints
- SQLAlchemy models for `User`, `Project`, `CodeSnippet`, and `Experiment`
- PostgreSQL-ready settings with SQLite fallback for local development
- Redis connectivity scaffolding and health checks
- Alembic migration scaffold with an initial schema revision
- Phase 2 execution engine with Docker-first sandboxing, sync runs, and queued jobs

## Quick Start

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Sandbox Image

Build the execution sandbox image before using Docker-backed runs:

```bash
docker build -f docker/Dockerfile -t big-o-playground-python-sandbox:latest .
```

## Core Endpoints

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}/snippets`
- `POST /api/v1/projects/{project_id}/snippets`
- `GET /api/v1/projects/{project_id}/experiments`
- `POST /api/v1/projects/{project_id}/experiments`
- `GET /api/v1/execution/status`
- `POST /api/v1/execution/run`
- `POST /api/v1/execution/jobs`
- `GET /api/v1/execution/jobs/{job_id}`
