# Runbook 06 — Scaling

**Estimated Time:** 5–15 minutes
**Who:** DevOps Engineer

---

## When to Scale Up

| Signal | Threshold | Action |
|--------|-----------|--------|
| CPU utilisation | > 70% sustained for 10 minutes | Add more ECS tasks |
| Memory utilisation | > 80% | Increase task memory allocation |
| p95 latency | > 500ms | Add more ECS tasks |
| Request throughput | > 50 req/s with only 2 tasks running | Add more tasks |

## When to Scale Down

| Signal | Threshold | Action |
|--------|-----------|--------|
| CPU utilisation | < 20% for 30 minutes | Reduce ECS tasks (minimum: 2) |
| Off-peak hours (nights/weekends) | Predictable low traffic | Configure scheduled scaling |

---

## Option A — Scale via ECS Console

```
AWS Console
  → ECS → Clusters → tourism-mlops-cluster
  → Services → tourism-api-service
  → Click "Update Service"
  → Desired tasks: change 2 → 4
  → Click "Update"
```

---

## Option B — Scale via AWS CLI

```bash
# Scale UP to 4 tasks
aws ecs update-service \
  --cluster tourism-mlops-cluster \
  --service tourism-api-service \
  --desired-count 4 \
  --region us-east-1

# Verify the scaling operation
aws ecs describe-services \
  --cluster tourism-mlops-cluster \
  --services tourism-api-service \
  --query "services[0].{Running:runningCount,Desired:desiredCount}"
```

---

## Option C — Enable Auto Scaling (Recommended for Production)

Automatically scale based on CPU utilisation:

```bash
# Register the scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/tourism-mlops-cluster/tourism-api-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Create a scale-out policy triggered at 70% CPU
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/tourism-mlops-cluster/tourism-api-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name scale-out-cpu \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 120,
    "ScaleInCooldown": 300
  }'
```

---

## Fix: Out of Memory (Exit Code 137)

If tasks are stopping with exit code 137:

1. Open `aws/ecs-task-definition.json`
2. Increase the memory allocation:
   ```json
   "cpu":    "1024",
   "memory": "2048"
   ```
3. Commit the change and push to `main` → CI/CD will deploy the updated task definition

---

## Verify Scaling Worked

```bash
# Check the number of running tasks
aws ecs describe-services \
  --cluster tourism-mlops-cluster \
  --services tourism-api-service \
  --query "services[0].runningCount"

# Confirm latency improved in Prometheus
curl 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(prediction_latency_seconds_bucket[5m]))'
```

On the Grafana dashboard, the Latency p95 panel should drop within 2–3 minutes of scaling.
