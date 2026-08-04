.PHONY: install-api run-api test-api lint-api format-api typecheck-api check-api docker-api install-web run-web test-web lint-web typecheck-web build-web check-web check docker qwen-spike db-upgrade db-downgrade db-reset seed-demo seed-demo-reset demo-backend demo-backend-retry

install-api:
	python -m pip install -e "./apps/api[dev]"

run-api:
	uvicorn app.main:app --app-dir apps/api --host 0.0.0.0 --port 8000 --reload

test-api:
	pytest apps/api/tests -m "not live_qwen"

lint-api:
	ruff check apps/api scripts/qwen_spike

format-api:
	ruff format apps/api scripts/qwen_spike

typecheck-api:
	mypy apps/api/app

check-api: lint-api typecheck-api test-api

install-web:
	npm --prefix apps/web ci

run-web:
	npm --prefix apps/web run dev

test-web:
	npm --prefix apps/web test

lint-web:
	npm --prefix apps/web run lint

typecheck-web:
	npm --prefix apps/web run typecheck

build-web:
	npm --prefix apps/web run build

check-web: lint-web typecheck-web test-web build-web

check: check-api check-web

db-upgrade:
	alembic -c apps/api/alembic.ini upgrade head

db-downgrade:
	alembic -c apps/api/alembic.ini downgrade -1

db-reset:
	alembic -c apps/api/alembic.ini downgrade base
	alembic -c apps/api/alembic.ini upgrade head
	PYTHONPATH=apps/api python -m app.db.seed --reset

seed-demo:
	PYTHONPATH=apps/api python -m app.db.seed

seed-demo-reset:
	PYTHONPATH=apps/api python -m app.db.seed --reset

demo-backend:
	PYTHONPATH=apps/api python -m tests.backend_demo happy

demo-backend-retry:
	PYTHONPATH=apps/api python -m tests.backend_demo retry

docker-api:
	docker compose up --build api

docker:
	docker compose up --build

qwen-spike:
	python scripts/qwen_spike/run_all.py
