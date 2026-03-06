"""
🤖 KorBot X Enhanced - AI Optimization Engine
Version: 2.0
Date: 2026-02-16

Advanced AI optimization with XGBoost confidence model, PPO exit optimization,
and Bayesian hyperparameter optimization.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import joblib
from pathlib import Path

# Machine Learning
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Reinforcement Learning
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
import gymnasium as gym

# Bayesian Optimization
from skopt import BayesSearchCV
from skopt.space import Real, Integer, Categorical

from utils import safe_execution, PerformanceTimer
from strategy_engine import Signal, SignalType

logger = logging.getLogger(__name__)


class FeatureEngineering:
    """Advanced feature engineering for ML models"""
    
    @staticmethod
    def create_features(df: pd.DataFrame, signal: Signal) -> pd.DataFrame:
        """
        Create comprehensive feature set
        
        Args:
            df: DataFrame with indicators
            signal: Trading signal
            
        Returns:
            DataFrame with features
        """
        if df is None or df.empty:
            return pd.DataFrame()
        
        features = pd.DataFrame()
        latest = df.iloc[-1]
        
        # 1. Price Momentum Features
        features['price_momentum_5'] = latest.get('Price_Momentum_5', 0)
        features['price_momentum_10'] = latest.get('Price_Momentum_10', 0)
        features['price_momentum_20'] = latest.get('Price_Momentum_20', 0)
        
        # 2. Volume Profile
        features['volume_ratio'] = latest.get('Volume_Ratio', 1.0)
        features['obv_change'] = df['OBV'].pct_change(5).iloc[-1] if 'OBV' in df else 0
        features['cmf'] = latest.get('CMF', 0)
        
        # 3. Volatility Regime
        features['volatility_regime'] = latest.get('Volatility_Regime', 1.0)
        features['atr'] = latest.get('ATR', 0)
        features['bb_width'] = latest.get('BB_width', 0)
        features['historical_vol'] = latest.get('Historical_Vol', 0)
        
        # 4. Trend Strength
        features['trend_strength'] = latest.get('Trend_Strength', 0)
        features['adx'] = latest.get('ADX', 0)
        features['adx_pos'] = latest.get('ADX_pos', 0)
        features['adx_neg'] = latest.get('ADX_neg', 0)
        
        # 5. RSI Divergence
        features['rsi'] = latest.get('RSI', 50)
        features['rsi_change'] = df['RSI'].diff(5).iloc[-1] if 'RSI' in df else 0
        
        # 6. MACD
        features['macd'] = latest.get('MACD', 0)
        features['macd_signal'] = latest.get('MACD_signal', 0)
        features['macd_diff'] = latest.get('MACD_diff', 0)
        
        # 7. Market Microstructure (from signal)
        features['spread'] = 0  # Will be updated with real spread
        features['spread_bps'] = 0
        
        # 8. Time Features
        now = datetime.now()
        features['hour'] = now.hour
        features['day_of_week'] = now.weekday()
        features['is_asian_session'] = 1 if 0 <= now.hour < 8 else 0
        features['is_london_session'] = 1 if 8 <= now.hour < 16 else 0
        features['is_ny_session'] = 1 if 13 <= now.hour < 21 else 0
        
        # 9. Pattern Features
        features['near_resistance'] = latest.get('Nearest_Resistance', np.nan)
        features['near_support'] = latest.get('Nearest_Support', np.nan)
        
        # 10. Stochastic
        features['stoch_k'] = latest.get('Stoch_K', 50)
        features['stoch_d'] = latest.get('Stoch_D', 50)
        
        # 11. Signal Characteristics
        features['signal_type'] = 1 if signal.type == SignalType.BUY else -1 if signal.type == SignalType.SELL else 0
        features['strategy_type'] = hash(signal.strategy) % 100  # Simple encoding
        
        # 12. Risk/Reward
        if signal.entry_price > 0 and signal.stop_loss > 0 and signal.take_profit > 0:
            risk = abs(signal.entry_price - signal.stop_loss)
            reward = abs(signal.take_profit - signal.entry_price)
            features['risk_reward_ratio'] = reward / risk if risk > 0 else 0
        else:
            features['risk_reward_ratio'] = 0
        
        # Fill NaN values
        features = features.fillna(0)
        
        return features


class XGBoostConfidence:
    """XGBoost model for signal confidence prediction"""
    
    def __init__(self, config: Dict):
        """
        Initialize XGBoost model
        
        Args:
            config: AI configuration
        """
        self.config = config.get('ai', {}).get('xgboost', {})
        self.enabled = self.config.get('enabled', True)
        self.min_confidence = self.config.get('min_confidence', 0.65)
        self.retrain_every = self.config.get('retrain_every_trades', 1000)
        
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.trades_since_training = 0
        
        # Model path
        self.model_dir = Path('models')
        self.model_dir.mkdir(exist_ok=True)
        self.model_path = self.model_dir / 'xgboost_confidence.joblib'
        self.scaler_path = self.model_dir / 'scaler.joblib'
        
        # Load existing model if available
        self.load_model()
        
        logger.info("XGBoost Confidence Model initialized")
    
    def load_model(self):
        """Load trained model from disk"""
        if self.model_path.exists() and self.scaler_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info("Loaded XGBoost model from disk")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self.model = None
    
    def save_model(self):
        """Save trained model to disk"""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("Saved XGBoost model to disk")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    @safe_execution(default_return=0.5)
    def predict_confidence(self, features: pd.DataFrame) -> float:
        """
        Predict signal confidence
        
        Args:
            features: Feature DataFrame
            
        Returns:
            Confidence score (0-1)
        """
        if not self.enabled or self.model is None:
            return 0.7  # Default confidence
        
        try:
            # Scale features
            X = self.scaler.transform(features)
            
            # Predict probability
            confidence = self.model.predict_proba(X)[0][1]
            
            return float(confidence)
        except Exception as e:
            logger.error(f"Error predicting confidence: {e}")
            return 0.5
    
    def train(self, historical_data: pd.DataFrame):
        """
        Train XGBoost model
        
        Args:
            historical_data: Historical trades with features and outcomes
        """
        if historical_data is None or len(historical_data) < 100:
            logger.warning("Not enough data to train XGBoost model")
            return
        
        logger.info(f"Training XGBoost model with {len(historical_data)} samples")
        
        try:
            # Prepare data
            X = historical_data.drop(['outcome', 'trade_id'], axis=1, errors='ignore')
            y = historical_data['outcome']  # 1 for win, 0 for loss
            
            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train XGBoost
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                objective='binary:logistic',
                eval_metric='logloss',
                use_label_encoder=False,
                random_state=42
            )
            
            self.model.fit(
                X_train_scaled, y_train,
                eval_set=[(X_test_scaled, y_test)],
                verbose=False
            )
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred)
            
            logger.info(
                f"XGBoost trained - Accuracy: {accuracy:.3f}, "
                f"Precision: {precision:.3f}, Recall: {recall:.3f}, F1: {f1:.3f}"
            )
            
            # Save model
            self.save_model()
            self.trades_since_training = 0
            
        except Exception as e:
            logger.error(f"Error training XGBoost: {e}", exc_info=True)
    
    def should_retrain(self) -> bool:
        """Check if model should be retrained"""
        return self.trades_since_training >= self.retrain_every
    
    def increment_trade_count(self):
        """Increment trade counter"""
        self.trades_since_training += 1


class TradingEnvironment(gym.Env):
    """Custom trading environment for PPO"""
    
    def __init__(self, historical_data: pd.DataFrame):
        """
        Initialize trading environment
        
        Args:
            historical_data: Historical price data
        """
        super(TradingEnvironment, self).__init__()
        
        self.df = historical_data
        self.current_step = 0
        self.position = 0  # 0: no position, 1: long, -1: short
        self.entry_price = 0
        self.balance = 10000
        self.initial_balance = 10000
        
        # Action space: 0: hold, 1: close
        self.action_space = gym.spaces.Discrete(2)
        
        # Observation space: price features
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32
        )
    
    def reset(self, seed=None, options=None):
        """Reset environment"""
        super().reset(seed=seed)
        self.current_step = 0
        self.position = 1  # Start with a position
        self.entry_price = self.df.iloc[0]['Close']
        self.balance = self.initial_balance
        return self._get_observation(), {}
    
    def _get_observation(self):
        """Get current observation"""
        row = self.df.iloc[self.current_step]
        
        obs = np.array([
            row['Close'] / self.entry_price - 1,  # Unrealized P&L
            row.get('RSI', 50) / 100,
            row.get('MACD', 0),
            row.get('ATR', 0),
            row.get('Volume_Ratio', 1),
            self.position,
            (row['Close'] - row['EMA_20']) / row['ATR'] if row.get('ATR', 0) > 0 else 0,
            row.get('ADX', 0) / 100,
            row.get('Stoch_K', 50) / 100,
            self.balance / self.initial_balance - 1
        ], dtype=np.float32)
        
        return obs
    
    def step(self, action):
        """Execute action"""
        current_price = self.df.iloc[self.current_step]['Close']
        
        reward = 0
        terminated = False
        
        # Action: 0 = hold, 1 = close
        if action == 1 and self.position != 0:
            # Close position
            pnl = (current_price - self.entry_price) * self.position
            self.balance += pnl
            
            # Reward based on Sharpe ratio
            returns = pnl / self.entry_price
            reward = returns * 100  # Scale reward
            
            self.position = 0
            terminated = True
        
        self.current_step += 1
        
        if self.current_step >= len(self.df) - 1:
            terminated = True
        
        truncated = False
        
        return self._get_observation(), reward, terminated, truncated, {}


class PPOExitOptimizer:
    """PPO model for optimal exit timing"""
    
    def __init__(self, config: Dict):
        """
        Initialize PPO optimizer
        
        Args:
            config: AI configuration
        """
        self.config = config.get('ai', {}).get('ppo', {})
        self.enabled = self.config.get('enabled', True)
        
        self.model = None
        self.model_dir = Path('models')
        self.model_dir.mkdir(exist_ok=True)
        self.model_path = self.model_dir / 'ppo_exit'
        
        logger.info("PPO Exit Optimizer initialized")
    
    def train(self, historical_data: pd.DataFrame, timesteps: int = 10000):
        """
        Train PPO model
        
        Args:
            historical_data: Historical price data with indicators
            timesteps: Number of training timesteps
        """
        if historical_data is None or len(historical_data) < 100:
            logger.warning("Not enough data to train PPO model")
            return
        
        logger.info(f"Training PPO model with {timesteps} timesteps")
        
        try:
            # Create environment
            env = TradingEnvironment(historical_data)
            
            # Train PPO
            self.model = PPO(
                'MlpPolicy',
                env,
                learning_rate=self.config.get('learning_rate', 0.0003),
                gamma=self.config.get('gamma', 0.99),
                clip_range=self.config.get('clip_epsilon', 0.2),
                verbose=0
            )
            
            self.model.learn(total_timesteps=timesteps)
            
            # Save model
            self.model.save(self.model_path)
            logger.info("PPO model trained and saved")
            
        except Exception as e:
            logger.error(f"Error training PPO: {e}", exc_info=True)
    
    def should_exit(self, observation: np.ndarray) -> bool:
        """
        Determine if position should be exited
        
        Args:
            observation: Current observation
            
        Returns:
            True if should exit
        """
        if not self.enabled or self.model is None:
            return False
        
        try:
            action, _ = self.model.predict(observation, deterministic=True)
            return action == 1  # 1 = close position
        except Exception as e:
            logger.error(f"Error predicting exit: {e}")
            return False


class BayesianOptimizer:
    """Bayesian optimization for hyperparameter tuning"""
    
    def __init__(self, config: Dict):
        """
        Initialize Bayesian optimizer
        
        Args:
            config: AI configuration
        """
        self.config = config.get('ai', {}).get('bayesian_optimization', {})
        self.enabled = self.config.get('enabled', True)
        self.n_iterations = self.config.get('n_iterations', 100)
        self.n_initial_points = self.config.get('n_initial_points', 20)
        
        logger.info("Bayesian Optimizer initialized")
    
    def optimize_strategy_parameters(
        self,
        strategy_name: str,
        parameter_space: Dict,
        objective_function: callable
    ) -> Dict:
        """
        Optimize strategy parameters
        
        Args:
            strategy_name: Name of strategy
            parameter_space: Dictionary of parameter ranges
            objective_function: Function to maximize
            
        Returns:
            Best parameters
        """
        if not self.enabled:
            return {}
        
        logger.info(f"Optimizing parameters for {strategy_name}")
        
        try:
            # Convert parameter space to skopt format
            search_space = []
            param_names = []
            
            for param_name, param_range in parameter_space.items():
                param_names.append(param_name)
                
                if isinstance(param_range, tuple) and len(param_range) == 2:
                    if isinstance(param_range[0], int):
                        search_space.append(Integer(param_range[0], param_range[1]))
                    else:
                        search_space.append(Real(param_range[0], param_range[1]))
                elif isinstance(param_range, list):
                    search_space.append(Categorical(param_range))
            
            # Run Bayesian optimization
            from skopt import gp_minimize
            
            result = gp_minimize(
                objective_function,
                search_space,
                n_calls=self.n_iterations,
                n_initial_points=self.n_initial_points,
                random_state=42,
                verbose=True
            )
            
            # Extract best parameters
            best_params = {
                param_names[i]: result.x[i]
                for i in range(len(param_names))
            }
            
            logger.info(f"Best parameters for {strategy_name}: {best_params}")
            logger.info(f"Best score: {-result.fun:.4f}")
            
            return best_params
            
        except Exception as e:
            logger.error(f"Error in Bayesian optimization: {e}", exc_info=True)
            return {}


class AIOptimizationEngine:
    """Main AI optimization engine"""
    
    def __init__(self, config: Dict):
        """
        Initialize AI optimization engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize components
        self.xgboost = XGBoostConfidence(config)
        self.ppo = PPOExitOptimizer(config)
        self.bayesian = BayesianOptimizer(config)
        self.feature_eng = FeatureEngineering()
        
        logger.info("AI Optimization Engine initialized")
    
    def enhance_signal(self, signal: Signal, df: pd.DataFrame) -> Signal:
        """
        Enhance signal with AI confidence
        
        Args:
            signal: Original signal
            df: DataFrame with indicators
            
        Returns:
            Enhanced signal
        """
        if signal is None:
            return None
        
        # Create features
        features = self.feature_eng.create_features(df, signal)
        
        # Predict confidence
        ai_confidence = self.xgboost.predict_confidence(features)
        
        # Update signal confidence (weighted average)
        signal.confidence = (signal.confidence * 0.5) + (ai_confidence * 0.5)
        
        logger.debug(
            f"Signal confidence enhanced: {signal.strategy} - "
            f"Original: {signal.confidence:.2f}, AI: {ai_confidence:.2f}"
        )
        
        return signal
    
    def should_exit_position(self, position_data: Dict, df: pd.DataFrame) -> bool:
        """
        Determine if position should be exited using PPO
        
        Args:
            position_data: Current position data
            df: DataFrame with indicators
            
        Returns:
            True if should exit
        """
        # Create observation for PPO
        # This is a simplified version
        obs = np.zeros(10, dtype=np.float32)
        # Fill with actual data...
        
        return self.ppo.should_exit(obs)


if __name__ == "__main__":
    # Test AI optimization
    from config_loader import get_config
    from data_layer import DataLayer
    from market_intel import MarketIntelligence
    
    config = get_config()
    data_layer = DataLayer(config)
    market_intel = MarketIntelligence(config)
    ai_engine = AIOptimizationEngine(config)
    
    symbol = config.get('trading.symbol', 'AUDCAD')
    
    # Get data
    df = data_layer.get_historical_data(symbol, 'H1', 500)
    if df is not None:
        df = market_intel.calculate_all_indicators(df)
        
        print("AI Optimization Engine ready!")
        print(f"XGBoost model: {'Loaded' if ai_engine.xgboost.model else 'Not trained'}")
        print(f"PPO model: {'Loaded' if ai_engine.ppo.model else 'Not trained'}")
    
    data_layer.cleanup()
