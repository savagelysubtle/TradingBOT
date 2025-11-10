"""Reporting and visualization for walk-forward optimization results."""

import logging
from typing import Any, Dict

import pandas as pd

from trading_bot.backtesting.walk_forward_minimal import calculate_wfe

logger = logging.getLogger(__name__)


def print_wfo_report(results: Dict[str, Any]) -> str:
    """Generate formatted WFO report.

    Args:
        results: WFO results dictionary from WalkForwardBacktester

    Returns:
        Formatted report string
    """
    overall = results["overall"]

    report = f"""
╔══════════════════════════════════════════════════════════════╗
║     WALK-FORWARD OPTIMIZATION REPORT                         ║
╚══════════════════════════════════════════════════════════════╝

OVERALL METRICS
{'─'*60}
Walk Forward Efficiency (WFE):  {overall['wfe']:.1%}
Status:                         {overall['status']}
Number of Periods:              {overall['num_periods']}

PERFORMANCE
{'─'*60}
Avg In-Sample Return:           {overall['avg_in_sample_return']:+.2%}
Avg Out-of-Sample Return:       {overall['avg_out_of_sample_return']:+.2%}
Degradation:                    {1 - overall['wfe']:.1%}

PARAMETER STABILITY
{'─'*60}
Avg Parameter Changes:          {overall.get('avg_parameter_changes', 0):.1f}
(Higher = less stable parameters)

PERIOD-BY-PERIOD BREAKDOWN
{'─'*60}
"""

    for i, (is_ret, oos_ret) in enumerate(
        zip(results["in_sample_returns"], results["out_of_sample_returns"]), 1
    ):
        period_wfe = calculate_wfe(is_ret, oos_ret)
        report += f"Period {i}: IS={is_ret:+.2%}, OOS={oos_ret:+.2%}, WFE={period_wfe:.1%}\n"

    report += f"\n{'═'*60}\n"

    return report


def create_wfo_comparison_table(results: Dict[str, Any]) -> pd.DataFrame:
    """Create comparison table for TUI display.

    Args:
        results: WFO results dictionary

    Returns:
        DataFrame with period-by-period comparison
    """
    df = pd.DataFrame(
        {
            "Period": range(1, results["overall"]["num_periods"] + 1),
            "In-Sample": results["in_sample_returns"],
            "Out-of-Sample": results["out_of_sample_returns"],
            "WFE": [
                calculate_wfe(is_r, oos_r)
                for is_r, oos_r in zip(
                    results["in_sample_returns"],
                    results["out_of_sample_returns"],
                )
            ],
        }
    )

    # Format as percentages for display
    df["In-Sample"] = df["In-Sample"].apply(lambda x: f"{x:+.2%}")
    df["Out-of-Sample"] = df["Out-of-Sample"].apply(lambda x: f"{x:+.2%}")
    df["WFE"] = df["WFE"].apply(lambda x: f"{x:.1%}")

    return df


