"""
API integration tests using FastAPI TestClient.
Run: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import numpy as np


# ── Mock model loading so tests don't need .pkl files ─────────
@pytest.fixture(autouse=True, scope="session")
def mock_models():
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([15.5])

    mock_scaler = MagicMock()
    mock_scaler.transform.side_effect = lambda x: x

    mock_encoder = MagicMock()

    with patch.dict("sys.modules", {}):
        with patch("joblib.load", side_effect=[mock_model, mock_scaler, mock_encoder]):
            from app.main import app
            yield app


@pytest.fixture(scope="session")
def client(mock_models):
    return TestClient(mock_models)


VALID_PAYLOAD = {
    "log_tourism_receipts":     20.5,
    "log_tourism_exports":      3.2,
    "log_tourism_expenditures": 18.9,
    "log_gdp":                  26.1,
    "inflation":                2.5,
    "year_norm":                0.85,
    "is_post_covid":            0,
    "decade":                   2010,
    "lag1_log_arrivals":        15.2,
    "lag2_log_arrivals":        15.0,
    "arrival_growth":           0.05,
    "country_enc":              42,
}


class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_body(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert "model" in data


class TestMetrics:
    def test_metrics_endpoint_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_content_type(self, client):
        resp = client.get("/metrics")
        assert "text/plain" in resp.headers["content-type"]

    def test_metrics_contains_prediction_counter(self, client):
        resp = client.get("/metrics")
        assert "prediction_requests_total" in resp.text


class TestPredict:
    def test_predict_valid_input(self, client):
        resp = client.post("/predict", json=VALID_PAYLOAD)
        assert resp.status_code == 200

    def test_predict_response_fields(self, client):
        resp = client.post("/predict", json=VALID_PAYLOAD)
        data = resp.json()
        assert "log_prediction" in data
        assert "predicted_arrivals" in data

    def test_predict_arrivals_is_positive(self, client):
        resp = client.post("/predict", json=VALID_PAYLOAD)
        assert resp.json()["predicted_arrivals"] >= 0

    def test_predict_missing_field_returns_422(self, client):
        bad_payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "log_gdp"}
        resp = client.post("/predict", json=bad_payload)
        assert resp.status_code == 422

    def test_predict_wrong_type_returns_422(self, client):
        bad_payload = {**VALID_PAYLOAD, "inflation": "not-a-number"}
        resp = client.post("/predict", json=bad_payload)
        assert resp.status_code == 422
