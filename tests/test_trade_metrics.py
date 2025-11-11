# File: tests/test_trade_metrics.py
# Block 31/?? Ã¢â‚¬â€ Unit tests for TradeMath
import pytest

from services.trade_math import TradeMath


def test_pnl_calculation_long():
    tm = TradeMath()
    result = tm.realized_pnl(qty=1, entry=5000.0, exit=5010.0, pt_value=50)
    assert result == pytest.approx(500.0, rel=1e-3)


def test_pnl_calculation_short():
    tm = TradeMath()
    result = tm.realized_pnl(qty=-1, entry=5000.0, exit=4990.0, pt_value=50)
    assert result == pytest.approx(500.0, rel=1e-3)


def test_drawdown_positive_runup():
    tm = TradeMath()
    prices = [100, 105, 103, 110, 108]
    dd, ru = tm.drawdown_runup(prices)
    assert dd >= 0
    assert ru >= 0


def test_mfe_mae():
    tm = TradeMath()
    prices = [100, 104, 102, 106, 101]
    mfe, mae = tm.mfe_mae(prices, entry_price=100)
    assert mfe > 0
    assert mae >= 0


def test_expectancy():
    tm = TradeMath()
    pnl = [100, -50, 200, -100]
    result = tm.expectancy(pnl)
    assert isinstance(result, float)
