"""
📊 regime_detector.py — Advanced Market Regime Detection
Version: 3.0
Date: 2026-03

Features:
- Hidden Markov Model (HMM) regime detection
- K-means clustering as fallback
- Volatility regime classification (5 states)
- Trend strength measurement
- Regime transition probability prediction
- Session-aware regime adjustment
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
from enum import Enum
import logging
from dataclasses import dataclass

try:
    from hmmlearn import hmm as hmmlearn_hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logging.getLogger(__name__).warning("hmmlearn not installed — using clustering-based regime detection")

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"


@dataclass
class RegimeState:
    """Full regime state with confidence and transition probabilities"""
    regime: MarketRegime
    confidence: float
    transition_prob_next: Dict[str, float]  # Probability of transitioning to each regime
    raw_state: int  # HMM hidden state index
    volatility_level: float
    trend_strength: float


class HMMRegimeDetector:
    """
    Hidden Markov Model-based regime detector.
    5 hidden states mapped to 5 market regimes.

    Features used:
    1. Returns (log return)
    2. Volatility (rolling std)
    3. Trend (EMA spread normalized)
    4. Volume ratio
    """

    N_STATES = 5
    REGIME_MAP = {
        0: MarketRegime.RANGING,
        1: MarketRegime.TRENDING_UP,
        2: MarketRegime.TRENDING_DOWN,
        3: MarketRegime.VOLATILE,
        4: MarketRegime.QUIET,
    }

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        self._state_regime_map: Dict[int, MarketRegime] = dict(self.REGIME_MAP)

    def _build_features(self, df: pd.DataFrame) -> np.ndarray:
        """Build 4D feature matrix from OHLCV data"""
        features = pd.DataFrame()

        # Log returns
        features['returns'] = np.log(df['Close'] / df['Close'].shift(1)).fillna(0)

        # Rolling volatility (10-bar)
        features['volatility'] = features['returns'].rolling(10).std().fillna(0)

        # Trend: EMA20 / EMA50 spread
        ema20 = df['Close'].ewm(span=20).mean()
        ema50 = df['Close'].ewm(span=50).mean()
        features['trend'] = ((ema20 - ema50) / df['Close']).fillna(0)

        # Volume ratio
        vol_ma = df['Volume'].rolling(20).mean()
        features['vol_ratio'] = (df['Volume'] / vol_ma).fillna(1.0)

        return features.values

    def fit(self, df: pd.DataFrame) -> bool:
        """Fit HMM on historical data (minimum 200 bars)"""
        if not HMM_AVAILABLE:
            logger.warning("hmmlearn not available — HMM not fitted")
            return False

        if df is None or len(df) < 200:
            logger.warning("Not enough data for HMM fitting (need 200+ bars)")
            return False

        X = self._build_features(df)
        X_scaled = self.scaler.fit_transform(X)

        self.model = hmmlearn_hmm.GaussianHMM(
            n_components=self.N_STATES,
            covariance_type="full",
            n_iter=100,
            random_state=42
        )

        try:
            self.model.fit(X_scaled)
            self.is_fitted = True

            # Map states to regimes by analyzing state means
            self._assign_state_regimes(X_scaled)
            logger.info(f"HMM fitted. State→Regime map: {self._state_regime_map}")
            return True
        except Exception as e:
            logger.error(f"HMM fitting failed: {e}")
            return False

    def _assign_state_regimes(self, X_scaled: np.ndarray):
        """
        Automatically assign regime labels to HMM states
        based on the statistical properties of each state.
        """
        if self.model is None:
            return

        means = self.model.means_  # Shape: (n_states, n_features)
        # Feature indices: [0]=returns, [1]=volatility, [2]=trend, [3]=vol_ratio

        for state in range(self.N_STATES):
            ret = means[state, 0]     # Mean return
            vol = means[state, 1]     # Mean volatility
            trend = means[state, 2]   # Mean trend

            # Classify state
            if vol > 1.5:  # High volatility
                self._state_regime_map[state] = MarketRegime.VOLATILE
            elif vol < -1.0:  # Very low volatility
                self._state_regime_map[state] = MarketRegime.QUIET
            elif trend > 0.5 and ret > 0:  # Strong positive trend
                self._state_regime_map[state] = MarketRegime.TRENDING_UP
            elif trend < -0.5 and ret < 0:  # Strong negative trend
                self._state_regime_map[state] = MarketRegime.TRENDING_DOWN
            else:  # Ranging
                self._state_regime_map[state] = MarketRegime.RANGING

    def predict(self, df: pd.DataFrame) -> Optional[RegimeState]:
        """
        Predict current market regime.

        Returns:
            RegimeState with confidence and transition probabilities
        """
        if not self.is_fitted or self.model is None or not HMM_AVAILABLE:
            return self._fallback_predict(df)

        X = self._build_features(df)
        if len(X) < 10:
            return None

        X_scaled = self.scaler.transform(X)

        try:
            # Get log-likelihood for each state at last step
            _, posterior = self.model.decode(X_scaled, algorithm='viterbi')
            current_state = int(posterior[-1])

            # Posterior probabilities for the last observation
            # Use forward-backward for state probabilities
            log_prob, posterior_probs = self.model.score_samples(X_scaled)
            state_probs = np.exp(posterior_probs[-1])  # Probability of each state at last step

            regime = self._state_regime_map.get(current_state, MarketRegime.RANGING)
            confidence = float(state_probs[current_state])

            # Transition probabilities
            trans_matrix = self.model.transmat_
            next_state_probs = trans_matrix[current_state]
            transition_prob = {
                self._state_regime_map.get(s, MarketRegime.RANGING).value: float(next_state_probs[s])
                for s in range(self.N_STATES)
            }

            # Volatility and trend from features
            latest_features = X_scaled[-1]
            vol_level = float(latest_features[1])
            trend_strength = float(abs(latest_features[2]))

            return RegimeState(
                regime=regime,
                confidence=confidence,
                transition_prob_next=transition_prob,
                raw_state=current_state,
                volatility_level=vol_level,
                trend_strength=trend_strength
            )
        except Exception as e:
            logger.error(f"HMM prediction error: {e}")
            return self._fallback_predict(df)

    def _fallback_predict(self, df: pd.DataFrame) -> Optional[RegimeState]:
        """Threshold-based fallback when HMM is not available"""
        if df is None or len(df) < 20:
            return None

        latest = df.iloc[-1]
        adx = float(latest.get('ADX', 20))
        bb_width = float(latest.get('BB_width', 0))
        atr = float(latest.get('ATR', 0))
        close = float(latest.get('Close', 0))

        # Normalized ATR
        norm_atr = atr / close if close > 0 else 0

        # Regime classification
        ema20 = float(latest.get('EMA_20', close))
        ema50 = float(latest.get('EMA_50', close))

        if norm_atr > 0.008:
            regime = MarketRegime.VOLATILE
        elif adx > 30:
            regime = MarketRegime.TRENDING_UP if ema20 > ema50 else MarketRegime.TRENDING_DOWN
        elif adx < 15 and norm_atr < 0.002:
            regime = MarketRegime.QUIET
        else:
            regime = MarketRegime.RANGING

        trend_strength = min(adx / 50.0, 1.0)

        return RegimeState(
            regime=regime,
            confidence=0.65,
            transition_prob_next={},
            raw_state=-1,
            volatility_level=norm_atr * 100,
            trend_strength=trend_strength
        )


class ClusteringRegimeDetector:
    """
    K-Means clustering backup regime detector.
    Useful when HMM is not available or data is insufficient.
    """

    N_CLUSTERS = 5
    CLUSTER_REGIME_MAP: Dict[int, MarketRegime] = {}

    def __init__(self):
        self.kmeans: Optional[KMeans] = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.cluster_regime_map: Dict[int, MarketRegime] = {}

    def _build_features(self, df: pd.DataFrame) -> np.ndarray:
        """3D feature: returns, volatility, trend"""
        returns = np.log(df['Close'] / df['Close'].shift(1)).fillna(0)
        volatility = returns.rolling(10).std().fillna(0)
        ema20 = df['Close'].ewm(span=20).mean()
        ema50 = df['Close'].ewm(span=50).mean()
        trend = ((ema20 - ema50) / df['Close']).fillna(0)
        return np.column_stack([returns, volatility, trend])

    def fit(self, df: pd.DataFrame) -> bool:
        if df is None or len(df) < 100:
            return False

        X = self._build_features(df)
        X_scaled = self.scaler.fit_transform(X)

        self.kmeans = KMeans(n_clusters=self.N_CLUSTERS, random_state=42, n_init=10)
        labels = self.kmeans.fit_predict(X_scaled)

        # Assign regimes to clusters
        centers = self.kmeans.cluster_centers_  # Shape: (5, 3)
        for cluster_id in range(self.N_CLUSTERS):
            ret, vol, trend = centers[cluster_id]
            if vol > 1.5:
                self.cluster_regime_map[cluster_id] = MarketRegime.VOLATILE
            elif vol < -1.0:
                self.cluster_regime_map[cluster_id] = MarketRegime.QUIET
            elif trend > 0.5:
                self.cluster_regime_map[cluster_id] = MarketRegime.TRENDING_UP
            elif trend < -0.5:
                self.cluster_regime_map[cluster_id] = MarketRegime.TRENDING_DOWN
            else:
                self.cluster_regime_map[cluster_id] = MarketRegime.RANGING

        self.is_fitted = True
        return True

    def predict(self, df: pd.DataFrame) -> Optional[MarketRegime]:
        if not self.is_fitted or self.kmeans is None:
            return None

        X = self._build_features(df)
        X_scaled = self.scaler.transform(X[-5:])  # Use last 5 bars
        cluster = int(self.kmeans.predict(X_scaled[-1:])[0])
        return self.cluster_regime_map.get(cluster, MarketRegime.RANGING)


class RegimeDetector:
    """
    Main regime detector combining HMM + Clustering + threshold fallback.
    Also tracks regime history for transition analysis.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.hmm = HMMRegimeDetector()
        self.clustering = ClusteringRegimeDetector()
        self.regime_history: List[MarketRegime] = []
        self.max_history = 100
        logger.info("RegimeDetector v2 initialized")

    def fit(self, df: pd.DataFrame):
        """Fit all detectors on historical data"""
        logger.info("Fitting regime detectors...")
        hmm_ok = self.hmm.fit(df)
        cluster_ok = self.clustering.fit(df)
        if hmm_ok:
            logger.info("HMM detector fitted")
        if cluster_ok:
            logger.info("Clustering detector fitted")

    def detect(self, df: pd.DataFrame) -> RegimeState:
        """
        Detect current market regime using best available method.

        Returns:
            RegimeState with full information
        """
        # Try HMM first
        state = self.hmm.predict(df)

        # Fallback to clustering
        if state is None and self.clustering.is_fitted:
            regime = self.clustering.predict(df)
            state = RegimeState(
                regime=regime or MarketRegime.RANGING,
                confidence=0.60,
                transition_prob_next={},
                raw_state=-1,
                volatility_level=0.0,
                trend_strength=0.0
            )

        # Final fallback: threshold-based
        if state is None:
            state = self.hmm._fallback_predict(df)

        if state is None:
            state = RegimeState(
                regime=MarketRegime.RANGING,
                confidence=0.5,
                transition_prob_next={},
                raw_state=-1,
                volatility_level=0.0,
                trend_strength=0.0
            )

        # Update history
        self.regime_history.append(state.regime)
        if len(self.regime_history) > self.max_history:
            self.regime_history.pop(0)

        return state

    def get_regime_stability(self) -> float:
        """
        Calculate how stable the regime has been recently.
        Returns 0 (unstable) to 1 (very stable).
        """
        if len(self.regime_history) < 5:
            return 0.5

        recent = self.regime_history[-10:]
        most_common = max(set(recent), key=recent.count)
        stability = recent.count(most_common) / len(recent)
        return stability

    def get_session_adjusted_regime(
        self,
        base_regime: MarketRegime,
        hour_utc: int
    ) -> MarketRegime:
        """
        Adjust regime based on trading session.
        Asian session tends to be quieter; London/NY are more volatile.
        """
        # Asian session: 0–8 UTC
        if 0 <= hour_utc < 8:
            if base_regime == MarketRegime.VOLATILE:
                return MarketRegime.RANGING  # Downgrade volatile in Asian
        # London open: 8–12 UTC
        elif 8 <= hour_utc < 12:
            if base_regime == MarketRegime.QUIET:
                return MarketRegime.RANGING  # Upgrade quiet at London open
        # NY + London overlap: 13–17 UTC
        elif 13 <= hour_utc < 17:
            pass  # No adjustment; use as-is

        return base_regime
