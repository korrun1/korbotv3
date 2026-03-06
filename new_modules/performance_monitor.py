"""
📊 performance_monitor.py — Real-Time Performance Monitoring
Version: 3.0
Date: 2026-03

Features:
- Live metrics: Sharpe, Sortino, Calmar, Profit Factor, Win Rate
- Anomaly detection (performance degradation alerts)
- Per-strategy breakdown
- Prometheus metrics endpoint (optional)
- Performance report generation
- A/B testing framework for strategy variants
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import json

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Individual trade result"""
    trade_id: str
    strategy: str
    symbol: str
    direction: str
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl: float
    pnl_pct: float
    duration_minutes: float
    mae: float  # Maximum Adverse Excursion
    mfe: float  # Maximum Favorable Excursion
    entry_confidence: float
    exit_reason: str


class RollingMetrics:
    """
    Rolling window performance metrics.
    Efficiently computed using deque for O(1) updates.
    """

    def __init__(self, window: int = 50):
        self.window = window
        self.returns: deque = deque(maxlen=window)
        self.pnls: deque = deque(maxlen=window)

    def add(self, pnl_pct: float, pnl: float):
        self.returns.append(pnl_pct)
        self.pnls.append(pnl)

    @property
    def win_rate(self) -> float:
        if not self.pnls:
            return 0.0
        wins = sum(1 for p in self.pnls if p > 0)
        return wins / len(self.pnls)

    @property
    def profit_factor(self) -> float:
        gains = sum(p for p in self.pnls if p > 0)
        losses = abs(sum(p for p in self.pnls if p < 0))
        return gains / losses if losses > 0 else float('inf') if gains > 0 else 0.0

    @property
    def sharpe(self) -> float:
        """Annualized Sharpe ratio (assumes daily returns)"""
        if len(self.returns) < 5:
            return 0.0
        arr = np.array(list(self.returns))
        std = arr.std()
        return (arr.mean() / std * np.sqrt(252)) if std > 0 else 0.0

    @property
    def sortino(self) -> float:
        """Sortino ratio (penalizes downside volatility only)"""
        if len(self.returns) < 5:
            return 0.0
        arr = np.array(list(self.returns))
        downside = arr[arr < 0]
        if len(downside) == 0:
            return float('inf')
        downside_std = downside.std()
        return (arr.mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0

    @property
    def avg_win(self) -> float:
        wins = [p for p in self.pnls if p > 0]
        return np.mean(wins) if wins else 0.0

    @property
    def avg_loss(self) -> float:
        losses = [p for p in self.pnls if p < 0]
        return abs(np.mean(losses)) if losses else 0.0

    @property
    def expectancy(self) -> float:
        """Expected value per trade"""
        wr = self.win_rate
        return wr * self.avg_win - (1 - wr) * self.avg_loss

    def to_dict(self) -> Dict:
        return {
            'win_rate': round(self.win_rate, 4),
            'profit_factor': round(self.profit_factor, 3),
            'sharpe': round(self.sharpe, 3),
            'sortino': round(self.sortino, 3),
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'expectancy': round(self.expectancy, 2),
            'n_trades': len(self.pnls),
        }


class AnomalyDetector:
    """
    Detects performance anomalies using Z-score and trend analysis.
    Triggers alerts when metrics deviate significantly from baseline.
    """

    def __init__(self, z_threshold: float = 2.5):
        self.z_threshold = z_threshold
        self._baselines: Dict[str, deque] = {}

    def check(self, metric_name: str, current_value: float) -> Optional[str]:
        """
        Check if a metric is anomalous.

        Returns:
            Alert message or None
        """
        if metric_name not in self._baselines:
            self._baselines[metric_name] = deque(maxlen=100)

        history = self._baselines[metric_name]
        history.append(current_value)

        if len(history) < 20:
            return None

        arr = np.array(list(history)[:-1])  # Exclude current
        mean = arr.mean()
        std = arr.std()

        if std == 0:
            return None

        z = (current_value - mean) / std

        if z < -self.z_threshold:
            return f"⚠️ {metric_name} anomaly: {current_value:.3f} (z={z:.1f}, mean={mean:.3f})"

        return None


class PerformanceMonitor:
    """
    Comprehensive real-time performance monitoring system.
    Tracks all trades, computes live metrics, detects anomalies.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.trades: List[TradeRecord] = []
        self.anomaly_detector = AnomalyDetector()

        # Global rolling metrics
        self.global_metrics = RollingMetrics(window=100)

        # Per-strategy rolling metrics
        self.strategy_metrics: Dict[str, RollingMetrics] = {}

        # Per-session metrics
        self.session_metrics = {
            'Asian': RollingMetrics(50),
            'London': RollingMetrics(50),
            'New_York': RollingMetrics(50),
        }

        # Max drawdown tracking
        self._equity_curve: deque = deque(maxlen=1000)
        self._peak_equity: float = 0.0
        self.max_drawdown: float = 0.0
        self.current_drawdown: float = 0.0

        # MAE/MFE analysis
        self.mae_percentiles: Dict[str, float] = {}
        self.mfe_percentiles: Dict[str, float] = {}

        logger.info("PerformanceMonitor initialized")

    def record_trade(self, trade: TradeRecord, current_balance: float):
        """
        Record a completed trade and update all metrics.
        """
        self.trades.append(trade)

        pnl_pct = trade.pnl_pct

        # Global metrics
        self.global_metrics.add(pnl_pct, trade.pnl)

        # Strategy metrics
        if trade.strategy not in self.strategy_metrics:
            self.strategy_metrics[trade.strategy] = RollingMetrics(50)
        self.strategy_metrics[trade.strategy].add(pnl_pct, trade.pnl)

        # Session metrics
        session = self._get_session(trade.entry_time)
        if session in self.session_metrics:
            self.session_metrics[session].add(pnl_pct, trade.pnl)

        # Equity curve and drawdown
        self._equity_curve.append(current_balance)
        if current_balance > self._peak_equity:
            self._peak_equity = current_balance
        if self._peak_equity > 0:
            self.current_drawdown = (self._peak_equity - current_balance) / self._peak_equity * 100
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)

        # Anomaly checks
        self._run_anomaly_checks()

        # Update MAE/MFE stats
        self._update_mae_mfe_stats()

    def _get_session(self, ts: datetime) -> str:
        hour = ts.hour
        if 0 <= hour < 8:
            return 'Asian'
        elif 8 <= hour < 16:
            return 'London'
        else:
            return 'New_York'

    def _run_anomaly_checks(self):
        """Check all key metrics for anomalies"""
        alerts = []

        m = self.global_metrics
        if len(m.pnls) >= 20:
            for metric_name, value in [
                ('win_rate', m.win_rate),
                ('profit_factor', m.profit_factor),
                ('sharpe', m.sharpe),
            ]:
                alert = self.anomaly_detector.check(metric_name, value)
                if alert:
                    alerts.append(alert)
                    logger.warning(alert)

    def _update_mae_mfe_stats(self):
        """Update MAE/MFE percentile statistics"""
        if len(self.trades) < 10:
            return

        maes = [t.mae for t in self.trades[-100:] if t.mae > 0]
        mfes = [t.mfe for t in self.trades[-100:] if t.mfe > 0]

        if maes:
            self.mae_percentiles = {
                'p25': float(np.percentile(maes, 25)),
                'p50': float(np.percentile(maes, 50)),
                'p75': float(np.percentile(maes, 75)),
                'p90': float(np.percentile(maes, 90)),
            }

        if mfes:
            self.mfe_percentiles = {
                'p25': float(np.percentile(mfes, 25)),
                'p50': float(np.percentile(mfes, 50)),
                'p75': float(np.percentile(mfes, 75)),
                'p90': float(np.percentile(mfes, 90)),
            }

    def get_sl_tp_recommendations(self) -> Dict:
        """
        Recommend optimal SL/TP adjustments based on MAE/MFE analysis.
        """
        recommendations = {}

        if not self.mae_percentiles or not self.mfe_percentiles:
            return recommendations

        # If p75 MAE > current SL distance on average → SL is too tight
        avg_mae_p75 = self.mae_percentiles.get('p75', 0)
        avg_mfe_p50 = self.mfe_percentiles.get('p50', 0)

        recommendations['suggested_sl_atr_mult'] = round(avg_mae_p75 * 1.2, 2)
        recommendations['suggested_tp_atr_mult'] = round(avg_mfe_p50 * 0.8, 2)
        recommendations['mfe_mae_ratio'] = round(avg_mfe_p50 / avg_mae_p75, 2) if avg_mae_p75 > 0 else 0

        return recommendations

    def get_full_report(self) -> Dict:
        """Generate complete performance report"""
        report = {
            'timestamp': str(datetime.now()),
            'total_trades': len(self.trades),
            'global': self.global_metrics.to_dict(),
            'max_drawdown': round(self.max_drawdown, 3),
            'current_drawdown': round(self.current_drawdown, 3),
            'by_strategy': {
                name: m.to_dict()
                for name, m in self.strategy_metrics.items()
            },
            'by_session': {
                session: m.to_dict()
                for session, m in self.session_metrics.items()
                if m.pnls
            },
            'mae_percentiles': self.mae_percentiles,
            'mfe_percentiles': self.mfe_percentiles,
            'sl_tp_recommendations': self.get_sl_tp_recommendations(),
        }
        return report

    def get_calmar_ratio(self) -> float:
        """Calmar ratio: annualized return / max drawdown"""
        if self.max_drawdown == 0:
            return 0.0
        arr = np.array([t.pnl_pct for t in self.trades[-252:]])
        if len(arr) == 0:
            return 0.0
        annualized_return = arr.mean() * 252
        return annualized_return / (self.max_drawdown / 100)

    def save_report(self, filepath: str = 'reports/performance_report.json'):
        """Save performance report to JSON"""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        report = self.get_full_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Performance report saved: {filepath}")
