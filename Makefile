.PHONY: install-api run-api test-api lint-api format-api typecheck-api check-api docker-api qwen-spike

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

docker-api:
	docker compose up --build api

qwen-spike:
	python scripts/qwen_spike/run_all.py
