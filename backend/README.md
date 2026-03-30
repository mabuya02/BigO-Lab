# Big O Playground Backend

Stateless FastAPI backend for:

- code execution
- experiment runs
- metrics aggregation
- complexity estimation
- explanation generation
- comparisons
- preset loading
- share payload generation

## Quick Start

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Active API Surface

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /api/v1/playground/status`
- `POST /api/v1/playground/run`
- `POST /api/v1/playground/experiment`
- `POST /api/v1/explanations/generate`
- `POST /api/v1/comparisons/compare`
- `GET /api/v1/presets`
- `GET /api/v1/presets/{slug}`
- `POST /api/v1/shares`
- `POST /api/v1/shares/resolve`
- `POST /api/v1/execution/run`
- `POST /api/v1/execution/jobs`
- `GET /api/v1/execution/jobs/{job_id}`

## Ollama Cloud Provider

Explanation generation supports two modes:

- `EXPLANATION_PROVIDER=heuristic`
- `EXPLANATION_PROVIDER=ollama_cloud`

Relevant env vars:

- `EXPLANATION_ALLOW_FALLBACK=true`
- `OLLAMA_API_KEY=...`
- `OLLAMA_MODEL=gpt-oss:120b`
- `OLLAMA_API_BASE_URL=https://ollama.com/api`
- `OLLAMA_TIMEOUT_SECONDS=20`
- `OLLAMA_TEMPERATURE=0.2`

If Ollama Cloud fails and fallback is enabled, the backend returns the built-in heuristic explanation instead of failing the request.

## Docker Sandbox

Build the sandbox image before using Docker-backed execution:

```bash
docker build --target sandbox -t big-o-playground-python-sandbox:latest .
```
