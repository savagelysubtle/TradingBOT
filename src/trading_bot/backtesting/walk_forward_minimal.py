"""Minimal walk-forward optimization functions for strategy validation."""

import logging

import numpy as np
import pandas as pd
from typing import List, Tuple

logger = logging.getLogger(__name__)


def split_walk_forward(
    data: pd.DataFrame,
    in_sample_pct: float = 0.70,
    out_of_sample_pct: float = 0.30,
    num_periods: int = 5,
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """Split data into rolling train/test windows for walk-forward analysis.

    Args:
        data: Historical OHLCV data (must be sorted by date)
        in_sample_pct: Percentage for training (0.70 = 70%)
        out_of_sample_pct: Percentage for testing (0.30 = 30%)
        num_periods: Number of walk-forward iterations

    Returns:
        List of (in_sample, out_of_sample) tuples

    Example:
        >>> splits = split_walk_forward(data, num_periods=5)
        >>> for is_data, oos_data in splits:
        >>>     print(f"Train: {len(is_data)} bars, Test: {len(oos_data)} bars")
    """
    total_bars = len(data)
    in_sample_len = int(total_bars * in_sample_pct)
    out_of_sample_len = int(total_bars * out_of_sample_pct)

    step_size = out_of_sample_len  # Roll forward by OOS length

    splits = []
    start_idx = 0

    for _ in range(num_periods):
        is_end = start_idx + in_sample_len
        oos_end = is_end + out_of_sample_len

        if oos_end > total_bars:
            break

        is_data = data.iloc[start_idx:is_end].copy()
        oos_data = data.iloc[is_end:oos_end].copy()

        splits.append((is_data, oos_data))

        # Roll forward by OOS length
        start_idx += step_size

    return splits


def calculate_wfe(
    in_sample_return: float,
    out_of_sample_return: float,
) -> float:
    """Calculate Walk Forward Efficiency.

    WFE = Out-of-Sample Return / In-Sample Return

    Interpretation:
    - WFE > 60%: Strategy not overfitted ✓
    - WFE 50-60%: Borderline
    - WFE < 50%: Likely overfitted ✗

    Args:
        in_sample_return: Return from in-sample (optimization) period
        out_of_sample_return: Return from out-of-sample (validation) period

    Returns:
        Walk Forward Efficiency as decimal (0.0-1.0+)
    """
    if in_sample_return <= 0:
        return 0.0
    return out_of_sample_return / in_sample_return


def wfe_status(wfe: float) -> str:
    """Determine if strategy is overfitted based on WFE.

    Args:
        wfe: Walk Forward Efficiency

    Returns:
        Status string: "ACCEPTABLE", "BORDERLINE", "OVERFITTED", or "SEVERELY_OVERFITTED"
    """
    if wfe >= 0.60:
        return "ACCEPTABLE"
    elif wfe >= 0.50:
        return "BORDERLINE"
    elif wfe >= 0.25:
        return "OVERFITTED"
    else:
        return "SEVERELY_OVERFITTED"

