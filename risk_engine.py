"""
🛡️ KorBot X Enhanced - Risk Management Engine
Version: 2.0
Date: 2026-02-16

Enhanced risk management with circuit breaker, dynamic sizing,
and advanced position management.
"""

import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd

logger = logging.getLogger(__name__)


class TradingState(Enum):
    """Trading state"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class RiskMetrics:
    """Risk metrics tracker"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    consecutive_losses: int = 0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    open_exposure: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)


class CircuitBreaker:
    """Circuit breaker to halt trading on excessive losses"""
    
    def __init__(self, config: Dict):
        """
        Initialize circuit breaker
        
        Args:
            config: Circuit breaker configuration
        """
        self.enabled = config.get('enabled', True)
        self.max_consecutive_losses = config.get('max_consecutive_losses', 3)
        self.cooldown_minutes = config.get('cooldown_minutes', 60)
        
        self.is_triggered = False
        self.trigger_time = None
        self.trigger_reason = None
    
    def check(self, risk_metrics: RiskMetrics, account_balance: float) -> Tuple[bool, Optional[str]]:
        """
        Check if circuit breaker should trigger
        
        Args:
            risk_metrics: Current risk metrics
            account_balance: Current account balance
            
        Returns:
            Tuple of (should_trigger, reason)
        """
        if not self.enabled:
            return False, None
        
        # Check if already triggered and still in cooldown
        if self.is_triggered:
            if self.trigger_time:
                elapsed = (datetime.now() - self.trigger_time).total_seconds() / 60
                if elapsed < self.cooldown_minutes:
                    return True, f"Circuit breaker active (cooldown: {self.cooldown_minutes - elapsed:.1f}m remaining)"
                else:
                    # Cooldown expired, reset
                    self.reset()
                    logger.info("Circuit breaker cooldown expired - resuming trading")
                    return False, None
        
        # Check consecutive losses
        if risk_metrics.consecutive_losses >= self.max_consecutive_losses:
            self.trigger("Max consecutive losses reached")
            return True, self.trigger_reason
        
        return False, None
    
    def trigger(self, reason: str):
        """
        Trigger circuit breaker
        
        Args:
            reason: Reason for triggering
        """
        self.is_triggered = True
        self.trigger_time = datetime.now()
        self.trigger_reason = reason
        logger.warning(f"🚨 Circuit Breaker TRIGGERED: {reason}")
    
    def reset(self):
        """Reset circuit breaker"""
        self.is_triggered = False
        self.trigger_time = None
        self.trigger_reason = None
        logger.info("Circuit Breaker reset")
    
    def force_reset(self):
        """Force reset (manual override)"""
        self.reset()
        logger.warning("Circuit Breaker FORCE RESET by user")


class RiskEngine:
    """Enhanced risk management engine"""
    
    def __init__(self, config: Dict):
        """
        Initialize risk engine
        
        Args:
            config: Risk configuration
        """
        self.config = config.get('risk', {})
        
        # Risk parameters
        self.base_risk_percent = self.config.get('base_risk_percent', 0.8)
        self.max_drawdown_percent = self.config.get('max_drawdown_percent', 5.0)
        self.max_daily_loss_percent = self.config.get('max_daily_loss_percent', 3.0)
        self.max_positions = self.config.get('max_positions', 3)
        self.max_symbol_exposure_percent = self.config.get('max_symbol_exposure_percent', 3.0)
        
        # Trading state
        self.state = TradingState.ACTIVE
        self.state_reason = None
        
        # Risk metrics
        self.metrics = RiskMetrics()
        
        # Circuit breaker
        circuit_config = self.config.get('circuit_breaker', {})
        self.circuit_breaker = CircuitBreaker(circuit_config)
        
        logger.info(
            f"Risk Engine initialized - Base risk: {self.base_risk_percent}%, "
            f"Max DD: {self.max_drawdown_percent}%, Max positions: {self.max_positions}"
        )
    
    def can_trade(self, account_info: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if trading is allowed
        
        Args:
            account_info: Account information
            
        Returns:
            Tuple of (can_trade, reason)
        """
        # Check if manually stopped
        if self.state == TradingState.STOPPED:
            return False, "Trading manually stopped"
        
        # Check circuit breaker
        triggered, reason = self.circuit_breaker.check(self.metrics, account_info['balance'])
        if triggered:
            self.state = TradingState.PAUSED
            self.state_reason = reason
            return False, reason
        
        # Check max drawdown
        if self.metrics.current_drawdown >= self.max_drawdown_percent:
            self.state = TradingState.STOPPED
            self.state_reason = f"Max drawdown reached ({self.metrics.current_drawdown:.2f}%)"
            logger.critical(f"🛑 {self.state_reason}")
            return False, self.state_reason
        
        # Check daily loss limit
        daily_loss_pct = (self.metrics.daily_pnl / account_info['balance']) * 100
        if daily_loss_pct <= -self.max_daily_loss_percent:
            self.state = TradingState.PAUSED
            self.state_reason = f"Daily loss limit reached ({abs(daily_loss_pct):.2f}%)"
            logger.warning(f"⏸️ {self.state_reason}")
            return False, self.state_reason
        
        # Check max positions
        # This will be checked in can_open_position
        
        return True, None
    
    def can_open_position(
        self,
        symbol: str,
        open_positions: List[Dict],
        account_info: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a new position can be opened
        
        Args:
            symbol: Trading symbol
            open_positions: List of currently open positions
            account_info: Account information
            
        Returns:
            Tuple of (can_open, reason)
        """
        # Check if trading is allowed
        can_trade, reason = self.can_trade(account_info)
        if not can_trade:
            return False, reason
        
        # Check max positions
        if len(open_positions) >= self.max_positions:
            return False, f"Max positions reached ({len(open_positions)}/{self.max_positions})"
        
        # Check symbol exposure
        symbol_positions = [p for p in open_positions if p['symbol'] == symbol]
        if len(symbol_positions) > 0:
            # Calculate current exposure for this symbol
            total_exposure = sum([
                abs(p['volume'] * p['price_open'])
                for p in symbol_positions
            ])
            
            exposure_pct = (total_exposure / account_info['balance']) * 100
            
            if exposure_pct >= self.max_symbol_exposure_percent:
                return False, f"Max symbol exposure reached for {symbol} ({exposure_pct:.2f}%)"
        
        return True, None
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        account_info: Dict,
        symbol_info: Dict,
        confidence: float = 0.7
    ) -> float:
        """
        Calculate position size based on risk
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            account_info: Account information
            symbol_info: Symbol information
            confidence: Signal confidence (0-1)
            
        Returns:
            Lot size
        """
        # Calculate stop loss in pips
        if 'JPY' in symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        stop_loss_pips = abs(entry_price - stop_loss) / pip_value
        
        if stop_loss_pips == 0:
            logger.error("Stop loss is zero pips!")
            return symbol_info['min_lot']
        
        # Dynamic risk based on confidence
        # Higher confidence = higher risk (up to base_risk_percent)
        adjusted_risk_percent = self.base_risk_percent * confidence
        
        # Reduce risk if consecutive losses
        if self.metrics.consecutive_losses > 0:
            risk_reduction = 0.8 ** self.metrics.consecutive_losses  # Exponential reduction
            adjusted_risk_percent *= risk_reduction
            logger.info(
                f"Risk reduced due to {self.metrics.consecutive_losses} consecutive losses: "
                f"{adjusted_risk_percent:.2f}%"
            )
        
        # Calculate risk amount
        risk_amount = account_info['balance'] * (adjusted_risk_percent / 100)
        
        # Calculate lot size
        # risk_amount = lot_size * contract_size * stop_loss_pips * pip_value * tick_value
        contract_size = symbol_info['trade_contract_size']
        tick_value = symbol_info.get('trade_tick_value', 1.0)
        
        lot_size = risk_amount / (contract_size * stop_loss_pips * pip_value * tick_value)
        
        # Round to lot step
        lot_step = symbol_info['lot_step']
        lot_size = round(lot_size / lot_step) * lot_step
        
        # Ensure within limits
        min_lot = symbol_info['min_lot']
        max_lot = symbol_info['max_lot']
        lot_size = max(min_lot, min(lot_size, max_lot))
        
        logger.info(
            f"Position sizing: Risk {adjusted_risk_percent:.2f}%, "
            f"SL {stop_loss_pips:.1f} pips, Lot size: {lot_size:.2f}"
        )
        
        return lot_size
    
    def calculate_dynamic_stop_loss(
        self,
        entry_price: float,
        direction: str,
        atr: float,
        symbol: str
    ) -> float:
        """
        Calculate dynamic stop loss based on ATR
        
        Args:
            entry_price: Entry price
            direction: 'BUY' or 'SELL'
            atr: Average True Range
            symbol: Trading symbol
            
        Returns:
            Stop loss price
        """
        sl_config = self.config.get('stop_loss', {})
        
        if sl_config.get('type') == 'atr_based':
            atr_multiplier = sl_config.get('atr_multiplier', 2.0)
            sl_distance = atr * atr_multiplier
        else:
            # Fixed pips
            if 'JPY' in symbol:
                pip_value = 0.01
            else:
                pip_value = 0.0001
            
            sl_pips = sl_config.get('fixed_pips', 20)
            sl_distance = sl_pips * pip_value
        
        # Apply min/max limits
        min_pips = sl_config.get('min_pips', 10)
        max_pips = sl_config.get('max_pips', 50)
        
        if 'JPY' in symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        min_distance = min_pips * pip_value
        max_distance = max_pips * pip_value
        
        sl_distance = max(min_distance, min(sl_distance, max_distance))
        
        # Calculate stop loss
        if direction == 'BUY':
            stop_loss = entry_price - sl_distance
        else:
            stop_loss = entry_price + sl_distance
        
        return stop_loss
    
    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str
    ) -> float:
        """
        Calculate take profit based on risk/reward ratio
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 'BUY' or 'SELL'
            
        Returns:
            Take profit price
        """
        tp_config = self.config.get('take_profit', {})
        rr_ratio = tp_config.get('risk_reward_ratio', 2.5)
        
        sl_distance = abs(entry_price - stop_loss)
        tp_distance = sl_distance * rr_ratio
        
        if direction == 'BUY':
            take_profit = entry_price + tp_distance
        else:
            take_profit = entry_price - tp_distance
        
        return take_profit
    
    def update_metrics(self, trade_result: Dict):
        """
        Update risk metrics after trade
        
        Args:
            trade_result: Trade result dictionary
        """
        self.metrics.total_trades += 1
        
        pnl = trade_result.get('pnl', 0)
        self.metrics.daily_pnl += pnl
        self.metrics.total_pnl += pnl
        
        if pnl > 0:
            self.metrics.winning_trades += 1
            self.metrics.consecutive_losses = 0
        else:
            self.metrics.losing_trades += 1
            self.metrics.consecutive_losses += 1
        
        # Update drawdown
        if self.metrics.total_pnl < 0:
            account_balance = trade_result.get('account_balance', 10000)
            self.metrics.current_drawdown = abs(self.metrics.total_pnl / account_balance * 100)
            self.metrics.max_drawdown = max(self.metrics.max_drawdown, self.metrics.current_drawdown)
        else:
            self.metrics.current_drawdown = 0
        
        logger.info(
            f"Metrics updated - Total: {self.metrics.total_trades}, "
            f"Win rate: {self.get_win_rate():.1f}%, "
            f"Consecutive losses: {self.metrics.consecutive_losses}, "
            f"Daily P/L: ${self.metrics.daily_pnl:.2f}"
        )
    
    def reset_daily_metrics(self):
        """Reset daily metrics"""
        self.metrics.daily_pnl = 0.0
        self.metrics.last_reset = datetime.now()
        logger.info("Daily metrics reset")
    
    def get_win_rate(self) -> float:
        """Calculate win rate"""
        if self.metrics.total_trades == 0:
            return 0.0
        return (self.metrics.winning_trades / self.metrics.total_trades) * 100
    
    def get_profit_factor(self) -> float:
        """Calculate profit factor"""
        if self.metrics.losing_trades == 0:
            return float('inf') if self.metrics.winning_trades > 0 else 0.0
        
        # This would need access to actual win/loss amounts
        # Placeholder calculation
        return self.metrics.winning_trades / max(self.metrics.losing_trades, 1)
    
    def get_metrics_summary(self) -> Dict:
        """Get risk metrics summary"""
        return {
            'state': self.state.value,
            'total_trades': self.metrics.total_trades,
            'winning_trades': self.metrics.winning_trades,
            'losing_trades': self.metrics.losing_trades,
            'win_rate': self.get_win_rate(),
            'consecutive_losses': self.metrics.consecutive_losses,
            'daily_pnl': self.metrics.daily_pnl,
            'total_pnl': self.metrics.total_pnl,
            'max_drawdown': self.metrics.max_drawdown,
            'current_drawdown': self.metrics.current_drawdown,
            'circuit_breaker_active': self.circuit_breaker.is_triggered
        }
    
    def stop_trading(self, reason: str = "Manual stop"):
        """Stop trading"""
        self.state = TradingState.STOPPED
        self.state_reason = reason
        logger.warning(f"🛑 Trading STOPPED: {reason}")
    
    def resume_trading(self):
        """Resume trading"""
        self.state = TradingState.ACTIVE
        self.state_reason = None
        self.circuit_breaker.reset()
        logger.info("✅ Trading RESUMED")


if __name__ == "__main__":
    # Test risk engine
    from config_loader import get_config
    
    config = get_config()
    risk_engine = RiskEngine(config)
    
    # Mock account info
    account_info = {
        'balance': 10000,
        'equity': 10000,
        'margin': 0,
        'free_margin': 10000
    }
    
    # Test if can trade
    can_trade, reason = risk_engine.can_trade(account_info)
    print(f"Can trade: {can_trade}, Reason: {reason}")
    
    # Test position sizing
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
    print(f"Calculated lot size: {lot_size:.2f}")
    
    # Simulate trades
    for i in range(5):
        result = {
            'pnl': -100 if i < 3 else 150,
            'account_balance': 10000
        }
        risk_engine.update_metrics(result)
        
        print(f"\nTrade {i+1}:")
        print(risk_engine.get_metrics_summary())
