"""SpaceX IPO valuation scenarios → estimated index weights."""

from __future__ import annotations

import pandas as pd

from .config import INDEX_TOTAL_MCAP_B


def index_weight_table(valuations_b: list[int], free_float_pct: float) -> pd.DataFrame:
    """Estimated index weights for each valuation scenario.

    S&P 500 and Nasdaq 100 weight companies by float-adjusted market cap, so
    the weight uses ``valuation × free_float``.  Index totals are approximate
    constants from config (the new addition slightly grows the denominator,
    which we include).  Russell 2000 is small-cap only — SpaceX would not
    qualify at any of these valuations.
    """
    rows = []
    for v in valuations_b:
        float_cap = v * free_float_pct
        row = {"IPO Valuation": f"${v:,}B", "Float-Adj. Cap ($B)": float_cap}
        for index_name, total in INDEX_TOTAL_MCAP_B.items():
            if index_name == "Russell 2000":
                row[f"{index_name} Weight"] = float("nan")  # large-cap: not eligible
            else:
                row[f"{index_name} Weight"] = float_cap / (total + float_cap)
        rows.append(row)
    return pd.DataFrame(rows).set_index("IPO Valuation")


def rank_context(valuation_b: float) -> str:
    """Rough qualitative context for where a valuation would rank."""
    if valuation_b >= 1000:
        return "Top-10 S&P 500 constituent territory — comparable to Berkshire Hathaway or Tesla."
    if valuation_b >= 500:
        return "Top-20 S&P 500 constituent — larger than most industrial and defense majors combined."
    if valuation_b >= 300:
        return "Top-30 S&P 500 constituent — would dwarf every pure-play space company by an order of magnitude."
    return "Top-50 S&P 500 constituent — roughly the size of Lockheed Martin + Northrop Grumman."
