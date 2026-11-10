# ReviewOps

A grounded AI code-review assistant, delivered through a Jenkins - Docker - Ansible - Kubernetes - ELK pipeline.
(CSE 816 Software Production Engineering final project.) See the proposal PDF for the full design.

## Project layout

```
reviewops/
├── README.md
├── Makefile                     # make venv | test | bench | run | build | up | down
├── Jenkinsfile                  # webhook-triggered pipeline (build, test, eval gate, scan, push, deploy)
├── docker-compose.yml           # local dev: reviewer app, Jenkins, Vault, optional Ollama
├── .env.example                 # copy to .env (never commit .env)
├── .gitignore  .dockerignore
├── app/
│   ├── Dockerfile               # stages: base, unit-test, eval-gate, runtime  (build from repo root)
│   ├── requirements.txt  requirements-dev.txt  pytest.ini
│   ├── reviewops/
│   │   ├── main.py              # FastAPI: /health /version /review /reviews and the status page /
│   │   ├── reviewer.py          # core logic: prompt -> LLM -> comments -> verdict policy
│   │   ├── llm.py               # FakeLLM (deterministic rules) + OllamaLLM
│   │   ├── diffutil.py          # unified-diff parser (added lines with file + line number)
│   │   ├── schemas.py  config.py  store.py  ui.py
│   │   ├── logging_setup.py     # structured JSON logs for ELK
│   │   └── prompts/v1.txt       # versioned prompt (a prompt change is a release)
│   └── tests/                   # test_core.py (stdlib), test_api.py (FastAPI)
├── benchmark/
│   ├── run_benchmark.py         # the EVAL GATE (recall / false-positive thresholds)
│   └── cases/                   # seeded-bug and clean diffs + labels.json
├── jenkins/                     # Jenkins image with docker CLI, ansible, kubectl + plugins.txt
├── ansible/
│   ├── site.yml                 # one-time bootstrap (roles: docker, k8s_cluster, jenkins, vault, elk)
│   ├── deploy.yml               # called by Jenkins: -e deploy_mode=canary|promote|discard|stable
│   ├── group_vars/all.yml
│   └── roles/
│       ├── app_deploy/          # IMPLEMENTED: namespace, Deployment, Service, HPA, canary/promote
│       └── docker k8s_cluster jenkins vault elk/   # placeholders to implement
└── elk/                         # week 4 (Filebeat, Logstash, Kibana dashboards)
```

## Quick start

**Without Docker** (needs Python 3.11+):
```bash
make venv
make test            # unit + API tests
make bench           # eval gate; should print "EVAL GATE: PASSED"
make run             # http://localhost:8000
```
Try it:
```bash
curl -s localhost:8000/review -H 'Content-Type: application/json' -d '{
  "repo": "demo/app", "pr_number": 1,
  "diff": "@@ -1,1 +1,2 @@\n x = 1\n+API_KEY = \"abcd1234\"\n"
}'
```
Then open http://localhost:8000 to see the history, version and prompt badges.

**With Docker:**
```bash
cp .env.example .env
docker compose up -d --build reviewer      # app on :8000
docker compose up -d                       # also Jenkins (:8080) and Vault (:8200)
```

## How the pieces fit
- `Jenkinsfile` builds Docker *targets*: `unit-test` and `eval-gate` fail the build if tests or the benchmark fail.
- The eval gate runs `benchmark/run_benchmark.py` (default: recall >= 0.8, false-positive rate <= 0.2; override with `MIN_RECALL`, `MAX_FALSE_POSITIVE_RATE`).
- Deploy goes through Ansible: `deploy_mode=canary` (1 new pod, own Service) -> benchmark against it -> `promote` (zero-downtime rolling update, canary removed) or `discard`.
- `LLM_BACKEND=fake` (default) is deterministic; set `LLM_BACKEND=ollama` and `OLLAMA_MODEL` for a real model.
- Verdict policy lives in code (`reviewer.decide_verdict`): the LLM can raise issues but can never approve a high/critical one.

## Status of this baseline
Verified in the generation environment: core unit tests (12), eval gate (pass, and fails when a rule is broken), YAML syntax of all configs, Kubernetes templates render to valid objects.
**Not yet run** (no network/Docker/cluster there): the FastAPI layer + `test_api.py`, Docker builds, Compose, Jenkins, Ansible against a cluster. Expect small fixes on first run.

## Troubleshooting
- `pydantic-core` fails with a Rust/`maturin` error: your Python is newer than the installed wheels support.
  `rm -rf .venv`, then `make venv`. If it still fails, use Python 3.12: `brew install python@3.12 && make venv PY=python3.12`.
  (Docker images already use Python 3.12.)
- `pip` DNS errors: check your internet/VPN; pip needs PyPI access.

## Next steps (matches the weekly plan)
- W1: run everything above, set up the Jenkins job + webhook tunnel, create the cluster.
- W2: Docker Hub credentials in Vault; Semgrep/Trivy findings into the prompt; more benchmark cases (target ~20).
- W3: PR-comment bot (Flow B); canary eval stage (reach the canary via port-forward or NodePort); metrics-server + HPA load test.
- W4: ELK (Filebeat -> Logstash -> Elasticsearch -> Kibana); implement remaining Ansible roles.

## Known gaps / TODO
- Jenkins container needs a kubeconfig that can reach your cluster (minikube/kind API is usually on localhost, which a container cannot see).
- Jenkins runs as root with the Docker socket mounted: acceptable for a local baseline only.
- `DOCKERHUB_USER` is a placeholder in `Jenkinsfile` and `ansible/group_vars/all.yml`.
- Trivy is report-only (`--exit-code 0`) until you decide to enforce.

## Git (when you are ready; nothing has been committed)
```bash
git init && git checkout -b main
git add . && git commit -m "Baseline project skeleton"
git remote add origin <your-repo-url> && git push -u origin main
```
Suggested workflow: short-lived feature branches and pull requests, so both members' commits show in history.
