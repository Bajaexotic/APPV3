def efficiency_ratio(mae_pts: float, mfe_pts: float) -> float:
    denom = mfe_pts + abs(mae_pts)
    return (mfe_pts / denom) if denom > 1e-9 else 0.0


def rr_to_target(total_target_pts: float | None, risk_pts: float | None):
    if total_target_pts is None or risk_pts is None or risk_pts <= 0:
        return None
    return total_target_pts / risk_pts
