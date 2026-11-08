# risk_metrics.py
from __future__ import annotations
from typing import Tuple, Optional

def ttc(gap_m: float, vf: float, vl: float) -> Optional[float]:
    """
    Time-To-Collision (s) for follower vs leader (1D).
    Returns None if no collision trajectory (vf <= vl or gap <= 0).
    """
    if vf <= vl or gap_m <= 0:
        return None
    rel = vf - vl
    return gap_m / rel if rel > 1e-3 else None

