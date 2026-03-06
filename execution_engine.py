"""
⚡ KorBot X Enhanced - Execution Engine
Version: 2.0
Date: 2026-02-16

Advanced trade execution engine with order management, position tracking,
and real-time monitoring.
"""

import MetaTrader5 as mt5
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import time

from strategy_engine import Signal, SignalType
from risk_engine import RiskEngine
from utils import retry_on_failure, safe_execution

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class Trade:
    """Trade data structure"""
    trade_id: str
    ticket: int
    symbol: str
    type: str  # 'BUY' or 'SELL'
    strategy: str
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pips: Optional[float] = None
    status: str = "open"
    confidence: float = 0.0
    reasons: List[str] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['entry_time'] = str(self.entry_time)
        data['exit_time'] = str(self.exit_time) if self.exit_time else None
        return data


class ExecutionEngine:
    """Trade execution and order management engine"""
    
    def __init__(self, config: Dict, data_layer, risk_engine: RiskEngine):
        """
        Initialize execution engine
        
        Args:
            config: Configuration dictionary
            data_layer: Data layer instance
            risk_engine: Risk engine instance
        """
        self.config = config
        self.data_layer = data_layer
        self.risk_engine = risk_engine
        
        self.trading_mode = config.get('trading', {}).get('mode', 'paper')
        self.is_paper_trading = self.trading_mode == 'paper'
        
        # Trade tracking
        self.open_trades: Dict[int, Trade] = {}  # ticket -> Trade
        self.closed_trades: List[Trade] = []
        self.pending_orders: Dict[str, Dict] = {}
        
        # Paper trading simulation
        self.paper_balance = 10000
        self.paper_equity = 10000
        self.paper_ticket_counter = 100000
        
        # Slippage simulation
        self.slippage_pips = 0.5
        
        logger.info(f"Execution Engine initialized - Mode: {self.trading_mode}")
    
    @retry_on_failure(max_attempts=3, delay=1.0)
    def execute_signal(
        self,
        signal: Signal,
        account_info: Dict,
        symbol_info: Dict
    ) -> Optional[Trade]:
        """
        Execute trading signal
        
        Args:
            signal: Trading signal
            account_info: Account information
            symbol_info: Symbol information
            
        Returns:
            Trade object if successful, None otherwise
        """
        # Check if signal meets confidence threshold
        if signal.confidence < 0.6:
            logger.info(f"Signal confidence too low ({signal.confidence:.2f}), skipping")
            return None
        
        # Check if can open position
        open_positions = self.get_open_positions(signal.symbol)
        can_open, reason = self.risk_engine.can_open_position(
            signal.symbol, open_positions, account_info
        )
        
        if not can_open:
            logger.warning(f"Cannot open position: {reason}")
            return None
        
        # Calculate position size
        lot_size = self.risk_engine.calculate_position_size(
            symbol=signal.symbol,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            account_info=account_info,
            symbol_info=symbol_info,
            confidence=signal.confidence
        )
        
        # Execute order
        if self.is_paper_trading:
            trade = self._execute_paper_order(signal, lot_size)
        else:
            trade = self._execute_real_order(signal, lot_size, symbol_info)
        
        if trade:
            self.open_trades[trade.ticket] = trade
            logger.info(
                f"✅ Trade opened: {trade.type} {trade.symbol} @ {trade.entry_price:.5f}, "
                f"Lot: {trade.lot_size:.2f}, SL: {trade.stop_loss:.5f}, TP: {trade.take_profit:.5f}"
            )
        
        return trade
    
    def _execute_paper_order(self, signal: Signal, lot_size: float) -> Optional[Trade]:
        """
        Execute paper trading order (simulation)
        
        Args:
            signal: Trading signal
            lot_size: Position size
            
        Returns:
            Trade object
        """
        # Generate ticket
        self.paper_ticket_counter += 1
        ticket = self.paper_ticket_counter
        
        # Apply slippage
        if 'JPY' in signal.symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        slippage = self.slippage_pips * pip_value
        entry_price = signal.entry_price
        
        if signal.type == SignalType.BUY:
            entry_price += slippage
        else:
            entry_price -= slippage
        
        # Create trade
        trade = Trade(
            trade_id=f"PAPER_{ticket}",
            ticket=ticket,
            symbol=signal.symbol,
            type=signal.type.value,
            strategy=signal.strategy,
            entry_price=entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            lot_size=lot_size,
            entry_time=datetime.now(),
            confidence=signal.confidence,
            reasons=signal.reasons
        )
        
        # Update paper balance (reserve margin)
        # Simplified margin calculation
        margin_required = lot_size * 100000 * 0.01  # 1% margin
        self.paper_balance -= margin_required
        
        logger.info(f"📝 Paper trade opened: {trade.trade_id}")
        
        return trade
    
    @safe_execution(default_return=None)
    def _execute_real_order(
        self,
        signal: Signal,
        lot_size: float,
        symbol_info: Dict
    ) -> Optional[Trade]:
        """
        Execute real MT5 order
        
        Args:
            signal: Trading signal
            lot_size: Position size
            symbol_info: Symbol information
            
        Returns:
            Trade object if successful
        """
        # Prepare request
        order_type = mt5.ORDER_TYPE_BUY if signal.type == SignalType.BUY else mt5.ORDER_TYPE_SELL
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": lot_size,
            "type": order_type,
            "price": signal.entry_price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "deviation": 20,
            "magic": 234000,
            "comment": f"KorBot_{signal.strategy}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result is None:
            error = mt5.last_error()
            logger.error(f"Order send failed: {error}")
            return None
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order rejected: {result.retcode}, {result.comment}")
            return None
        
        # Create trade
        trade = Trade(
            trade_id=f"MT5_{result.order}",
            ticket=result.order,
            symbol=signal.symbol,
            type=signal.type.value,
            strategy=signal.strategy,
            entry_price=result.price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            lot_size=lot_size,
            entry_time=datetime.now(),
            confidence=signal.confidence,
            reasons=signal.reasons
        )
        
        logger.info(f"✅ Real trade opened: {trade.trade_id}, Ticket: {result.order}")
        
        return trade
    
    def close_position(self, ticket: int, reason: str = "Manual close") -> bool:
        """
        Close position
        
        Args:
            ticket: Position ticket
            reason: Reason for closing
            
        Returns:
            True if successful
        """
        if ticket not in self.open_trades:
            logger.warning(f"Trade {ticket} not found in open trades")
            return False
        
        trade = self.open_trades[ticket]
        
        if self.is_paper_trading:
            success = self._close_paper_position(trade, reason)
        else:
            success = self._close_real_position(trade, reason)
        
        if success:
            # Update metrics
            self.risk_engine.update_metrics({
                'pnl': trade.pnl,
                'account_balance': self.paper_balance if self.is_paper_trading else 0
            })
            
            # Move to closed trades
            self.closed_trades.append(trade)
            del self.open_trades[ticket]
            
            logger.info(
                f"✅ Trade closed: {trade.trade_id}, P/L: ${trade.pnl:.2f} ({trade.pnl_pips:.1f} pips)"
            )
        
        return success
    
    def _close_paper_position(self, trade: Trade, reason: str) -> bool:
        """Close paper trading position"""
        # Get current price
        price_data = self.data_layer.get_current_price(trade.symbol)
        if not price_data:
            logger.error("Cannot get current price")
            return False
        
        # Determine exit price
        if trade.type == 'BUY':
            exit_price = price_data['bid']
        else:
            exit_price = price_data['ask']
        
        # Apply slippage
        if 'JPY' in trade.symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        slippage = self.slippage_pips * pip_value
        if trade.type == 'BUY':
            exit_price -= slippage
        else:
            exit_price += slippage
        
        # Calculate P/L
        if trade.type == 'BUY':
            pnl_pips = (exit_price - trade.entry_price) / pip_value
            pnl = (exit_price - trade.entry_price) * trade.lot_size * 100000
        else:
            pnl_pips = (trade.entry_price - exit_price) / pip_value
            pnl = (trade.entry_price - exit_price) * trade.lot_size * 100000
        
        # Update trade
        trade.exit_time = datetime.now()
        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.pnl_pips = pnl_pips
        trade.status = "closed"
        
        # Update paper balance
        margin_released = trade.lot_size * 100000 * 0.01
        self.paper_balance += margin_released + pnl
        self.paper_equity = self.paper_balance
        
        logger.info(f"📝 Paper trade closed: {trade.trade_id}, Reason: {reason}")
        
        return True
    
    @safe_execution(default_return=False)
    def _close_real_position(self, trade: Trade, reason: str) -> bool:
        """Close real MT5 position"""
        # Prepare close request
        order_type = mt5.ORDER_TYPE_SELL if trade.type == 'BUY' else mt5.ORDER_TYPE_BUY
        
        # Get current price
        price_data = self.data_layer.get_current_price(trade.symbol)
        if not price_data:
            return False
        
        price = price_data['bid'] if trade.type == 'BUY' else price_data['ask']
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": trade.symbol,
            "volume": trade.lot_size,
            "type": order_type,
            "position": trade.ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": f"KorBot_Close_{reason}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send close order
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Failed to close position: {result.retcode if result else 'None'}")
            return False
        
        # Update trade
        trade.exit_time = datetime.now()
        trade.exit_price = result.price
        
        # Calculate P/L
        if 'JPY' in trade.symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        if trade.type == 'BUY':
            trade.pnl_pips = (trade.exit_price - trade.entry_price) / pip_value
            trade.pnl = (trade.exit_price - trade.entry_price) * trade.lot_size * 100000
        else:
            trade.pnl_pips = (trade.entry_price - trade.exit_price) / pip_value
            trade.pnl = (trade.entry_price - trade.exit_price) * trade.lot_size * 100000
        
        trade.status = "closed"
        
        return True
    
    def check_stop_loss_take_profit(self):
        """Check all open positions for SL/TP hits"""
        for ticket, trade in list(self.open_trades.items()):
            price_data = self.data_layer.get_current_price(trade.symbol)
            if not price_data:
                continue
            
            current_price = price_data['bid'] if trade.type == 'BUY' else price_data['ask']
            
            should_close = False
            reason = ""
            
            # Check stop loss
            if trade.type == 'BUY' and current_price <= trade.stop_loss:
                should_close = True
                reason = "Stop Loss"
            elif trade.type == 'SELL' and current_price >= trade.stop_loss:
                should_close = True
                reason = "Stop Loss"
            
            # Check take profit
            if trade.type == 'BUY' and current_price >= trade.take_profit:
                should_close = True
                reason = "Take Profit"
            elif trade.type == 'SELL' and current_price <= trade.take_profit:
                should_close = True
                reason = "Take Profit"
            
            if should_close:
                self.close_position(ticket, reason)
    
    def update_trailing_stop(self):
        """Update trailing stop loss for open positions"""
        tp_config = self.config.get('risk', {}).get('take_profit', {})
        
        if not tp_config.get('use_trailing', False):
            return
        
        trailing_multiplier = tp_config.get('trailing_atr_multiplier', 1.5)
        
        for ticket, trade in self.open_trades.items():
            # Get current data
            df = self.data_layer.get_historical_data(trade.symbol, 'H1', 50)
            if df is None or df.empty:
                continue
            
            atr = df.iloc[-1].get('ATR', 0)
            if atr == 0:
                continue
            
            price_data = self.data_layer.get_current_price(trade.symbol)
            if not price_data:
                continue
            
            current_price = price_data['bid'] if trade.type == 'BUY' else price_data['ask']
            
            # Calculate new stop loss
            if trade.type == 'BUY':
                new_sl = current_price - (atr * trailing_multiplier)
                # Only update if new SL is higher
                if new_sl > trade.stop_loss:
                    self._update_stop_loss(trade, new_sl)
            else:
                new_sl = current_price + (atr * trailing_multiplier)
                # Only update if new SL is lower
                if new_sl < trade.stop_loss:
                    self._update_stop_loss(trade, new_sl)
    
    def _update_stop_loss(self, trade: Trade, new_sl: float):
        """Update stop loss for a trade"""
        if self.is_paper_trading:
            trade.stop_loss = new_sl
            logger.info(f"Updated trailing SL for {trade.trade_id}: {new_sl:.5f}")
        else:
            # MT5 modify position
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": trade.symbol,
                "position": trade.ticket,
                "sl": new_sl,
                "tp": trade.take_profit
            }
            
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                trade.stop_loss = new_sl
                logger.info(f"Updated trailing SL for {trade.trade_id}: {new_sl:.5f}")
    
    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get open positions
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            List of position dictionaries
        """
        if self.is_paper_trading:
            positions = []
            for trade in self.open_trades.values():
                if symbol and trade.symbol != symbol:
                    continue
                
                # Get current price for unrealized P/L
                price_data = self.data_layer.get_current_price(trade.symbol)
                if price_data:
                    current_price = price_data['bid'] if trade.type == 'BUY' else price_data['ask']
                    
                    if 'JPY' in trade.symbol:
                        pip_value = 0.01
                    else:
                        pip_value = 0.0001
                    
                    if trade.type == 'BUY':
                        unrealized_pnl = (current_price - trade.entry_price) * trade.lot_size * 100000
                    else:
                        unrealized_pnl = (trade.entry_price - current_price) * trade.lot_size * 100000
                else:
                    unrealized_pnl = 0
                
                positions.append({
                    'ticket': trade.ticket,
                    'symbol': trade.symbol,
                    'type': trade.type,
                    'volume': trade.lot_size,
                    'price_open': trade.entry_price,
                    'price_current': current_price if price_data else trade.entry_price,
                    'sl': trade.stop_loss,
                    'tp': trade.take_profit,
                    'profit': unrealized_pnl,
                    'time': trade.entry_time
                })
            
            return positions
        else:
            return self.data_layer.get_open_positions(symbol)
    
    def get_account_summary(self) -> Dict:
        """Get account summary"""
        if self.is_paper_trading:
            # Calculate unrealized P/L
            unrealized_pnl = 0
            for trade in self.open_trades.values():
                price_data = self.data_layer.get_current_price(trade.symbol)
                if price_data:
                    current_price = price_data['bid'] if trade.type == 'BUY' else price_data['ask']
                    if trade.type == 'BUY':
                        unrealized_pnl += (current_price - trade.entry_price) * trade.lot_size * 100000
                    else:
                        unrealized_pnl += (trade.entry_price - current_price) * trade.lot_size * 100000
            
            return {
                'balance': self.paper_balance,
                'equity': self.paper_balance + unrealized_pnl,
                'margin': sum([t.lot_size * 100000 * 0.01 for t in self.open_trades.values()]),
                'free_margin': self.paper_balance - sum([t.lot_size * 100000 * 0.01 for t in self.open_trades.values()]),
                'profit': unrealized_pnl,
                'open_trades': len(self.open_trades)
            }
        else:
            account_info = self.data_layer.get_account_info()
            if account_info:
                account_info['open_trades'] = len(self.open_trades)
            return account_info or {}


if __name__ == "__main__":
    # Test execution engine
    from config_loader import get_config
    from data_layer import DataLayer
    
    config = get_config()
    data_layer = DataLayer(config)
    risk_engine = RiskEngine(config)
    execution_engine = ExecutionEngine(config, data_layer, risk_engine)
    
    print(f"Execution Engine initialized - Mode: {execution_engine.trading_mode}")
    print(f"Paper trading: {execution_engine.is_paper_trading}")
    
    # Get account summary
    summary = execution_engine.get_account_summary()
    print(f"Account summary: {summary}")
    
    data_layer.cleanup()
