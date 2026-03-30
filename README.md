# Big O Playground

Interactive algorithm analysis workspace with:

- `frontend/`: Next.js playground UI
- `backend/`: FastAPI analysis and execution API

## Local Development

```bash
make install
make dev
```

That starts:

- frontend on `http://localhost:3000`
- backend on `http://127.0.0.1:8000`

The frontend is wired to the backend in `make dev` by setting:

- `NEXT_PUBLIC_PLAYGROUND_API_MODE=backend`
- `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1`

## Frontend Modes

The frontend supports two modes:

- `backend`: call the real FastAPI API
- `mock`: use local dummy data for UI-only work

See [`frontend/.env.example`](frontend/.env.example).

## Ollama Cloud Explanations

The backend explanation endpoint supports an Ollama Cloud provider with heuristic fallback.

Relevant backend env vars:

- `EXPLANATION_PROVIDER=heuristic|ollama_cloud`
- `EXPLANATION_ALLOW_FALLBACK=true|false`
- `OLLAMA_API_KEY=...`
- `OLLAMA_MODEL=gpt-oss:120b`
- `OLLAMA_API_BASE_URL=https://ollama.com/api`

If Ollama Cloud is unavailable, the API falls back to the built-in deterministic explanation generator unless fallback is disabled.
