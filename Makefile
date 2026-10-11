.PHONY: install test lint typecheck test-web build-web verify run-api run-cli run-worker

install:
	.venv/bin/python -m pip install -e 'packages/contracts[dev]' -e packages/agent-kernel -e packages/speccraft

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check apps packages tests

typecheck:
	.venv/bin/mypy apps packages/contracts/src packages/agent-kernel/src packages/speccraft/src

test-web:
	npm --prefix apps/web run test

build-web:
	npm --prefix apps/web run build

verify: test lint typecheck test-web build-web

run-api:
	.venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 8765

run-cli:
	.venv/bin/python -m apps.cli

run-worker:
	.venv/bin/python -m apps.worker
