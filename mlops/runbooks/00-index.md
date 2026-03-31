# MLOps Runbooks — Tourism Arrivals Prediction API

## Index

| # | Runbook | When to Use |
|---|---------|-------------|
| 01 | [Deployment](./01-deployment.md) | Deploying a new model or code change |
| 02 | [Rollback](./02-rollback.md) | Something broke after a deploy |
| 03 | [Incident Response](./03-incident-response.md) | API is down or showing high error rates |
| 04 | [Monitoring & Alerts](./04-monitoring-alerts.md) | A Grafana or Prometheus alert fired |
| 05 | [Model Retraining](./05-model-retraining.md) | Model accuracy dropped or new data is available |
| 06 | [Scaling](./06-scaling.md) | High traffic or cost optimisation needed |
| 07 | [Secrets & Access](./07-secrets-access.md) | Managing AWS credentials or GitHub secrets |

---

## System Overview

```
GitHub Push
    │
    ▼
CI Pipeline (ci.yml)
    │  lint → test → docker build → ECR push
    ▼
CD Pipeline (cd.yml)
    │  ECS Fargate rolling deploy → smoke test
    ▼
AWS ECS (Fargate)
    │  tourism-api container (port 8000)
    ▼
Application Load Balancer
    │  internet-facing, health checks
    ▼
Prometheus ──scrape /metrics──► Grafana Dashboard
    │
    ▼
Alert Rules → Slack / PagerDuty
```

## Quick Reference — Key URLs

| Service | URL |
|---------|-----|
| API Health | `http://<ALB-DNS>/health` |
| API Docs (Swagger) | `http://<ALB-DNS>/docs` |
| Prometheus | `http://prometheus:9090` |
| Grafana | `http://grafana:3000` (admin / admin123) |
| GitHub Actions | `https://github.com/<org>/<repo>/actions` |
| AWS ECS Console | `https://console.aws.amazon.com/ecs` |

## Severity Levels

| Level | Meaning | Target Response Time |
|-------|---------|----------------------|
| P1 — Critical | API completely down, data loss | 15 minutes |
| P2 — High | Error rate > 5%, p95 latency > 500ms | 1 hour |
| P3 — Medium | Degraded performance, one service down | 4 hours |
| P4 — Low | Non-critical alert, cosmetic issue | Next business day |
