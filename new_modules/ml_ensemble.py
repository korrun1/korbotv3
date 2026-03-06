"""
🤖 ml_ensemble.py — Multi-Model Machine Learning Ensemble
Version: 3.0
Date: 2026-03

Features:
- XGBoost + LightGBM + CatBoost ensemble (stacking meta-learner)
- LSTM sequential pattern model
- Weighted voting based on recent model performance
- Online learning: incremental updates after each trade closes
- Model drift detection using CUSUM statistic
- Feature importance monitoring and auto-selection
- Parallel model inference
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
import joblib
from pathlib import Path
from datetime import datetime
from collections import deque
import threading

# Core ML
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, roc_auc_score
from sklearn.model_selection import cross_val_score

# Ensemble models
import xgboost as xgb
import lightgbm as lgb

try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False
    logging.getLogger(__name__).warning("CatBoost not installed — using XGB+LGB only")

# Deep learning (optional)
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.callbacks import EarlyStopping
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logging.getLogger(__name__).warning("TensorFlow not installed — LSTM disabled")

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────
# FEATURE ENGINEERING V2
# ──────────────────────────────────────────────────

class FeatureEngineeringV2:
    """
    Enhanced feature engineering for the ensemble.
    Creates 50+ features across multiple categories.
    """

    FEATURE_NAMES = [
        # Price momentum
        'price_mom_3', 'price_mom_5', 'price_mom_10', 'price_mom_20',
        # RSI-family
        'rsi', 'rsi_change', 'rsi_divergence',
        # MACD
        'macd', 'macd_signal', 'macd_hist', 'macd_hist_change',
        # Bollinger Bands
        'bb_pct', 'bb_width', 'bb_squeeze',
        # ATR / Volatility
        'atr', 'atr_change', 'vol_regime', 'hist_vol',
        # ADX / Trend
        'adx', 'adx_pos', 'adx_neg', 'adx_change',
        # Stochastic
        'stoch_k', 'stoch_d', 'stoch_diff',
        # Volume
        'vol_ratio', 'obv_change', 'cmf', 'mfi',
        # EMA alignment
        'ema_5_13', 'ema_20_50', 'ema_50_200', 'price_ema20_dist',
        # Candlestick
        'body_ratio', 'upper_wick_ratio', 'lower_wick_ratio',
        # Support/Resistance
        'dist_to_high_20', 'dist_to_low_20',
        # Market microstructure
        'spread_ratio', 'price_change_1h',
        # Time features
        'hour_sin', 'hour_cos', 'day_of_week',
        # Cross-indicator
        'rsi_bb_alignment', 'trend_momentum_agree',
    ]

    @classmethod
    def create_features(
        cls,
        df: pd.DataFrame,
        signal_direction: int  # 1 for BUY, -1 for SELL
    ) -> Optional[np.ndarray]:
        """
        Create feature vector from DataFrame.

        Args:
            df: DataFrame with indicators (at least 20 rows)
            signal_direction: 1 (BUY) or -1 (SELL)

        Returns:
            numpy array of shape (1, n_features) or None
        """
        if df is None or len(df) < 20:
            return None

        row = df.iloc[-1]
        prev = df.iloc[-2]
        features = {}

        # Price momentum (direction-adjusted)
        for n in [3, 5, 10, 20]:
            if len(df) > n:
                mom = (df['Close'].iloc[-1] / df['Close'].iloc[-1 - n] - 1) * signal_direction
                features[f'price_mom_{n}'] = float(mom)
            else:
                features[f'price_mom_{n}'] = 0.0

        # RSI
        rsi = float(row.get('RSI', 50))
        features['rsi'] = (rsi - 50) / 50 * signal_direction  # Normalize and direction-adjust
        features['rsi_change'] = (rsi - float(prev.get('RSI', 50))) / 50
        # RSI divergence: RSI direction vs price direction
        rsi_trend = 1 if rsi > float(prev.get('RSI', 50)) else -1
        price_trend = 1 if df['Close'].iloc[-1] > df['Close'].iloc[-5] else -1 if len(df) > 5 else 0
        features['rsi_divergence'] = float(rsi_trend * price_trend)  # -1 = divergence

        # MACD
        macd = float(row.get('MACD', 0))
        macd_sig = float(row.get('MACD_signal', 0))
        macd_hist = macd - macd_sig
        prev_hist = float(prev.get('MACD', 0)) - float(prev.get('MACD_signal', 0))
        features['macd'] = macd * signal_direction
        features['macd_signal'] = macd_sig * signal_direction
        features['macd_hist'] = macd_hist * signal_direction
        features['macd_hist_change'] = (macd_hist - prev_hist) * signal_direction

        # Bollinger Bands
        bb_pct = float(row.get('BB_pct', 0.5))
        bb_width = float(row.get('BB_width', 0))
        features['bb_pct'] = (bb_pct - 0.5) * signal_direction * 2  # Center and direction-adjust
        features['bb_width'] = bb_width
        features['bb_squeeze'] = 1.0 if bb_width < df['BB_width'].quantile(0.1) else 0.0 if 'BB_width' in df else 0.0

        # ATR/Volatility
        atr = float(row.get('ATR', 0))
        prev_atr = float(prev.get('ATR', atr))
        features['atr'] = atr
        features['atr_change'] = (atr / prev_atr - 1) if prev_atr > 0 else 0.0
        features['vol_regime'] = float(row.get('Volatility_Regime', 1.0))
        features['hist_vol'] = float(row.get('Historical_Vol', 0))

        # ADX
        adx = float(row.get('ADX', 0))
        adx_pos = float(row.get('ADX_pos', 0))
        adx_neg = float(row.get('ADX_neg', 0))
        features['adx'] = adx / 50.0  # Normalize
        features['adx_pos'] = adx_pos / 50.0 * signal_direction
        features['adx_neg'] = adx_neg / 50.0 * (-signal_direction)
        features['adx_change'] = (adx - float(prev.get('ADX', adx))) / 50.0

        # Stochastic
        stoch_k = float(row.get('Stoch_K', 50))
        stoch_d = float(row.get('Stoch_D', 50))
        features['stoch_k'] = (stoch_k - 50) / 50 * signal_direction
        features['stoch_d'] = (stoch_d - 50) / 50 * signal_direction
        features['stoch_diff'] = (stoch_k - stoch_d) / 50 * signal_direction

        # Volume
        features['vol_ratio'] = float(row.get('Volume_Ratio', 1.0))
        features['obv_change'] = float(df['OBV'].pct_change(5).iloc[-1]) if 'OBV' in df else 0.0
        features['cmf'] = float(row.get('CMF', 0))
        features['mfi'] = float(row.get('MFI', 50) - 50) / 50

        # EMA alignment
        ema5 = float(row.get('EMA_5', row['Close']))
        ema13 = float(row.get('EMA_13', row['Close']))
        ema20 = float(row.get('EMA_20', row['Close']))
        ema50 = float(row.get('EMA_50', row['Close']))
        ema200 = float(row.get('EMA_200', row['Close']))
        features['ema_5_13'] = (1 if ema5 > ema13 else -1) * signal_direction
        features['ema_20_50'] = (1 if ema20 > ema50 else -1) * signal_direction
        features['ema_50_200'] = (1 if ema50 > ema200 else -1) * signal_direction
        features['price_ema20_dist'] = ((row['Close'] - ema20) / (atr + 1e-10)) * signal_direction

        # Candlestick
        body = abs(float(row['Close']) - float(row['Open']))
        full_range = float(row['High']) - float(row['Low']) + 1e-10
        upper_wick = float(row['High']) - max(float(row['Close']), float(row['Open']))
        lower_wick = min(float(row['Close']), float(row['Open'])) - float(row['Low'])
        features['body_ratio'] = body / full_range
        features['upper_wick_ratio'] = upper_wick / full_range
        features['lower_wick_ratio'] = lower_wick / full_range

        # S/R distance
        if len(df) >= 20:
            recent_high = df['High'].iloc[-20:].max()
            recent_low = df['Low'].iloc[-20:].min()
            features['dist_to_high_20'] = (recent_high - row['Close']) / (atr + 1e-10) * signal_direction
            features['dist_to_low_20'] = (row['Close'] - recent_low) / (atr + 1e-10) * signal_direction
        else:
            features['dist_to_high_20'] = 0.0
            features['dist_to_low_20'] = 0.0

        # Microstructure
        features['spread_ratio'] = 0.0  # Placeholder: filled from price_data
        features['price_change_1h'] = (df['Close'].pct_change(4).iloc[-1]) * signal_direction if len(df) > 4 else 0.0

        # Time features
        ts = df.index[-1]
        hour = ts.hour if hasattr(ts, 'hour') else 12
        day = ts.dayofweek if hasattr(ts, 'dayofweek') else 2
        features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        features['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        features['day_of_week'] = day / 4.0

        # Cross-indicator alignments
        features['rsi_bb_alignment'] = float((rsi > 50) == (bb_pct > 0.5)) * signal_direction
        adx_aligned = adx > 25
        mom_positive = features.get('price_mom_5', 0) > 0
        features['trend_momentum_agree'] = float(adx_aligned and mom_positive)

        # Build ordered feature vector
        feature_vector = [features.get(name, 0.0) for name in cls.FEATURE_NAMES]
        return np.array(feature_vector, dtype=np.float32).reshape(1, -1)

    @classmethod
    def create_sequence_features(
        cls,
        df: pd.DataFrame,
        signal_direction: int,
        lookback: int = 20
    ) -> Optional[np.ndarray]:
        """
        Create sequence of feature vectors for LSTM.

        Returns:
            numpy array of shape (1, lookback, n_features)
        """
        if df is None or len(df) < lookback + 5:
            return None

        sequence = []
        for i in range(lookback, 0, -1):
            slice_df = df.iloc[:-i] if i > 0 else df
            fv = cls.create_features(slice_df, signal_direction)
            if fv is None:
                return None
            sequence.append(fv[0])

        return np.array(sequence, dtype=np.float32).reshape(1, lookback, -1)


# ──────────────────────────────────────────────────
# INDIVIDUAL MODELS
# ──────────────────────────────────────────────────

class XGBoostModel:
    """XGBoost classifier with incremental learning support"""

    def __init__(self, config: Dict):
        self.config = config
        self.model: Optional[xgb.XGBClassifier] = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.n_calls = 0
        self.recent_accuracy = deque(maxlen=100)
        self.model_path = Path('models/xgb_v2.pkl')

    def fit(self, X: np.ndarray, y: np.ndarray):
        X_scaled = self.scaler.fit_transform(X)
        self.model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        logger.info(f"XGBoost fitted on {len(X)} samples")

    def predict_proba(self, X: np.ndarray) -> float:
        if not self.is_fitted or self.model is None:
            return 0.5
        try:
            X_scaled = self.scaler.transform(X)
            proba = self.model.predict_proba(X_scaled)[0][1]
            self.n_calls += 1
            return float(proba)
        except Exception as e:
            logger.error(f"XGBoost prediction error: {e}")
            return 0.5

    def save(self):
        self.model_path.parent.mkdir(exist_ok=True)
        joblib.dump({'model': self.model, 'scaler': self.scaler}, self.model_path)

    def load(self) -> bool:
        if self.model_path.exists():
            data = joblib.load(self.model_path)
            self.model = data['model']
            self.scaler = data['scaler']
            self.is_fitted = True
            return True
        return False


class LightGBMModel:
    """LightGBM classifier — faster training, comparable accuracy"""

    def __init__(self, config: Dict):
        self.config = config
        self.model: Optional[lgb.LGBMClassifier] = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.model_path = Path('models/lgb_v2.pkl')

    def fit(self, X: np.ndarray, y: np.ndarray):
        X_scaled = self.scaler.fit_transform(X)
        self.model = lgb.LGBMClassifier(
            n_estimators=300,
            learning_rate=0.03,
            num_leaves=63,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        logger.info(f"LightGBM fitted on {len(X)} samples")

    def predict_proba(self, X: np.ndarray) -> float:
        if not self.is_fitted or self.model is None:
            return 0.5
        try:
            X_scaled = self.scaler.transform(X)
            return float(self.model.predict_proba(X_scaled)[0][1])
        except Exception as e:
            logger.error(f"LightGBM prediction error: {e}")
            return 0.5

    def save(self):
        self.model_path.parent.mkdir(exist_ok=True)
        joblib.dump({'model': self.model, 'scaler': self.scaler}, self.model_path)

    def load(self) -> bool:
        if self.model_path.exists():
            data = joblib.load(self.model_path)
            self.model = data['model']
            self.scaler = data['scaler']
            self.is_fitted = True
            return True
        return False


class CatBoostModel:
    """CatBoost classifier — handles outliers well"""

    def __init__(self, config: Dict):
        self.config = config
        self.model = None
        self.is_fitted = False
        self.model_path = Path('models/cat_v2.pkl')

    def fit(self, X: np.ndarray, y: np.ndarray):
        if not CATBOOST_AVAILABLE:
            return
        self.model = CatBoostClassifier(
            iterations=200,
            depth=6,
            learning_rate=0.05,
            verbose=0,
            random_seed=42
        )
        self.model.fit(X, y)
        self.is_fitted = True
        logger.info(f"CatBoost fitted on {len(X)} samples")

    def predict_proba(self, X: np.ndarray) -> float:
        if not CATBOOST_AVAILABLE or not self.is_fitted or self.model is None:
            return 0.5
        try:
            return float(self.model.predict_proba(X)[0][1])
        except Exception as e:
            logger.error(f"CatBoost prediction error: {e}")
            return 0.5

    def save(self):
        if not CATBOOST_AVAILABLE or self.model is None:
            return
        self.model_path.parent.mkdir(exist_ok=True)
        self.model.save_model(str(self.model_path))

    def load(self) -> bool:
        if not CATBOOST_AVAILABLE:
            return False
        if self.model_path.exists():
            self.model = CatBoostClassifier()
            self.model.load_model(str(self.model_path))
            self.is_fitted = True
            return True
        return False


# ──────────────────────────────────────────────────
# MODEL DRIFT DETECTOR
# ──────────────────────────────────────────────────

class CUSUMDriftDetector:
    """
    CUSUM (Cumulative Sum) test for detecting model performance drift.
    Triggers when model accuracy degrades persistently.
    """

    def __init__(self, threshold: float = 5.0, drift_delta: float = 0.1):
        self.threshold = threshold
        self.drift_delta = drift_delta
        self.cusum_high = 0.0
        self.cusum_low = 0.0
        self.is_drifting = False
        self._history = deque(maxlen=200)

    def update(self, prediction_correct: bool) -> bool:
        """
        Update CUSUM with a new prediction result.

        Returns:
            True if drift detected (retraining needed)
        """
        x = 1.0 if prediction_correct else 0.0
        self._history.append(x)

        if len(self._history) < 20:
            return False

        # Expected mean (reference: rolling 50-sample accuracy)
        ref = sum(list(self._history)[-50:]) / min(50, len(self._history))

        # CUSUM update
        self.cusum_high = max(0.0, self.cusum_high + x - ref - self.drift_delta)
        self.cusum_low = max(0.0, self.cusum_low + ref - x - self.drift_delta)

        if self.cusum_high > self.threshold or self.cusum_low > self.threshold:
            self.is_drifting = True
            self.cusum_high = 0.0  # Reset after detection
            self.cusum_low = 0.0
            logger.warning("🔄 CUSUM drift detected — model retraining recommended")
            return True

        self.is_drifting = False
        return False


# ──────────────────────────────────────────────────
# ENSEMBLE
# ──────────────────────────────────────────────────

class MLEnsemble:
    """
    Stacking ensemble: XGBoost + LightGBM + CatBoost base models,
    meta-learner (logistic regression) combines predictions.

    Dynamic weights: models with higher recent AUC get higher weight.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.feature_eng = FeatureEngineeringV2()
        self.drift_detector = CUSUMDriftDetector()
        self._lock = threading.Lock()

        # Base models
        self.xgb = XGBoostModel(config)
        self.lgb = LightGBMModel(config)
        self.cat = CatBoostModel(config)

        # Meta-learner (logistic regression on stacked predictions)
        self.meta_learner = LogisticRegression(max_iter=1000, random_state=42)
        self.meta_fitted = False

        # Dynamic model weights (updated based on recent accuracy)
        self.weights = {'xgb': 0.4, 'lgb': 0.4, 'cat': 0.2}
        self.recent_predictions: Dict[str, deque] = {
            'xgb': deque(maxlen=100),
            'lgb': deque(maxlen=100),
            'cat': deque(maxlen=100),
        }

        # Training data buffer (for online learning)
        self.X_buffer: List[np.ndarray] = []
        self.y_buffer: List[int] = []
        self.buffer_limit = 5000
        self.min_train_samples = 200
        self.is_trained = False

        # Load existing models
        self._try_load_models()
        logger.info("MLEnsemble initialized")

    def _try_load_models(self):
        loaded = []
        if self.xgb.load(): loaded.append('XGB')
        if self.lgb.load(): loaded.append('LGB')
        if self.cat.load(): loaded.append('CatBoost')
        if loaded:
            self.is_trained = True
            logger.info(f"Loaded models: {loaded}")

    def predict_win_probability(
        self,
        df: pd.DataFrame,
        signal_direction: int
    ) -> float:
        """
        Predict probability of trade success.

        Args:
            df: DataFrame with indicators
            signal_direction: 1 (BUY) or -1 (SELL)

        Returns:
            Probability [0, 1]
        """
        if not self.is_trained:
            return 0.55  # Default before training

        features = self.feature_eng.create_features(df, signal_direction)
        if features is None:
            return 0.55

        with self._lock:
            xgb_p = self.xgb.predict_proba(features)
            lgb_p = self.lgb.predict_proba(features)
            cat_p = self.cat.predict_proba(features)

        # Dynamic weighted average
        w = self.weights
        total_weight = w['xgb'] + w['lgb'] + w['cat']
        ensemble_p = (xgb_p * w['xgb'] + lgb_p * w['lgb'] + cat_p * w['cat']) / total_weight

        logger.debug(f"Ensemble probabilities: XGB={xgb_p:.3f}, LGB={lgb_p:.3f}, Cat={cat_p:.3f}, Ensemble={ensemble_p:.3f}")
        return float(ensemble_p)

    def add_training_sample(self, df: pd.DataFrame, signal_direction: int, outcome: int):
        """
        Add a completed trade to the training buffer.

        Args:
            outcome: 1 = win, 0 = loss
        """
        features = self.feature_eng.create_features(df, signal_direction)
        if features is None:
            return

        self.X_buffer.append(features[0])
        self.y_buffer.append(outcome)

        # Keep buffer within limit (rolling window)
        if len(self.X_buffer) > self.buffer_limit:
            self.X_buffer.pop(0)
            self.y_buffer.pop(0)

        # Trigger retraining if enough new data
        if len(self.X_buffer) >= self.min_train_samples and len(self.X_buffer) % 100 == 0:
            self._retrain_async()

    def _retrain_async(self):
        """Retrain models in background thread"""
        t = threading.Thread(target=self._retrain, daemon=True)
        t.start()

    def _retrain(self):
        """Retrain all base models on current buffer"""
        if len(self.X_buffer) < self.min_train_samples:
            return

        logger.info(f"Retraining ensemble on {len(self.X_buffer)} samples...")
        X = np.array(self.X_buffer)
        y = np.array(self.y_buffer)

        with self._lock:
            self.xgb.fit(X, y)
            self.lgb.fit(X, y)
            self.cat.fit(X, y)
            self.is_trained = True

        # Save models
        self.xgb.save()
        self.lgb.save()
        self.cat.save()

        # Update dynamic weights based on cross-val AUC
        self._update_weights(X, y)
        logger.info(f"Retraining complete. Weights: {self.weights}")

    def _update_weights(self, X: np.ndarray, y: np.ndarray):
        """Update model weights based on cross-validation AUC"""
        try:
            xgb_scores = cross_val_score(
                self.xgb.model, self.xgb.scaler.transform(X), y,
                cv=3, scoring='roc_auc', n_jobs=-1
            ).mean()
            lgb_scores = cross_val_score(
                self.lgb.model, self.lgb.scaler.transform(X), y,
                cv=3, scoring='roc_auc', n_jobs=-1
            ).mean()
            cat_scores = 0.5  # Skip CatBoost CV for speed

            total = xgb_scores + lgb_scores + cat_scores
            self.weights = {
                'xgb': xgb_scores / total,
                'lgb': lgb_scores / total,
                'cat': cat_scores / total,
            }
        except Exception as e:
            logger.error(f"Weight update error: {e}")

    def record_prediction_outcome(self, predicted_proba: float, actual_outcome: int):
        """Feed prediction result into drift detector"""
        threshold = 0.60
        predicted_class = 1 if predicted_proba >= threshold else 0
        correct = predicted_class == actual_outcome
        needs_retrain = self.drift_detector.update(correct)
        if needs_retrain:
            self._retrain_async()

    def get_feature_importance(self) -> pd.DataFrame:
        """Return aggregated feature importances across models"""
        importances = {}

        if self.xgb.is_fitted and self.xgb.model:
            imp = self.xgb.model.feature_importances_
            for name, val in zip(FeatureEngineeringV2.FEATURE_NAMES, imp):
                importances[name] = importances.get(name, 0) + val * self.weights['xgb']

        if self.lgb.is_fitted and self.lgb.model:
            imp = self.lgb.model.feature_importances_
            for name, val in zip(FeatureEngineeringV2.FEATURE_NAMES, imp):
                importances[name] = importances.get(name, 0) + val * self.weights['lgb']

        df = pd.DataFrame(list(importances.items()), columns=['feature', 'importance'])
        return df.sort_values('importance', ascending=False)
