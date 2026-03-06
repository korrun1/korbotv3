"""
⚙️ KorBot X Enhanced - Configuration Loader
Version: 2.0
Date: 2026-02-16

Secure configuration loading from YAML and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Secure configuration loader"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = {}
        
        # Load environment variables from .env file
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded environment variables from .env file")
        
        # Load configuration
        self.load_config()
        self.inject_env_vars()
        self.validate_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading configuration: {e}")
    
    def inject_env_vars(self):
        """Inject sensitive data from environment variables"""
        
        # MT5 Configuration
        mt5_config = {
            'login': os.getenv('MT5_LOGIN'),
            'password': os.getenv('MT5_PASSWORD'),
            'server': os.getenv('MT5_SERVER')
        }
        self.config['mt5'] = mt5_config
        
        # Telegram Configuration
        if 'telegram' in self.config:
            self.config['telegram']['token'] = os.getenv('TELEGRAM_TOKEN')
            self.config['telegram']['chat_id'] = os.getenv('TELEGRAM_CHAT_ID')
        
        # Redis Password
        if 'database' in self.config and 'redis' in self.config['database']:
            redis_password = os.getenv('REDIS_PASSWORD')
            if redis_password:
                self.config['database']['redis']['password'] = redis_password
        
        # Trading Mode Override
        trading_mode = os.getenv('TRADING_MODE')
        if trading_mode:
            self.config['trading']['mode'] = trading_mode
        
        # Log Level Override
        log_level = os.getenv('LOG_LEVEL')
        if log_level:
            self.config['logging']['level'] = log_level
        
        logger.info("Injected environment variables into configuration")
    
    def validate_config(self):
        """Validate configuration"""
        
        # Check required sections
        required_sections = ['trading', 'risk', 'database', 'logging']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate MT5 credentials if not in test mode
        if not self.config.get('development', {}).get('mock_mt5', False):
            mt5 = self.config.get('mt5', {})
            if not mt5.get('login') or not mt5.get('password'):
                logger.warning(
                    "MT5 credentials not set. Set MT5_LOGIN and MT5_PASSWORD "
                    "environment variables, or enable mock_mt5 in config."
                )
        
        # Validate Telegram credentials if enabled
        telegram = self.config.get('telegram', {})
        if telegram.get('enabled', False):
            if not telegram.get('token') or not telegram.get('chat_id'):
                logger.warning(
                    "Telegram enabled but credentials not set. "
                    "Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID environment variables."
                )
        
        # Validate risk parameters
        risk = self.config['risk']
        if risk['base_risk_percent'] <= 0 or risk['base_risk_percent'] > 5:
            raise ValueError("base_risk_percent must be between 0 and 5")
        
        if risk['max_drawdown_percent'] <= 0 or risk['max_drawdown_percent'] > 20:
            raise ValueError("max_drawdown_percent must be between 0 and 20")
        
        # Ensure at least one strategy is enabled
        strategies = self.config['trading']['strategies']
        if not any(strategies.values()):
            raise ValueError("At least one strategy must be enabled")
        
        # Validate mode
        if self.config['trading']['mode'] not in ['paper', 'live']:
            raise ValueError("trading mode must be 'paper' or 'live'")
        
        logger.info("Configuration validated successfully")
    
    def get(self, key_path: str = None, default: Any = None) -> Any:
        """
        Get configuration value by key path
        
        Args:
            key_path: Dot-separated path (e.g., 'risk.base_risk_percent')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        if key_path is None:
            return self.config
        
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def save(self, output_path: str = None):
        """
        Save current configuration to file (excluding sensitive data)
        
        Args:
            output_path: Path to save configuration
        """
        if output_path is None:
            output_path = self.config_path
        
        # Create a copy without sensitive data
        safe_config = self.config.copy()
        
        # Remove sensitive data
        if 'mt5' in safe_config:
            safe_config['mt5'] = {
                'login': '***',
                'password': '***',
                'server': safe_config['mt5'].get('server', '***')
            }
        
        if 'telegram' in safe_config:
            safe_config['telegram']['token'] = '***'
            safe_config['telegram']['chat_id'] = '***'
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(safe_config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Saved configuration to {output_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def reload(self):
        """Reload configuration from file"""
        self.load_config()
        self.inject_env_vars()
        self.validate_config()
        logger.info("Configuration reloaded")
    
    def __repr__(self):
        """String representation (without sensitive data)"""
        return f"ConfigLoader(mode={self.get('trading.mode')}, symbol={self.get('trading.symbol')})"


# Global configuration instance
_config_instance = None


def get_config(config_path: str = "config/config.yaml") -> ConfigLoader:
    """
    Get global configuration instance (Singleton pattern)
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ConfigLoader instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
    
    return _config_instance


def reload_config():
    """Reload global configuration"""
    global _config_instance
    
    if _config_instance is not None:
        _config_instance.reload()
    else:
        _config_instance = ConfigLoader()


if __name__ == "__main__":
    # Test configuration loading
    config = get_config()
    print("Configuration loaded successfully!")
    print(f"Trading mode: {config.get('trading.mode')}")
    print(f"Base risk: {config.get('risk.base_risk_percent')}%")
    print(f"Enabled strategies: {config.get('trading.strategies')}")
