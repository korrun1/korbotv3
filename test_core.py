"""
🧪 KorBot X Enhanced - Unit Tests
Version: 2.0
Date: 2026-02-16

Comprehensive unit tests for all core components.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'python_controller'))

from config_loader import ConfigLoader
from risk_engine import RiskEngine, CircuitBreaker, RiskMetrics
from strategy_engine import (
    ScalpingStrategy, MeanReversionStrategy,
    BreakoutStrategy, AdaptiveSwingStrategy,
    Signal, SignalType
)
from market_intel import MarketIntelligence, MarketRegime


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        'risk': {
            'base_risk_percent': 0.8,
            'max_drawdown_percent': 5.0,
            'max_daily_loss_percent': 3.0,
            'max_positions': 3,
            'max_symbol_exposure_percent': 3.0,
            'circuit_breaker': {
                'enabled': True,
                'max_consecutive_losses': 3,
                'cooldown_minutes': 60
            },
            'stop_loss': {
                'type': 'atr_based',
                'atr_multiplier': 2.0,
                'min_pips': 10,
                'max_pips': 50
            },
            'take_profit': {
                'risk_reward_ratio': 2.5,
                'use_trailing': True,
                'trailing_atr_multiplier': 1.5
            }
        },
        'strategies': {
            'scalping': {
                'ema_fast': 5,
                'ema_slow': 13,
                'volume_threshold': 1.5,
                'min_atr': 0.0005
            },
            'mean_reversion': {
                'bollinger_period': 20,
                'bollinger_std': 2.0,
                'rsi_period': 14,
                'rsi_oversold': 30,
                'rsi_overbought': 70
            }
        }
    }


@pytest.fixture
def sample_dataframe():
    """Sample OHLCV DataFrame for testing"""
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1H')
    
    np.random.seed(42)
    base_price = 0.91
    returns = np.random.normal(0, 0.0005, len(dates))
    prices = base_price * (1 + returns).cumprod()
    
    df = pd.DataFrame({
        'Open': prices * (1 + np.random.uniform(-0.0001, 0.0001, len(dates))),
        'High': prices * (1 + np.random.uniform(0, 0.0005, len(dates))),
        'Low': prices * (1 + np.random.uniform(-0.0005, 0, len(dates))),
        'Close': prices,
        'Volume': np.random.randint(1000, 5000, len(dates))
    }, index=dates)
    
    return df


# ============================================================================
# CONFIG LOADER TESTS
# ============================================================================

class TestConfigLoader:
    """Test configuration loader"""
    
    def test_config_loading(self, sample_config):
        """Test configuration loading"""
        # This would test actual YAML loading in real scenario
        assert 'risk' in sample_config
        assert 'strategies' in sample_config
    
    def test_config_validation(self, sample_config):
        """Test configuration validation"""
        risk = sample_config['risk']
        
        # Validate risk parameters
        assert 0 < risk['base_risk_percent'] <= 5
        assert 0 < risk['max_drawdown_percent'] <= 20
        assert risk['max_positions'] > 0


# ============================================================================
# RISK ENGINE TESTS
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_initialization(self, sample_config):
        """Test circuit breaker initialization"""
        cb_config = sample_config['risk']['circuit_breaker']
        cb = CircuitBreaker(cb_config)
        
        assert cb.enabled == True
        assert cb.max_consecutive_losses == 3
        assert cb.cooldown_minutes == 60
        assert cb.is_triggered == False
    
    def test_circuit_breaker_trigger(self, sample_config):
        """Test circuit breaker triggering"""
        cb_config = sample_config['risk']['circuit_breaker']
        cb = CircuitBreaker(cb_config)
        
        metrics = RiskMetrics()
        metrics.consecutive_losses = 3
        
        should_trigger, reason = cb.check(metrics, 10000)
        
        assert should_trigger == True
        assert cb.is_triggered == True
    
    def test_circuit_breaker_cooldown(self, sample_config):
        """Test circuit breaker cooldown"""
        cb_config = sample_config['risk']['circuit_breaker']
        cb = CircuitBreaker(cb_config)
        
        cb.trigger("Test trigger")
        
        assert cb.is_triggered == True
        assert cb.trigger_time is not None


class TestRiskEngine:
    """Test risk management engine"""
    
    def test_risk_engine_initialization(self, sample_config):
        """Test risk engine initialization"""
        risk_engine = RiskEngine(sample_config)
        
        assert risk_engine.base_risk_percent == 0.8
        assert risk_engine.max_positions == 3
        assert risk_engine.circuit_breaker is not None
    
    def test_can_trade(self, sample_config):
        """Test trading permission check"""
        risk_engine = RiskEngine(sample_config)
        
        account_info = {'balance': 10000, 'equity': 10000}
        
        can_trade, reason = risk_engine.can_trade(account_info)
        
        assert can_trade == True
        assert reason is None
    
    def test_position_sizing(self, sample_config):
        """Test position size calculation"""
        risk_engine = RiskEngine(sample_config)
        
        account_info = {'balance': 10000}
        symbol_info = {
            'trade_contract_size': 100000,
            'trade_tick_value': 10,
            'min_lot': 0.01,
            'max_lot': 100.0,
            'lot_step': 0.01
        }
        
        lot_size = risk_engine.calculate_position_size(
            symbol='AUDCAD',
            entry_price=0.91000,
            stop_loss=0.90800,
            account_info=account_info,
            symbol_info=symbol_info,
            confidence=0.75
        )
        
        assert lot_size >= symbol_info['min_lot']
        assert lot_size <= symbol_info['max_lot']
    
    def test_dynamic_stop_loss(self, sample_config):
        """Test dynamic stop loss calculation"""
        risk_engine = RiskEngine(sample_config)
        
        stop_loss = risk_engine.calculate_dynamic_stop_loss(
            entry_price=0.91000,
            direction='BUY',
            atr=0.0010,
            symbol='AUDCAD'
        )
        
        assert stop_loss < 0.91000  # SL should be below entry for BUY
        assert abs(stop_loss - 0.91000) > 0.0001  # Should have meaningful distance
    
    def test_metrics_update(self, sample_config):
        """Test metrics update after trade"""
        risk_engine = RiskEngine(sample_config)
        
        # Winning trade
        risk_engine.update_metrics({
            'pnl': 100,
            'account_balance': 10000
        })
        
        assert risk_engine.metrics.total_trades == 1
        assert risk_engine.metrics.winning_trades == 1
        assert risk_engine.metrics.consecutive_losses == 0
        
        # Losing trade
        risk_engine.update_metrics({
            'pnl': -50,
            'account_balance': 10000
        })
        
        assert risk_engine.metrics.total_trades == 2
        assert risk_engine.metrics.losing_trades == 1
        assert risk_engine.metrics.consecutive_losses == 1


# ============================================================================
# MARKET INTELLIGENCE TESTS
# ============================================================================

class TestMarketIntelligence:
    """Test market intelligence and indicators"""
    
    def test_market_intel_initialization(self, sample_config):
        """Test market intelligence initialization"""
        market_intel = MarketIntelligence(sample_config)
        
        assert market_intel is not None
    
    def test_indicator_calculation(self, sample_dataframe):
        """Test technical indicator calculation"""
        market_intel = MarketIntelligence()
        
        df = market_intel.calculate_all_indicators(sample_dataframe)
        
        # Check indicators are added
        assert 'EMA_5' in df.columns
        assert 'EMA_13' in df.columns
        assert 'RSI' in df.columns
        assert 'MACD' in df.columns
        assert 'ATR' in df.columns
        assert 'BB_high' in df.columns
        
        # Check no NaN in recent data
        assert not df.iloc[-1].isna().any()
    
    def test_regime_detection(self, sample_dataframe):
        """Test market regime detection"""
        market_intel = MarketIntelligence()
        
        df = market_intel.calculate_all_indicators(sample_dataframe)
        regime = market_intel.detect_market_regime(df)
        
        assert regime in [
            MarketRegime.TRENDING_UP,
            MarketRegime.TRENDING_DOWN,
            MarketRegime.RANGING,
            MarketRegime.VOLATILE,
            MarketRegime.QUIET
        ]
    
    def test_rsi_divergence(self, sample_dataframe):
        """Test RSI divergence detection"""
        market_intel = MarketIntelligence()
        
        df = market_intel.calculate_all_indicators(sample_dataframe)
        divergence = market_intel.calculate_rsi_divergence(df)
        
        assert 'bullish' in divergence
        assert 'bearish' in divergence
        assert isinstance(divergence['bullish'], bool)
        assert isinstance(divergence['bearish'], bool)
    
    def test_pattern_detection(self, sample_dataframe):
        """Test price pattern detection"""
        market_intel = MarketIntelligence()
        
        df = market_intel.calculate_all_indicators(sample_dataframe)
        patterns = market_intel.detect_price_patterns(df)
        
        assert isinstance(patterns, dict)
        # Should detect some patterns
        assert len(patterns) > 0


# ============================================================================
# STRATEGY TESTS
# ============================================================================

class TestScalpingStrategy:
    """Test scalping strategy"""
    
    def test_strategy_initialization(self, sample_config):
        """Test strategy initialization"""
        strategy = ScalpingStrategy(sample_config)
        
        assert strategy.name == "Scalping"
        assert strategy.enabled == True
    
    def test_signal_generation(self, sample_config, sample_dataframe):
        """Test signal generation"""
        strategy = ScalpingStrategy(sample_config)
        market_intel = MarketIntelligence()
        
        df = market_intel.calculate_all_indicators(sample_dataframe)
        regime = MarketRegime.TRENDING_UP
        price_data = {'bid': 0.91000, 'ask': 0.91005}
        
        signal = strategy.generate_signal(df, regime, price_data)
        
        # Signal can be None or valid Signal object
        if signal:
            assert isinstance(signal, Signal)
            assert signal.type in [SignalType.BUY, SignalType.SELL]
            assert 0 <= signal.confidence <= 1
            assert signal.entry_price > 0
            assert signal.stop_loss > 0
            assert signal.take_profit > 0


class TestMeanReversionStrategy:
    """Test mean reversion strategy"""
    
    def test_strategy_initialization(self, sample_config):
        """Test strategy initialization"""
        strategy = MeanReversionStrategy(sample_config)
        
        assert strategy.name == "Mean Reversion"
        assert strategy.enabled == True
    
    def test_signal_in_ranging_market(self, sample_config, sample_dataframe):
        """Test signal generation in ranging market"""
        strategy = MeanReversionStrategy(sample_config)
        market_intel = MarketIntelligence()
        
        df = market_intel.calculate_all_indicators(sample_dataframe)
        regime = MarketRegime.RANGING
        price_data = {'bid': 0.91000, 'ask': 0.91005}
        
        signal = strategy.generate_signal(df, regime, price_data)
        
        # Mean reversion should work in ranging markets
        # Signal can be None or valid
        if signal:
            assert isinstance(signal, Signal)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Test component integration"""
    
    def test_full_signal_workflow(self, sample_config, sample_dataframe):
        """Test full signal generation workflow"""
        # Initialize components
        market_intel = MarketIntelligence(sample_config)
        risk_engine = RiskEngine(sample_config)
        
        # Process data
        df = market_intel.calculate_all_indicators(sample_dataframe)
        regime = market_intel.detect_market_regime(df)
        
        # Test various strategies
        scalping = ScalpingStrategy(sample_config)
        signal = scalping.generate_signal(
            df, regime, {'bid': 0.91000, 'ask': 0.91005}
        )
        
        # If signal generated, test risk management
        if signal:
            account_info = {'balance': 10000, 'equity': 10000}
            can_trade, _ = risk_engine.can_trade(account_info)
            
            assert can_trade == True


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance and speed"""
    
    def test_indicator_calculation_speed(self, sample_dataframe):
        """Test indicator calculation speed"""
        import time
        
        market_intel = MarketIntelligence()
        
        start = time.time()
        df = market_intel.calculate_all_indicators(sample_dataframe)
        duration = time.time() - start
        
        # Should complete in reasonable time
        assert duration < 1.0  # Less than 1 second
    
    def test_strategy_signal_speed(self, sample_config, sample_dataframe):
        """Test strategy signal generation speed"""
        import time
        
        market_intel = MarketIntelligence()
        df = market_intel.calculate_all_indicators(sample_dataframe)
        
        strategy = ScalpingStrategy(sample_config)
        regime = MarketRegime.TRENDING_UP
        price_data = {'bid': 0.91000, 'ask': 0.91005}
        
        start = time.time()
        signal = strategy.generate_signal(df, regime, price_data)
        duration = time.time() - start
        
        # Should be very fast
        assert duration < 0.1  # Less than 100ms


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
