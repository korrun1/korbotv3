"""
📈 KorBot X Enhanced - Market Intelligence
Version: 2.0
Date: 2026-02-16

Advanced market analysis with technical indicators, market regime detection,
and enhanced pattern recognition.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging
from ta import trend, momentum, volatility, volume as ta_volume
from scipy.signal import argrelextrema
from enum import Enum

from utils import memoize, PerformanceTimer

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"


class MarketIntelligence:
    """Advanced market analysis and intelligence"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize market intelligence
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        logger.info("Market Intelligence initialized")
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicators
        """
        if df is None or df.empty:
            return df
        
        df = df.copy()
        
        with PerformanceTimer("Indicators Calculation", logger):
            # Trend Indicators
            df = self._add_trend_indicators(df)
            
            # Momentum Indicators
            df = self._add_momentum_indicators(df)
            
            # Volatility Indicators
            df = self._add_volatility_indicators(df)
            
            # Volume Indicators
            df = self._add_volume_indicators(df)
            
            # Custom Indicators
            df = self._add_custom_indicators(df)
        
        return df
    
    def _add_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add trend indicators"""
        
        # EMAs (multiple periods)
        for period in [5, 13, 20, 50, 100, 200]:
            df[f'EMA_{period}'] = trend.ema_indicator(df['Close'], window=period)
        
        # MACD
        macd = trend.MACD(df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MACD_diff'] = macd.macd_diff()
        
        # ADX (Average Directional Index)
        adx = trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
        df['ADX'] = adx.adx()
        df['ADX_pos'] = adx.adx_pos()
        df['ADX_neg'] = adx.adx_neg()
        
        # Ichimoku Cloud
        high_9 = df['High'].rolling(window=9).max()
        low_9 = df['Low'].rolling(window=9).min()
        df['Ichimoku_conversion'] = (high_9 + low_9) / 2
        
        high_26 = df['High'].rolling(window=26).max()
        low_26 = df['Low'].rolling(window=26).min()
        df['Ichimoku_base'] = (high_26 + low_26) / 2
        
        return df
    
    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum indicators"""
        
        # RSI
        df['RSI'] = momentum.rsi(df['Close'], window=14)
        
        # Stochastic Oscillator
        stoch = momentum.StochasticOscillator(
            df['High'], df['Low'], df['Close'],
            window=14, smooth_window=3
        )
        df['Stoch_K'] = stoch.stoch()
        df['Stoch_D'] = stoch.stoch_signal()
        
        # Williams %R
        df['Williams_R'] = momentum.williams_r(
            df['High'], df['Low'], df['Close'], lbp=14
        )
        
        # Rate of Change (ROC)
        df['ROC'] = momentum.roc(df['Close'], window=12)
        
        # Money Flow Index (MFI)
        df['MFI'] = ta_volume.money_flow_index(
            df['High'], df['Low'], df['Close'], df['Volume'], window=14
        )
        
        return df
    
    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility indicators"""
        
        # Bollinger Bands
        bollinger = volatility.BollingerBands(df['Close'], window=20, window_dev=2)
        df['BB_high'] = bollinger.bollinger_hband()
        df['BB_mid'] = bollinger.bollinger_mavg()
        df['BB_low'] = bollinger.bollinger_lband()
        df['BB_width'] = bollinger.bollinger_wband()
        df['BB_pct'] = bollinger.bollinger_pband()
        
        # ATR (Average True Range)
        atr = volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14)
        df['ATR'] = atr.average_true_range()
        
        # Keltner Channels
        keltner = volatility.KeltnerChannel(
            df['High'], df['Low'], df['Close'], window=20
        )
        df['KC_high'] = keltner.keltner_channel_hband()
        df['KC_mid'] = keltner.keltner_channel_mband()
        df['KC_low'] = keltner.keltner_channel_lband()
        
        # Historical Volatility
        returns = df['Close'].pct_change()
        df['Historical_Vol'] = returns.rolling(window=20).std() * np.sqrt(252)
        
        return df
    
    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume indicators"""
        
        # Volume Moving Average
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # On-Balance Volume (OBV)
        df['OBV'] = ta_volume.on_balance_volume(df['Close'], df['Volume'])
        
        # Accumulation/Distribution Line
        df['ADL'] = ta_volume.acc_dist_index(
            df['High'], df['Low'], df['Close'], df['Volume']
        )
        
        # Chaikin Money Flow
        df['CMF'] = ta_volume.chaikin_money_flow(
            df['High'], df['Low'], df['Close'], df['Volume'], window=20
        )
        
        # Volume Price Trend
        df['VPT'] = ta_volume.volume_price_trend(df['Close'], df['Volume'])
        
        return df
    
    def _add_custom_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add custom indicators"""
        
        # Price Momentum
        df['Price_Momentum_5'] = df['Close'].pct_change(5)
        df['Price_Momentum_10'] = df['Close'].pct_change(10)
        df['Price_Momentum_20'] = df['Close'].pct_change(20)
        
        # Volatility Regime
        atr_ma = df['ATR'].rolling(window=20).mean()
        df['Volatility_Regime'] = df['ATR'] / atr_ma
        
        # Trend Strength
        df['Trend_Strength'] = abs(df['EMA_20'] - df['EMA_50']) / df['ATR']
        
        # Support/Resistance Levels
        df = self._identify_support_resistance(df)
        
        return df
    
    def _identify_support_resistance(self, df: pd.DataFrame, order: int = 5) -> pd.DataFrame:
        """
        Identify support and resistance levels
        
        Args:
            df: DataFrame with price data
            order: Order for local extrema detection
            
        Returns:
            DataFrame with support/resistance levels
        """
        # Find local maxima (resistance)
        local_max = argrelextrema(df['High'].values, np.greater, order=order)[0]
        
        # Find local minima (support)
        local_min = argrelextrema(df['Low'].values, np.less, order=order)[0]
        
        # Initialize columns
        df['Is_Resistance'] = False
        df['Is_Support'] = False
        
        if len(local_max) > 0:
            df.iloc[local_max, df.columns.get_loc('Is_Resistance')] = True
        
        if len(local_min) > 0:
            df.iloc[local_min, df.columns.get_loc('Is_Support')] = True
        
        # Calculate distance to nearest support/resistance
        if len(local_max) > 0:
            resistance_levels = df.iloc[local_max]['High'].values
            df['Nearest_Resistance'] = df['Close'].apply(
                lambda x: min([abs(x - r) for r in resistance_levels if r > x], default=np.nan)
            )
        else:
            df['Nearest_Resistance'] = np.nan
        
        if len(local_min) > 0:
            support_levels = df.iloc[local_min]['Low'].values
            df['Nearest_Support'] = df['Close'].apply(
                lambda x: min([abs(x - s) for s in support_levels if s < x], default=np.nan)
            )
        else:
            df['Nearest_Support'] = np.nan
        
        return df
    
    def detect_market_regime(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detect current market regime
        
        Args:
            df: DataFrame with indicators
            
        Returns:
            MarketRegime enum
        """
        if df is None or df.empty or len(df) < 50:
            return MarketRegime.QUIET
        
        # Get latest values
        latest = df.iloc[-1]
        
        # Check ADX for trend strength
        adx = latest.get('ADX', 0)
        
        # Check ATR for volatility
        atr = latest.get('ATR', 0)
        atr_ma = df['ATR'].rolling(window=20).mean().iloc[-1] if 'ATR' in df else 0
        volatility_ratio = atr / atr_ma if atr_ma > 0 else 1.0
        
        # High volatility
        if volatility_ratio > 1.5:
            return MarketRegime.VOLATILE
        
        # Low volatility
        if volatility_ratio < 0.5:
            return MarketRegime.QUIET
        
        # Strong trend
        if adx > 25:
            # Check trend direction
            ema_20 = latest.get('EMA_20', 0)
            ema_50 = latest.get('EMA_50', 0)
            
            if ema_20 > ema_50:
                return MarketRegime.TRENDING_UP
            else:
                return MarketRegime.TRENDING_DOWN
        
        # Ranging market
        return MarketRegime.RANGING
    
    def calculate_rsi_divergence(self, df: pd.DataFrame, lookback: int = 20) -> Dict:
        """
        Detect RSI divergence
        
        Args:
            df: DataFrame with price and RSI
            lookback: Lookback period
            
        Returns:
            Dictionary with divergence information
        """
        if df is None or df.empty or len(df) < lookback or 'RSI' not in df:
            return {'bullish': False, 'bearish': False}
        
        recent_df = df.iloc[-lookback:]
        
        # Find price peaks and troughs
        price_peaks = argrelextrema(recent_df['Close'].values, np.greater, order=3)[0]
        price_troughs = argrelextrema(recent_df['Close'].values, np.less, order=3)[0]
        
        # Find RSI peaks and troughs
        rsi_peaks = argrelextrema(recent_df['RSI'].values, np.greater, order=3)[0]
        rsi_troughs = argrelextrema(recent_df['RSI'].values, np.less, order=3)[0]
        
        bullish_divergence = False
        bearish_divergence = False
        
        # Bullish divergence: price lower low, RSI higher low
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            price_ll = recent_df.iloc[price_troughs[-2]]['Close'] > recent_df.iloc[price_troughs[-1]]['Close']
            rsi_hl = recent_df.iloc[rsi_troughs[-2]]['RSI'] < recent_df.iloc[rsi_troughs[-1]]['RSI']
            bullish_divergence = price_ll and rsi_hl
        
        # Bearish divergence: price higher high, RSI lower high
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            price_hh = recent_df.iloc[price_peaks[-2]]['Close'] < recent_df.iloc[price_peaks[-1]]['Close']
            rsi_lh = recent_df.iloc[rsi_peaks[-2]]['RSI'] > recent_df.iloc[rsi_peaks[-1]]['RSI']
            bearish_divergence = price_hh and rsi_lh
        
        return {
            'bullish': bullish_divergence,
            'bearish': bearish_divergence
        }
    
    def detect_price_patterns(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Detect common price patterns
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary of detected patterns
        """
        if df is None or df.empty or len(df) < 3:
            return {}
        
        patterns = {}
        
        # Get last 3 candles
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        
        # Pin Bar (Hammer/Shooting Star)
        body_c3 = abs(c3['Close'] - c3['Open'])
        total_range_c3 = c3['High'] - c3['Low']
        
        if total_range_c3 > 0:
            # Bullish Pin Bar (Hammer)
            lower_wick = min(c3['Open'], c3['Close']) - c3['Low']
            patterns['bullish_pin_bar'] = (
                lower_wick > 2 * body_c3 and
                (c3['High'] - max(c3['Open'], c3['Close'])) < body_c3
            )
            
            # Bearish Pin Bar (Shooting Star)
            upper_wick = c3['High'] - max(c3['Open'], c3['Close'])
            patterns['bearish_pin_bar'] = (
                upper_wick > 2 * body_c3 and
                (min(c3['Open'], c3['Close']) - c3['Low']) < body_c3
            )
        
        # Engulfing Pattern
        bullish_c2 = c2['Close'] < c2['Open']
        bullish_c3 = c3['Close'] > c3['Open']
        patterns['bullish_engulfing'] = (
            bullish_c2 and bullish_c3 and
            c3['Open'] < c2['Close'] and
            c3['Close'] > c2['Open']
        )
        
        bearish_c2 = c2['Close'] > c2['Open']
        bearish_c3 = c3['Close'] < c3['Open']
        patterns['bearish_engulfing'] = (
            bearish_c2 and bearish_c3 and
            c3['Open'] > c2['Close'] and
            c3['Close'] < c2['Open']
        )
        
        # Doji
        patterns['doji'] = body_c3 < 0.1 * total_range_c3 if total_range_c3 > 0 else False
        
        return patterns
    
    def calculate_market_microstructure(self, price_data: Dict) -> Dict:
        """
        Calculate market microstructure metrics
        
        Args:
            price_data: Dictionary with bid/ask prices
            
        Returns:
            Dictionary with microstructure metrics
        """
        if not price_data:
            return {}
        
        bid = price_data.get('bid', 0)
        ask = price_data.get('ask', 0)
        spread = ask - bid
        
        mid_price = (bid + ask) / 2
        
        return {
            'spread': spread,
            'spread_bps': (spread / mid_price * 10000) if mid_price > 0 else 0,
            'mid_price': mid_price
        }


if __name__ == "__main__":
    # Test market intelligence
    import sys
    sys.path.append('.')
    
    from data_layer import DataLayer
    from config_loader import get_config
    
    config = get_config()
    data_layer = DataLayer(config)
    market_intel = MarketIntelligence(config)
    
    symbol = config.get('trading.symbol', 'AUDCAD')
    
    # Get data
    df = data_layer.get_historical_data(symbol, 'H1', 200)
    
    if df is not None:
        # Calculate indicators
        df = market_intel.calculate_all_indicators(df)
        print(f"Calculated indicators for {len(df)} bars")
        print(df.tail())
        
        # Detect regime
        regime = market_intel.detect_market_regime(df)
        print(f"Market regime: {regime.value}")
        
        # Detect patterns
        patterns = market_intel.detect_price_patterns(df)
        print(f"Detected patterns: {patterns}")
        
        # RSI divergence
        divergence = market_intel.calculate_rsi_divergence(df)
        print(f"RSI divergence: {divergence}")
    
    data_layer.cleanup()
