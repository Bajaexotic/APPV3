"""
services/stats_service.py

Panel 3 trading statistics calculator.
Computes comprehensive metrics from closed trades in the database.

Metrics Calculated:
- Total PnL: Sum of all realized P&Ls
- Max Drawdown: Largest peak-to-trough decline in equity curve
- Max Run-Up: Largest trough-to-peak gain in equity curve
- Expectancy: (Win% × AvgWin) - (Loss% × AvgLoss)
- Avg Time: Average duration per trade (h:m:s format)
- Trades: Total trade count
- Best/Worst: Highest profit and worst loss
- Hit Rate: Win percentage
- Commissions: Total commissions paid
- Avg R: Average R-multiple per trade
- Profit Factor: Gross profit / Gross loss
- Streak: Max consecutive wins/losses (W/L format)
- MAE: Average Maximum Adverse Excursion
- MFE: Average Maximum Favorable Excursion
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple


def _timeframe_start(tf: str, now: datetime | None = None) -> datetime:
    now = now or datetime.utcnow()
    t = tf.upper()
    if t == "1D":
        return now - timedelta(days=1)
    if t == "1W":
        return now - timedelta(weeks=1)
    if t == "1M":
        return now - timedelta(days=30)
    if t == "3M":
        return now - timedelta(days=90)
    # YTD
    return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def compute_trading_stats_for_timeframe(tf: str, mode: str | None = None) -> dict[str, Any]:
    """Compute Panel 3 stats for the given timeframe using DB trades.

    Args:
        tf: Timeframe ("1D", "1W", "1M", "3M", "YTD")
        mode: Filter by mode ("SIM", "LIVE", or None for all)

    Returns a dict keyed by PANEL3_METRICS friendly labels.
    Uses TradeRecord.exit_time when present; falls back to timestamp.
    """
    print(f"\n[DEBUG STATS] compute_trading_stats_for_timeframe() called:")
    print(f"  timeframe={tf}, mode={mode}")

    # Local imports to avoid hard dependency at import time
    try:
        import statistics as stats

        from data.db_engine import get_session
        from data.schema import TradeRecord
        from services.trade_math import TradeMath
        print(f"[DEBUG STATS] ✓ Imports successful")
    except Exception as e:
        print(f"[DEBUG STATS] ✗ Import failed: {e}")
        return {}

    start = _timeframe_start(tf)
    print(f"[DEBUG STATS] Querying trades from {start.isoformat()}")

    # Get active mode from state manager if not provided
    if mode is None:
        try:
            from core.app_state import get_state_manager
            state = get_state_manager()
            # Use position_mode if there's an active position, otherwise current_mode
            mode = state.position_mode if state and state.has_active_position() else (state.current_mode if state else "SIM")
            print(f"[DEBUG STATS] Mode detected from state: {mode}")
        except Exception as e:
            mode = "SIM"  # Default fallback
            print(f"[DEBUG STATS] Mode detection failed, using default: {mode}")

    print(f"[DEBUG STATS] Final mode filter: {mode}")

    pnls: list[float] = []
    commissions_sum = 0.0
    r_mults: list[float] = []
    durations: list[float] = []
    mae_list: list[float] = []
    mfe_list: list[float] = []

    print(f"[DEBUG STATS] Opening database session...")
    with get_session() as s:  # type: ignore
        time_field = getattr(TradeRecord, "exit_time", None) or getattr(TradeRecord, "timestamp")
        query = (
            s.query(TradeRecord)
            .filter(TradeRecord.realized_pnl.isnot(None))
            .filter(time_field >= start)
        )

        # Filter by mode if provided
        if mode:
            query = query.filter(TradeRecord.mode == mode)

        rows = query.order_by(time_field.asc()).all()
        print(f"[DEBUG STATS] Found {len(rows)} trades in database for {tf} / mode={mode}")

        if not rows:
            print(f"[DEBUG STATS] ⚠ No trades found! Returning empty stats")

        for idx, r in enumerate(rows, 1):
            print(f"[DEBUG STATS] Trade {idx}: {r.symbol} | PnL={r.realized_pnl} | Exit={r.exit_time}")
            if r.realized_pnl is not None:
                pnls.append(float(r.realized_pnl))
                print(f"  → Added to PnL list: {r.realized_pnl}")
            if getattr(r, "commissions", None) is not None:
                commissions_sum += float(r.commissions)
            if getattr(r, "r_multiple", None) is not None:
                r_mults.append(float(r.r_multiple))
            if getattr(r, "entry_time", None) and getattr(r, "exit_time", None):
                with contextlib.suppress(Exception):
                    durations.append((r.exit_time - r.entry_time).total_seconds())
            if getattr(r, "mae", None) is not None:
                mae_list.append(float(r.mae))
            if getattr(r, "mfe", None) is not None:
                mfe_list.append(float(r.mfe))

    print(f"\n[DEBUG STATS] ✓ Database query complete")
    print(f"  Total PnL values collected: {len(pnls)}")
    print(f"  PnL list: {pnls}")

    total = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    sum_w = sum(wins)
    sum_l = abs(sum(losses))
    hit_rate = (len(wins) / total * 100.0) if total else 0.0
    pf = (sum_w / sum_l) if sum_l > 0 else None

    # Expectancy using proper formula: (Win% × AvgWin) - (Loss% × AvgLoss)
    expectancy = TradeMath.expectancy(pnls) if pnls else 0.0

    # Sharpe Ratio (for sharpe bar widget only, not displayed in grid)
    try:
        sharpe = (stats.mean(pnls) / (stats.pstdev(pnls) or 1.0)) if pnls else 0.0
    except Exception:
        sharpe = 0.0

    # Equity series for DD/Run-up
    eq: list[float] = []
    acc = 0.0
    for p in pnls:
        acc += p
        eq.append(acc)
    max_dd, max_ru = TradeMath.drawdown_runup(eq) if eq else (0.0, 0.0)

    # Streaks (W/L)
    max_w, max_l, cur_w, cur_l = 0, 0, 0, 0
    for v in pnls:
        if v > 0:
            cur_w += 1
            cur_l = 0
        elif v < 0:
            cur_l += 1
            cur_w = 0
        else:
            cur_w = 0
            cur_l = 0
        max_w = max(max_w, cur_w)
        max_l = max(max_l, cur_l)

    # Aggregates
    total_pnl = sum(pnls) if pnls else 0.0
    avg_r = (sum(r_mults) / len(r_mults)) if r_mults else None
    avg_time_str = "-"
    if durations:
        avg_sec = sum(durations) / len(durations)
        h = int(avg_sec // 3600)
        m = int((avg_sec % 3600) // 60)
        s = int(avg_sec % 60)
        avg_time_str = f"{h:d}h {m:02d}m {s:02d}s" if h else f"{m:d}m {s:02d}s"

    mae_avg = (sum(mae_list) / len(mae_list)) if mae_list else None
    mfe_avg = (sum(mfe_list) / len(mfe_list)) if mfe_list else None

    print(f"\n[DEBUG STATS] Calculation Summary:")
    print(f"  Total PnL: {total_pnl}")
    print(f"  Wins: {len(wins)} trades = ${sum_w:,.2f}")
    print(f"  Losses: {len(losses)} trades = ${sum_l:,.2f}")
    print(f"  Hit Rate: {hit_rate:.1f}%")
    print(f"  Max Drawdown: {max_dd:.2f}")
    print(f"  Max Run-Up: {max_ru:.2f}")
    print(f"  Expectancy: {expectancy:.2f}")
    print(f"  Profit Factor: {pf if pf else 'N/A'}")

    result_dict = {
        "Total PnL": f"{total_pnl:.2f}",
        "Max Drawdown": f"{-max_dd:.2f}",
        "Max Run-Up": f"{max_ru:.2f}",
        "Expectancy": f"{expectancy:.2f}",
        "Avg Time": avg_time_str,
        "Trades": str(total),
        "Best": f"{(max(pnls) if pnls else 0.0):.2f}",
        "Worst": f"{(min(pnls) if pnls else 0.0):.2f}",
        "Hit Rate": f"{hit_rate:.1f}%",
        "Commissions": f"{commissions_sum:.2f}" if commissions_sum else "-",
        "Avg R": f"{avg_r:.2f}" if avg_r is not None else "-",
        "Profit Factor": f"{pf:.2f}" if pf is not None else "-",
        "Streak": f"W{max_w}/L{max_l}",
        "MAE": f"{mae_avg:.2f}" if mae_avg is not None else "-",
        "MFE": f"{mfe_avg:.2f}" if mfe_avg is not None else "-",
        # Helper: sign for coloring
        "_total_pnl_value": total_pnl,
        "_trade_count": total,  # For empty state detection
        # Sharpe Ratio for sharpe bar widget (not displayed in grid)
        "Sharpe Ratio": f"{sharpe:.2f}",
    }

    print(f"\n[DEBUG STATS] ✓ Stats calculation complete, returning {len(result_dict)} metrics")
    print(f"  Total PnL (formatted): {result_dict.get('Total PnL')}")
    print(f"  Trade Count: {result_dict.get('Trades')}")
    print(f"\n{'='*80}\n")

    return result_dict
