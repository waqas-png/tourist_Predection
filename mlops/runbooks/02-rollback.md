# Runbook 02 — Rollback

**Severity:** P1–P2
**Estimated Time:** 5–10 minutes
**Who:** DevOps / On-Call Engineer

---

## When to Rollback

| Signal | Action |
|--------|--------|
| Error rate > 5% after deploy | Rollback immediately |
| API health check failing | Rollback immediately |
| ECS tasks repeatedly crashing | Rollback immediately |
| p95 latency > 1 second | Consider rollback |
| Smoke test failed in CD pipeline | Automatic rollback (circuit breaker active) |

> **Note:** The ECS deployment circuit breaker is enabled in `cloudformation.yml`.
> If tasks fail during a deploy, ECS will **automatically** roll back.
> Use this runbook when a manual rollback is needed after a successful deploy.

---

## Option A — Rollback via GitHub Actions (Recommended)

### Step 1: Find the last working commit SHA
```bash
git log --oneline -10
# Identify the last commit that was stable
# e.g.: a1b2c3d  feat: previous working version
```

### Step 2: Revert the bad commit
```bash
git revert HEAD          # Reverts the latest commit
git push origin main     # CI/CD will automatically re-deploy
```

To revert a specific commit:
```bash
git revert <bad-commit-sha>
git push origin main
```

---

## Option B — Direct Rollback via AWS ECS Console (Fastest)

Use this if GitHub Actions is slow or unavailable.

### Step 1: Open ECS Console
```
AWS Console
  → ECS
  → Clusters → tourism-mlops-cluster
  → Services → tourism-api-service
  → Click "Update Service"
```

### Step 2: Select the previous task definition revision
```
Task Definition → Revision dropdown
  → Select the previous revision (e.g., tourism-ml-api:4 instead of :5)
→ Click "Update"
```

### Step 3: Monitor the rollback
```
Services → tourism-api-service → Deployments tab
→ New tasks will start, old tasks will drain and terminate
→ Completes in approximately 2–3 minutes
```

---

## Option C — Rollback via AWS CLI

```bash
# List recent task definition revisions
aws ecs list-task-definitions \
  --family-prefix tourism-ml-api \
  --sort DESC \
  --query "taskDefinitionArns[:5]"

# Roll back to the previous revision
aws ecs update-service \
  --cluster tourism-mlops-cluster \
  --service tourism-api-service \
  --task-definition tourism-ml-api:PREVIOUS_REVISION_NUMBER \
  --region us-east-1

# Wait for the rollback to stabilise
aws ecs wait services-stable \
  --cluster tourism-mlops-cluster \
  --services tourism-api-service \
  --region us-east-1

echo "Rollback complete"
```

---

## Option D — Rollback to a Specific Docker Image

```bash
# List available images in ECR
aws ecr list-images \
  --repository-name tourism-ml-api \
  --region us-east-1 \
  --query "imageIds[*].imageTag" \
  --output table

# Update the task definition image URI in ECS Console
# or re-tag the old image as latest and push
```

---

## Post-Rollback Verification

Run these checks 3 minutes after the rollback completes:

```bash
# 1. Health check
curl http://<ALB-DNS>/health
# Expected: {"status": "ok", "model": "ridge_regression"}

# 2. Check error rate in Prometheus
curl 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(prediction_requests_total{status="error"}[2m])'
# Expected: 0 or near-zero

# 3. Verify ECS task health
aws ecs describe-services \
  --cluster tourism-mlops-cluster \
  --services tourism-api-service \
  --query "services[0].{Running:runningCount, Desired:desiredCount, Pending:pendingCount}"
# Expected: Running == Desired, Pending == 0
```

---

## After the Rollback

1. **Find the root cause** — what broke?
   - Application logs: `AWS Console → CloudWatch → /ecs/tourism-ml-api`
   - GitHub Actions logs: open the failed workflow run
   - Prometheus: note the time of the error rate spike

2. **Fix the issue** before pushing to `main` again

3. **Test on staging** (if a staging environment exists)

4. **Write an incident log** using the template in [Runbook 03](./03-incident-response.md)
