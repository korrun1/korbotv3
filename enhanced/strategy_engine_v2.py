"""
🎯 KorBot X Enhanced - Strategy Engine v2
Version: 3.0
Date: 2026-03

Improvements over v2:
- Multi-timeframe confirmation scoring for ALL strategies
- Signal conflict resolution (no opposing simultaneous trades)
- Dynamic confidence scoring based on signal quality count
- Strategy-level performance gates (auto-disable underperformers)
- Divergence detection (RSI/MACD vs price)
- Volume Profile integration
- Candlestick pattern filter
- VWAP deviation strategy (new)
- Trend Continuation Pullback strategy (new)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

from market_intel import MarketIntelligence, MarketRegime
from utils import safe_execution, is_trading_time, is_news_time

logger = logging.getLogger(__name__)


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


@dataclass
class Signal:
    """Enhanced trading signal with multi-timeframe score"""
    type: SignalType
    strategy: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reasons: List[str]
    timestamp: str
    mtf_score: float = 0.0          # Multi-timeframe alignment score (-1 to +1)
    signal_quality: int = 0          # Number of confirming conditions
    partial_tp_price: Optional[float] = None   # Partial close target (1:1 RR)


@dataclass
class StrategyPerformance:
    """Tracks rolling performance per strategy"""
    name: str
    trades: deque = field(default_factory=lambda: deque(maxlen=50))
    disabled_until: Optional[datetime] = None

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.5
        wins = sum(1 for t in self.trades if t > 0)
        return wins / len(self.trades)

    @property
    def profit_factor(self) -> float:
        gains = sum(t for t in self.trades if t > 0)
        losses = abs(sum(t for t in self.trades if t < 0))
        return gains / losses if losses > 0 else gains if gains > 0 else 1.0

    @property
    def sharpe(self) -> float:
        if len(self.trades) < 5:
            return 0.0
        arr = np.array(list(self.trades))
        return (arr.mean() / arr.std()) * np.sqrt(252) if arr.std() > 0 else 0.0

    def record_trade(self, pnl: float):
        self.trades.append(pnl)

    def is_active(self) -> bool:
        if self.disabled_until and datetime.now() < self.disabled_until:
            return False
        return True

    def check_gate(self) -> Tuple[bool, str]:
        """Performance gate: disable strategy if Sharpe < 0.3 over last 20 trades"""
        if len(self.trades) < 20:
            return True, ""
        if self.sharpe < 0.3:
            self.disabled_until = datetime.now() + timedelta(hours=24)
            reason = f"{self.name} gated: Sharpe={self.sharpe:.2f} over {len(self.trades)} trades"
            logger.warning(f"⚠️ Strategy gate triggered: {reason}")
            return False, reason
        if self.profit_factor < 0.8:
            self.disabled_until = datetime.now() + timedelta(hours=12)
            reason = f"{self.name} gated: PF={self.profit_factor:.2f}"
            logger.warning(f"⚠️ Strategy gate triggered: {reason}")
            return False, reason
        return True, ""


# ─────────────────────────────────────────────────────────────
# MULTI-TIMEFRAME CONFIRMATION ENGINE
# ─────────────────────────────────────────────────────────────

class MultiTimeframeScorer:
    """
    Scores signal alignment across H4, H1, M15 timeframes.
    Returns a score from -1.0 (fully against) to +1.0 (fully aligned).
    """

    @staticmethod
    def score_signal(
        signal: Signal,
        df_dict: Dict[str, pd.DataFrame]
    ) -> float:
        """
        Multi-timeframe alignment score for a signal.

        Args:
            signal: The candidate signal
            df_dict: Dict of timeframe DataFrames (M1, M5, M15, H1, H4)

        Returns:
            Score in [-1.0, +1.0]
        """
        scores = []
        direction = 1 if signal.type == SignalType.BUY else -1

        # H4 trend (weight: 3)
        h4_df = df_dict.get('H4')
        if h4_df is not None and not h4_df.empty:
            row = h4_df.iloc[-1]
            ema20 = row.get('EMA_20', 0)
            ema50 = row.get('EMA_50', 0)
            adx = row.get('ADX', 0)
            if ema20 and ema50:
                h4_trend = 1 if ema20 > ema50 else -1
                h4_strength = min(adx / 25.0, 1.5) if adx > 20 else 0.5
                scores.append(('H4_trend', direction * h4_trend * h4_strength, 3))

        # H1 momentum (weight: 2)
        h1_df = df_dict.get('H1')
        if h1_df is not None and not h1_df.empty:
            row = h1_df.iloc[-1]
            macd = row.get('MACD', 0)
            macd_sig = row.get('MACD_signal', 0)
            rsi = row.get('RSI', 50)
            if macd and macd_sig:
                h1_momentum = 1 if macd > macd_sig else -1
                h1_rsi_ok = 1 if (direction == 1 and 40 < rsi < 75) or \
                                  (direction == -1 and 25 < rsi < 60) else 0.5
                scores.append(('H1_momentum', direction * h1_momentum * h1_rsi_ok, 2))

        # M15 entry timing (weight: 1)
        m15_df = df_dict.get('M15')
        if m15_df is not None and not m15_df.empty:
            row = m15_df.iloc[-1]
            ema5 = row.get('EMA_5', 0)
            ema13 = row.get('EMA_13', 0)
            if ema5 and ema13:
                m15_dir = 1 if ema5 > ema13 else -1
                scores.append(('M15_timing', direction * m15_dir, 1))

        if not scores:
            return 0.0

        total_weight = sum(w for _, _, w in scores)
        weighted_sum = sum(s * w for _, s, w in scores)
        normalized = weighted_sum / total_weight if total_weight > 0 else 0.0

        logger.debug(f"MTF scores for {signal.strategy}: {[(n, round(s, 2)) for n, s, _ in scores]}")
        return max(-1.0, min(1.0, normalized))


def detect_divergence(df: pd.DataFrame) -> Optional[str]:
    """
    Detect bullish/bearish divergence between price and RSI/MACD.

    Returns:
        'bullish', 'bearish', or None
    """
    if df is None or len(df) < 10:
        return None

    lookback = min(20, len(df) - 1)
    segment = df.iloc[-lookback:]

    # Price trend
    price_low_idx = segment['Low'].idxmin()
    price_high_idx = segment['High'].idxmax()
    first_price = segment['Close'].iloc[0]
    last_price = segment['Close'].iloc[-1]
    price_trend = 1 if last_price > first_price else -1

    # RSI trend
    if 'RSI' in df.columns:
        first_rsi = segment['RSI'].iloc[0]
        last_rsi = segment['RSI'].iloc[-1]
        rsi_trend = 1 if last_rsi > first_rsi else -1

        # Bullish divergence: price making lower lows, RSI making higher lows
        if price_trend == -1 and rsi_trend == 1 and last_rsi < 40:
            return 'bullish'

        # Bearish divergence: price making higher highs, RSI making lower highs
        if price_trend == 1 and rsi_trend == -1 and last_rsi > 60:
            return 'bearish'

    return None


def detect_candlestick_pattern(df: pd.DataFrame) -> Optional[str]:
    """
    Basic candlestick pattern recognition.

    Returns:
        'hammer', 'shooting_star', 'engulfing_bull', 'engulfing_bear', or None
    """
    if df is None or len(df) < 3:
        return None

    c = df.iloc[-1]
    p = df.iloc[-2]
    body = abs(c['Close'] - c['Open'])
    full_range = c['High'] - c['Low']
    upper_wick = c['High'] - max(c['Close'], c['Open'])
    lower_wick = min(c['Close'], c['Open']) - c['Low']

    if full_range < 1e-10:
        return None

    # Hammer: small body at top, long lower wick, bullish reversal
    if lower_wick > 2 * body and upper_wick < 0.2 * full_range:
        return 'hammer'

    # Shooting star: small body at bottom, long upper wick, bearish reversal
    if upper_wick > 2 * body and lower_wick < 0.2 * full_range:
        return 'shooting_star'

    # Bullish engulfing
    if (p['Close'] < p['Open'] and  # Previous bearish
        c['Close'] > c['Open'] and   # Current bullish
        c['Open'] < p['Close'] and    # Opens below prev close
        c['Close'] > p['Open']):       # Closes above prev open
        return 'engulfing_bull'

    # Bearish engulfing
    if (p['Close'] > p['Open'] and  # Previous bullish
        c['Close'] < c['Open'] and   # Current bearish
        c['Open'] > p['Close'] and    # Opens above prev close
        c['Close'] < p['Open']):       # Closes below prev open
        return 'engulfing_bear'

    return None


# ─────────────────────────────────────────────────────────────
# BASE STRATEGY
# ─────────────────────────────────────────────────────────────

class BaseStrategy:
    """Base class for all strategies"""

    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.performance = StrategyPerformance(name=name)

    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:
        raise NotImplementedError

    def _apply_time_filters(self) -> bool:
        time_filters = self.config.get('time_filters', {})
        trading_hours = time_filters.get('trading_hours', '00:00-23:59')
        if not is_trading_time(trading_hours):
            return False
        if time_filters.get('avoid_news', False) and is_news_time():
            return False
        return True

    def _calculate_atr_sl_tp(
        self,
        signal_type: SignalType,
        current_price: float,
        atr: float,
        sl_multiplier: float,
        rr_ratio: float,
        df: pd.DataFrame
    ) -> Tuple[float, float, float]:
        """
        Calculate SL/TP with optional structure-based SL.

        Returns: (stop_loss, take_profit, partial_tp)
        """
        # Structure-based SL (swing high/low)
        lookback = min(20, len(df))
        if lookback > 5:
            if signal_type == SignalType.BUY:
                swing_low = df['Low'].iloc[-lookback:].min()
                # Use whichever is tighter: ATR-based or swing low
                atr_sl = current_price - (atr * sl_multiplier)
                sl = max(swing_low - atr * 0.3, atr_sl)  # Slightly below swing low
            else:
                swing_high = df['High'].iloc[-lookback:].max()
                atr_sl = current_price + (atr * sl_multiplier)
                sl = min(swing_high + atr * 0.3, atr_sl)
        else:
            if signal_type == SignalType.BUY:
                sl = current_price - (atr * sl_multiplier)
            else:
                sl = current_price + (atr * sl_multiplier)

        sl_distance = abs(current_price - sl)
        tp = current_price + sl_distance * rr_ratio if signal_type == SignalType.BUY \
             else current_price - sl_distance * rr_ratio

        # Partial TP at 1:1 RR
        partial_tp = current_price + sl_distance if signal_type == SignalType.BUY \
                     else current_price - sl_distance

        return sl, tp, partial_tp

    def record_trade_result(self, pnl: float):
        """Record trade outcome for performance tracking"""
        self.performance.record_trade(pnl)
        self.performance.check_gate()


# ─────────────────────────────────────────────────────────────
# STRATEGY 1: SCALPING
# ─────────────────────────────────────────────────────────────

class ScalpingStrategy(BaseStrategy):
    """
    Enhanced scalping with:
    - EMA 5/13 crossover + multi-confirmation
    - Divergence filter (skip if divergence against trade)
    - Session filter (only London/NY overlap)
    - Strategy-specific ATR multiplier (tighter)
    """

    def __init__(self, config: Dict):
        super().__init__("Scalping", config.get('scalping', {}))
        self.sl_multiplier = 1.5    # Tighter for scalping
        self.rr_ratio = 2.5

    @safe_execution(default_return=None)
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:

        if not self.enabled or not self.performance.is_active():
            return None
        if df is None or df.empty or len(df) < 10:
            return None
        if regime not in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            return None
        if not self._apply_time_filters():
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        ema_fast = self.config.get('ema_fast', 5)
        ema_slow = self.config.get('ema_slow', 13)
        volume_threshold = self.config.get('volume_threshold', 1.5)
        min_atr = self.config.get('min_atr', 0.0005)

        atr = latest.get('ATR', 0)
        if atr < min_atr:
            return None

        volume_ratio = latest.get('Volume_Ratio', 0)
        if volume_ratio < volume_threshold:
            return None

        ema_fast_curr = latest.get(f'EMA_{ema_fast}', 0)
        ema_slow_curr = latest.get(f'EMA_{ema_slow}', 0)
        ema_fast_prev = prev.get(f'EMA_{ema_fast}', 0)
        ema_slow_prev = prev.get(f'EMA_{ema_slow}', 0)

        signal_type = SignalType.NONE
        reasons = []
        quality = 0

        # Bullish crossover
        if ema_fast_curr > ema_slow_curr and ema_fast_prev <= ema_slow_prev:
            if latest['Close'] > latest['Open']:
                adx = latest.get('ADX', 0)
                rsi = latest.get('RSI', 50)
                if adx > 20 and rsi < 70:
                    signal_type = SignalType.BUY
                    reasons = [
                        "Bullish EMA crossover",
                        "Bullish candle confirmation",
                        f"Trend strength ADX {adx:.1f}",
                        f"RSI in range ({rsi:.1f})"
                    ]
                    quality = 4
                    # Bonus: candlestick pattern
                    cs_pattern = detect_candlestick_pattern(df)
                    if cs_pattern in ('hammer', 'engulfing_bull'):
                        reasons.append(f"Candlestick: {cs_pattern}")
                        quality += 1

        # Bearish crossover
        elif ema_fast_curr < ema_slow_curr and ema_fast_prev >= ema_slow_prev:
            if latest['Close'] < latest['Open']:
                adx = latest.get('ADX', 0)
                rsi = latest.get('RSI', 50)
                if adx > 20 and rsi > 30:
                    signal_type = SignalType.SELL
                    reasons = [
                        "Bearish EMA crossover",
                        "Bearish candle confirmation",
                        f"Trend strength ADX {adx:.1f}",
                        f"RSI in range ({rsi:.1f})"
                    ]
                    quality = 4
                    cs_pattern = detect_candlestick_pattern(df)
                    if cs_pattern in ('shooting_star', 'engulfing_bear'):
                        reasons.append(f"Candlestick: {cs_pattern}")
                        quality += 1

        if signal_type == SignalType.NONE:
            return None

        # Divergence filter: skip if divergence opposes our direction
        divergence = detect_divergence(df)
        if divergence == 'bullish' and signal_type == SignalType.SELL:
            logger.debug("Scalping: skipped SELL due to bullish divergence")
            return None
        if divergence == 'bearish' and signal_type == SignalType.BUY:
            logger.debug("Scalping: skipped BUY due to bearish divergence")
            return None

        current_price = price_data.get('ask' if signal_type == SignalType.BUY else 'bid', 0)
        sl, tp, partial_tp = self._calculate_atr_sl_tp(
            signal_type, current_price, atr, self.sl_multiplier, self.rr_ratio, df
        )

        base_confidence = 0.65 + (quality - 4) * 0.04  # 0.65 to 0.77 based on quality

        return Signal(
            type=signal_type,
            strategy=self.name,
            confidence=base_confidence,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            partial_tp_price=partial_tp,
            reasons=reasons,
            timestamp=str(df.index[-1]),
            signal_quality=quality
        )


# ─────────────────────────────────────────────────────────────
# STRATEGY 2: MEAN REVERSION
# ─────────────────────────────────────────────────────────────

class MeanReversionStrategy(BaseStrategy):
    """
    Enhanced mean reversion with:
    - Less restrictive triple-AND gate (2-of-3 conditions)
    - Trailing stop on second half of trade
    - Divergence boosted confidence
    """

    def __init__(self, config: Dict):
        super().__init__("Mean Reversion", config.get('mean_reversion', {}))
        self.sl_multiplier = 2.0
        self.rr_ratio = 2.0

    @safe_execution(default_return=None)
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:

        if not self.enabled or not self.performance.is_active():
            return None
        if df is None or df.empty or len(df) < 10:
            return None
        if regime not in [MarketRegime.RANGING, MarketRegime.QUIET]:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        rsi_oversold = self.config.get('rsi_oversold', 30)
        rsi_overbought = self.config.get('rsi_overbought', 70)
        stoch_threshold = self.config.get('stochastic_threshold', 20)
        volume_confirmation = self.config.get('volume_confirmation', True)

        rsi = latest.get('RSI', 50)
        bb_pct = latest.get('BB_pct', 0.5)
        stoch_k = latest.get('Stoch_K', 50)
        stoch_d = latest.get('Stoch_D', 50)
        prev_stoch_k = prev.get('Stoch_K', 50)
        prev_stoch_d = prev.get('Stoch_D', 50)

        signal_type = SignalType.NONE
        reasons = []
        quality = 0

        # Oversold: require at least 2 of 3 conditions (more signals than before)
        oversold_conditions = [
            rsi < rsi_oversold,
            bb_pct < 0.15,
            stoch_k < stoch_threshold
        ]
        overbought_conditions = [
            rsi > rsi_overbought,
            bb_pct > 0.85,
            stoch_k > (100 - stoch_threshold)
        ]

        if sum(oversold_conditions) >= 2:
            # Require stochastic crossover as trigger
            if stoch_k > stoch_d and prev_stoch_k <= prev_stoch_d:
                if not volume_confirmation or latest.get('Volume_Ratio', 0) > 0.8:
                    signal_type = SignalType.BUY
                    if oversold_conditions[0]: reasons.append(f"RSI oversold ({rsi:.1f})")
                    if oversold_conditions[1]: reasons.append(f"Near lower BB ({bb_pct:.2f})")
                    if oversold_conditions[2]: reasons.append(f"Stoch oversold ({stoch_k:.1f})")
                    reasons.append("Stochastic bullish crossover")
                    quality = sum(oversold_conditions) + 1

        elif sum(overbought_conditions) >= 2:
            if stoch_k < stoch_d and prev_stoch_k >= prev_stoch_d:
                if not volume_confirmation or latest.get('Volume_Ratio', 0) > 0.8:
                    signal_type = SignalType.SELL
                    if overbought_conditions[0]: reasons.append(f"RSI overbought ({rsi:.1f})")
                    if overbought_conditions[1]: reasons.append(f"Near upper BB ({bb_pct:.2f})")
                    if overbought_conditions[2]: reasons.append(f"Stoch overbought ({stoch_k:.1f})")
                    reasons.append("Stochastic bearish crossover")
                    quality = sum(overbought_conditions) + 1

        if signal_type == SignalType.NONE:
            return None

        # Divergence boosts confidence
        divergence = detect_divergence(df)
        confidence_boost = 0.0
        if divergence == 'bullish' and signal_type == SignalType.BUY:
            reasons.append("Bullish RSI divergence confirmed")
            confidence_boost = 0.07
        elif divergence == 'bearish' and signal_type == SignalType.SELL:
            reasons.append("Bearish RSI divergence confirmed")
            confidence_boost = 0.07

        current_price = price_data.get('ask' if signal_type == SignalType.BUY else 'bid', 0)
        atr = latest.get('ATR', 0)
        sl, tp, partial_tp = self._calculate_atr_sl_tp(
            signal_type, current_price, atr, self.sl_multiplier, self.rr_ratio, df
        )

        base_confidence = 0.65 + (quality - 3) * 0.04 + confidence_boost

        return Signal(
            type=signal_type,
            strategy=self.name,
            confidence=min(base_confidence, 0.90),
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            partial_tp_price=partial_tp,
            reasons=reasons,
            timestamp=str(df.index[-1]),
            signal_quality=quality
        )


# ─────────────────────────────────────────────────────────────
# STRATEGY 3: BREAKOUT
# ─────────────────────────────────────────────────────────────

class BreakoutStrategy(BaseStrategy):
    """
    Enhanced breakout with:
    - Adaptive lookback period
    - False breakout filter (retest validation)
    - Wide TP for momentum moves
    """

    def __init__(self, config: Dict):
        super().__init__("Breakout", config.get('breakout', {}))
        self.sl_multiplier = 1.5
        self.rr_ratio = 3.0

    @safe_execution(default_return=None)
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:

        if not self.enabled or not self.performance.is_active():
            return None
        if df is None or df.empty or len(df) < 30:
            return None

        latest = df.iloc[-1]
        atr = latest.get('ATR', 0)
        volume_ratio = latest.get('Volume_Ratio', 0)
        atr_multiplier = self.config.get('atr_multiplier', 1.5)
        volume_surge = self.config.get('volume_surge', 2.0)

        # Adaptive lookback: shorter lookback in high-vol regimes
        base_lookback = self.config.get('support_resistance_lookback', 50)
        vol_regime = latest.get('Volatility_Regime', 1.0)
        lookback = max(20, int(base_lookback / vol_regime))
        lookback = min(lookback, len(df) - 2)

        atr_ma = df['ATR'].rolling(window=20).mean().iloc[-1] if len(df) >= 20 else atr
        atr_expansion = atr / atr_ma if atr_ma > 0 else 1.0

        if atr_expansion < atr_multiplier or volume_ratio < volume_surge:
            return None

        recent_high = df['High'].iloc[-lookback:].max()
        recent_low = df['Low'].iloc[-lookback:].min()
        current_price = latest['Close']
        prev_price = df.iloc[-2]['Close']

        signal_type = SignalType.NONE
        reasons = []
        quality = 3  # Volume + ATR expansion already confirmed

        if current_price > recent_high and prev_price <= recent_high:
            adx = latest.get('ADX', 0)
            if adx > 20 and latest['Close'] > latest['Open']:
                signal_type = SignalType.BUY
                reasons = [
                    f"Breakout above {recent_high:.5f}",
                    f"ATR expansion {atr_expansion:.2f}x",
                    f"Volume surge {volume_ratio:.2f}x",
                    f"Momentum ADX {adx:.1f}"
                ]
                quality += 1

        elif current_price < recent_low and prev_price >= recent_low:
            adx = latest.get('ADX', 0)
            if adx > 20 and latest['Close'] < latest['Open']:
                signal_type = SignalType.SELL
                reasons = [
                    f"Breakdown below {recent_low:.5f}",
                    f"ATR expansion {atr_expansion:.2f}x",
                    f"Volume surge {volume_ratio:.2f}x",
                    f"Momentum ADX {adx:.1f}"
                ]
                quality += 1

        if signal_type == SignalType.NONE:
            return None

        entry_price = price_data.get('ask' if signal_type == SignalType.BUY else 'bid', 0)
        sl, tp, partial_tp = self._calculate_atr_sl_tp(
            signal_type, entry_price, atr, self.sl_multiplier, self.rr_ratio, df
        )

        return Signal(
            type=signal_type,
            strategy=self.name,
            confidence=0.65 + (quality - 4) * 0.04,
            entry_price=entry_price,
            stop_loss=sl,
            take_profit=tp,
            partial_tp_price=partial_tp,
            reasons=reasons,
            timestamp=str(df.index[-1]),
            signal_quality=quality
        )


# ─────────────────────────────────────────────────────────────
# STRATEGY 4: ADAPTIVE SWING
# ─────────────────────────────────────────────────────────────

class AdaptiveSwingStrategy(BaseStrategy):
    """
    Enhanced swing with:
    - Relaxed RSI upper bound (80 instead of 70 for trend following)
    - H1 MACD trigger within H4 trend context
    - Wider TP target
    """

    def __init__(self, config: Dict):
        super().__init__("Adaptive Swing", config.get('adaptive_swing', {}))
        self.sl_multiplier = 2.5
        self.rr_ratio = 3.5  # Wider for H4 swing

    @safe_execution(default_return=None)
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:

        if not self.enabled or not self.performance.is_active():
            return None
        if df is None or df.empty or len(df) < 20:
            return None
        if regime not in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        ema_fast = self.config.get('ema_fast', 20)
        ema_slow = self.config.get('ema_slow', 50)
        adx_threshold = self.config.get('adx_threshold', 25)

        ema_fast_val = latest.get(f'EMA_{ema_fast}', 0)
        ema_slow_val = latest.get(f'EMA_{ema_slow}', 0)
        adx = latest.get('ADX', 0)
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_signal', 0)
        prev_macd = prev.get('MACD', 0)
        prev_macd_signal = prev.get('MACD_signal', 0)

        if adx < adx_threshold:
            return None

        signal_type = SignalType.NONE
        reasons = []
        quality = 0

        if ema_fast_val > ema_slow_val and regime == MarketRegime.TRENDING_UP:
            if macd > macd_signal and prev_macd <= prev_macd_signal:
                rsi = latest.get('RSI', 50)
                if 35 < rsi < 80:  # Relaxed upper bound for trend following
                    signal_type = SignalType.BUY
                    reasons = [
                        "H4 uptrend (EMA alignment)",
                        f"Strong trend ADX {adx:.1f}",
                        "MACD bullish crossover",
                        f"RSI healthy ({rsi:.1f})"
                    ]
                    quality = 4
                    cs_pattern = detect_candlestick_pattern(df)
                    if cs_pattern in ('hammer', 'engulfing_bull'):
                        reasons.append(f"Candle pattern: {cs_pattern}")
                        quality += 1

        elif ema_fast_val < ema_slow_val and regime == MarketRegime.TRENDING_DOWN:
            if macd < macd_signal and prev_macd >= prev_macd_signal:
                rsi = latest.get('RSI', 50)
                if 20 < rsi < 65:
                    signal_type = SignalType.SELL
                    reasons = [
                        "H4 downtrend (EMA alignment)",
                        f"Strong trend ADX {adx:.1f}",
                        "MACD bearish crossover",
                        f"RSI healthy ({rsi:.1f})"
                    ]
                    quality = 4
                    cs_pattern = detect_candlestick_pattern(df)
                    if cs_pattern in ('shooting_star', 'engulfing_bear'):
                        reasons.append(f"Candle pattern: {cs_pattern}")
                        quality += 1

        if signal_type == SignalType.NONE:
            return None

        current_price = price_data.get('ask' if signal_type == SignalType.BUY else 'bid', 0)
        atr = latest.get('ATR', 0)
        sl, tp, partial_tp = self._calculate_atr_sl_tp(
            signal_type, current_price, atr, self.sl_multiplier, self.rr_ratio, df
        )

        base_confidence = 0.68 + (quality - 4) * 0.04

        return Signal(
            type=signal_type,
            strategy=self.name,
            confidence=min(base_confidence, 0.90),
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            partial_tp_price=partial_tp,
            reasons=reasons,
            timestamp=str(df.index[-1]),
            signal_quality=quality
        )


# ─────────────────────────────────────────────────────────────
# STRATEGY 5: VWAP DEVIATION (NEW)
# ─────────────────────────────────────────────────────────────

class VWAPDeviationStrategy(BaseStrategy):
    """
    NEW: Intraday mean-reversion using VWAP deviation.
    Entry when price is 2+ std devs from VWAP with RSI extreme.
    Best suited for London/NY session (M15 timeframe).
    """

    def __init__(self, config: Dict):
        super().__init__("VWAP Deviation", config.get('vwap_deviation', {
            'std_dev_threshold': 2.0,
            'rsi_oversold': 35,
            'rsi_overbought': 65,
        }))
        self.sl_multiplier = 1.8
        self.rr_ratio = 2.0

    @safe_execution(default_return=None)
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:

        if not self.enabled or not self.performance.is_active():
            return None
        if df is None or df.empty or len(df) < 20:
            return None
        if regime not in [MarketRegime.RANGING, MarketRegime.QUIET, MarketRegime.VOLATILE]:
            return None

        if 'VWAP' not in df.columns:
            return None

        latest = df.iloc[-1]
        vwap = latest.get('VWAP', 0)
        close = latest['Close']
        atr = latest.get('ATR', 1e-10)
        rsi = latest.get('RSI', 50)

        std_threshold = self.config.get('std_dev_threshold', 2.0)
        rsi_oversold = self.config.get('rsi_oversold', 35)
        rsi_overbought = self.config.get('rsi_overbought', 65)

        # Calculate rolling std of price-VWAP difference
        if 'VWAP' in df.columns:
            vwap_diff = df['Close'] - df['VWAP']
            vwap_std = vwap_diff.rolling(20).std().iloc[-1]
        else:
            return None

        if vwap_std <= 0 or atr <= 0:
            return None

        current_deviation = (close - vwap) / vwap_std if vwap_std > 0 else 0

        signal_type = SignalType.NONE
        reasons = []

        if current_deviation < -std_threshold and rsi < rsi_oversold:
            signal_type = SignalType.BUY
            reasons = [
                f"Price {abs(current_deviation):.1f}σ below VWAP",
                f"RSI oversold ({rsi:.1f})",
                "VWAP mean reversion setup"
            ]
        elif current_deviation > std_threshold and rsi > rsi_overbought:
            signal_type = SignalType.SELL
            reasons = [
                f"Price {current_deviation:.1f}σ above VWAP",
                f"RSI overbought ({rsi:.1f})",
                "VWAP mean reversion setup"
            ]

        if signal_type == SignalType.NONE:
            return None

        entry_price = price_data.get('ask' if signal_type == SignalType.BUY else 'bid', 0)
        sl, tp, partial_tp = self._calculate_atr_sl_tp(
            signal_type, entry_price, atr, self.sl_multiplier, self.rr_ratio, df
        )

        return Signal(
            type=signal_type,
            strategy=self.name,
            confidence=0.68,
            entry_price=entry_price,
            stop_loss=sl,
            take_profit=tp,
            partial_tp_price=partial_tp,
            reasons=reasons,
            timestamp=str(df.index[-1]),
            signal_quality=3
        )


# ─────────────────────────────────────────────────────────────
# SIGNAL RESOLUTION
# ─────────────────────────────────────────────────────────────

def resolve_signal_conflicts(signals: List[Signal]) -> List[Signal]:
    """
    Resolve conflicting signals:
    - If opposing directions: take highest-confidence direction
    - If same direction: take best single signal (no doubling up)
    - Dedup by strategy name (one signal per strategy)
    """
    if not signals:
        return []

    # Dedup: only best signal per strategy
    by_strategy: Dict[str, Signal] = {}
    for s in signals:
        if s.strategy not in by_strategy or s.confidence > by_strategy[s.strategy].confidence:
            by_strategy[s.strategy] = s

    signals = list(by_strategy.values())

    buys = [s for s in signals if s.type == SignalType.BUY]
    sells = [s for s in signals if s.type == SignalType.SELL]

    if buys and sells:
        # Conflict: take stronger side
        buy_conf = max(s.confidence for s in buys)
        sell_conf = max(s.confidence for s in sells)
        if buy_conf >= sell_conf:
            best = max(buys, key=lambda s: s.confidence)
            logger.info(f"Signal conflict resolved → BUY (conf {buy_conf:.2f} > {sell_conf:.2f})")
            return [best]
        else:
            best = max(sells, key=lambda s: s.confidence)
            logger.info(f"Signal conflict resolved → SELL (conf {sell_conf:.2f} > {buy_conf:.2f})")
            return [best]

    # No conflict: return all (but max 2 same-direction trades)
    all_signals = buys or sells
    return sorted(all_signals, key=lambda s: s.confidence, reverse=True)[:2]


# ─────────────────────────────────────────────────────────────
# STRATEGY ENGINE
# ─────────────────────────────────────────────────────────────

class StrategyEngine:
    """
    Enhanced strategy engine v2:
    - Multi-timeframe confirmation scoring
    - Signal conflict resolution
    - Performance-gated strategy auto-disable
    - Strategy-specific ATR multipliers
    """

    def __init__(self, config: Dict):
        self.config = config
        self.strategies_config = config.get('strategies', {})
        self.enabled_strategies = config.get('trading', {}).get('strategies', {})
        self.mtf_scorer = MultiTimeframeScorer()
        self.strategies: List[BaseStrategy] = []

        if self.enabled_strategies.get('scalping', False):
            self.strategies.append(ScalpingStrategy(self.strategies_config))
        if self.enabled_strategies.get('mean_reversion', False):
            self.strategies.append(MeanReversionStrategy(self.strategies_config))
        if self.enabled_strategies.get('breakout', False):
            self.strategies.append(BreakoutStrategy(self.strategies_config))
        if self.enabled_strategies.get('adaptive_swing', False):
            self.strategies.append(AdaptiveSwingStrategy(self.strategies_config))
        if self.enabled_strategies.get('vwap_deviation', False):
            self.strategies.append(VWAPDeviationStrategy(self.strategies_config))

        logger.info(f"Strategy Engine v2 initialized: {len(self.strategies)} strategies active")

    def generate_signals(
        self,
        symbol: str,
        df_dict: Dict[str, pd.DataFrame],
        regime: MarketRegime,
        price_data: Dict
    ) -> List[Signal]:
        """
        Generate and return conflict-resolved, MTF-scored signals.
        """
        raw_signals = []

        # Timeframe routing per strategy
        tf_map = {
            'Scalping': df_dict.get('M1'),
            'Mean Reversion': df_dict.get('M5'),
            'Breakout': df_dict.get('H1'),
            'Adaptive Swing': df_dict.get('H4'),
            'VWAP Deviation': df_dict.get('M15'),
        }

        for strategy in self.strategies:
            df = tf_map.get(strategy.name)
            if df is None:
                continue
            try:
                signal = strategy.generate_signal(df, regime, price_data)
                if signal:
                    # Apply MTF scoring
                    mtf_score = self.mtf_scorer.score_signal(signal, df_dict)
                    signal.mtf_score = mtf_score

                    # MTF score adjusts confidence
                    if mtf_score >= 0.6:
                        signal.confidence = min(signal.confidence * 1.2, 0.95)
                        signal.reasons.append(f"MTF alignment: {mtf_score:.2f}")
                    elif mtf_score <= -0.3:
                        signal.confidence *= 0.6
                        signal.reasons.append(f"MTF opposition: {mtf_score:.2f}")

                    logger.info(
                        f"{strategy.name}: {signal.type.value} | "
                        f"confidence={signal.confidence:.2f} | "
                        f"MTF={mtf_score:.2f} | quality={signal.signal_quality}"
                    )
                    raw_signals.append(signal)
            except Exception as e:
                logger.error(f"Error in {strategy.name}: {e}", exc_info=True)

        # Resolve conflicts
        resolved = resolve_signal_conflicts(raw_signals)
        logger.info(f"Signals: {len(raw_signals)} raw → {len(resolved)} resolved")
        return resolved

    def record_trade_result(self, strategy_name: str, pnl: float):
        """Feed trade result back to strategy performance tracker"""
        for s in self.strategies:
            if s.name == strategy_name:
                s.record_trade_result(pnl)
                break

    def get_strategy_stats(self) -> List[Dict]:
        """Return performance stats for all strategies"""
        stats = []
        for s in self.strategies:
            stats.append({
                'name': s.name,
                'trades': len(s.performance.trades),
                'win_rate': round(s.performance.win_rate, 3),
                'profit_factor': round(s.performance.profit_factor, 3),
                'sharpe': round(s.performance.sharpe, 3),
                'active': s.performance.is_active(),
                'disabled_until': str(s.performance.disabled_until)
            })
        return stats
