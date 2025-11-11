"""
tests/test_stats_calculations.py

Unit tests for Panel 3 statistics calculations.
Verifies formulas against known correct outputs.
"""

from datetime import datetime, timedelta
from typing import List
import unittest


class TestExpectancyCalculation(unittest.TestCase):
    """Test expectancy formula: (Win% × AvgWin) - (Loss% × AvgLoss)"""

    def test_expectancy_basic(self):
        """
        Test case from "Trade Your Way to Financial Freedom" by Van Tharp:
        - 5 trades: [+$500, +$300, -$200, -$100, +$400]
        - Wins: 3 trades, sum=$1200, avg=$400
        - Losses: 2 trades, sum=$300, avg=$150
        - Win rate: 60%
        - Expected: (0.6 × 400) - (0.4 × 150) = 240 - 60 = $180
        """
        from services.trade_math import TradeMath

        pnls = [500.0, 300.0, -200.0, -100.0, 400.0]
        expectancy = TradeMath.expectancy(pnls)

        self.assertAlmostEqual(expectancy, 180.0, places=2)

    def test_expectancy_all_winners(self):
        """All winning trades should have positive expectancy"""
        from services.trade_math import TradeMath

        pnls = [100.0, 200.0, 150.0, 300.0]
        expectancy = TradeMath.expectancy(pnls)

        self.assertGreater(expectancy, 0)
        self.assertAlmostEqual(expectancy, 187.5, places=2)  # Mean of wins

    def test_expectancy_all_losers(self):
        """All losing trades should have negative expectancy"""
        from services.trade_math import TradeMath

        pnls = [-100.0, -200.0, -150.0, -50.0]
        expectancy = TradeMath.expectancy(pnls)

        self.assertLess(expectancy, 0)
        self.assertAlmostEqual(expectancy, -125.0, places=2)

    def test_expectancy_empty(self):
        """Empty list should return 0"""
        from services.trade_math import TradeMath

        expectancy = TradeMath.expectancy([])
        self.assertEqual(expectancy, 0.0)


class TestDrawdownRunup(unittest.TestCase):
    """Test max drawdown and runup calculations"""

    def test_drawdown_simple(self):
        """
        Equity curve: [100, 150, 120, 180, 160]
        Algorithm tracks running peak/trough:
        - At 150: peak=150
        - At 120: DD from peak 150 = 150-120 = 30
        - At 180: peak=180, RU from trough 100 = 180-100 = 80
        - At 160: DD from peak 180 = 180-160 = 20 (but max DD is still 30)
        """
        from services.trade_math import TradeMath

        equity = [100, 150, 120, 180, 160]
        max_dd, max_ru = TradeMath.drawdown_runup(equity)

        self.assertAlmostEqual(max_dd, 30.0, places=2)  # 150 - 120 (largest drawdown from a peak)
        self.assertAlmostEqual(max_ru, 80.0, places=2)  # 180 - 100 (largest runup from a trough)

    def test_drawdown_monotonic_up(self):
        """Monotonically increasing equity should have no drawdown"""
        from services.trade_math import TradeMath

        equity = [100, 150, 200, 300, 500]
        max_dd, max_ru = TradeMath.drawdown_runup(equity)

        self.assertEqual(max_dd, 0.0)
        self.assertEqual(max_ru, 400.0)  # 500 - 100

    def test_drawdown_monotonic_down(self):
        """Monotonically decreasing equity should have no runup"""
        from services.trade_math import TradeMath

        equity = [500, 400, 300, 200, 100]
        max_dd, max_ru = TradeMath.drawdown_runup(equity)

        self.assertEqual(max_dd, 400.0)  # 500 - 100
        self.assertEqual(max_ru, 0.0)


class TestEquityCurveSlope(unittest.TestCase):
    """Test linear regression slope calculation"""

    def test_slope_positive_trend(self):
        """
        Perfect uptrend: equity = [100, 200, 300, 400, 500]
        Slope should be exactly 100 per trade
        """
        eq = [100, 200, 300, 400, 500]
        n = len(eq)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(eq) / n
        numerator = sum((x[i] - x_mean) * (eq[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator

        self.assertAlmostEqual(slope, 100.0, places=2)

    def test_slope_negative_trend(self):
        """
        Perfect downtrend: equity = [500, 400, 300, 200, 100]
        Slope should be exactly -100 per trade
        """
        eq = [500, 400, 300, 200, 100]
        n = len(eq)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(eq) / n
        numerator = sum((x[i] - x_mean) * (eq[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator

        self.assertAlmostEqual(slope, -100.0, places=2)

    def test_slope_flat(self):
        """Flat equity curve should have slope near 0"""
        eq = [100, 100, 100, 100, 100]
        n = len(eq)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(eq) / n
        numerator = sum((x[i] - x_mean) * (eq[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0.0

        self.assertAlmostEqual(slope, 0.0, places=2)


class TestProfitFactor(unittest.TestCase):
    """Test profit factor: Gross profit / Gross loss"""

    def test_profit_factor_basic(self):
        """
        Wins: [300, 200, 500] = 1000
        Losses: [-100, -150] = 250
        PF: 1000 / 250 = 4.0
        """
        pnls = [300, 200, -100, 500, -150]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        sum_w = sum(wins)
        sum_l = abs(sum(losses))
        pf = sum_w / sum_l if sum_l > 0 else None

        self.assertAlmostEqual(pf, 4.0, places=2)

    def test_profit_factor_no_losses(self):
        """All winners should have undefined PF (or infinity)"""
        pnls = [100, 200, 300]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        sum_w = sum(wins)
        sum_l = abs(sum(losses))
        pf = sum_w / sum_l if sum_l > 0 else None

        self.assertIsNone(pf)  # Undefined (infinity)


class TestStreakCalculation(unittest.TestCase):
    """Test max consecutive win/loss streak"""

    def test_streak_simple(self):
        """
        PnLs: [+100, +200, -50, -30, -20, +150, +80, +90, -40]
        Max win streak: 3 (trades 6-8)
        Max loss streak: 3 (trades 3-5)
        """
        pnls = [100, 200, -50, -30, -20, 150, 80, 90, -40]

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

        self.assertEqual(max_w, 3)
        self.assertEqual(max_l, 3)


class TestMAEMFE(unittest.TestCase):
    """Test MAE/MFE calculation"""

    def test_mfe_mae_long(self):
        """
        Long trade entry at 100
        Prices: [100, 105, 98, 110, 95, 102]
        MFE: 110 - 100 = 10 (max favorable)
        MAE: 95 - 100 = -5, so MAE = 5 (max adverse, absolute)
        """
        from services.trade_math import TradeMath

        prices = [100, 105, 98, 110, 95, 102]
        entry = 100
        mfe, mae = TradeMath.mfe_mae(prices, entry)

        self.assertAlmostEqual(mfe, 10.0, places=2)
        self.assertAlmostEqual(mae, 5.0, places=2)


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
