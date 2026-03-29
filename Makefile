.PHONY: dev dev-backend dev-frontend install install-backend install-frontend lint lint-backend lint-frontend test test-backend test-frontend build build-frontend clean

# ── Development ──

dev:
	@make -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && pnpm dev

# ── Install dependencies ──

install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && pnpm install

# ── Linting ──

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check .

lint-frontend:
	cd frontend && pnpm lint

# ── Testing ──

test: test-backend test-frontend

test-backend:
	cd backend && pytest

test-frontend:
	cd frontend && pnpm test

# ── Build ──

build: build-frontend

build-frontend:
	cd frontend && pnpm build

# ── Cleanup ──

clean:
	find backend -type d -name __pycache__ -exec rm -rf {} +
	rm -rf frontend/.next frontend/node_modules/.cache
