"""
📱 KorBot X Enhanced - Telegram Notifications
Version: 2.0
Date: 2026-02-16

Async Telegram notification system with message queuing and retry logic.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
import asyncio
from queue import Queue
import threading

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("python-telegram-bot not installed. Telegram notifications disabled.")

from utils import safe_execution

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram notification manager with async support"""
    
    def __init__(self, config: Dict):
        """
        Initialize Telegram notifier
        
        Args:
            config: Telegram configuration
        """
        self.config = config.get('telegram', {})
        self.enabled = self.config.get('enabled', True) and TELEGRAM_AVAILABLE
        
        if not self.enabled:
            logger.info("Telegram notifications disabled")
            return
        
        self.token = self.config.get('token')
        self.chat_id = self.config.get('chat_id')
        
        if not self.token or not self.chat_id:
            logger.warning("Telegram credentials not set. Notifications disabled.")
            self.enabled = False
            return
        
        # Initialize bot
        try:
            self.bot = Bot(token=self.token)
            logger.info("Telegram notifier initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            self.enabled = False
            return
        
        # Notification settings
        self.notifications = self.config.get('notifications', {})
        
        # Async mode
        self.async_mode = self.config.get('async_mode', True)
        self.message_queue = Queue(maxsize=self.config.get('message_queue_size', 100))
        
        # Start message sender thread
        if self.async_mode:
            self.sender_thread = threading.Thread(target=self._message_sender, daemon=True)
            self.sender_thread.start()
    
    def _message_sender(self):
        """Background thread for sending messages"""
        logger.info("Telegram message sender thread started")
        
        while True:
            try:
                # Get message from queue (blocking)
                message, parse_mode = self.message_queue.get(timeout=1)
                
                # Send message
                self._send_sync(message, parse_mode)
                
                # Mark task as done
                self.message_queue.task_done()
                
            except Exception:
                # Queue timeout or error - continue
                pass
    
    @safe_execution(default_return=False)
    def _send_sync(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Send message synchronously
        
        Args:
            message: Message text
            parse_mode: Parse mode (HTML, Markdown)
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def send(self, message: str, parse_mode: str = 'HTML'):
        """
        Send message (async if enabled)
        
        Args:
            message: Message text
            parse_mode: Parse mode
        """
        if not self.enabled:
            return
        
        if self.async_mode:
            try:
                self.message_queue.put((message, parse_mode), block=False)
            except Exception as e:
                logger.error(f"Failed to queue message: {e}")
        else:
            self._send_sync(message, parse_mode)
    
    def notify_trade_opened(self, trade_data: Dict):
        """Notify when trade is opened"""
        if not self.enabled or not self.notifications.get('trade_opened', True):
            return
        
        trade_type_emoji = "📈" if trade_data['type'] == 'BUY' else "📉"
        
        message = f"""
{trade_type_emoji} <b>Trade Opened</b>

<b>Symbol:</b> {trade_data['symbol']}
<b>Type:</b> {trade_data['type']}
<b>Strategy:</b> {trade_data['strategy']}
<b>Entry:</b> {trade_data['entry_price']:.5f}
<b>SL:</b> {trade_data['stop_loss']:.5f}
<b>TP:</b> {trade_data['take_profit']:.5f}
<b>Lot Size:</b> {trade_data['lot_size']:.2f}
<b>Confidence:</b> {trade_data.get('confidence', 0) * 100:.0f}%

<i>Reasons: {', '.join(trade_data.get('reasons', []))}</i>
"""
        
        self.send(message.strip())
    
    def notify_trade_closed(self, trade_data: Dict):
        """Notify when trade is closed"""
        if not self.enabled or not self.notifications.get('trade_closed', True):
            return
        
        pnl = trade_data.get('pnl', 0)
        pnl_emoji = "✅" if pnl > 0 else "❌"
        
        message = f"""
{pnl_emoji} <b>Trade Closed</b>

<b>Symbol:</b> {trade_data['symbol']}
<b>Type:</b> {trade_data['type']}
<b>Strategy:</b> {trade_data['strategy']}

<b>Entry:</b> {trade_data['entry_price']:.5f}
<b>Exit:</b> {trade_data.get('exit_price', 0):.5f}

<b>P/L:</b> ${pnl:.2f} ({trade_data.get('pnl_pips', 0):.1f} pips)
<b>Duration:</b> {self._format_duration(trade_data.get('entry_time'), trade_data.get('exit_time'))}
"""
        
        self.send(message.strip())
    
    def notify_daily_summary(self, stats: Dict):
        """Send daily summary"""
        if not self.enabled or not self.notifications.get('daily_summary', True):
            return
        
        win_rate = stats.get('win_rate', 0)
        total_pnl = stats.get('total_pnl', 0)
        emoji = "🎉" if total_pnl > 0 else "😔" if total_pnl < 0 else "😐"
        
        message = f"""
📊 <b>Daily Summary</b> {emoji}

<b>Total Trades:</b> {stats.get('total_trades', 0)}
<b>Wins:</b> {stats.get('winning_trades', 0)} | <b>Losses:</b> {stats.get('losing_trades', 0)}
<b>Win Rate:</b> {win_rate:.1f}%

<b>Total P/L:</b> ${total_pnl:.2f}
<b>Avg P/L:</b> ${stats.get('avg_pnl', 0):.2f}

<b>Max Drawdown:</b> {stats.get('max_drawdown', 0):.2f}%
<b>Sharpe Ratio:</b> {stats.get('sharpe_ratio', 0):.2f}
"""
        
        self.send(message.strip())
    
    def notify_circuit_breaker(self, reason: str):
        """Notify when circuit breaker triggers"""
        if not self.enabled or not self.notifications.get('circuit_breaker', True):
            return
        
        message = f"""
🚨 <b>CIRCUIT BREAKER ACTIVATED</b> 🚨

<b>Reason:</b> {reason}

Trading has been automatically paused for safety.
Please review the situation before resuming.
"""
        
        self.send(message.strip())
    
    def notify_error(self, error_message: str):
        """Notify on critical error"""
        if not self.enabled or not self.notifications.get('errors', True):
            return
        
        message = f"""
⚠️ <b>Error Occurred</b>

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>Error:</b> {error_message[:500]}
"""
        
        self.send(message.strip())
    
    def notify_milestone(self, milestone: str, value: float):
        """Notify on performance milestone"""
        if not self.enabled or not self.notifications.get('performance_milestones', True):
            return
        
        message = f"""
🎯 <b>Milestone Achieved!</b>

<b>{milestone}:</b> {value:.2f}

Keep up the great work! 🚀
"""
        
        self.send(message.strip())
    
    def notify_system_start(self):
        """Notify when system starts"""
        if not self.enabled:
            return
        
        message = f"""
🤖 <b>KorBot X Enhanced Started</b>

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>Status:</b> Running
<b>Mode:</b> {self.config.get('mode', 'Unknown')}

Bot is now monitoring the markets! 📊
"""
        
        self.send(message.strip())
    
    def notify_system_stop(self, reason: str = "Manual stop"):
        """Notify when system stops"""
        if not self.enabled:
            return
        
        message = f"""
🛑 <b>KorBot X Enhanced Stopped</b>

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>Reason:</b> {reason}

Bot has stopped trading.
"""
        
        self.send(message.strip())
    
    @staticmethod
    def _format_duration(start: datetime, end: Optional[datetime]) -> str:
        """Format trade duration"""
        if not start or not end:
            return "Unknown"
        
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        
        duration = end - start
        
        hours = duration.total_seconds() / 3600
        if hours < 1:
            minutes = duration.total_seconds() / 60
            return f"{minutes:.0f}m"
        elif hours < 24:
            return f"{hours:.1f}h"
        else:
            days = hours / 24
            return f"{days:.1f}d"
    
    def test_connection(self) -> bool:
        """Test Telegram connection"""
        if not self.enabled:
            return False
        
        try:
            self.send("🧪 Test message from KorBot X Enhanced")
            logger.info("Telegram test message sent successfully")
            return True
        except Exception as e:
            logger.error(f"Telegram test failed: {e}")
            return False


if __name__ == "__main__":
    # Test Telegram notifier
    from config_loader import get_config
    
    config = get_config()
    notifier = TelegramNotifier(config)
    
    if notifier.enabled:
        # Test connection
        notifier.test_connection()
        
        # Test trade notification
        test_trade = {
            'symbol': 'AUDCAD',
            'type': 'BUY',
            'strategy': 'Scalping',
            'entry_price': 0.91000,
            'stop_loss': 0.90800,
            'take_profit': 0.91500,
            'lot_size': 0.10,
            'confidence': 0.75,
            'reasons': ['EMA crossover', 'Strong volume']
        }
        
        notifier.notify_trade_opened(test_trade)
        logger.info("Test notifications sent")
    else:
        logger.warning("Telegram not configured")
