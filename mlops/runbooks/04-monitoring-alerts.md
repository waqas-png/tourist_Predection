# Runbook 04 — Monitoring & Alerts

**Who:** DevOps / ML Engineer
**Purpose:** Setting up, querying, and maintaining Grafana and Prometheus

---

## Grafana Dashboard Access

```
URL:      http://grafana:3000
          (local Docker Compose environment)

Username: admin
Password: admin123
          (change GF_SECURITY_ADMIN_PASSWORD in production)

Dashboard: ML Monitoring → Tourism ML API — Monitoring
```

---

## Dashboard Panels — Explanation

| Panel | Prometheus Query | Healthy Range |
|-------|-----------------|---------------|
| Total Prediction Requests | `sum(prediction_requests_total)` | Steadily increasing |
| Success vs Error Rate | `rate(prediction_requests_total[1m])` | Errors near zero |
| Error Rate % | errors / total × 100 | Below 1% |
| API Uptime | `up{job="tourism-api"}` | 1 (green) |
| Latency p50 / p95 / p99 | `histogram_quantile(...)` | p95 < 200ms |
| Last Predicted Arrivals | `predicted_arrivals_last` | Non-zero value |

---

## Querying Prometheus Manually

Open: `http://prometheus:9090`

### Useful PromQL Queries

```promql
# Total successful predictions
sum(prediction_requests_total{status="success"})

# Error rate per second (last 5 minutes)
rate(prediction_requests_total{status="error"}[5m])

# Success rate as a percentage
100 * rate(prediction_requests_total{status="success"}[5m])
    / rate(prediction_requests_total[5m])

# p50 prediction latency
histogram_quantile(0.50, rate(prediction_latency_seconds_bucket[5m]))

# p95 prediction latency
histogram_quantile(0.95, rate(prediction_latency_seconds_bucket[5m]))

# API up/down status
up{job="tourism-api"}

# Last predicted arrivals value
predicted_arrivals_last
```

---

## Alert Rules — Detailed Reference

File: `monitoring/prometheus/alert_rules.yml`

### Alert 1: APIDown
```yaml
expr:  up{job="tourism-api"} == 0
for:   1m
```
- **Meaning:** The API has been unreachable for more than 1 minute
- **Severity:** Critical (P1)
- **Action:** [Runbook 03 — Section A](./03-incident-response.md#section-a--api-down-p1)

---

### Alert 2: HighErrorRate
```yaml
expr:  rate(errors[5m]) / rate(total[5m]) > 0.05
for:   2m
```
- **Meaning:** More than 5% of requests have been failing for 2+ minutes
- **Severity:** Warning (P2)
- **Action:** [Runbook 03 — Section B](./03-incident-response.md#section-b--high-error-rate-p2)

---

### Alert 3: SlowPredictions
```yaml
expr:  histogram_quantile(0.95, ...) > 0.5
for:   5m
```
- **Meaning:** 95th percentile latency has exceeded 500ms for 5+ minutes
- **Severity:** Warning (P2/P3)
- **Action:** [Runbook 03 — Section C](./03-incident-response.md#section-c--slow-predictions-p2p3)

---

### Alert 4: NoTraffic
```yaml
expr:  rate(prediction_requests_total[10m]) == 0
for:   10m
```
- **Meaning:** No prediction requests received for 10 minutes
- **Severity:** Info (P3)
- **Action:** [Runbook 03 — Section D](./03-incident-response.md#section-d--no-traffic-p3)

---

## Checking Prometheus Targets

```
http://prometheus:9090/targets
```

Expected state:

| Job | Target | State |
|-----|--------|-------|
| tourism-api | api:8000 | UP (green) |
| prometheus | localhost:9090 | UP (green) |

If a target shows `DOWN`:
```bash
# Verify the API container is running
docker ps | grep api

# Test connectivity from the Prometheus container
docker exec prometheus wget -qO- http://api:8000/metrics | head -5
```

---

## Creating a New Alert in Grafana

1. Open a dashboard panel → click `Edit`
2. Go to the `Alert` tab → `New alert rule`
3. Fill in:
   ```
   Name:        High Prediction Volume
   Condition:   sum(rate(prediction_requests_total[1m])) > 100
   For:         5m
   Severity:    warning
   ```
4. Set a notification policy (Slack or Email)
5. Click `Save`

---

## Grafana Slack Notification Setup

```
Grafana → Alerting → Contact Points → Add contact point

Name:    Slack ML Alerts
Type:    Slack
Webhook: https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

Click Test → then Save
```

---

## Restarting the Monitoring Stack

```bash
cd mlops

# Restart only Prometheus
docker-compose -f docker/docker-compose.yml restart prometheus

# Restart only Grafana
docker-compose -f docker/docker-compose.yml restart grafana

# Restart everything
docker-compose -f docker/docker-compose.yml restart

# View logs
docker-compose -f docker/docker-compose.yml logs -f prometheus
docker-compose -f docker/docker-compose.yml logs -f grafana
```

---

## Reload Prometheus Config (No Restart)

```bash
# Hot reload — Prometheus does not restart
curl -X POST http://prometheus:9090/-/reload

# Verify the new config was loaded
curl http://prometheus:9090/api/v1/status/config
```

---

## Backing Up Prometheus Data

```bash
docker run --rm \
  -v mlops_prometheus_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/prometheus-$(date +%Y%m%d).tar.gz /data

echo "Backup saved: backup/prometheus-$(date +%Y%m%d).tar.gz"
```
