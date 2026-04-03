SHELL := /bin/bash

.PHONY: dev dev-backend dev-frontend install install-backend install-frontend lint lint-backend lint-frontend test test-backend test-frontend build build-frontend docker-build docker-up docker-down clean migrate migrate-up migrate-down migrate-history

# ── Development ──

dev:
	@set -m; \
	trap 'trap - INT TERM EXIT; \
		[ -n "$$backend_pid" ] && kill -- -$$backend_pid 2>/dev/null; \
		[ -n "$$frontend_pid" ] && kill -- -$$frontend_pid 2>/dev/null; \
		wait' INT TERM EXIT; \
	(cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000) & backend_pid=$$!; \
	(cd frontend && NEXT_PUBLIC_PLAYGROUND_API_MODE=backend NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 pnpm dev) & frontend_pid=$$!; \
	wait

dev-backend:
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && NEXT_PUBLIC_PLAYGROUND_API_MODE=backend NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 pnpm dev

# ── Install dependencies ──

install: install-backend install-frontend

install-backend:
	cd backend && source .venv/bin/activate && pip install -r requirements.txt

install-frontend:
	cd frontend && pnpm install

# ── Linting ──

lint: lint-backend lint-frontend

lint-backend:
	cd backend && source .venv/bin/activate && python3 -m compileall app tests

lint-frontend:
	cd frontend && pnpm lint

# ── Testing ──

test: test-backend test-frontend

test-backend:
	cd backend && source .venv/bin/activate && python3 -m unittest discover tests

test-frontend:
	cd frontend && pnpm test

# ── Build ──

build: build-frontend

build-frontend:
	cd frontend && pnpm build

# ── Migrations (Alembic) ──

migrate:  ## Auto-generate a migration from model changes (usage: make migrate m="add users table")
	cd backend && source .venv/bin/activate && alembic revision --autogenerate -m "$(m)"

migrate-up:  ## Apply all pending migrations
	cd backend && source .venv/bin/activate && alembic upgrade head

migrate-down:  ## Rollback the last migration
	cd backend && source .venv/bin/activate && alembic downgrade -1

migrate-history:  ## Show migration history
	cd backend && source .venv/bin/activate && alembic history --verbose

# ── Docker ──

docker-build:
	docker compose -f docker/docker-compose.yml build

docker-up:
	docker compose -f docker/docker-compose.yml up --build

docker-down:
	docker compose -f docker/docker-compose.yml down

# ── Cleanup ──

clean:
	find backend -type d -name __pycache__ -exec rm -rf {} +
	rm -rf frontend/.next frontend/node_modules/.cache
