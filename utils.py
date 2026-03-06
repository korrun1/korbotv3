"""
🛠️ KorBot X Enhanced - Utility Functions
Version: 2.0
Date: 2026-02-16

Core utility functions for logging, error handling, caching, and helpers.
"""

import logging
import json
import time
import functools
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
import traceback
from collections import OrderedDict
import hashlib


# ============================================================================
# LOGGING SETUP
# ============================================================================

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'trade_id'):
            log_data['trade_id'] = record.trade_id
        if hasattr(record, 'strategy'):
            log_data['strategy'] = record.strategy
        if hasattr(record, 'symbol'):
            log_data['symbol'] = record.symbol
            
        return json.dumps(log_data)


def setup_logger(name: str, config: Dict) -> logging.Logger:
    """
    Setup logger with configuration
    
    Args:
        name: Logger name
        config: Logging configuration from config.yaml
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.get('level', 'INFO')))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler
    if config.get('console_output', True):
        console_handler = logging.StreamHandler()
        if config.get('format') == 'json':
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
        logger.addHandler(console_handler)
    
    # File handlers
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    for log_type, log_file in config.get('files', {}).items():
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=config.get('rotation', {}).get('max_bytes', 10485760),
            backupCount=config.get('rotation', {}).get('backup_count', 5)
        )
        
        if config.get('format') == 'json':
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
        
        logger.addHandler(file_handler)
    
    return logger


# ============================================================================
# ERROR HANDLING & RETRY
# ============================================================================

def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry function on failure with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger = logging.getLogger(func.__module__)
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {str(e)}",
                            exc_info=True
                        )
                        raise
                    
                    logger = logging.getLogger(func.__module__)
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}). "
                        f"Retrying in {current_delay}s... Error: {str(e)}"
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
            
        return wrapper
    return decorator


def safe_execution(default_return=None, log_exception=True):
    """
    Decorator for safe function execution with exception handling
    
    Args:
        default_return: Value to return on exception
        log_exception: Whether to log the exception
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_exception:
                    logger = logging.getLogger(func.__module__)
                    logger.error(
                        f"Exception in {func.__name__}: {str(e)}",
                        exc_info=True
                    )
                return default_return
        return wrapper
    return decorator


# ============================================================================
# CACHING
# ============================================================================

class LRUCache:
    """Simple LRU (Least Recently Used) Cache implementation"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 60):
        """
        Initialize LRU Cache
        
        Args:
            max_size: Maximum number of items in cache
            ttl: Time to live for cache items (seconds)
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            return None
        
        # Check TTL
        if time.time() - self.timestamps[key] > self.ttl:
            self.cache.pop(key)
            self.timestamps.pop(key)
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def set(self, key: str, value: Any):
        """Set value in cache"""
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                oldest_key = next(iter(self.cache))
                self.cache.pop(oldest_key)
                self.timestamps.pop(oldest_key)
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)


def memoize(ttl: int = 60):
    """
    Memoization decorator with TTL
    
    Args:
        ttl: Time to live for cached results (seconds)
    """
    cache = {}
    timestamps = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = hashlib.md5(
                f"{func.__name__}:{str(args)}:{str(kwargs)}".encode()
            ).hexdigest()
            
            # Check if cached and not expired
            if key in cache:
                if time.time() - timestamps[key] < ttl:
                    return cache[key]
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache[key] = result
            timestamps[key] = time.time()
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# TIME & DATE HELPERS
# ============================================================================

def is_trading_time(trading_hours: str = "00:00-23:59") -> bool:
    """
    Check if current time is within trading hours
    
    Args:
        trading_hours: Trading hours in format "HH:MM-HH:MM" (UTC)
        
    Returns:
        True if within trading hours
    """
    start_time, end_time = trading_hours.split('-')
    start_hour, start_minute = map(int, start_time.split(':'))
    end_hour, end_minute = map(int, end_time.split(':'))
    
    now = datetime.utcnow()
    current_minutes = now.hour * 60 + now.minute
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    
    if start_minutes <= end_minutes:
        return start_minutes <= current_minutes <= end_minutes
    else:  # Crosses midnight
        return current_minutes >= start_minutes or current_minutes <= end_minutes


def is_news_time(news_times: list = None) -> bool:
    """
    Check if current time is near major news release
    
    Args:
        news_times: List of news times (HH:MM format)
        
    Returns:
        True if within 15 minutes of news time
    """
    if not news_times:
        # Default major news times (UTC)
        news_times = ["08:30", "10:00", "12:30", "14:00", "15:00"]
    
    now = datetime.utcnow()
    current_minutes = now.hour * 60 + now.minute
    
    for news_time in news_times:
        hour, minute = map(int, news_time.split(':'))
        news_minutes = hour * 60 + minute
        
        # Check if within 15 minutes before or after
        if abs(current_minutes - news_minutes) <= 15:
            return True
    
    return False


# ============================================================================
# DATA HELPERS
# ============================================================================

def normalize_value(value: float, min_val: float, max_val: float) -> float:
    """Normalize value to 0-1 range"""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def calculate_pips(price1: float, price2: float, symbol: str = "AUDCAD") -> float:
    """
    Calculate pip difference between two prices
    
    Args:
        price1: First price
        price2: Second price
        symbol: Trading symbol
        
    Returns:
        Pip difference
    """
    # For JPY pairs, 1 pip = 0.01, for others 1 pip = 0.0001
    pip_value = 0.01 if 'JPY' in symbol else 0.0001
    return abs(price1 - price2) / pip_value


def format_price(price: float, symbol: str = "AUDCAD") -> str:
    """Format price with appropriate decimal places"""
    if 'JPY' in symbol:
        return f"{price:.3f}"
    else:
        return f"{price:.5f}"


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

class PerformanceTimer:
    """Context manager for measuring execution time"""
    
    def __init__(self, name: str, logger: logging.Logger = None):
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        self.logger.debug(f"{self.name} took {duration:.4f} seconds")
        return False


def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.debug(f"{func.__name__} execution time: {duration:.4f}s")
        return result
    return wrapper


# ============================================================================
# VALIDATION
# ============================================================================

def validate_config(config: Dict) -> bool:
    """
    Validate configuration dictionary
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_keys = ['trading', 'risk', 'database', 'logging']
    
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
    
    # Validate risk parameters
    risk = config['risk']
    if risk['base_risk_percent'] <= 0 or risk['base_risk_percent'] > 5:
        raise ValueError("base_risk_percent must be between 0 and 5")
    
    if risk['max_drawdown_percent'] <= 0 or risk['max_drawdown_percent'] > 20:
        raise ValueError("max_drawdown_percent must be between 0 and 20")
    
    # Validate strategies
    trading = config['trading']
    if not any(trading['strategies'].values()):
        raise ValueError("At least one strategy must be enabled")
    
    return True


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

# Global logger for utils module
logger = logging.getLogger(__name__)
