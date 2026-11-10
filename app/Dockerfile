# Build from the REPO ROOT:  docker build -f app/Dockerfile --target <stage> .
# Stages: unit-test and eval-gate FAIL the build if tests/benchmark fail (used by Jenkins).
# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/srv
WORKDIR /srv
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS unit-test
COPY app/requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY app/reviewops ./reviewops
COPY app/tests ./tests
RUN python -m pytest -q tests

FROM base AS eval-gate
COPY app/reviewops ./reviewops
COPY benchmark ./benchmark
RUN python benchmark/run_benchmark.py

FROM base AS runtime
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
COPY app/reviewops ./reviewops
RUN useradd --system --uid 10001 appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "reviewops.main:app", "--host", "0.0.0.0", "--port", "8000"]
