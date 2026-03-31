"""
FastAPI application — Tourism Arrivals Prediction
Exposes:
  POST /predict        -> model prediction
  GET  /health         -> liveness probe
  GET  /metrics        -> Prometheus scrape endpoint
"""

import time
import joblib
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from app.schemas import PredictionRequest, PredictionResponse

# ── Load models ────────────────────────────────────────────────
MODEL_DIR = Path("outputs/models")

try:
    model   = joblib.load(MODEL_DIR / "ridge_regression.pkl")
    scaler  = joblib.load(MODEL_DIR / "scaler.pkl")
    encoder = joblib.load(MODEL_DIR / "label_encoder.pkl")
except FileNotFoundError as e:
    raise RuntimeError(f"Model files not found: {e}. Run the notebook first.")

# ── Prometheus metrics ─────────────────────────────────────────
PREDICTION_COUNT   = Counter("prediction_requests_total",
                              "Total prediction requests",
                              ["status"])          # success / error

PREDICTION_LATENCY = Histogram("prediction_latency_seconds",
                                "Time to serve a prediction",
                                buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0])

PREDICTED_VALUE    = Gauge("predicted_arrivals_last",
                            "Last predicted tourism arrivals value")

MODEL_INFO         = Gauge("model_info",
                            "Model metadata",
                            ["model_name", "version"])
MODEL_INFO.labels(model_name="ridge_regression", version="1.0").set(1)

# ── App ────────────────────────────────────────────────────────
app = FastAPI(
    title="Tourism Arrivals Prediction API",
    description="MLOps-ready REST API for predicting international tourism arrivals",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "model": "ridge_regression"}


@app.get("/metrics")
def metrics():
    """Prometheus scrape endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    start = time.time()
    try:
        features = np.array([[
            request.log_tourism_receipts,
            request.log_tourism_exports,
            request.log_tourism_expenditures,
            request.log_gdp,
            request.inflation,
            request.year_norm,
            request.is_post_covid,
            request.decade,
            request.lag1_log_arrivals,
            request.lag2_log_arrivals,
            request.arrival_growth,
            request.country_enc,
        ]])

        features_scaled = scaler.transform(features)
        log_pred        = model.predict(features_scaled)[0]
        arrivals_pred   = int(np.expm1(log_pred))

        PREDICTION_COUNT.labels(status="success").inc()
        PREDICTED_VALUE.set(arrivals_pred)

        return PredictionResponse(
            log_prediction=round(float(log_pred), 4),
            predicted_arrivals=arrivals_pred,
        )

    except Exception as e:
        PREDICTION_COUNT.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        PREDICTION_LATENCY.observe(time.time() - start)
