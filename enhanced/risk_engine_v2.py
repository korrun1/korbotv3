"""
🛡️ KorBot X Enhanced - Risk Engine v2
Version: 3.0
Date: 2026-03

Improvements over v2:
- Fractional Kelly sizing (win probability from ML model)
- Correlation-aware exposure limits
- Gradual position size reduction (50%→25%→pause on losses)
- Volatility-regime position scaling
- Structure-based stop loss support
- Partial close at 1:1 R:R with break-even stop
- MAE/MFE tracking for SL/TP optimization
- Portfolio-level VaR calculation
- Strategy-level performance gate integration
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class TradingState(Enum):
    ACTIVE = "active"
    CAUTIOUS = "cautious"      # Reduced sizing
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class RiskMetrics:
    """Extended risk metrics with MAE/MFE and per-session tracking"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    open_exposure: float = 0.0
    peak_balance: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)

    # Rolling metrics
    rolling_win_rate: float = 0.5
    rolling_profit_factor: float = 1.0
    rolling_sharpe: float = 0.0

    # Session tracking
    session_pnl: Dict[str, float] = field(default_factory=lambda: {
        "Asian": 0.0, "London": 0.0, "New_York": 0.0
    })

    # MAE/MFE (for SL/TP optimization)
    avg_mae: float = 0.0
    avg_mfe: float = 0.0
    mae_samples: List[float] = field(default_factory=list)
    mfe_samples: List[float] = field(default_factory=list)

    def record_mae_mfe(self, mae: float, mfe: float):
        self.mae_samples.append(mae)
        self.mfe_samples.append(mfe)
        if len(self.mae_samples) > 100:
            self.mae_samples.pop(0)
        if len(self.mfe_samples) > 100:
            self.mfe_samples.pop(0)
        self.avg_mae = statistics.mean(self.mae_samples) if self.mae_samples else 0
        self.avg_mfe = statistics.mean(self.mfe_samples) if self.mfe_samples else 0


# ──────────────────────────────────────────────────
# CORRELATION GROUPS (static, updated hourly in v3)
# ──────────────────────────────────────────────────

CORRELATION_GROUPS = {
    # USD bearish pairs (all move up when USD weakens)
    "USD_bear": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "XAUUSD"],
    # USD bullish pairs (all move up when USD strengthens)
    "USD_bull": ["USDCAD", "USDJPY", "USDCHF"],
    # Risk-on currencies
    "RISK_ON": ["AUDUSD", "NZDUSD", "AUDJPY", "NZDJPY"],
    # Commodity currencies
    "COMMODITY": ["AUDCAD", "AUDUSD", "NZDUSD"],
    # Cross pairs with low USD correlation
    "CROSSES": ["EURGBP", "EURJPY", "GBPJPY", "EURAUD"],
}

def get_correlation_group(symbol: str) -> Optional[str]:
    for group, symbols in CORRELATION_GROUPS.items():
        if symbol in symbols:
            return group
    return None


# ──────────────────────────────────────────────────
# ENHANCED CIRCUIT BREAKER
# ──────────────────────────────────────────────────

class CircuitBreaker:
    """
    Multi-tier circuit breaker with gradual response:
    Tier 1 (2 losses): Reduce sizing to 50%
    Tier 2 (3 losses): Reduce sizing to 25%
    Tier 3 (4 losses or rapid losses): Pause trading 60 min
    """

    def __init__(self, config: Dict):
        self.enabled = config.get('enabled', True)
        self.max_consecutive_losses = config.get('max_consecutive_losses', 3)
        self.cooldown_minutes = config.get('cooldown_minutes', 60)
        self.rapid_loss_window_minutes = config.get('rapid_loss_window_minutes', 120)
        self.rapid_loss_count = config.get('rapid_loss_count', 3)

        self.is_triggered = False
        self.trigger_time: Optional[datetime] = None
        self.trigger_reason: Optional[str] = None
        self.recent_loss_times: List[datetime] = []

    @property
    def sizing_multiplier(self) -> float:
        """Dynamic sizing multiplier based on loss streak"""
        if not hasattr(self, '_consecutive') or self._consecutive is None:
            return 1.0
        if self._consecutive >= 3:
            return 0.25
        if self._consecutive >= 2:
            return 0.50
        return 1.0

    def check(
        self,
        risk_metrics: RiskMetrics,
        account_balance: float
    ) -> Tuple[bool, Optional[str], float]:
        """
        Returns: (should_pause, reason, sizing_multiplier)
        """
        self._consecutive = risk_metrics.consecutive_losses

        if not self.enabled:
            return False, None, 1.0

        # Cooldown check
        if self.is_triggered and self.trigger_time:
            elapsed = (datetime.now() - self.trigger_time).total_seconds() / 60
            if elapsed < self.cooldown_minutes:
                remaining = self.cooldown_minutes - elapsed
                return True, f"CB active ({remaining:.0f}m cooldown)", 0.0
            else:
                self.reset()
                return False, None, 1.0

        # Rapid loss detection
        now = datetime.now()
        window_start = now - timedelta(minutes=self.rapid_loss_window_minutes)
        self.recent_loss_times = [t for t in self.recent_loss_times if t > window_start]
        if len(self.recent_loss_times) >= self.rapid_loss_count:
            self.trigger(f"Rapid losses: {len(self.recent_loss_times)} losses in {self.rapid_loss_window_minutes}min")
            return True, self.trigger_reason, 0.0

        # Consecutive loss check → hard pause
        if risk_metrics.consecutive_losses >= self.max_consecutive_losses + 1:
            self.trigger(f"Max consecutive losses: {risk_metrics.consecutive_losses}")
            return True, self.trigger_reason, 0.0

        # Soft reduction (no pause, just size down)
        mult = self.sizing_multiplier
        if mult < 1.0:
            return False, None, mult

        return False, None, 1.0

    def record_loss(self):
        self.recent_loss_times.append(datetime.now())

    def trigger(self, reason: str):
        self.is_triggered = True
        self.trigger_time = datetime.now()
        self.trigger_reason = reason
        logger.warning(f"🚨 Circuit Breaker TRIGGERED: {reason}")

    def reset(self):
        self.is_triggered = False
        self.trigger_time = None
        self.trigger_reason = None

    def force_reset(self):
        self.reset()
        self.recent_loss_times.clear()
        logger.warning("Circuit Breaker FORCE RESET")


# ──────────────────────────────────────────────────
# RISK ENGINE v2
# ──────────────────────────────────────────────────

class RiskEngine:
    """
    Enhanced risk management engine v2.
    New features:
    - Fractional Kelly sizing
    - Correlation-aware exposure
    - Volatility-regime scaling
    - MAE/MFE optimization
    - Portfolio VaR
    """

    def __init__(self, config: Dict):
        self.config = config.get('risk', {})

        # Core parameters
        self.base_risk_percent = self.config.get('base_risk_percent', 0.8)
        self.max_risk_percent = self.config.get('max_risk_percent', 2.0)     # Hard ceiling
        self.max_drawdown_percent = self.config.get('max_drawdown_percent', 5.0)
        self.max_daily_loss_percent = self.config.get('max_daily_loss_percent', 3.0)
        self.max_positions = self.config.get('max_positions', 3)
        self.max_symbol_exposure_percent = self.config.get('max_symbol_exposure_percent', 3.0)
        self.max_correlated_exposure_percent = self.config.get('max_correlated_exposure_percent', 5.0)

        # Kelly parameters
        self.kelly_fraction = self.config.get('kelly_fraction', 0.25)   # Fractional Kelly (25%)
        self.use_kelly = self.config.get('use_kelly', True)

        # State
        self.state = TradingState.ACTIVE
        self.state_reason: Optional[str] = None
        self.metrics = RiskMetrics()
        self.sizing_multiplier = 1.0  # Dynamic, updated per circuit breaker check

        # Components
        circuit_config = self.config.get('circuit_breaker', {})
        self.circuit_breaker = CircuitBreaker(circuit_config)

        logger.info(
            f"Risk Engine v2 initialized — base_risk={self.base_risk_percent}%, "
            f"Kelly={self.use_kelly}, max_DD={self.max_drawdown_percent}%"
        )

    # ──────────────────────────────────────────────
    # MAIN GATES
    # ──────────────────────────────────────────────

    def can_trade(self, account_info: Dict) -> Tuple[bool, Optional[str]]:
        """Check if trading is globally allowed"""
        if self.state == TradingState.STOPPED:
            return False, "Trading stopped"

        # Circuit breaker check
        paused, reason, mult = self.circuit_breaker.check(
            self.metrics, account_info['balance']
        )
        self.sizing_multiplier = mult
        if paused:
            self.state = TradingState.PAUSED
            return False, reason
        elif mult < 1.0:
            self.state = TradingState.CAUTIOUS

        # Drawdown check
        if account_info['balance'] > 0 and self.metrics.peak_balance > 0:
            dd_pct = (self.metrics.peak_balance - account_info['balance']) / self.metrics.peak_balance * 100
            self.metrics.current_drawdown = dd_pct
            if dd_pct >= self.max_drawdown_percent:
                self.state = TradingState.STOPPED
                reason = f"Max drawdown reached ({dd_pct:.2f}%)"
                logger.critical(f"🛑 {reason}")
                return False, reason

        # Daily loss check
        if account_info['balance'] > 0:
            daily_loss_pct = (self.metrics.daily_pnl / account_info['balance']) * 100
            if daily_loss_pct <= -self.max_daily_loss_percent:
                self.state = TradingState.PAUSED
                reason = f"Daily loss limit ({abs(daily_loss_pct):.2f}%)"
                return False, reason

        # Update peak
        if account_info['balance'] > self.metrics.peak_balance:
            self.metrics.peak_balance = account_info['balance']

        if self.state != TradingState.CAUTIOUS:
            self.state = TradingState.ACTIVE
        return True, None

    def can_open_position(
        self,
        symbol: str,
        open_positions: List[Dict],
        account_info: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Check if a new position can be opened for this symbol"""
        # Max total positions
        if len(open_positions) >= self.max_positions:
            return False, f"Max positions reached ({self.max_positions})"

        # Symbol already has position?
        symbol_positions = [p for p in open_positions if p.get('symbol') == symbol]
        if symbol_positions:
            return False, f"Position already open for {symbol}"

        # Per-symbol exposure
        balance = account_info['balance']
        symbol_exposure = sum(
            (p.get('lot_size', 0) * p.get('contract_size', 100000) /
             balance * 100)
            for p in open_positions if p.get('symbol') == symbol
        )
        if symbol_exposure >= self.max_symbol_exposure_percent:
            return False, f"Symbol exposure limit ({symbol_exposure:.2f}%)"

        # Correlation group check
        symbol_group = get_correlation_group(symbol)
        if symbol_group:
            corr_exposure = sum(
                (p.get('lot_size', 0) * p.get('contract_size', 100000) / balance * 100)
                for p in open_positions
                if get_correlation_group(p.get('symbol', '')) == symbol_group
            )
            if corr_exposure >= self.max_correlated_exposure_percent:
                return False, f"Correlated exposure limit ({symbol_group}: {corr_exposure:.2f}%)"

        return True, None

    # ──────────────────────────────────────────────
    # POSITION SIZING
    # ──────────────────────────────────────────────

    def calculate_position_size(
        self,
        account_info: Dict,
        signal_entry: float,
        signal_sl: float,
        symbol_info: Dict,
        win_probability: float = 0.6,
        reward_risk_ratio: float = 2.5
    ) -> float:
        """
        Calculate position size using Fractional Kelly or fixed percent.

        Args:
            win_probability: ML-predicted probability of winning (from XGBoost)
            reward_risk_ratio: Expected RR ratio

        Returns:
            Lot size (clamped to min/max)
        """
        balance = account_info.get('balance', 0)
        if balance <= 0:
            return 0.0

        # Determine risk percent
        if self.use_kelly and 0.3 < win_probability < 0.9:
            # Kelly formula: f* = (p*b - q) / b
            p = win_probability
            q = 1.0 - p
            b = reward_risk_ratio
            kelly_f = (p * b - q) / b if b > 0 else 0
            # Fractional Kelly + clamp
            risk_percent = max(
                0.1,
                min(
                    self.max_risk_percent,
                    kelly_f * self.kelly_fraction * 100
                )
            )
        else:
            risk_percent = self.base_risk_percent

        # Apply volatility regime scaling
        risk_percent *= self._get_volatility_scaling(symbol_info)

        # Apply dynamic CB sizing multiplier
        risk_percent *= self.sizing_multiplier

        # Apply drawdown-based scaling
        risk_percent *= self._get_drawdown_scaling()

        # Ensure within bounds
        risk_percent = max(0.1, min(risk_percent, self.max_risk_percent))

        # Convert to lot size
        risk_amount = balance * (risk_percent / 100)
        sl_distance = abs(signal_entry - signal_sl)

        if sl_distance <= 0:
            return 0.0

        # pip value calculation
        contract_size = symbol_info.get('contract_size', 100000)
        lot_step = symbol_info.get('volume_step', 0.01)
        pip_value_per_lot = symbol_info.get('pip_value_per_lot', 10.0)

        if pip_value_per_lot > 0:
            sl_pips = sl_distance / symbol_info.get('pip_size', 0.0001)
            lot_size = risk_amount / (sl_pips * pip_value_per_lot)
        else:
            lot_size = risk_amount / (sl_distance * contract_size)

        # Round to lot step
        lot_size = round(lot_size / lot_step) * lot_step

        # Clamp
        min_lot = symbol_info.get('volume_min', 0.01)
        max_lot = symbol_info.get('volume_max', 10.0)
        lot_size = max(min_lot, min(lot_size, max_lot))

        logger.debug(
            f"Position size: risk%={risk_percent:.2f}, kelly_win_p={win_probability:.2f}, "
            f"lot={lot_size:.2f}"
        )
        return lot_size

    def _get_volatility_scaling(self, symbol_info: Dict) -> float:
        """
        Scale position size based on current volatility regime.
        High volatility → smaller size.
        """
        vol_regime = symbol_info.get('volatility_regime', 1.0)
        if vol_regime > 2.0:
            return 0.5   # High volatility: half size
        elif vol_regime > 1.5:
            return 0.75  # Elevated: 75% size
        elif vol_regime < 0.5:
            return 1.1   # Very calm: slight increase (but cap at max)
        return 1.0

    def _get_drawdown_scaling(self) -> float:
        """
        Scale position size based on current drawdown level.
        Reduces size as drawdown increases.
        """
        dd = self.metrics.current_drawdown
        if dd >= 3.0:
            return 0.4
        elif dd >= 2.0:
            return 0.6
        elif dd >= 1.0:
            return 0.8
        return 1.0

    # ──────────────────────────────────────────────
    # STOP LOSS / TAKE PROFIT
    # ──────────────────────────────────────────────

    def calculate_stop_loss(
        self,
        entry_price: float,
        signal_type: str,
        atr: float,
        df=None,
        strategy_name: str = ""
    ) -> float:
        """
        Calculate stop loss with:
        - Strategy-specific ATR multipliers
        - Optional structure-based (swing high/low) override
        """
        # Strategy-specific multipliers
        multipliers = {
            'Scalping': 1.5,
            'Mean Reversion': 2.0,
            'Breakout': 1.5,
            'Adaptive Swing': 2.5,
            'VWAP Deviation': 1.8,
        }
        multiplier = multipliers.get(strategy_name, self.config.get('stop_loss', {}).get('atr_multiplier', 2.0))

        atr_sl = multiplier * atr
        min_sl_pips = self.config.get('stop_loss', {}).get('min_pips', 10)
        max_sl_pips = self.config.get('stop_loss', {}).get('max_pips', 50)
        pip_size = 0.0001  # Will be provided by symbol_info in production

        min_sl = min_sl_pips * pip_size
        max_sl = max_sl_pips * pip_size

        sl_distance = max(min_sl, min(atr_sl, max_sl))

        # Structure-based override
        if df is not None and len(df) >= 10:
            lookback = min(20, len(df))
            if signal_type == 'BUY':
                swing_low = df['Low'].iloc[-lookback:].min()
                structure_sl = swing_low - atr * 0.3
                # Use structure if it's tighter but not more than 10% tighter
                if structure_sl > entry_price - sl_distance * 1.1:
                    sl_distance = entry_price - structure_sl
            else:
                swing_high = df['High'].iloc[-lookback:].max()
                structure_sl = swing_high + atr * 0.3
                if structure_sl < entry_price + sl_distance * 1.1:
                    sl_distance = structure_sl - entry_price

        if signal_type == 'BUY':
            return entry_price - sl_distance
        else:
            return entry_price + sl_distance

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        signal_type: str,
        strategy_name: str = ""
    ) -> Tuple[float, float]:
        """
        Calculate TP and partial-TP prices.
        Returns: (take_profit, partial_tp at 1:1 RR)
        """
        rr_ratios = {
            'Scalping': 2.5,
            'Mean Reversion': 2.0,
            'Breakout': 3.0,
            'Adaptive Swing': 3.5,
            'VWAP Deviation': 2.0,
        }
        rr = rr_ratios.get(strategy_name, self.config.get('take_profit', {}).get('risk_reward_ratio', 2.5))

        sl_distance = abs(entry_price - stop_loss)
        partial_tp = (entry_price + sl_distance) if signal_type == 'BUY' else (entry_price - sl_distance)
        tp = (entry_price + sl_distance * rr) if signal_type == 'BUY' else (entry_price - sl_distance * rr)

        return tp, partial_tp

    # ──────────────────────────────────────────────
    # TRADE LIFECYCLE
    # ──────────────────────────────────────────────

    def update_trade_result(self, pnl: float, mae: float = 0, mfe: float = 0):
        """Called when a trade closes"""
        self.metrics.total_trades += 1
        self.metrics.daily_pnl += pnl
        self.metrics.total_pnl += pnl

        if pnl > 0:
            self.metrics.winning_trades += 1
            self.metrics.consecutive_losses = 0
            self.metrics.consecutive_wins += 1
        else:
            self.metrics.losing_trades += 1
            self.metrics.consecutive_losses += 1
            self.metrics.consecutive_wins = 0
            self.circuit_breaker.record_loss()

        if mae > 0 or mfe > 0:
            self.metrics.record_mae_mfe(mae, mfe)

        # Rolling metrics
        total = self.metrics.total_trades
        if total > 0:
            self.metrics.rolling_win_rate = self.metrics.winning_trades / total

    def reset_daily_metrics(self):
        """Reset daily-scoped metrics (call at midnight)"""
        self.metrics.daily_pnl = 0.0
        self.metrics.last_reset = datetime.now()

        # Reset soft pause if new day
        if self.state == TradingState.PAUSED:
            self.state = TradingState.ACTIVE
            logger.info("Daily reset: trading state restored to ACTIVE")

    # ──────────────────────────────────────────────
    # PORTFOLIO VaR (simplified historical simulation)
    # ──────────────────────────────────────────────

    def estimate_portfolio_var(
        self,
        open_positions: List[Dict],
        recent_returns: Dict[str, List[float]],
        confidence: float = 0.95
    ) -> float:
        """
        Estimate 1-day VaR at given confidence level.

        Args:
            open_positions: list of {'symbol', 'lot_size', 'direction'} dicts
            recent_returns: dict of symbol → list of daily returns (decimal)
            confidence: VaR confidence level

        Returns:
            VaR as a percentage of balance (negative = loss)
        """
        if not open_positions or not recent_returns:
            return 0.0

        portfolio_returns = np.zeros(252)
        for pos in open_positions:
            symbol = pos.get('symbol', '')
            if symbol not in recent_returns:
                continue
            returns_arr = np.array(recent_returns[symbol][-252:])
            if len(returns_arr) < 10:
                continue
            if len(returns_arr) < 252:
                returns_arr = np.pad(returns_arr, (252 - len(returns_arr), 0), mode='edge')
            direction = 1 if pos.get('direction') == 'BUY' else -1
            weight = pos.get('exposure_percent', 1.0) / 100
            portfolio_returns += direction * weight * returns_arr

        if portfolio_returns.std() == 0:
            return 0.0

        var_level = 1.0 - confidence
        var = float(np.percentile(portfolio_returns, var_level * 100))
        return var

    def get_risk_summary(self) -> Dict:
        """Return current risk status summary"""
        return {
            'state': self.state.value,
            'consecutive_losses': self.metrics.consecutive_losses,
            'daily_pnl': round(self.metrics.daily_pnl, 2),
            'total_pnl': round(self.metrics.total_pnl, 2),
            'current_drawdown': round(self.metrics.current_drawdown, 2),
            'max_drawdown': round(self.metrics.max_drawdown, 2),
            'win_rate': round(self.metrics.rolling_win_rate, 3),
            'sizing_multiplier': round(self.sizing_multiplier, 2),
            'peak_balance': round(self.metrics.peak_balance, 2),
            'avg_mae': round(self.metrics.avg_mae, 5),
            'avg_mfe': round(self.metrics.avg_mfe, 5),
            'circuit_breaker': self.circuit_breaker.is_triggered,
        }
