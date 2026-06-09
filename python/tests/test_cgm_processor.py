"""
test_cgm_processor.py - Unit tests for CGM processing module
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.cgm_processor import UnifiedCGMProcessor


class TestUnifiedCGMProcessor:

    @pytest.fixture
    def processor(self):
        return UnifiedCGMProcessor()

    @pytest.fixture
    def sample_cgm_data(self):
        """Generate synthetic CGM data for testing."""
        timestamps = pd.date_range(start='2026-01-01', periods=288, freq='5min')
        glucose = 120 + 20 * np.sin(np.linspace(0, 2*np.pi, 288)) + np.random.normal(0, 10, 288)
        return pd.DataFrame({
            'timestamp': timestamps,
            'glucose_mgdl': glucose,
            'device_type': 'dexcom_g7'
        })

    def test_standardize_creates_required_columns(self, processor):
        raw = pd.DataFrame({
            'timestamp_raw': ['2026-01-01 08:00', '2026-01-01 08:05'],
            'glucose_raw': ['120', '125'],
            'device_type': 'dexcom_g7'
        })
        result = processor._standardize(raw, 'dexcom_g7')
        assert 'timestamp' in result.columns
        assert 'glucose_mgdl' in result.columns
        assert result['glucose_mgdl'].dtype == np.float64

    def test_qc_flags_impossible_values(self, processor):
        df = pd.DataFrame({
            'timestamp': pd.date_range('2026-01-01', periods=5, freq='5min'),
            'glucose_mgdl': [120.0, 500.0, 30.0, 150.0, 150.0],
            'device_type': 'dexcom_g7'
        })
        result = processor._apply_qc(df)
        # 500 and 30 should be removed (impossible)
        assert len(result) == 3
        assert all(result['glucose_mgdl'] < 400)
        assert all(result['glucose_mgdl'] > 40)

    def test_qc_removes_duplicates(self, processor):
        ts = pd.Timestamp('2026-01-01 08:00')
        df = pd.DataFrame({
            'timestamp': [ts, ts, ts + timedelta(minutes=5)],
            'glucose_mgdl': [120.0, 121.0, 125.0],
            'device_type': 'dexcom_g7'
        })
        result = processor._apply_qc(df)
        assert len(result) == 2

    def test_gap_filling_interpolates_small_gaps(self, processor):
        timestamps = [datetime(2026, 1, 1, 8, 0), 
                     datetime(2026, 1, 1, 8, 15),  # 15 min gap
                     datetime(2026, 1, 1, 8, 20)]
        df = pd.DataFrame({
            'timestamp': timestamps,
            'glucose_mgdl': [120.0, np.nan, 130.0],
            'device_type': 'dexcom_g7'
        })
        result = processor._fill_gaps(df, max_gap_min=15)
        # Should interpolate the middle value
        assert len(result) == 3
        assert result['glucose_mgdl'].isna().sum() == 0

    def test_gap_filling_flags_large_gaps(self, processor):
        timestamps = [datetime(2026, 1, 1, 8, 0), 
                     datetime(2026, 1, 1, 9, 0),  # 60 min gap
                     datetime(2026, 1, 1, 9, 5)]
        df = pd.DataFrame({
            'timestamp': timestamps,
            'glucose_mgdl': [120.0, np.nan, 130.0],
            'device_type': 'dexcom_g7'
        })
        result = processor._fill_gaps(df, max_gap_min=15)
        # Large gap should not be filled
        assert result['gap_flag'].iloc[1] == True

    def test_compute_metrics_returns_all_keys(self, processor, sample_cgm_data):
        metrics = processor.compute_metrics(sample_cgm_data)
        required_keys = ['n_readings', 'mean_glucose', 'sd_glucose', 'cv', 
                        'tir', 'gmi', 'gri', 'mage']
        for key in required_keys:
            assert key in metrics, f"Missing key: {key}"

    def test_compute_metrics_tir_range(self, processor):
        df = pd.DataFrame({
            'timestamp': pd.date_range('2026-01-01', periods=10, freq='5min'),
            'glucose_mgdl': [60, 70, 100, 120, 150, 180, 190, 200, 250, 300],
            'device_type': 'dexcom_g7'
        })
        metrics = processor.compute_metrics(df)
        # 70-180: 100, 120, 150, 180 = 4/10 = 40%
        assert metrics['tir'] == 40.0
        assert metrics['tbr'] == 10.0  # <70: 60
        assert metrics['tar'] == 50.0  # >180: 190, 200, 250, 300

    def test_compute_metrics_gmi_formula(self, processor):
        df = pd.DataFrame({
            'timestamp': pd.date_range('2026-01-01', periods=10, freq='5min'),
            'glucose_mgdl': [154.0] * 10,
            'device_type': 'dexcom_g7'
        })
        metrics = processor.compute_metrics(df)
        # GMI = 3.31 + 0.02392 * 154 = 6.99
        assert abs(metrics['gmi'] - 7.0) < 0.1

    def test_unsupported_device_raises_error(self, processor):
        with pytest.raises(ValueError, match="Unsupported device"):
            processor.process("dummy.csv", "unsupported_device")


class TestCGMQualityFlags:

    def test_default_flags_are_false(self):
        flags = CGMQualityFlags()
        assert flags.impossible == False
        assert flags.hypoglycemia == False
        assert flags.hyperglycemia == False
        assert flags.missing == False
        assert flags.duplicate == False
