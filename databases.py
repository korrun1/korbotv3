"""
💾 KorBot X Enhanced - Database Manager
Version: 2.0
Date: 2026-02-16

Optimized database management for SQLite and Redis with batch operations
and efficient data handling.
"""

import sqlite3
import redis
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import pickle
from contextlib import contextmanager

from utils import safe_execution, PerformanceTimer

logger = logging.getLogger(__name__)


class SQLiteManager:
    """SQLite database manager for historical trade data"""
    
    def __init__(self, config: Dict):
        """
        Initialize SQLite manager
        
        Args:
            config: Database configuration
        """
        self.config = config.get('database', {}).get('sqlite', {})
        self.db_path = Path(self.config.get('path', 'data/historical.sqlite'))
        self.wal_mode = self.config.get('wal_mode', True)
        
        # Create data directory if not exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._initialize_database()
        
        logger.info(f"SQLite Manager initialized: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        
        if self.wal_mode:
            conn.execute('PRAGMA journal_mode=WAL')
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Create database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    ticket INTEGER,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    lot_size REAL NOT NULL,
                    exit_time TEXT,
                    exit_price REAL,
                    pnl REAL,
                    pnl_pips REAL,
                    status TEXT NOT NULL,
                    confidence REAL,
                    reasons TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    total_pnl REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Strategy performance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    date TEXT NOT NULL,
                    trades INTEGER,
                    wins INTEGER,
                    losses INTEGER,
                    pnl REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indices
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)')
            
            logger.info("Database tables initialized")
    
    @safe_execution(default_return=None)
    def save_trade(self, trade_data: Dict) -> bool:
        """
        Save trade to database
        
        Args:
            trade_data: Trade dictionary
            
        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO trades 
                (trade_id, ticket, symbol, type, strategy, entry_time, entry_price,
                 stop_loss, take_profit, lot_size, exit_time, exit_price, pnl, pnl_pips,
                 status, confidence, reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data['trade_id'],
                trade_data.get('ticket'),
                trade_data['symbol'],
                trade_data['type'],
                trade_data['strategy'],
                str(trade_data['entry_time']),
                trade_data['entry_price'],
                trade_data['stop_loss'],
                trade_data['take_profit'],
                trade_data['lot_size'],
                str(trade_data.get('exit_time')) if trade_data.get('exit_time') else None,
                trade_data.get('exit_price'),
                trade_data.get('pnl'),
                trade_data.get('pnl_pips'),
                trade_data['status'],
                trade_data.get('confidence'),
                json.dumps(trade_data.get('reasons', []))
            ))
            
            logger.debug(f"Saved trade: {trade_data['trade_id']}")
            return True
    
    @safe_execution(default_return=[])
    def get_trades(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get trades from database
        
        Args:
            symbol: Filter by symbol
            strategy: Filter by strategy
            limit: Maximum number of trades
            
        Returns:
            List of trade dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM trades WHERE 1=1'
            params = []
            
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
            
            if strategy:
                query += ' AND strategy = ?'
                params.append(strategy)
            
            query += ' ORDER BY entry_time DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            trades = []
            for row in rows:
                trade = dict(row)
                trade['reasons'] = json.loads(trade['reasons']) if trade['reasons'] else []
                trades.append(trade)
            
            return trades
    
    @safe_execution(default_return={})
    def get_statistics(self, days: int = 30) -> Dict:
        """
        Get trading statistics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Statistics dictionary
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total trades
            cursor.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                       SUM(pnl) as total_pnl,
                       AVG(pnl) as avg_pnl
                FROM trades
                WHERE status = 'closed'
                AND exit_time >= datetime('now', '-' || ? || ' days')
            ''', (days,))
            
            row = cursor.fetchone()
            
            stats = {
                'total_trades': row['total'] or 0,
                'winning_trades': row['wins'] or 0,
                'losing_trades': row['losses'] or 0,
                'total_pnl': row['total_pnl'] or 0,
                'avg_pnl': row['avg_pnl'] or 0,
                'win_rate': (row['wins'] / row['total'] * 100) if row['total'] else 0
            }
            
            return stats


class RedisManager:
    """Redis manager for real-time data caching"""
    
    def __init__(self, config: Dict):
        """
        Initialize Redis manager
        
        Args:
            config: Database configuration
        """
        self.config = config.get('database', {}).get('redis', {})
        
        self.host = self.config.get('host', 'localhost')
        self.port = self.config.get('port', 6379)
        self.db = self.config.get('db', 0)
        self.password = self.config.get('password')
        
        self.use_pipeline = self.config.get('use_pipeline', True)
        self.pipeline_size = self.config.get('pipeline_size', 100)
        
        # Connect to Redis
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Redis Manager initialized: {self.host}:{self.port}")
            
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            self.client = None
    
    @safe_execution(default_return=None)
    def set(self, key: str, value: Any, expiry: int = 3600) -> bool:
        """
        Set value in Redis
        
        Args:
            key: Key
            value: Value (will be serialized)
            expiry: Expiry time in seconds
            
        Returns:
            True if successful
        """
        if not self.client:
            return False
        
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)
            
            self.client.setex(key, expiry, value)
            return True
            
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    @safe_execution(default_return=None)
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis
        
        Args:
            key: Key
            
        Returns:
            Value (deserialized) or None
        """
        if not self.client:
            return None
        
        try:
            value = self.client.get(key)
            
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    @safe_execution(default_return=False)
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.client:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    def save_market_data(self, symbol: str, timeframe: str, data: Dict):
        """Save market data to Redis"""
        key = f"market:{symbol}:{timeframe}"
        self.set(key, data, expiry=60)  # 1 minute expiry
    
    def get_market_data(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get market data from Redis"""
        key = f"market:{symbol}:{timeframe}"
        return self.get(key)
    
    def save_signal(self, signal_data: Dict):
        """Save signal to Redis"""
        key = f"signal:{signal_data['symbol']}:{datetime.now().timestamp()}"
        self.set(key, signal_data, expiry=3600)  # 1 hour expiry
    
    def get_open_positions(self) -> List[Dict]:
        """Get open positions from Redis"""
        positions = []
        
        if not self.client:
            return positions
        
        try:
            keys = self.client.keys("position:*")
            for key in keys:
                data = self.get(key)
                if data:
                    positions.append(data)
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
        
        return positions
    
    def save_position(self, position_data: Dict):
        """Save position to Redis"""
        key = f"position:{position_data['ticket']}"
        self.set(key, position_data, expiry=86400)  # 24 hours
    
    def delete_position(self, ticket: int):
        """Delete position from Redis"""
        key = f"position:{ticket}"
        self.delete(key)


class DatabaseManager:
    """Unified database manager"""
    
    def __init__(self, config: Dict):
        """
        Initialize database manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize managers
        self.sqlite = SQLiteManager(config)
        self.redis = RedisManager(config)
        
        logger.info("Database Manager initialized")
    
    def save_trade(self, trade_data: Dict):
        """Save trade to both SQLite and Redis"""
        # Save to SQLite (permanent)
        self.sqlite.save_trade(trade_data)
        
        # Save to Redis if open (temporary)
        if trade_data['status'] == 'open':
            self.redis.save_position(trade_data)
        else:
            # Remove from Redis if closed
            if trade_data.get('ticket'):
                self.redis.delete_position(trade_data['ticket'])
    
    def get_trades(self, **kwargs) -> List[Dict]:
        """Get trades from SQLite"""
        return self.sqlite.get_trades(**kwargs)
    
    def get_statistics(self, days: int = 30) -> Dict:
        """Get statistics from SQLite"""
        return self.sqlite.get_statistics(days)
    
    def cache_market_data(self, symbol: str, timeframe: str, data: Dict):
        """Cache market data in Redis"""
        self.redis.save_market_data(symbol, timeframe, data)
    
    def get_cached_market_data(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get cached market data from Redis"""
        return self.redis.get_market_data(symbol, timeframe)


if __name__ == "__main__":
    # Test database manager
    from config_loader import get_config
    
    config = get_config()
    db_manager = DatabaseManager(config)
    
    # Test trade save
    test_trade = {
        'trade_id': 'TEST_001',
        'ticket': 12345,
        'symbol': 'AUDCAD',
        'type': 'BUY',
        'strategy': 'Scalping',
        'entry_time': datetime.now(),
        'entry_price': 0.91000,
        'stop_loss': 0.90800,
        'take_profit': 0.91500,
        'lot_size': 0.10,
        'status': 'open',
        'confidence': 0.75,
        'reasons': ['EMA crossover', 'Strong volume']
    }
    
    db_manager.save_trade(test_trade)
    logger.info("Test trade saved")
    
    # Get statistics
    stats = db_manager.get_statistics(30)
    logger.info(f"Statistics: {stats}")
    
    # Test Redis cache
    db_manager.redis.set('test_key', {'value': 123}, expiry=60)
    cached_value = db_manager.redis.get('test_key')
    logger.info(f"Cached value: {cached_value}")
