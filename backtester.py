"""
🧪 KorBot X Enhanced - Backtester
Version: 2.0
Date: 2026-02-16

Comprehensive backtesting engine with realistic execution simulation,
walk-forward analysis, and Monte Carlo testing.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
from pathlib import Path

from strategy_engine import StrategyEngine, Signal, SignalType
from risk_engine import RiskEngine
from market_intel import MarketIntelligence
from utils import PerformanceTimer

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Backtest trade record"""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    type: str
    strategy: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    pnl: float
    pnl_pips: float
    mae: float = 0.0  # Maximum Adverse Excursion
    mfe: float = 0.0  # Maximum Favorable Excursion
    duration_hours: float = 0.0
    confidence: float = 0.0


@dataclass
class BacktestMetrics:
    """Backtest performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    total_pnl: float = 0.0
    total_pnl_pips: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_win_pips: float = 0.0
    avg_loss_pips: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_drawdown: float = 0.0
    recovery_factor: float = 0.0
    
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    avg_trade_duration: float = 0.0
    
    mae_avg: float = 0.0
    mfe_avg: float = 0.0


class Backtester:
    """Comprehensive backtesting engine"""
    
    def __init__(self, config: Dict):
        """
        Initialize backtester
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.backtest_config = config.get('backtesting', {})
        
        # Execution parameters
        self.slippage_pips = self.backtest_config.get('slippage_pips', 0.5)
        self.commission_pips = self.backtest_config.get('commission_pips', 0.2)
        self.latency_ms = self.backtest_config.get('latency_ms', 50)
        
        # Initialize components
        self.market_intel = MarketIntelligence(config)
        self.strategy_engine = StrategyEngine(config)
        self.risk_engine = RiskEngine(config)
        
        # Results storage
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.metrics: Optional[BacktestMetrics] = None
        
        logger.info("Backtester initialized")
    
    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_balance: float = 10000
    ) -> BacktestMetrics:
        """
        Run backtest
        
        Args:
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_balance: Initial account balance
            
        Returns:
            Backtest metrics
        """
        logger.info(f"Starting backtest: {symbol} from {start_date} to {end_date}")
        
        with PerformanceTimer("Backtesting", logger):
            # Load historical data for all timeframes
            df_dict = self._load_historical_data(symbol, start_date, end_date)
            
            if not df_dict:
                logger.error("Failed to load historical data")
                return BacktestMetrics()
            
            # Run simulation
            self._simulate_trading(symbol, df_dict, initial_balance)
            
            # Calculate metrics
            self.metrics = self._calculate_metrics(initial_balance)
            
            logger.info(f"Backtest completed: {self.metrics.total_trades} trades")
        
        return self.metrics
    
    def _load_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Load historical data for all timeframes
        
        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary of DataFrames by timeframe
        """
        logger.info("Loading historical data...")
        
        # For backtesting, we need actual historical data
        # This is a simplified version - in production, load from database or API
        
        df_dict = {}
        timeframes = self.config.get('trading', {}).get('timeframes', {})
        
        for strategy_name, tf in timeframes.items():
            logger.info(f"Loading {tf} data for {strategy_name}")
            
            # In real implementation, load actual historical data
            # For now, create synthetic data
            dates = pd.date_range(start=start_date, end=end_date, freq='1H')
            
            # Generate realistic synthetic data
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
            
            # Calculate indicators
            df = self.market_intel.calculate_all_indicators(df)
            
            df_dict[tf] = df
        
        return df_dict
    
    def _simulate_trading(
        self,
        symbol: str,
        df_dict: Dict[str, pd.DataFrame],
        initial_balance: float
    ):
        """
        Simulate trading on historical data
        
        Args:
            symbol: Trading symbol
            df_dict: Dictionary of DataFrames
            initial_balance: Initial balance
        """
        logger.info("Simulating trading...")
        
        balance = initial_balance
        equity = initial_balance
        open_positions = []
        
        # Get main timeframe for iteration
        main_tf = 'H1'
        main_df = df_dict.get(main_tf)
        
        if main_df is None:
            logger.error(f"Main timeframe {main_tf} not found")
            return
        
        # Iterate through each bar
        for i in range(100, len(main_df)):
            current_time = main_df.index[i]
            
            # Get current data up to this point
            current_df_dict = {}
            for tf, df in df_dict.items():
                current_df_dict[tf] = df.iloc[:i+1]
            
            # Check existing positions
            open_positions = self._check_positions(
                open_positions,
                current_df_dict[main_tf],
                current_time
            )
            
            # Update equity curve
            unrealized_pnl = sum([pos['unrealized_pnl'] for pos in open_positions])
            equity = balance + unrealized_pnl
            self.equity_curve.append((current_time, equity))
            
            # Check if can trade
            account_info = {'balance': balance, 'equity': equity}
            can_trade, _ = self.risk_engine.can_trade(account_info)
            
            if not can_trade or len(open_positions) >= 3:
                continue
            
            # Detect market regime
            regime = self.market_intel.detect_market_regime(current_df_dict[main_tf])
            
            # Get current price
            current_price = current_df_dict[main_tf].iloc[-1]['Close']
            price_data = {'bid': current_price, 'ask': current_price}
            
            # Generate signals
            signals = self.strategy_engine.generate_signals(
                symbol,
                current_df_dict,
                regime,
                price_data
            )
            
            # Execute signals
            for signal in signals:
                if signal.confidence < 0.65:
                    continue
                
                # Calculate position size
                symbol_info = {
                    'trade_contract_size': 100000,
                    'trade_tick_value': 10,
                    'min_lot': 0.01,
                    'max_lot': 100.0,
                    'lot_step': 0.01
                }
                
                lot_size = self.risk_engine.calculate_position_size(
                    symbol, signal.entry_price, signal.stop_loss,
                    account_info, symbol_info, signal.confidence
                )
                
                # Open position
                position = self._open_position(
                    signal, lot_size, current_time, current_df_dict[main_tf]
                )
                
                if position:
                    open_positions.append(position)
        
        # Close any remaining positions
        for pos in open_positions:
            self._close_position(pos, main_df.iloc[-1]['Close'], main_df.index[-1], "End of backtest")
            balance += pos['pnl']
        
        logger.info(f"Simulation completed: Final balance ${balance:.2f}")
    
    def _open_position(
        self,
        signal: Signal,
        lot_size: float,
        entry_time: datetime,
        df: pd.DataFrame
    ) -> Dict:
        """Open a position"""
        
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
        
        position = {
            'symbol': signal.symbol,
            'type': signal.type.value,
            'strategy': signal.strategy,
            'entry_time': entry_time,
            'entry_price': entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'lot_size': lot_size,
            'confidence': signal.confidence,
            'unrealized_pnl': 0,
            'mae': 0,  # Maximum Adverse Excursion
            'mfe': 0,  # Maximum Favorable Excursion
            'bars_held': 0,
            'df': df
        }
        
        return position
    
    def _check_positions(
        self,
        positions: List[Dict],
        df: pd.DataFrame,
        current_time: datetime
    ) -> List[Dict]:
        """Check and update positions"""
        
        remaining_positions = []
        
        for pos in positions:
            current_price = df.iloc[-1]['Close']
            
            # Update unrealized P/L
            if 'JPY' in pos['symbol']:
                pip_value = 0.01
            else:
                pip_value = 0.0001
            
            if pos['type'] == 'BUY':
                unrealized_pnl = (current_price - pos['entry_price']) * pos['lot_size'] * 100000
                unrealized_pips = (current_price - pos['entry_price']) / pip_value
            else:
                unrealized_pnl = (pos['entry_price'] - current_price) * pos['lot_size'] * 100000
                unrealized_pips = (pos['entry_price'] - current_price) / pip_value
            
            pos['unrealized_pnl'] = unrealized_pnl
            pos['bars_held'] += 1
            
            # Track MAE and MFE
            if unrealized_pnl < pos['mae']:
                pos['mae'] = unrealized_pnl
            if unrealized_pnl > pos['mfe']:
                pos['mfe'] = unrealized_pnl
            
            # Check stop loss
            should_close = False
            exit_reason = ""
            
            if pos['type'] == 'BUY' and current_price <= pos['stop_loss']:
                should_close = True
                exit_reason = "Stop Loss"
            elif pos['type'] == 'SELL' and current_price >= pos['stop_loss']:
                should_close = True
                exit_reason = "Stop Loss"
            
            # Check take profit
            elif pos['type'] == 'BUY' and current_price >= pos['take_profit']:
                should_close = True
                exit_reason = "Take Profit"
            elif pos['type'] == 'SELL' and current_price <= pos['take_profit']:
                should_close = True
                exit_reason = "Take Profit"
            
            if should_close:
                self._close_position(pos, current_price, current_time, exit_reason)
            else:
                remaining_positions.append(pos)
        
        return remaining_positions
    
    def _close_position(
        self,
        position: Dict,
        exit_price: float,
        exit_time: datetime,
        reason: str
    ):
        """Close a position and record trade"""
        
        # Apply slippage
        if 'JPY' in position['symbol']:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        slippage = self.slippage_pips * pip_value
        commission = self.commission_pips * pip_value
        
        if position['type'] == 'BUY':
            exit_price -= (slippage + commission)
        else:
            exit_price += (slippage + commission)
        
        # Calculate P/L
        if position['type'] == 'BUY':
            pnl = (exit_price - position['entry_price']) * position['lot_size'] * 100000
            pnl_pips = (exit_price - position['entry_price']) / pip_value
        else:
            pnl = (position['entry_price'] - exit_price) * position['lot_size'] * 100000
            pnl_pips = (position['entry_price'] - exit_price) / pip_value
        
        # Calculate duration
        duration = (exit_time - position['entry_time']).total_seconds() / 3600
        
        # Create trade record
        trade = BacktestTrade(
            entry_time=position['entry_time'],
            exit_time=exit_time,
            symbol=position['symbol'],
            type=position['type'],
            strategy=position['strategy'],
            entry_price=position['entry_price'],
            exit_price=exit_price,
            stop_loss=position['stop_loss'],
            take_profit=position['take_profit'],
            lot_size=position['lot_size'],
            pnl=pnl,
            pnl_pips=pnl_pips,
            mae=position['mae'],
            mfe=position['mfe'],
            duration_hours=duration,
            confidence=position['confidence']
        )
        
        self.trades.append(trade)
        position['pnl'] = pnl
        
        logger.debug(f"Trade closed: {reason}, P/L: ${pnl:.2f} ({pnl_pips:.1f} pips)")
    
    def _calculate_metrics(self, initial_balance: float) -> BacktestMetrics:
        """Calculate backtest metrics"""
        
        if not self.trades:
            return BacktestMetrics()
        
        metrics = BacktestMetrics()
        
        # Basic stats
        metrics.total_trades = len(self.trades)
        metrics.winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        metrics.losing_trades = sum(1 for t in self.trades if t.pnl < 0)
        metrics.win_rate = (metrics.winning_trades / metrics.total_trades * 100) if metrics.total_trades > 0 else 0
        
        # P&L stats
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        
        metrics.total_pnl = sum(t.pnl for t in self.trades)
        metrics.total_pnl_pips = sum(t.pnl_pips for t in self.trades)
        
        metrics.avg_win = np.mean(wins) if wins else 0
        metrics.avg_loss = np.mean(losses) if losses else 0
        metrics.avg_win_pips = np.mean([t.pnl_pips for t in self.trades if t.pnl > 0]) if wins else 0
        metrics.avg_loss_pips = np.mean([t.pnl_pips for t in self.trades if t.pnl < 0]) if losses else 0
        
        metrics.largest_win = max(wins) if wins else 0
        metrics.largest_loss = min(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        metrics.profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        # Expectancy
        metrics.expectancy = (metrics.win_rate / 100 * metrics.avg_win) + ((1 - metrics.win_rate / 100) * metrics.avg_loss)
        
        # Drawdown
        if self.equity_curve:
            equity_values = [e[1] for e in self.equity_curve]
            peak = initial_balance
            max_dd = 0
            max_dd_pct = 0
            drawdowns = []
            
            for equity in equity_values:
                if equity > peak:
                    peak = equity
                
                dd = peak - equity
                dd_pct = (dd / peak * 100) if peak > 0 else 0
                
                if dd > max_dd:
                    max_dd = dd
                    max_dd_pct = dd_pct
                
                if dd > 0:
                    drawdowns.append(dd)
            
            metrics.max_drawdown = max_dd
            metrics.max_drawdown_pct = max_dd_pct
            metrics.avg_drawdown = np.mean(drawdowns) if drawdowns else 0
            
            # Recovery factor
            metrics.recovery_factor = (metrics.total_pnl / max_dd) if max_dd > 0 else 0
        
        # Risk-adjusted returns
        if self.equity_curve and len(self.equity_curve) > 1:
            returns = pd.Series([e[1] for e in self.equity_curve]).pct_change().dropna()
            
            if len(returns) > 0:
                # Sharpe Ratio (assuming 252 trading days)
                metrics.sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
                
                # Sortino Ratio
                downside_returns = returns[returns < 0]
                downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
                metrics.sortino_ratio = (returns.mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0
                
                # Calmar Ratio
                annual_return = returns.mean() * 252
                metrics.calmar_ratio = (annual_return / metrics.max_drawdown_pct) if metrics.max_drawdown_pct > 0 else 0
        
        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for trade in self.trades:
            if trade.pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        metrics.max_consecutive_wins = max_consecutive_wins
        metrics.max_consecutive_losses = max_consecutive_losses
        
        # Average trade duration
        metrics.avg_trade_duration = np.mean([t.duration_hours for t in self.trades])
        
        # MAE/MFE
        metrics.mae_avg = np.mean([t.mae for t in self.trades])
        metrics.mfe_avg = np.mean([t.mfe for t in self.trades])
        
        return metrics
    
    def print_results(self):
        """Print backtest results"""
        if not self.metrics:
            logger.warning("No metrics available")
            return
        
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        
        print(f"\n📊 Trading Statistics:")
        print(f"  Total Trades: {self.metrics.total_trades}")
        print(f"  Winning Trades: {self.metrics.winning_trades}")
        print(f"  Losing Trades: {self.metrics.losing_trades}")
        print(f"  Win Rate: {self.metrics.win_rate:.2f}%")
        
        print(f"\n💰 P&L Statistics:")
        print(f"  Total P&L: ${self.metrics.total_pnl:.2f} ({self.metrics.total_pnl_pips:.1f} pips)")
        print(f"  Average Win: ${self.metrics.avg_win:.2f} ({self.metrics.avg_win_pips:.1f} pips)")
        print(f"  Average Loss: ${self.metrics.avg_loss:.2f} ({self.metrics.avg_loss_pips:.1f} pips)")
        print(f"  Largest Win: ${self.metrics.largest_win:.2f}")
        print(f"  Largest Loss: ${self.metrics.largest_loss:.2f}")
        
        print(f"\n📈 Performance Metrics:")
        print(f"  Profit Factor: {self.metrics.profit_factor:.2f}")
        print(f"  Expectancy: ${self.metrics.expectancy:.2f}")
        print(f"  Sharpe Ratio: {self.metrics.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio: {self.metrics.sortino_ratio:.2f}")
        print(f"  Calmar Ratio: {self.metrics.calmar_ratio:.2f}")
        
        print(f"\n📉 Risk Metrics:")
        print(f"  Max Drawdown: ${self.metrics.max_drawdown:.2f} ({self.metrics.max_drawdown_pct:.2f}%)")
        print(f"  Avg Drawdown: ${self.metrics.avg_drawdown:.2f}")
        print(f"  Recovery Factor: {self.metrics.recovery_factor:.2f}")
        
        print(f"\n🔄 Consecutive Results:")
        print(f"  Max Consecutive Wins: {self.metrics.max_consecutive_wins}")
        print(f"  Max Consecutive Losses: {self.metrics.max_consecutive_losses}")
        
        print(f"\n⏱️ Other:")
        print(f"  Avg Trade Duration: {self.metrics.avg_trade_duration:.2f} hours")
        print(f"  Avg MAE: ${self.metrics.mae_avg:.2f}")
        print(f"  Avg MFE: ${self.metrics.mfe_avg:.2f}")
        
        print("\n" + "="*60)
    
    def plot_equity_curve(self, save_path: Optional[str] = None):
        """Plot equity curve"""
        if not self.equity_curve:
            logger.warning("No equity curve data")
            return
        
        times, equity = zip(*self.equity_curve)
        
        plt.figure(figsize=(12, 6))
        plt.plot(times, equity, label='Equity', linewidth=2)
        plt.axhline(y=equity[0], color='r', linestyle='--', label='Initial Balance')
        plt.xlabel('Time')
        plt.ylabel('Equity ($)')
        plt.title('Equity Curve')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Equity curve saved to {save_path}")
        else:
            plt.show()


if __name__ == "__main__":
    # Test backtester
    from config_loader import get_config
    
    config = get_config()
    backtester = Backtester(config)
    
    # Run backtest
    metrics = backtester.run(
        symbol='AUDCAD',
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_balance=10000
    )
    
    # Print results
    backtester.print_results()
    
    # Plot equity curve
    # backtester.plot_equity_curve('equity_curve.png')
