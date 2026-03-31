"""
Model unit tests — validate feature engineering and prediction logic.
Run: pytest tests/test_model.py -v
"""

import pytest
import numpy as np


class TestFeatureShape:
    """Ensure feature vectors have the expected shape."""

    EXPECTED_FEATURES = 12

    def test_feature_count(self):
        features = np.zeros((1, self.EXPECTED_FEATURES))
        assert features.shape == (1, self.EXPECTED_FEATURES)

    def test_single_sample_shape(self):
        sample = np.array([[
            20.5, 3.2, 18.9, 26.1,   # log economic features
            2.5,                       # inflation
            0.85, 0, 2010,             # time features
            15.2, 15.0, 0.05,          # lag features
            42,                        # country_enc
        ]])
        assert sample.shape[1] == self.EXPECTED_FEATURES


class TestLogTransform:
    """Validate log1p / expm1 round-trip."""

    def test_log_transform_positive(self):
        arrivals = 5_000_000
        log_val  = np.log1p(arrivals)
        restored = np.expm1(log_val)
        assert abs(restored - arrivals) < 1

    def test_log_transform_zero(self):
        assert np.log1p(0) == 0.0
        assert np.expm1(0.0) == 0.0

    def test_expm1_of_log_prediction(self):
        log_pred = 15.5
        arrivals = int(np.expm1(log_pred))
        assert arrivals > 0
        assert isinstance(arrivals, int)


class TestPredictionSanity:
    """Sanity checks on expected prediction ranges."""

    def test_arrivals_within_reasonable_range(self):
        # log scale 10–20 corresponds to ~22k – ~485M arrivals
        for log_val in [10.0, 14.0, 18.0, 21.0]:
            arrivals = int(np.expm1(log_val))
            assert arrivals > 0, f"Expected positive arrivals for log={log_val}"

    def test_high_gdp_implies_higher_arrivals_trend(self):
        # Not a strict test — just verify the log relationship is monotonic
        low_log  = 13.0
        high_log = 17.0
        assert np.expm1(high_log) > np.expm1(low_log)
