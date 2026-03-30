.PHONY: dev dev-backend dev-frontend install install-backend install-frontend lint lint-backend lint-frontend test test-backend test-frontend build build-frontend docker-build docker-up docker-down clean

# ── Development ──

dev:
	@make -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && NEXT_PUBLIC_PLAYGROUND_API_MODE=backend NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 pnpm dev

# ── Install dependencies ──

install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && pnpm install

# ── Linting ──

lint: lint-backend lint-frontend

lint-backend:
	cd backend && python3 -m compileall app tests

lint-frontend:
	cd frontend && pnpm lint

# ── Testing ──

test: test-backend test-frontend

test-backend:
	cd backend && python3 -m unittest discover tests

test-frontend:
	cd frontend && pnpm test

# ── Build ──

build: build-frontend

build-frontend:
	cd frontend && pnpm build

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
