# Runbook 05 — Model Retraining

**Estimated Time:** 30–60 minutes
**Who:** ML Engineer

---

## When to Retrain

| Trigger | Signal | Threshold |
|---------|--------|-----------|
| Scheduled retraining | Monthly cron job | 1st of every month |
| Model drift detected | R² drops on recent data | R² < 0.95 |
| New data available | World Bank dataset updated | Annually |
| Prediction anomaly | `predicted_arrivals_last` unusually high or low | ±50% from baseline |

---

## Step 1 — Download the Latest Dataset

```bash
# Install Kaggle CLI if not installed
pip install kaggle

# Download the latest dataset
kaggle datasets download bushraqurban/tourism-and-economic-impact \
  -p "Waqas data/" --unzip

# Verify the file
ls -lh "Waqas data/world_tourism_economy_data.csv"
```

---

## Step 2 — Execute the Notebook

```bash
cd "Waqas data"

jupyter nbconvert \
  --to notebook \
  --execute \
  --inplace datascience.ipynb \
  --ExecutePreprocessor.timeout=600
```

Expected output at the end of the notebook:
```
Rank 1st  Ridge Regression   | R²=0.9999+ | RMSE=0.01xx
Rank 2nd  Gradient Boosting  | R²=0.999x  | RMSE=0.06xx
Rank 3rd  Random Forest      | R²=0.997x  | RMSE=0.11xx
```

**If R² drops below 0.95:** Stop and investigate data quality before proceeding.

---

## Step 3 — Compare New vs Old Metrics

```bash
# View the new model metrics
cat outputs/metrics/model_comparison.csv

# Compare against the previous run (if archived)
diff outputs/metrics/model_comparison.csv outputs/metrics/model_comparison_prev.csv
```

Acceptance criteria before deploying the new model:

| Metric | Minimum Required |
|--------|-----------------|
| Best model R² | >= 0.95 |
| Best model RMSE (log scale) | <= 0.20 |
| All models pass sanity check | Yes |

---

## Step 4 — Copy Model Files to the mlops Folder

```bash
cp outputs/models/ridge_regression.pkl  mlops/outputs/models/
cp outputs/models/gradient_boosting.pkl mlops/outputs/models/
cp outputs/models/random_forest.pkl     mlops/outputs/models/
cp outputs/models/scaler.pkl            mlops/outputs/models/
cp outputs/models/label_encoder.pkl     mlops/outputs/models/

echo "Model files updated"
ls -lh mlops/outputs/models/
```

---

## Step 5 — Run Tests

```bash
cd mlops
pip install -r requirements.txt
pytest tests/ -v
```

All tests must pass before deploying the updated model.

---

## Step 6 — Deploy the New Model

Follow [Runbook 01 — Deployment](./01-deployment.md) from Step 1.

---

## Step 7 — Post-Retrain Monitoring

Monitor the Grafana dashboard for 30 minutes after the deploy:

- `predicted_arrivals_last` — values should be in the expected range
- `Error Rate %` — should remain near 0%
- `Latency p95` — should remain below 200ms

---

## Model-Level Rollback

If the new model produces incorrect predictions after deploy:

```bash
# Restore the previous model files from git history
git log --oneline -- mlops/outputs/models/
git checkout <PREVIOUS_COMMIT> -- mlops/outputs/models/

# Commit and redeploy
git add mlops/outputs/models/
git commit -m "revert: restore previous model version"
git push origin main
```
