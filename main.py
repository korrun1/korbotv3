"""
🚀 KorBot X Enhanced - Main Entry Point
Version: 2.0
Date: 2026-02-16

Main trading bot orchestrator with all components integrated.
"""

import logging
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional
import schedule

from config_loader import get_config, reload_config
from utils import setup_logger
from data_layer import DataLayer
from market_intel import MarketIntelligence
from strategy_engine import StrategyEngine
from risk_engine import RiskEngine
from ai_optimization import AIOptimizationEngine
from execution_engine import ExecutionEngine
from databases import DatabaseManager
from telegram_notify import TelegramNotifier

logger = logging.getLogger(__name__)


class KorBotX:
    """Main trading bot class"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize KorBot X
        
        Args:
            config_path: Path to configuration file
        """
        print("\n" + "="*60)
        print("🤖 KorBot X Enhanced - Version 2.0")
        print("="*60 + "\n")
        
        # Load configuration
        self.config = get_config(config_path)
        
        # Setup logging
        log_config = self.config.get('logging', {})
        self.logger = setup_logger('korbot', log_config)
        
        logger.info("Initializing KorBot X Enhanced...")
        
        # Initialize components
        self._initialize_components()
        
        # State management
        self.running = False
        self.paused = False
        self.last_signal_check = None
        self.last_daily_reset = datetime.now().date()
        
        # Performance tracking
        self.session_start = datetime.now()
        self.trades_today = 0
        
        logger.info("✅ KorBot X Enhanced initialized successfully!")
    
    def _initialize_components(self):
        """Initialize all bot components"""
        logger.info("Initializing components...")
        
        # Core components
        self.data_layer = DataLayer(self.config)
        self.market_intel = MarketIntelligence(self.config)
        self.strategy_engine = StrategyEngine(self.config)
        self.risk_engine = RiskEngine(self.config)
        self.ai_engine = AIOptimizationEngine(self.config)
        self.execution_engine = ExecutionEngine(
            self.config,
            self.data_layer,
            self.risk_engine
        )
        self.database = DatabaseManager(self.config)
        self.notifier = TelegramNotifier(self.config)
        
        # Get trading symbol
        self.symbol = self.config.get('trading.symbol', 'AUDCAD')
        self.timeframes = self.config.get('trading.timeframes', {})
        
        # System configuration
        self.data_refresh_interval = self.config.get(
            'system.data_refresh_interval', 1
        )
        
        logger.info("✅ All components initialized")
    
    def start(self):
        """Start the trading bot"""
        logger.info("🚀 Starting KorBot X Enhanced...")
        
        self.running = True
        
        # Send start notification
        self.notifier.notify_system_start()
        
        # Schedule daily tasks
        schedule.every().day.at("00:00").do(self._daily_tasks)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("✅ KorBot X Enhanced is now running!")
        logger.info(f"📊 Monitoring symbol: {self.symbol}")
        logger.info(f"🎯 Mode: {self.config.get('trading.mode', 'unknown')}")
        
        # Main trading loop
        try:
            while self.running:
                self._trading_loop()
                
                # Run scheduled tasks
                schedule.run_pending()
                
                # Sleep
                time.sleep(self.data_refresh_interval)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.stop()
        except Exception as e:
            logger.critical(f"Critical error in main loop: {e}", exc_info=True)
            self.notifier.notify_error(f"Critical error: {str(e)}")
            self.stop()
    
    def _trading_loop(self):
        """Main trading loop iteration"""
        try:
            # Check if paused
            if self.paused:
                return
            
            # Get account info
            account_info = self.execution_engine.get_account_summary()
            if not account_info:
                logger.warning("Cannot get account info")
                return
            
            # Check if can trade
            can_trade, reason = self.risk_engine.can_trade(account_info)
            if not can_trade:
                if not self.paused:
                    logger.warning(f"Trading paused: {reason}")
                    self.paused = True
                    self.notifier.notify_circuit_breaker(reason)
                return
            
            # Resume if was paused
            if self.paused:
                logger.info("Trading resumed")
                self.paused = False
            
            # Check existing positions
            self._check_positions()
            
            # Generate new signals (throttled)
            now = datetime.now()
            if (self.last_signal_check is None or
                (now - self.last_signal_check).total_seconds() >= 60):
                
                self._generate_and_execute_signals(account_info)
                self.last_signal_check = now
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}", exc_info=True)
    
    def _check_positions(self):
        """Check and manage open positions"""
        try:
            # Check stop loss / take profit
            self.execution_engine.check_stop_loss_take_profit()
            
            # Update trailing stops
            self.execution_engine.update_trailing_stop()
            
        except Exception as e:
            logger.error(f"Error checking positions: {e}", exc_info=True)
    
    def _generate_and_execute_signals(self, account_info: Dict):
        """Generate and execute trading signals"""
        try:
            # Get historical data for all timeframes
            df_dict = {}
            for tf_name, tf in self.timeframes.items():
                df = self.data_layer.get_historical_data(self.symbol, tf, 200)
                if df is not None:
                    df = self.market_intel.calculate_all_indicators(df)
                    df_dict[tf] = df
            
            if not df_dict:
                logger.warning("No data available for signal generation")
                return
            
            # Detect market regime
            main_tf = self.timeframes.get('breakout', 'H1')
            regime = self.market_intel.detect_market_regime(df_dict[main_tf])
            
            # Get current price
            price_data = self.data_layer.get_current_price(self.symbol)
            if not price_data:
                return
            
            # Generate signals
            signals = self.strategy_engine.generate_signals(
                self.symbol,
                df_dict,
                regime,
                price_data
            )
            
            if not signals:
                return
            
            logger.info(f"Generated {len(signals)} signals")
            
            # Enhance signals with AI
            for signal in signals:
                # Use main timeframe data for AI features
                main_df = df_dict.get(main_tf)
                if main_df is not None:
                    signal = self.ai_engine.enhance_signal(signal, main_df)
                
                # Check if confidence meets threshold
                min_confidence = self.config.get('ai.xgboost.min_confidence', 0.65)
                if signal.confidence < min_confidence:
                    logger.info(
                        f"Signal confidence too low: {signal.strategy} - "
                        f"{signal.confidence:.2f} < {min_confidence}"
                    )
                    continue
                
                # Get symbol info
                symbol_info = self.data_layer.get_symbol_info(self.symbol)
                if not symbol_info:
                    continue
                
                # Execute signal
                trade = self.execution_engine.execute_signal(
                    signal,
                    account_info,
                    symbol_info
                )
                
                if trade:
                    # Save to database
                    self.database.save_trade(trade.to_dict())
                    
                    # Send notification
                    self.notifier.notify_trade_opened(trade.to_dict())
                    
                    # Update counter
                    self.trades_today += 1
                    
                    logger.info(f"✅ Trade executed: {trade.trade_id}")
            
        except Exception as e:
            logger.error(f"Error generating/executing signals: {e}", exc_info=True)
    
    def _daily_tasks(self):
        """Daily maintenance tasks"""
        logger.info("Running daily tasks...")
        
        try:
            # Reset daily metrics
            self.risk_engine.reset_daily_metrics()
            
            # Get daily statistics
            stats = self.database.get_statistics(days=1)
            
            # Send daily summary
            if stats['total_trades'] > 0:
                self.notifier.notify_daily_summary(stats)
            
            # Check for milestones
            self._check_milestones(stats)
            
            # Reset counter
            self.trades_today = 0
            self.last_daily_reset = datetime.now().date()
            
            logger.info("✅ Daily tasks completed")
            
        except Exception as e:
            logger.error(f"Error in daily tasks: {e}", exc_info=True)
    
    def _check_milestones(self, stats: Dict):
        """Check and notify about performance milestones"""
        # Win rate milestones
        win_rate = stats.get('win_rate', 0)
        if win_rate >= 70 and self.trades_today >= 10:
            self.notifier.notify_milestone("Win Rate", win_rate)
        
        # Profit milestones
        total_pnl = stats.get('total_pnl', 0)
        if total_pnl >= 1000:
            self.notifier.notify_milestone("Daily Profit", total_pnl)
    
    def stop(self, reason: str = "Manual stop"):
        """Stop the trading bot"""
        logger.info(f"🛑 Stopping KorBot X Enhanced... Reason: {reason}")
        
        self.running = False
        
        # Close all open positions
        try:
            for ticket in list(self.execution_engine.open_trades.keys()):
                self.execution_engine.close_position(ticket, "System shutdown")
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
        
        # Cleanup
        try:
            self.data_layer.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        # Send stop notification
        self.notifier.notify_system_stop(reason)
        
        # Print session summary
        self._print_session_summary()
        
        logger.info("✅ KorBot X Enhanced stopped successfully")
    
    def _print_session_summary(self):
        """Print session summary"""
        duration = datetime.now() - self.session_start
        hours = duration.total_seconds() / 3600
        
        stats = self.database.get_statistics(days=1)
        
        print("\n" + "="*60)
        print("📊 SESSION SUMMARY")
        print("="*60)
        print(f"Duration: {hours:.1f} hours")
        print(f"Trades Today: {self.trades_today}")
        print(f"Total P/L: ${stats.get('total_pnl', 0):.2f}")
        print(f"Win Rate: {stats.get('win_rate', 0):.1f}%")
        print("="*60 + "\n")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.stop("Signal received")
        sys.exit(0)


def main():
    """Main entry point"""
    try:
        # Create and start bot
        bot = KorBotX()
        bot.start()
        
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
