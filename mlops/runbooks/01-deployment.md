# Runbook 01 — Deployment

**Severity:** N/A (planned activity)
**Estimated Time:** 10–20 minutes
**Who:** DevOps / ML Engineer

---

## Pre-Deployment Checklist

Complete all of the following BEFORE deploying:

- [ ] Notebook has been executed and `outputs/models/` contains all `.pkl` files
- [ ] `pytest tests/ -v` passes locally
- [ ] `docker build -f docker/Dockerfile .` succeeds locally
- [ ] AWS credentials are configured (`aws sts get-caller-identity` returns a valid account)
- [ ] All GitHub Secrets are set (see [Runbook 07](./07-secrets-access.md))
- [ ] Grafana dashboard is open for live monitoring
- [ ] Team has been notified of the upcoming deploy (Slack / email)

---

## Step 1 — Push Code

```bash
git add .
git commit -m "feat: describe your change here"
git push origin main
```

GitHub Actions will start automatically.

---

## Step 2 — Monitor the CI Pipeline

1. Open GitHub → `Actions` tab
2. Watch the `CI — Test & Build` workflow
3. Verify all stages pass:

```
lint  ──►  test  ──►  build (Docker + ECR push)
 ✅           ✅              ✅
```

**If a stage fails:**

| Error | Fix |
|-------|-----|
| `black` format check fails | Run `black app/ tests/` locally and commit |
| `pytest` fails | Run `pytest tests/ -v` locally, fix the failing test |
| ECR push fails | Check AWS credentials (see Runbook 07) |
| Docker build fails | Check `requirements.txt` for version conflicts |

---

## Step 3 — Monitor the CD Pipeline

After CI passes, CD triggers automatically:

```
CI success
    │
    ▼
CD: register new ECS task definition
    │
    ▼
ECS rolling deploy
(old tasks + new tasks run simultaneously)
    │
    ▼
New tasks become healthy → old tasks terminate
    │
    ▼
Smoke test: GET /health → HTTP 200?
    │
    ▼
Deploy complete ✅
```

**Monitor via ECS Console:**
```
AWS Console → ECS → Clusters → tourism-mlops-cluster
           → Services → tourism-api-service
           → Deployments tab
```

---

## Step 4 — Post-Deploy Verification

Run these checks 2 minutes after the deploy completes:

### 4a. Health Check
```bash
curl http://<ALB-DNS>/health
# Expected: {"status": "ok", "model": "ridge_regression"}
```

### 4b. Test a Prediction
```bash
curl -X POST http://<ALB-DNS>/predict \
  -H "Content-Type: application/json" \
  -d '{
    "log_tourism_receipts": 20.5,
    "log_tourism_exports": 3.2,
    "log_tourism_expenditures": 18.9,
    "log_gdp": 26.1,
    "inflation": 2.5,
    "year_norm": 0.85,
    "is_post_covid": 0,
    "decade": 2010,
    "lag1_log_arrivals": 15.2,
    "lag2_log_arrivals": 15.0,
    "arrival_growth": 0.05,
    "country_enc": 42
  }'
# Expected: {"log_prediction": ..., "predicted_arrivals": ...}
```

### 4c. Grafana Check
1. Open Grafana → `Tourism ML API — Monitoring` dashboard
2. Verify:
   - **API Uptime** panel → `UP` (green)
   - **Error Rate %** → `0%` or negligible
   - **Prediction Latency p95** → below 200ms

### 4d. Prometheus Target Check
```
http://prometheus:9090/targets
→ tourism-api job → State: UP (green)
```

---

## Step 5 — Deploy Complete

- [ ] Grafana dashboard shows all panels healthy
- [ ] `/health` returns HTTP 200
- [ ] `/predict` returns a valid prediction response
- [ ] Announce deploy success in Slack

---

## Rollback Trigger Conditions

Immediately follow [Runbook 02 — Rollback](./02-rollback.md) if ANY of these occur after deploy:

- Error rate > 5%
- p95 latency > 500ms
- `/health` does not return 200
- ECS tasks are crashing (restart count > 2)
