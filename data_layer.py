"""
📊 KorBot X Enhanced - Data Layer
Version: 2.0
Date: 2026-02-16

Enhanced data layer with robust MT5 connection management, error handling,
and efficient data retrieval with caching.
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging
import time
from functools import lru_cache

from utils import retry_on_failure, safe_execution, PerformanceTimer, LRUCache
from config_loader import get_config

logger = logging.getLogger(__name__)


class MT5Connection:
    """MetaTrader 5 connection manager with auto-reconnection"""
    
    def __init__(self, config: Dict):
        """
        Initialize MT5 connection
        
        Args:
            config: MT5 configuration dictionary
        """
        self.config = config
        self.connected = False
        self.last_connection_attempt = None
        self.connection_retry_delay = 10  # seconds
    
    @retry_on_failure(max_attempts=3, delay=2.0)
    def connect(self) -> bool:
        """
        Connect to MT5
        
        Returns:
            True if connection successful
        """
        # Check if already connected
        if self.connected and mt5.terminal_info() is not None:
            return True
        
        # Rate limit connection attempts
        if self.last_connection_attempt:
            time_since_last = time.time() - self.last_connection_attempt
            if time_since_last < self.connection_retry_delay:
                logger.warning(f"Connection retry delay: waiting {self.connection_retry_delay - time_since_last:.1f}s")
                return False
        
        self.last_connection_attempt = time.time()
        
        # Initialize MT5
        if not mt5.initialize():
            error = mt5.last_error()
            logger.error(f"MT5 initialization failed: {error}")
            return False
        
        # Login if credentials provided
        if self.config.get('login') and self.config.get('password'):
            login = int(self.config['login'])
            password = self.config['password']
            server = self.config.get('server', '')
            
            if not mt5.login(login=login, password=password, server=server):
                error = mt5.last_error()
                logger.error(f"MT5 login failed: {error}")
                mt5.shutdown()
                return False
            
            logger.info(f"Connected to MT5: Account {login}, Server {server}")
        else:
            logger.info("Connected to MT5 (no login credentials)")
        
        self.connected = True
        return True
    
    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")
    
    def check_connection(self) -> bool:
        """
        Check if connection is alive
        
        Returns:
            True if connected
        """
        if not self.connected:
            return False
        
        # Check terminal info to verify connection
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            logger.warning("MT5 connection lost")
            self.connected = False
            return False
        
        return True
    
    def reconnect(self) -> bool:
        """
        Reconnect to MT5
        
        Returns:
            True if reconnection successful
        """
        logger.info("Attempting to reconnect to MT5...")
        self.disconnect()
        time.sleep(2)
        return self.connect()
    
    def __enter__(self):
        """Context manager entry"""
        if not self.check_connection():
            self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Don't disconnect on exit - keep connection alive
        pass


class DataLayer:
    """Enhanced data layer with caching and robust error handling"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize data layer
        
        Args:
            config: Configuration dictionary (optional, loads from file if None)
        """
        if config is None:
            config = get_config()
        
        self.config = config
        self.mt5_config = config.get('mt5', {})
        self.connection = MT5Connection(self.mt5_config)
        
        # Initialize caching
        cache_config = config.get('performance', {}).get('cache', {})
        self.cache_enabled = cache_config.get('enabled', True)
        self.cache = LRUCache(
            max_size=cache_config.get('max_size', 1000),
            ttl=cache_config.get('ttl_seconds', 60)
        ) if self.cache_enabled else None
        
        # Connect to MT5
        if not config.get('development', {}).get('mock_mt5', False):
            self.connection.connect()
        
        logger.info("Data Layer initialized")
    
    @safe_execution(default_return=None)
    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Get current bid/ask prices for symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with 'bid', 'ask', 'spread'
        """
        # Check cache
        if self.cache_enabled:
            cache_key = f"price_{symbol}"
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        # Ensure connection
        if not self.connection.check_connection():
            if not self.connection.reconnect():
                logger.error("Failed to reconnect to MT5")
                return None
        
        # Get tick
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            error = mt5.last_error()
            logger.error(f"Failed to get tick for {symbol}: {error}")
            return None
        
        price_data = {
            'bid': tick.bid,
            'ask': tick.ask,
            'spread': tick.ask - tick.bid,
            'timestamp': datetime.fromtimestamp(tick.time)
        }
        
        # Cache result
        if self.cache_enabled:
            self.cache.set(cache_key, price_data)
        
        return price_data
    
    @retry_on_failure(max_attempts=3, delay=1.0)
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        bars: int = 1000,
        start_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, H1, H4, D1)
            bars: Number of bars to retrieve
            start_date: Start date (optional)
            
        Returns:
            DataFrame with OHLCV data
        """
        # Check cache
        if self.cache_enabled:
            cache_key = f"hist_{symbol}_{timeframe}_{bars}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Ensure connection
        if not self.connection.check_connection():
            if not self.connection.reconnect():
                logger.error("Failed to reconnect to MT5")
                return None
        
        # Map timeframe string to MT5 constant
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }
        
        mt5_timeframe = timeframe_map.get(timeframe)
        if mt5_timeframe is None:
            logger.error(f"Invalid timeframe: {timeframe}")
            return None
        
        # Get data
        if start_date:
            rates = mt5.copy_rates_from(symbol, mt5_timeframe, start_date, bars)
        else:
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)
        
        if rates is None or len(rates) == 0:
            error = mt5.last_error()
            logger.error(f"Failed to get historical data for {symbol}: {error}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # Rename columns
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'tick_volume': 'Volume'
        }, inplace=True)
        
        # Select relevant columns
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Cache result
        if self.cache_enabled:
            self.cache.set(cache_key, df)
        
        logger.debug(f"Retrieved {len(df)} bars for {symbol} {timeframe}")
        return df
    
    @safe_execution(default_return=None)
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Get symbol information
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with symbol information
        """
        # Ensure connection
        if not self.connection.check_connection():
            if not self.connection.reconnect():
                return None
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            error = mt5.last_error()
            logger.error(f"Failed to get info for {symbol}: {error}")
            return None
        
        return {
            'name': symbol_info.name,
            'point': symbol_info.point,
            'digits': symbol_info.digits,
            'spread': symbol_info.spread,
            'trade_contract_size': symbol_info.trade_contract_size,
            'min_lot': symbol_info.volume_min,
            'max_lot': symbol_info.volume_max,
            'lot_step': symbol_info.volume_step,
            'trade_tick_size': symbol_info.trade_tick_size,
            'trade_tick_value': symbol_info.trade_tick_value
        }
    
    @safe_execution(default_return=None)
    def get_account_info(self) -> Optional[Dict]:
        """
        Get account information
        
        Returns:
            Dictionary with account information
        """
        # Ensure connection
        if not self.connection.check_connection():
            if not self.connection.reconnect():
                return None
        
        account_info = mt5.account_info()
        if account_info is None:
            error = mt5.last_error()
            logger.error(f"Failed to get account info: {error}")
            return None
        
        return {
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'free_margin': account_info.margin_free,
            'margin_level': account_info.margin_level,
            'profit': account_info.profit,
            'leverage': account_info.leverage,
            'currency': account_info.currency
        }
    
    @safe_execution(default_return=[])
    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get open positions
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            List of position dictionaries
        """
        # Ensure connection
        if not self.connection.check_connection():
            if not self.connection.reconnect():
                return []
        
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        if positions is None:
            return []
        
        position_list = []
        for pos in positions:
            position_list.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'swap': pos.swap,
                'time': datetime.fromtimestamp(pos.time)
            })
        
        return position_list
    
    def calculate_lot_size(
        self,
        symbol: str,
        risk_amount: float,
        stop_loss_pips: float
    ) -> float:
        """
        Calculate position size based on risk
        
        Args:
            symbol: Trading symbol
            risk_amount: Amount to risk in account currency
            stop_loss_pips: Stop loss distance in pips
            
        Returns:
            Lot size
        """
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            logger.error(f"Cannot calculate lot size for {symbol}")
            return 0.01  # Minimum lot size
        
        # Get pip value
        if 'JPY' in symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        # Calculate lot size
        # risk_amount = lot_size * contract_size * stop_loss_pips * pip_value
        lot_size = risk_amount / (symbol_info['trade_contract_size'] * stop_loss_pips * pip_value)
        
        # Round to lot step
        lot_step = symbol_info['lot_step']
        lot_size = round(lot_size / lot_step) * lot_step
        
        # Ensure within limits
        lot_size = max(symbol_info['min_lot'], min(lot_size, symbol_info['max_lot']))
        
        return lot_size
    
    def is_market_open(self, symbol: str) -> bool:
        """
        Check if market is open for trading
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if market is open
        """
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return False
        
        # Check if trading is allowed
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return False
        
        # Market is open if we can get tick data
        return True
    
    def cleanup(self):
        """Cleanup resources"""
        if self.cache:
            self.cache.clear()
        self.connection.disconnect()
        logger.info("Data Layer cleaned up")


if __name__ == "__main__":
    # Test data layer
    from config_loader import get_config
    
    config = get_config()
    data_layer = DataLayer(config)
    
    symbol = config.get('trading.symbol', 'AUDCAD')
    
    # Test current price
    price = data_layer.get_current_price(symbol)
    print(f"Current price for {symbol}: {price}")
    
    # Test historical data
    df = data_layer.get_historical_data(symbol, 'H1', 100)
    print(f"Retrieved {len(df)} bars")
    print(df.tail())
    
    # Test account info
    account = data_layer.get_account_info()
    print(f"Account info: {account}")
    
    # Cleanup
    data_layer.cleanup()
