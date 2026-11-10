.PHONY: venv test bench run build up down
PY ?= python3
VENV := .venv

venv:
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install -r app/requirements-dev.txt

test:
	cd app && ../$(VENV)/bin/python -m pytest -q

bench:
	PYTHONPATH=app $(PY) benchmark/run_benchmark.py

run:
	cd app && ../$(VENV)/bin/uvicorn reviewops.main:app --reload --port 8000

build:
	docker build --target runtime -f app/Dockerfile -t reviewops:dev .

up:
	docker compose up -d --build

down:
	docker compose down
