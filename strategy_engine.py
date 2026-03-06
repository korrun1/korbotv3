"""
🎯 KorBot X Enhanced - Strategy Engine
Version: 2.0
Date: 2026-02-16

Enhanced strategy engine with improved filters, multi-timeframe analysis,
and robust signal generation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging
from dataclasses import dataclass

from market_intel import MarketIntelligence, MarketRegime
from utils import safe_execution, is_trading_time, is_news_time

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types"""
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


@dataclass
class Signal:
    """Trading signal"""
    type: SignalType
    strategy: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reasons: List[str]
    timestamp: str


class BaseStrategy:
    """Base class for all strategies"""
    
    def __init__(self, name: str, config: Dict):
        """
        Initialize strategy
        
        Args:
            name: Strategy name
            config: Strategy configuration
        """
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:
        """
        Generate trading signal
        
        Args:
            df: DataFrame with indicators
            regime: Current market regime
            price_data: Current price data
            
        Returns:
            Signal object or None
        """
        raise NotImplementedError("Subclasses must implement generate_signal")
    
    def _apply_time_filters(self) -> bool:
        """Apply time-based filters"""
        time_filters = self.config.get('time_filters', {})
        
        # Check trading hours
        trading_hours = time_filters.get('trading_hours', '00:00-23:59')
        if not is_trading_time(trading_hours):
            return False
        
        # Avoid news times
        if time_filters.get('avoid_news', False) and is_news_time():
            return False
        
        return True


class ScalpingStrategy(BaseStrategy):
    """Enhanced scalping strategy with noise filtering"""
    
    def __init__(self, config: Dict):
        super().__init__("Scalping", config.get('scalping', {}))
    
    @safe_execution(default_return=None)
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:
        """Generate scalping signal"""
        
        if not self.enabled or df is None or df.empty:
            return None
        
        # Only trade in trending markets for scalping
        if regime not in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            return None
        
        # Apply time filters
        if not self._apply_time_filters():
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Get parameters
        ema_fast = self.config.get('ema_fast', 5)
        ema_slow = self.config.get('ema_slow', 13)
        volume_threshold = self.config.get('volume_threshold', 1.5)
        min_atr = self.config.get('min_atr', 0.0005)
        
        # Check minimum volatility
        atr = latest.get('ATR', 0)
        if atr < min_atr:
            logger.debug(f"Scalping: ATR too low ({atr:.6f})")
            return None
        
        # Volume confirmation
        volume_ratio = latest.get('Volume_Ratio', 0)
        if volume_ratio < volume_threshold:
            logger.debug(f"Scalping: Volume too low (ratio {volume_ratio:.2f})")
            return None
        
        # EMA crossover
        ema_fast_curr = latest.get(f'EMA_{ema_fast}', 0)
        ema_slow_curr = latest.get(f'EMA_{ema_slow}', 0)
        ema_fast_prev = prev.get(f'EMA_{ema_fast}', 0)
        ema_slow_prev = prev.get(f'EMA_{ema_slow}', 0)
        
        signal_type = SignalType.NONE
        reasons = []
        
        # Bullish crossover
        if (ema_fast_curr > ema_slow_curr and
            ema_fast_prev <= ema_slow_prev):
            
            # Additional filters
            # 1. Price action confirmation
            if latest['Close'] > latest['Open']:  # Bullish candle
                reasons.append("Bullish EMA crossover")
                reasons.append("Bullish candle confirmation")
                
                # 2. ADX check (trend strength)
                adx = latest.get('ADX', 0)
                if adx > 20:
                    reasons.append(f"Strong trend (ADX {adx:.1f})")
                    
                    # 3. Not overbought
                    rsi = latest.get('RSI', 50)
                    if rsi < 70:
                        reasons.append(f"Not overbought (RSI {rsi:.1f})")
                        signal_type = SignalType.BUY
        
        # Bearish crossover
        elif (ema_fast_curr < ema_slow_curr and
              ema_fast_prev >= ema_slow_prev):
            
            # Additional filters
            if latest['Close'] < latest['Open']:  # Bearish candle
                reasons.append("Bearish EMA crossover")
                reasons.append("Bearish candle confirmation")
                
                adx = latest.get('ADX', 0)
                if adx > 20:
                    reasons.append(f"Strong trend (ADX {adx:.1f})")
                    
                    rsi = latest.get('RSI', 50)
                    if rsi > 30:
                        reasons.append(f"Not oversold (RSI {rsi:.1f})")
                        signal_type = SignalType.SELL
        
        if signal_type == SignalType.NONE:
            return None
        
        # Calculate entry, SL, TP
        current_price = price_data.get('ask' if signal_type == SignalType.BUY else 'bid', 0)
        atr_multiplier = 2.0
        
        if signal_type == SignalType.BUY:
            stop_loss = current_price - (atr * atr_multiplier)
            take_profit = current_price + (atr * atr_multiplier * 2.5)
        else:
            stop_loss = current_price + (atr * atr_multiplier)
            take_profit = current_price - (atr * atr_multiplier * 2.5)
        
        return Signal(
            type=signal_type,
            strategy=self.name,
            confidence=0.75,  # Will be enhanced by AI
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasons=reasons,
            timestamp=str(df.index[-1])
        )


class MeanReversionStrategy(BaseStrategy):
    """Enhanced mean reversion strategy"""
    
    def __init__(self, config: Dict):
        super().__init__("Mean Reversion", config.get('mean_reversion', {}))
    
    @safe_execution(default_return=None)
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:
        """Generate mean reversion signal"""
        
        if not self.enabled or df is None or df.empty:
            return None
        
        # Only trade in ranging markets
        if regime not in [MarketRegime.RANGING, MarketRegime.QUIET]:
            return None
        
        latest = df.iloc[-1]
        
        # Get parameters
        rsi_oversold = self.config.get('rsi_oversold', 30)
        rsi_overbought = self.config.get('rsi_overbought', 70)
        stoch_threshold = self.config.get('stochastic_threshold', 20)
        volume_confirmation = self.config.get('volume_confirmation', True)
        
        signal_type = SignalType.NONE
        reasons = []
        
        # Get indicators
        rsi = latest.get('RSI', 50)
        bb_pct = latest.get('BB_pct', 0.5)
        stoch_k = latest.get('Stoch_K', 50)
        stoch_d = latest.get('Stoch_D', 50)
        
        # Oversold conditions (BUY)
        if (rsi < rsi_oversold and
            bb_pct < 0.1 and  # Price near lower BB
            stoch_k < stoch_threshold):
            
            reasons.append(f"Oversold (RSI {rsi:.1f})")
            reasons.append(f"Price at lower Bollinger Band ({bb_pct:.2f})")
            reasons.append(f"Stochastic oversold ({stoch_k:.1f})")
            
            # Stochastic bullish crossover
            prev_stoch_k = df.iloc[-2].get('Stoch_K', 50)
            prev_stoch_d = df.iloc[-2].get('Stoch_D', 50)
            
            if stoch_k > stoch_d and prev_stoch_k <= prev_stoch_d:
                reasons.append("Stochastic bullish crossover")
                
                # Volume confirmation
                if not volume_confirmation or latest.get('Volume_Ratio', 0) > 1.0:
                    reasons.append("Volume confirmed")
                    signal_type = SignalType.BUY
        
        # Overbought conditions (SELL)
        elif (rsi > rsi_overbought and
              bb_pct > 0.9 and  # Price near upper BB
              stoch_k > (100 - stoch_threshold)):
            
            reasons.append(f"Overbought (RSI {rsi:.1f})")
            reasons.append(f"Price at upper Bollinger Band ({bb_pct:.2f})")
            reasons.append(f"Stochastic overbought ({stoch_k:.1f})")
            
            # Stochastic bearish crossover
            prev_stoch_k = df.iloc[-2].get('Stoch_K', 50)
            prev_stoch_d = df.iloc[-2].get('Stoch_D', 50)
            
            if stoch_k < stoch_d and prev_stoch_k >= prev_stoch_d:
                reasons.append("Stochastic bearish crossover")
                
                if not volume_confirmation or latest.get('Volume_Ratio', 0) > 1.0:
                    reasons.append("Volume confirmed")
                    signal_type = SignalType.SELL
        
        if signal_type == SignalType.NONE:
            return None
        
        # Calculate entry, SL, TP
        current_price = price_data.get('ask' if signal_type == SignalType.BUY else 'bid', 0)
        bb_mid = latest.get('BB_mid', current_price)
        atr = latest.get('ATR', 0)
        
        if signal_type == SignalType.BUY:
            stop_loss = latest.get('BB_low', current_price - atr * 2)
            take_profit = bb_mid  # Target mean reversion to middle BB
        else:
            stop_loss = latest.get('BB_high', current_price + atr * 2)
            take_profit = bb_mid
        
        return Signal(
            type=signal_type,
            strategy=self.name,
            confidence=0.70,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasons=reasons,
            timestamp=str(df.index[-1])
        )


class BreakoutStrategy(BaseStrategy):
    """Enhanced breakout strategy with confirmation layers"""
    
    def __init__(self, config: Dict):
        super().__init__("Breakout", config.get('breakout', {}))
    
    @safe_execution(default_return=None)
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:
        """Generate breakout signal"""
        
        if not self.enabled or df is None or df.empty:
            return None
        
        latest = df.iloc[-1]
        
        # Get parameters
        atr_multiplier = self.config.get('atr_multiplier', 1.5)
        volume_surge = self.config.get('volume_surge', 2.0)
        lookback = self.config.get('support_resistance_lookback', 50)
        
        signal_type = SignalType.NONE
        reasons = []
        
        # Get indicators
        atr = latest.get('ATR', 0)
        volume_ratio = latest.get('Volume_Ratio', 0)
        
        # ATR expansion check (volatility increase)
        atr_ma = df['ATR'].rolling(window=20).mean().iloc[-1] if len(df) >= 20 else atr
        atr_expansion = atr / atr_ma if atr_ma > 0 else 1.0
        
        if atr_expansion < atr_multiplier:
            return None  # Not enough volatility expansion
        
        # Volume surge check
        if volume_ratio < volume_surge:
            return None  # Not enough volume
        
        # Support/Resistance breakout
        recent_high = df['High'].iloc[-lookback:].max()
        recent_low = df['Low'].iloc[-lookback:].min()
        
        current_price = latest['Close']
        prev_price = df.iloc[-2]['Close']
        
        # Bullish breakout
        if current_price > recent_high and prev_price <= recent_high:
            reasons.append(f"Breakout above resistance ({recent_high:.5f})")
            reasons.append(f"ATR expansion ({atr_expansion:.2f}x)")
            reasons.append(f"Volume surge ({volume_ratio:.2f}x)")
            
            # ADX confirmation
            adx = latest.get('ADX', 0)
            if adx > 20:
                reasons.append(f"Trend strengthening (ADX {adx:.1f})")
                
                # Price action confirmation
                if latest['Close'] > latest['Open']:
                    reasons.append("Bullish candle confirmation")
                    signal_type = SignalType.BUY
        
        # Bearish breakout
        elif current_price < recent_low and prev_price >= recent_low:
            reasons.append(f"Breakdown below support ({recent_low:.5f})")
            reasons.append(f"ATR expansion ({atr_expansion:.2f}x)")
            reasons.append(f"Volume surge ({volume_ratio:.2f}x)")
            
            adx = latest.get('ADX', 0)
            if adx > 20:
                reasons.append(f"Trend strengthening (ADX {adx:.1f})")
                
                if latest['Close'] < latest['Open']:
                    reasons.append("Bearish candle confirmation")
                    signal_type = SignalType.SELL
        
        if signal_type == SignalType.NONE:
            return None
        
        # Calculate entry, SL, TP
        current_price = price_data.get('ask' if signal_type == SignalType.BUY else 'bid', 0)
        
        if signal_type == SignalType.BUY:
            stop_loss = recent_high - (atr * 1.5)  # Stop below breakout level
            take_profit = current_price + (atr * 3.0)  # Larger target for breakouts
        else:
            stop_loss = recent_low + (atr * 1.5)
            take_profit = current_price - (atr * 3.0)
        
        return Signal(
            type=signal_type,
            strategy=self.name,
            confidence=0.72,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasons=reasons,
            timestamp=str(df.index[-1])
        )


class AdaptiveSwingStrategy(BaseStrategy):
    """Enhanced adaptive swing strategy"""
    
    def __init__(self, config: Dict):
        super().__init__("Adaptive Swing", config.get('adaptive_swing', {}))
    
    @safe_execution(default_return=None)
    def generate_signal(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        price_data: Dict
    ) -> Optional[Signal]:
        """Generate swing signal"""
        
        if not self.enabled or df is None or df.empty:
            return None
        
        # Only trade in trending markets
        if regime not in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Get parameters
        ema_fast = self.config.get('ema_fast', 20)
        ema_slow = self.config.get('ema_slow', 50)
        adx_threshold = self.config.get('adx_threshold', 25)
        
        signal_type = SignalType.NONE
        reasons = []
        
        # Get indicators
        ema_fast_val = latest.get(f'EMA_{ema_fast}', 0)
        ema_slow_val = latest.get(f'EMA_{ema_slow}', 0)
        adx = latest.get('ADX', 0)
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_signal', 0)
        prev_macd = prev.get('MACD', 0)
        prev_macd_signal = prev.get('MACD_signal', 0)
        
        # Strong trend check
        if adx < adx_threshold:
            return None
        
        # Bullish signal
        if (ema_fast_val > ema_slow_val and
            regime == MarketRegime.TRENDING_UP):
            
            # MACD bullish crossover
            if macd > macd_signal and prev_macd <= prev_macd_signal:
                reasons.append("Uptrend confirmed (EMAs)")
                reasons.append(f"Strong trend (ADX {adx:.1f})")
                reasons.append("MACD bullish crossover")
                
                # Additional confirmation
                rsi = latest.get('RSI', 50)
                if 40 < rsi < 70:
                    reasons.append(f"RSI healthy zone ({rsi:.1f})")
                    signal_type = SignalType.BUY
        
        # Bearish signal
        elif (ema_fast_val < ema_slow_val and
              regime == MarketRegime.TRENDING_DOWN):
            
            # MACD bearish crossover
            if macd < macd_signal and prev_macd >= prev_macd_signal:
                reasons.append("Downtrend confirmed (EMAs)")
                reasons.append(f"Strong trend (ADX {adx:.1f})")
                reasons.append("MACD bearish crossover")
                
                rsi = latest.get('RSI', 50)
                if 30 < rsi < 60:
                    reasons.append(f"RSI healthy zone ({rsi:.1f})")
                    signal_type = SignalType.SELL
        
        if signal_type == SignalType.NONE:
            return None
        
        # Calculate entry, SL, TP
        current_price = price_data.get('ask' if signal_type == SignalType.BUY else 'bid', 0)
        atr = latest.get('ATR', 0)
        
        if signal_type == SignalType.BUY:
            stop_loss = current_price - (atr * 2.5)
            take_profit = current_price + (atr * 5.0)  # Larger RR for swing
        else:
            stop_loss = current_price + (atr * 2.5)
            take_profit = current_price - (atr * 5.0)
        
        return Signal(
            type=signal_type,
            strategy=self.name,
            confidence=0.75,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasons=reasons,
            timestamp=str(df.index[-1])
        )


class StrategyEngine:
    """Main strategy engine coordinating all strategies"""
    
    def __init__(self, config: Dict):
        """
        Initialize strategy engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.strategies_config = config.get('strategies', {})
        self.enabled_strategies = config.get('trading', {}).get('strategies', {})
        
        # Initialize strategies
        self.strategies = []
        
        if self.enabled_strategies.get('scalping', False):
            self.strategies.append(ScalpingStrategy(self.strategies_config))
        
        if self.enabled_strategies.get('mean_reversion', False):
            self.strategies.append(MeanReversionStrategy(self.strategies_config))
        
        if self.enabled_strategies.get('breakout', False):
            self.strategies.append(BreakoutStrategy(self.strategies_config))
        
        if self.enabled_strategies.get('adaptive_swing', False):
            self.strategies.append(AdaptiveSwingStrategy(self.strategies_config))
        
        logger.info(f"Strategy Engine initialized with {len(self.strategies)} strategies")
    
    def generate_signals(
        self,
        symbol: str,
        df_dict: Dict[str, pd.DataFrame],
        regime: MarketRegime,
        price_data: Dict
    ) -> List[Signal]:
        """
        Generate signals from all strategies
        
        Args:
            symbol: Trading symbol
            df_dict: Dictionary of DataFrames for each timeframe
            regime: Current market regime
            price_data: Current price data
            
        Returns:
            List of signals
        """
        signals = []
        
        for strategy in self.strategies:
            # Get appropriate timeframe for strategy
            if isinstance(strategy, ScalpingStrategy):
                df = df_dict.get('M1')
            elif isinstance(strategy, MeanReversionStrategy):
                df = df_dict.get('M5')
            elif isinstance(strategy, BreakoutStrategy):
                df = df_dict.get('H1')
            elif isinstance(strategy, AdaptiveSwingStrategy):
                df = df_dict.get('H4')
            else:
                df = None
            
            if df is None:
                continue
            
            try:
                signal = strategy.generate_signal(df, regime, price_data)
                if signal:
                    logger.info(
                        f"{strategy.name} generated {signal.type.value} signal "
                        f"with confidence {signal.confidence:.2f}"
                    )
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error generating signal from {strategy.name}: {e}", exc_info=True)
        
        return signals


if __name__ == "__main__":
    # Test strategy engine
    from config_loader import get_config
    from data_layer import DataLayer
    from market_intel import MarketIntelligence
    
    config = get_config()
    data_layer = DataLayer(config)
    market_intel = MarketIntelligence(config)
    strategy_engine = StrategyEngine(config)
    
    symbol = config.get('trading.symbol', 'AUDCAD')
    
    # Get data for all timeframes
    df_dict = {}
    for tf in ['M1', 'M5', 'H1', 'H4']:
        df = data_layer.get_historical_data(symbol, tf, 200)
        if df is not None:
            df = market_intel.calculate_all_indicators(df)
            df_dict[tf] = df
    
    # Get current price and regime
    price_data = data_layer.get_current_price(symbol)
    regime = market_intel.detect_market_regime(df_dict.get('H1'))
    
    # Generate signals
    signals = strategy_engine.generate_signals(symbol, df_dict, regime, price_data)
    
    print(f"\nGenerated {len(signals)} signals:")
    for signal in signals:
        print(f"\n{signal.strategy}: {signal.type.value}")
        print(f"Confidence: {signal.confidence:.2f}")
        print(f"Entry: {signal.entry_price:.5f}")
        print(f"SL: {signal.stop_loss:.5f}")
        print(f"TP: {signal.take_profit:.5f}")
        print(f"Reasons: {', '.join(signal.reasons)}")
    
    data_layer.cleanup()
