.PHONY: help install install-api install-frontend dev api frontend cli lint build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────────

install: install-api install-frontend ## Install all dependencies

install-api: ## Create venv and install Python deps
	python3 -m venv api/venv
	api/venv/bin/pip install --upgrade pip
	api/venv/bin/pip install -r api/requirements.txt

install-frontend: ## Install frontend npm packages
	cd frontend && npm install

# ── Dev servers ────────────────────────────────────────

dev: ## Run API + frontend concurrently
	@make -j2 api frontend

api: ## Start FastAPI backend (port 8000)
	cd api && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

frontend: ## Start Vite dev server
	cd frontend && npm run dev

# ── CLI ────────────────────────────────────────────────

cli: ## Run CLI (usage: make cli ARGS="holdings --json")
	cd api && source venv/bin/activate && python cli.py $(ARGS)

# ── Quality ────────────────────────────────────────────

lint: ## Lint frontend
	cd frontend && npm run lint

build: ## Production build of frontend
	cd frontend && npm run build

# ── Cleanup ────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf frontend/dist
	find api -type d -name __pycache__ -exec rm -rf {} +
