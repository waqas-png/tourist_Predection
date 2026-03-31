# Runbook 07 — Secrets & Access Management

**Who:** DevOps Engineer / Team Lead
**Purpose:** Managing GitHub Secrets, AWS IAM roles, and Grafana credentials

---

## GitHub Secrets Required

Navigate to: `GitHub → Repository → Settings → Secrets and variables → Actions`

Add the following secrets:

| Secret Name | Value | Used In |
|-------------|-------|---------|
| `AWS_IAM_ROLE_ARN` | `arn:aws:iam::ACCOUNT_ID:role/GitHubActionsRole` | CI/CD OIDC authentication |
| `AWS_REGION` | `us-east-1` | All AWS actions |
| `ECR_REPOSITORY` | `tourism-ml-api` | Docker image push |
| `API_URL` | `http://<ALB-DNS>` | Smoke test, monitor workflow |
| `PROMETHEUS_URL` | `http://prometheus:9090` | Monitor workflow |
| `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/...` | Failure notifications |

---

## AWS IAM Role for GitHub Actions (OIDC)

Using OIDC means no long-lived AWS access keys are stored — this is the most secure approach.

### Step 1 — Create the OIDC Identity Provider in AWS

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### Step 2 — Create the IAM Role

```bash
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name GitHubActionsRole \
  --assume-role-policy-document file://trust-policy.json
```

### Step 3 — Attach Permissions to the Role

```bash
# Allow pushing Docker images to ECR
aws iam attach-role-policy \
  --role-name GitHubActionsRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# Allow deploying to ECS
aws iam attach-role-policy \
  --role-name GitHubActionsRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
```

### Step 4 — Add the Role ARN to GitHub Secrets

```
Secret name:  AWS_IAM_ROLE_ARN
Secret value: arn:aws:iam::YOUR_ACCOUNT_ID:role/GitHubActionsRole
```

---

## ECS Task Execution Role

Required for ECS containers to pull images from ECR and write logs to CloudWatch.

```bash
# Create the role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "Service": "ecs-tasks.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach the required managed policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

---

## Rotate Grafana Admin Password

```bash
# Option 1: Update the Docker Compose environment variable
# Edit docker/docker-compose.yml:
#   GF_SECURITY_ADMIN_PASSWORD=new_strong_password_here

# Then restart Grafana
docker-compose -f docker/docker-compose.yml restart grafana

# Option 2: Use the Grafana REST API
curl -X PUT http://admin:OLD_PASSWORD@grafana:3000/api/user/password \
  -H "Content-Type: application/json" \
  -d '{
    "oldPassword": "admin123",
    "newPassword": "new_strong_password",
    "confirmNew": "new_strong_password"
  }'
```

---

## Slack Webhook Setup

1. Go to: `https://api.slack.com/apps`
2. Click `Create New App` → `From Scratch`
3. Name the app `Tourism MLOps Alerts` and select your workspace
4. Go to `Incoming Webhooks` → toggle **ON** → click `Add New Webhook to Workspace`
5. Select the channel (e.g. `#ml-alerts`) → click **Allow**
6. Copy the webhook URL → add it to GitHub Secret `SLACK_WEBHOOK_URL`

Test the webhook:
```bash
curl -X POST $SLACK_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"text": "Test alert from Tourism MLOps"}'
```

---

## Access Revocation (Offboarding a Team Member)

```bash
# Remove their IAM user (if one exists)
aws iam delete-user --user-name <username>

# Revoke any GitHub Personal Access Tokens — via GitHub Settings → Developer settings

# Rotate the Grafana admin password (see above)

# Regenerate the Slack webhook if the old one may have been shared
```

---

## Secret Rotation Schedule

| Secret | Rotation Frequency |
|--------|-------------------|
| Grafana admin password | Every 90 days |
| Slack webhook URL | Only if compromised |
| AWS OIDC role | No rotation needed — OIDC tokens are short-lived |
| ECR credentials | No rotation needed — managed by OIDC |
