# ELK (week 4)

Planned files:
- `filebeat.yml`   - DaemonSet config: read container logs, ship to Logstash
- `logstash.conf`  - parse the JSON log lines emitted by `reviewops/logging_setup.py`
- `kibana/`        - exported dashboards (reviews over time, verdicts, latency, canary results)

The app already logs one JSON object per review (`event=review_completed`) to stdout.
Deploy this stack to Kubernetes with the `ansible/roles/elk` role.
