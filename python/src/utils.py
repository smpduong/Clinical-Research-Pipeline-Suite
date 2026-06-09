"""
utils.py - Shared utility functions for the Clinical Research Pipeline Suite.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple


def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """
    Compute Cohen's d effect size.

    Args:
        group1: Array of values for group 1
        group2: Array of values for group 2

    Returns:
        Cohen's d (standardized mean difference)
    """
    n1, n2 = len(group1), len(group2)
    pooled_std = np.sqrt(((n1 - 1) * np.var(group1, ddof=1) + 
                          (n2 - 1) * np.var(group2, ddof=1)) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def classify_effect_size(d: float) -> str:
    """Classify Cohen's d into small/medium/large per Cohen (1988)."""
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"


def wide_to_long(df: pd.DataFrame, id_cols: List[str], 
                 time_col: str, value_cols: List[str],
                 time_mapping: Optional[Dict] = None) -> pd.DataFrame:
    """
    Convert wide-format longitudinal data to long format.

    Args:
        df: Wide-format DataFrame
        id_cols: Columns that identify the subject
        time_col: Name for the new time variable
        value_cols: Base names of columns to pivot (e.g., ['score_1', 'score_2'])
        time_mapping: Optional mapping of suffixes to time values

    Returns:
        Long-format DataFrame
    """
    long_data = []
    for _, row in df.iterrows():
        for col in value_cols:
            if col in row.index and pd.notna(row[col]):
                time_val = time_mapping.get(col, col) if time_mapping else col
                entry = {id_col: row[id_col] for id_col in id_cols}
                entry[time_col] = time_val
                entry['value'] = row[col]
                long_data.append(entry)
    return pd.DataFrame(long_data)
