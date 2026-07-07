"""
cgm_processor.py - Unified CGM Data Processing Module

Device-agnostic parser for continuous glucose monitor (CGM) data.
Supports Dexcom G6/G7, FreeStyle Libre 2/3, and Medtronic sensors.

Usage:
    from src.cgm_processor import UnifiedCGMProcessor
    processor = UnifiedCGMProcessor()
    df = processor.process("data.csv", device_type="dexcom_g7")
    metrics = processor.compute_metrics(df)
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CGMQualityFlags:
    """Quality control flags for CGM readings."""

    impossible: bool = False  # < 40 or > 400 mg/dL
    hypoglycemia: bool = False  # < 70 mg/dL
    hyperglycemia: bool = False  # > 180 mg/dL
    missing: bool = False  # Gap > 15 min
    duplicate: bool = False  # Same timestamp


class UnifiedCGMProcessor:
    """
    Process CGM data from any major device.

    Implements the Adapter pattern: each device type has a specific parser
    that converts proprietary formats to a unified schema.
    """

    SUPPORTED_DEVICES = ["dexcom_g7", "dexcom_g6", "libre_3", "libre_2", "medtronic_g4"]
    ISF_CORRECTION = 1.0  # Interstitial-to-plasma conversion placeholder

    def __init__(self):
        self.time_in_range_low = 70
        self.time_in_range_high = 180
        self.time_in_tight_range_low = 70
        self.time_in_tight_range_high = 140

    def process(self, csv_path: str, device_type: str) -> pd.DataFrame:
        """Main entry point: parse, standardize, QC, gap-fill."""
        if device_type not in self.SUPPORTED_DEVICES:
            raise ValueError(
                f"Unsupported device: {device_type}. Use: {self.SUPPORTED_DEVICES}"
            )

        parser = getattr(self, f"_parse_{device_type}")
        raw = parser(csv_path)
        standardized = self._standardize(raw, device_type)
        qc = self._apply_qc(standardized)
        filled = self._fill_gaps(qc)
        return filled

    def _parse_dexcom_g7(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df = df.rename(
            columns={
                "Timestamp": "timestamp_raw",
                "Glucose Value (mg/dL)": "glucose_raw",
                "Transmitter Time": "transmitter_time",
            }
        )
        df["device_type"] = "dexcom_g7"
        return df

    def _parse_dexcom_g6(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df = df.rename(
            columns={
                "Timestamp": "timestamp_raw",
                "Glucose Value (mg/dL)": "glucose_raw",
            }
        )
        df["device_type"] = "dexcom_g6"
        return df

    def _parse_libre_3(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path, skiprows=1)
        df = df.rename(
            columns={
                "Device Timestamp": "timestamp_raw",
                "Historic Glucose (mg/dL)": "glucose_raw",
            }
        )
        df["device_type"] = "libre_3"
        return df

    def _parse_libre_2(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path, skiprows=1)
        df = df.rename(
            columns={
                "Device Timestamp": "timestamp_raw",
                "Historic Glucose (mg/dL)": "glucose_raw",
            }
        )
        df["device_type"] = "libre_2"
        return df

    def _parse_medtronic_g4(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df = df.rename(
            columns={"Date": "timestamp_raw", "Sensor Glucose (mg/dL)": "glucose_raw"}
        )
        df["device_type"] = "medtronic_g4"
        return df

    def _standardize(self, df: pd.DataFrame, device_type: str) -> pd.DataFrame:
        """Standardize to unified schema: timestamp, glucose_mgdl, device_type."""
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp_raw"], errors="coerce")
        df["glucose_mgdl"] = pd.to_numeric(df["glucose_raw"], errors="coerce").astype(
            float
        )

        if device_type in ["libre_2", "libre_3"]:
            df["glucose_mgdl"] = df["glucose_mgdl"] * self.ISF_CORRECTION

        df = df.sort_values("timestamp").reset_index(drop=True)
        return df[["timestamp", "glucose_mgdl", "device_type"]].copy()

    def _apply_qc(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply clinical quality control flags.

        Flags:
        - impossible: <40 or >400 mg/dL (sensor error or detached)
        - duplicate: same timestamp (double export)
        - out_of_target: physiologically possible but outside 70-180
        """
        df = df.copy()
        df["qc_flag"] = "valid"

        impossible = (df["glucose_mgdl"] < 40) | (df["glucose_mgdl"] > 400)
        df.loc[impossible, "qc_flag"] = "impossible"

        oot = ((df["glucose_mgdl"] < 70) | (df["glucose_mgdl"] > 180)) & ~impossible
        df.loc[oot, "qc_flag"] = "out_of_target"

        dupes = df.duplicated(subset=["timestamp"], keep="first")
        df.loc[dupes, "qc_flag"] = "duplicate"

        # Remove impossible and duplicates before analysis
        df = df[~df["qc_flag"].isin(["impossible", "duplicate"])].copy()
        return df

    def _fill_gaps(self, df: pd.DataFrame, max_gap_min: int = 15) -> pd.DataFrame:
        """
        Linear interpolation for gaps <= max_gap_min.

        Rationale: Small gaps (e.g., swimming, temporary sensor removal) can be
        reasonably interpolated. Large gaps indicate extended sensor disconnection
        and should be flagged, not filled, to avoid fabricating data across an
        extended dropout.

        Each reading whose preceding interval exceeds ``max_gap_min`` starts a new
        segment; interpolation is performed within segments only, so values are
        never carried across a long gap.
        """
        df = df.copy().sort_values("timestamp").reset_index(drop=True)

        df["gap_minutes"] = df["timestamp"].diff().dt.total_seconds() / 60
        df["gap_flag"] = (df["gap_minutes"] > max_gap_min).fillna(False)

        segment = df["gap_flag"].cumsum()
        df["glucose_mgdl"] = df.groupby(segment)["glucose_mgdl"].transform(
            lambda s: s.interpolate(method="linear", limit_direction="both")
        )
        return df

    def compute_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute comprehensive glycemic metrics per ADA standards.

        Metrics:
        - TIR: Time in Range (70-180 mg/dL), ADA target >70%
        - GMI: Glucose Management Indicator (HbA1c equivalent)
        - GRI: Glycemic Risk Index (composite of lows and highs)
        - CV: Coefficient of Variation (glucose stability)
        - MAGE: Mean Amplitude of Glycemic Excursions
        """
        glucose = df["glucose_mgdl"]
        n = len(glucose)

        if n == 0:
            return {}

        mean_glucose = glucose.mean()
        sd_glucose = glucose.std()
        cv = (sd_glucose / mean_glucose) * 100 if mean_glucose > 0 else 0

        in_range = (glucose >= self.time_in_range_low) & (
            glucose <= self.time_in_range_high
        )
        tir = in_range.mean() * 100

        in_tight = (glucose >= self.time_in_tight_range_low) & (
            glucose <= self.time_in_tight_range_high
        )
        titr = in_tight.mean() * 100

        tbr = (glucose < 70).mean() * 100
        tar = (glucose > 180).mean() * 100
        tvr = (glucose > 250).mean() * 100

        gmi = 3.31 + (0.02392 * mean_glucose)
        gri = (3.0 * tbr) + (1.6 * tar)
        mage = self._calculate_mage(glucose)
        conga = self._calculate_conga(df)

        total_days = (df["timestamp"].max() - df["timestamp"].min()).days + 1
        expected_readings = total_days * 288
        wear_time = (n / expected_readings) * 100 if expected_readings > 0 else 0

        return {
            "n_readings": n,
            "total_days": total_days,
            "wear_time_pct": round(wear_time, 1),
            "mean_glucose": round(mean_glucose, 1),
            "sd_glucose": round(sd_glucose, 1),
            "cv": round(cv, 1),
            "cv_category": "Stable" if cv < 36 else "Unstable",
            "tir": round(tir, 1),
            "titr": round(titr, 1),
            "tbr": round(tbr, 1),
            "tar": round(tar, 1),
            "tvr": round(tvr, 1),
            "gmi": round(gmi, 1),
            "gri": round(gri, 1),
            "mage": round(mage, 1),
            "conga": round(conga, 1) if conga else None,
        }

    def _calculate_mage(self, glucose: pd.Series) -> float:
        """Mean Amplitude of Glycemic Excursions (simplified)."""
        sd_g = glucose.std()
        excursions = glucose.diff().abs().dropna()
        mage = excursions[excursions > sd_g].mean()
        return mage if not pd.isna(mage) else 0.0

    def _calculate_conga(self, df: pd.DataFrame) -> Optional[float]:
        """Continuous Overall Net Glycemic Action (1-hour)."""
        df = df.copy().set_index("timestamp").sort_index()
        hourly = df["glucose_mgdl"].resample("1h").mean().dropna()
        if len(hourly) < 2:
            return None
        diffs = hourly.diff().abs().dropna()
        return diffs.std() if len(diffs) > 0 else None
