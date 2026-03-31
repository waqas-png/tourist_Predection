# Runbook 03 — Incident Response

**Estimated Time:** Depends on severity
**Who:** On-Call Engineer

---

## Incident Response Flow

```
Alert received (Grafana / Slack / PagerDuty)
        │
        ▼
    Assess severity
        │
   ┌────┴────┐
  P1/P2    P3/P4
   │          │
   ▼          ▼
Acknowledge  Schedule fix
immediately  for next sprint
   │
   ▼
Diagnose (see sections below)
   │
   ▼
Apply fix or rollback
   │
   ▼
Verify resolution
   │
   ▼
Write post-incident log
```

---

## Alert Reference Table

| Alert Name | Prometheus Expression | Possible Cause | Go To |
|-----------|----------------------|----------------|-------|
| `APIDown` | `up == 0` | Container crash, network issue | Section A |
| `HighErrorRate` | error % > 5% | Bad input, model error, code bug | Section B |
| `SlowPredictions` | p95 > 500ms | High load, resource starvation | Section C |
| `NoTraffic` | requests == 0 for 10m | ALB misconfiguration, DNS issue | Section D |

---

## Section A — API Down (P1)

**Grafana:** `APIDown` alert firing

### Diagnose

```bash
# 1. Check ECS task state
aws ecs describe-services \
  --cluster tourism-mlops-cluster \
  --services tourism-api-service \
  --query "services[0].{Running:runningCount,Desired:desiredCount,Pending:pendingCount}"

# 2. Get recently stopped tasks and check exit reason
aws ecs list-tasks \
  --cluster tourism-mlops-cluster \
  --service-name tourism-api-service \
  --desired-status STOPPED \
  --query "taskArns[:3]"

aws ecs describe-tasks \
  --cluster tourism-mlops-cluster \
  --tasks <TASK_ARN> \
  --query "tasks[0].containers[0].{Reason:reason,Status:lastStatus,ExitCode:exitCode}"

# 3. Read application logs
aws logs get-log-events \
  --log-group-name /ecs/tourism-ml-api \
  --log-stream-name <STREAM_NAME> \
  --limit 50 \
  --query "events[*].message"
```

### Common Exit Codes and Fixes

| Exit Code | Cause | Fix |
|-----------|-------|-----|
| 137 | Out of Memory (OOM) | Increase ECS task memory — see [Runbook 06](./06-scaling.md) |
| 1 | App crash (missing model file, import error) | Check logs, verify model `.pkl` files exist |
| 0 | Unexpected graceful shutdown | Check CloudWatch events |

---

## Section B — High Error Rate (P2)

**Grafana:** Error Rate % panel > 5%

### Diagnose

```bash
# 1. Query error rate trend in Prometheus
curl 'http://prometheus:9090/api/v1/query_range' \
  --data-urlencode 'query=rate(prediction_requests_total{status="error"}[1m])' \
  --data-urlencode 'start=now-30m' \
  --data-urlencode 'end=now' \
  --data-urlencode 'step=60'

# 2. Filter application error logs
aws logs filter-log-events \
  --log-group-name /ecs/tourism-ml-api \
  --filter-pattern "ERROR" \
  --start-time $(date -d '30 minutes ago' +%s000) \
  --query "events[*].message"

# 3. Manually test a prediction request
curl -X POST http://<ALB-DNS>/predict \
  -H "Content-Type: application/json" \
  -d '{"log_tourism_receipts":20.5,"log_tourism_exports":3.2,
       "log_tourism_expenditures":18.9,"log_gdp":26.1,
       "inflation":2.5,"year_norm":0.85,"is_post_covid":0,
       "decade":2010,"lag1_log_arrivals":15.2,
       "lag2_log_arrivals":15.0,"arrival_growth":0.05,"country_enc":42}'
```

### Common Causes and Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `500 Internal Server Error` | Model loading failed | Verify `.pkl` files are present |
| `422 Unprocessable Entity` | Client sending bad input | Share API docs — client-side issue |
| Errors started right after deploy | Bad deploy | [Rollback — Runbook 02](./02-rollback.md) |
| Errors are intermittent | Resource pressure | [Scale up — Runbook 06](./06-scaling.md) |

---

## Section C — Slow Predictions (P2/P3)

**Grafana:** Prediction Latency p95 > 500ms

### Diagnose

```bash
# 1. Check latency percentiles in Prometheus
curl 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(prediction_latency_seconds_bucket[5m]))'

# 2. Check ECS CPU utilisation
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=tourism-mlops-cluster \
  --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average
```

### Common Causes and Fixes

| Cause | Fix |
|-------|-----|
| CPU above 80% | [Scale up tasks — Runbook 06](./06-scaling.md) |
| High number of concurrent requests | Add more ECS tasks |
| Network latency between ALB and ECS | Ensure ALB and ECS are in the same region and AZ |

---

## Section D — No Traffic (P3)

**Grafana:** `NoTraffic` alert — no requests for 10 minutes

### Diagnose

```bash
# 1. Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN> \
  --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}"

# 2. DNS resolution check
nslookup <ALB-DNS>

# 3. Verify ALB security group allows port 80
aws ec2 describe-security-groups \
  --group-ids <ALB-SG-ID> \
  --query "SecurityGroups[0].IpPermissions"
```

---

## Incident Log Template

Fill this in after every P1 or P2 incident:

```
## Incident Report

Date:         YYYY-MM-DD HH:MM UTC
Duration:     X minutes
Severity:     P1 / P2 / P3
Alert:        Alert name that fired
Engineer:     Your name

### Timeline
- HH:MM  Alert received
- HH:MM  Investigation started
- HH:MM  Root cause identified: ...
- HH:MM  Fix applied: ...
- HH:MM  Verified — incident resolved

### Root Cause
[2–3 sentences describing what happened]

### Fix Applied
[What action was taken to resolve it]

### Prevention
[What should be done to prevent this from happening again]
```
