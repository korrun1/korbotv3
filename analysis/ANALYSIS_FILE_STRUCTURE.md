# 📁 ANALYSIS_FILE_STRUCTURE.md
## KorBot X Enhanced — Complete File Structure Analysis
**Analyzed:** March 2026 | **Bot Version:** 2.0

---

## Overview

| File | Lines | Role | Complexity |
|------|-------|------|------------|
| `main.py` | 372 | Orchestrator / Entry Point | Medium |
| `strategy_engine.py` | 648 | Signal Generation (4 strategies) | High |
| `risk_engine.py` | 529 | Risk & Position Management | High |
| `ai_optimization.py` | 615 | ML: XGBoost + PPO + Bayesian | High |
| `execution_engine.py` | 615 | MT5 Order Routing | High |
| `data_layer.py` | 496 | MT5 Data Fetching + Cache | Medium |
| `market_intel.py` | 467 | Technical Indicators + Regime | Medium |
| `databases.py` | 499 | SQLite + Redis Management | Medium |
| `backtester.py` | 675 | Walk-Forward + Monte Carlo | High |
| `dashboard.py` | 964 | PyQt6 GUI | Medium |
| `config_loader.py` | 245 | YAML Config + Env Vars | Low |
| `utils.py` | 452 | Decorators + Helpers | Low |
| `telegram_notify.py` | 356 | Async Telegram Alerts | Low |
| `test_core.py` | 455 | Pytest Unit Tests | Medium |
| `config.yaml` | ~180 | Full Configuration | — |
| `requirements.txt` | ~80 | Dependencies | — |

**Total Python:** ~7,400 lines across 14 files

---

## File-by-File Deep Analysis

---

### 1. `main.py` — Orchestrator
**Purpose:** Top-level bot controller. Creates `KorBotX` class, wires all components, runs the main loop.

**Key Classes/Functions:**
- `KorBotX.__init__()` — initializes all 8 sub-components
- `KorBotX.start()` — main loop with 1-second tick via `schedule`
- `KorBotX._trading_loop()` — per-tick logic: check positions, generate signals
- `KorBotX._generate_and_execute_signals()` — multi-timeframe data → indicators → regime → signals → AI enhance → execute
- `KorBotX._daily_tasks()` — midnight reset + daily summary

**Dependencies:** All other modules

**Strengths:**
- Clean orchestration pattern
- Graceful shutdown via signal handlers
- Daily task scheduling

**Weaknesses:**
- Single-symbol only (`self.symbol` is one string)
- Signal generation throttled to 60-second intervals (hardcoded)
- No watchdog/auto-restart logic beyond `schedule`
- Session state not persisted across restarts

**Optimization Opportunities:**
- Multi-symbol parallelism via `asyncio` or `ProcessPoolExecutor`
- Configurable signal throttle per strategy
- Persistent state in Redis to survive restarts

---

### 2. `strategy_engine.py` — Signal Generation
**Purpose:** Defines 4 trading strategies + `StrategyEngine` coordinator.

**Key Classes:**
- `Signal` (dataclass) — entry, SL, TP, confidence, reasons
- `BaseStrategy` — abstract base with time-filter helpers
- `ScalpingStrategy` — EMA 5/13 crossover + ADX + volume (M1)
- `MeanReversionStrategy` — BB + RSI + Stochastic (M5)
- `BreakoutStrategy` — S/R breakout + ATR expansion + volume surge (H1)
- `AdaptiveSwingStrategy` — EMA 20/50 + MACD + ADX (H4)
- `StrategyEngine` — instantiates enabled strategies, routes data

**Dependencies:** `market_intel`, `utils`

**Strengths:**
- Regime-aware (each strategy has target regimes)
- Multi-layered confirmation (3+ conditions per signal)
- `@safe_execution` decorator prevents crashes

**Weaknesses:**
- Static initial confidence (0.70–0.75) before AI enhancement
- No multi-timeframe confirmation (each strategy uses only ONE timeframe)
- No signal deduplication (could fire the same direction twice)
- Strategy timeframe is hardcoded in `generate_signals()` logic, not configurable
- No volume profile or order flow analysis
- No divergence detection

**Optimization Opportunities:**
- Add higher-timeframe trend filter to each strategy
- Add divergence (RSI/MACD vs price) detection
- Dynamic confidence based on signal quality count
- Signal deduplication/aggregation layer

---

### 3. `risk_engine.py` — Risk Management
**Purpose:** Position sizing, circuit breaker, drawdown monitoring, trade permission.

**Key Classes:**
- `RiskMetrics` (dataclass) — real-time P&L, drawdown, consecutive losses
- `CircuitBreaker` — triggers on 3 consecutive losses; 60-min cooldown
- `RiskEngine` — Kelly-ish sizing, max exposure checks, SL/TP calculation

**Key Methods:**
- `can_trade()` — checks circuit breaker + drawdown + daily loss
- `can_open_position()` — checks max positions + symbol exposure
- `calculate_position_size()` — risk-percent based, ATR-adjusted stop
- `calculate_stop_loss()` — ATR × multiplier or fixed pips
- `calculate_take_profit()` — risk-reward ratio × SL distance
- `update_trailing_stop()` — ATR-based trailing

**Dependencies:** None (standalone)

**Strengths:**
- Multi-layer circuit breaker (consecutive losses + drawdown + daily loss)
- ATR-based SL avoids arbitrary pip counts
- Clean `RiskMetrics` dataclass for real-time tracking

**Weaknesses:**
- Position sizing is fixed-percentage, NOT Kelly Criterion
- No correlation awareness (can open correlated positions simultaneously)
- Circuit breaker only checks consecutive losses (not % drawdown trigger)
- No volatility-regime adjustment to position size
- `max_symbol_exposure_percent` not checked against portfolio-level VaR
- Trailing stop logic is simple ATR — no chandelier or parabolic SAR

**Optimization Opportunities:**
- Fractional Kelly with ML-predicted win probability
- Correlation matrix to reduce correlated exposure
- Volatility-scaled position sizing (reduce size in high-vol regimes)
- VaR-based portfolio-level constraint

---

### 4. `ai_optimization.py` — Machine Learning
**Purpose:** XGBoost confidence scoring, PPO exit timing, Bayesian hyperparameter optimization.

**Key Classes:**
- `FeatureEngineering` — 40+ features from indicators (momentum, volume, volatility, trend, time)
- `XGBoostConfidence` — binary classifier predicting signal success
- `TradingEnvironment` — OpenAI Gym env for PPO training
- `PPOExitOptimizer` — `stable_baselines3` PPO for exit timing
- `BayesianOptimizer` — `scikit-optimize` for parameter search
- `AIOptimizationEngine` — combines all three

**Dependencies:** `xgboost`, `stable_baselines3`, `gymnasium`, `skopt`, `sklearn`

**Strengths:**
- Rich 40+ feature set for XGBoost
- PPO integrated for exit optimization (novel approach)
- Bayesian replaces genetic algorithm (more efficient)
- Model persistence with `joblib`

**Weaknesses:**
- XGBoost trained offline; no online learning
- PPO `TradingEnvironment` observation is fixed at 10 features (underpowered)
- No model drift detection or retraining trigger
- Feature set doesn't include inter-symbol correlation
- No model ensemble (single XGBoost only for confidence)
- Bayesian optimization runs in full, not warm-started
- No LightGBM or CatBoost alternative models

**Optimization Opportunities:**
- Multi-model ensemble (XGBoost + LightGBM + CatBoost + LSTM)
- Online learning via incremental XGBoost
- Richer PPO observation space (20+ features)
- Model drift detection with CUSUM statistic
- Feature importance monitoring + auto-reselection

---

### 5. `execution_engine.py` — Order Execution
**Purpose:** MT5 order placement, position tracking, SL/TP management, trailing stops.

**Key Classes:**
- `Trade` (dataclass) — full trade record with entry/exit/PnL
- `ExecutionEngine` — market orders, close positions, SL/TP check, trailing

**Key Methods:**
- `execute_signal()` — validates signal → calculates lot → places market order
- `close_position()` — market close with slippage handling
- `check_stop_loss_take_profit()` — manual SL/TP if MT5 doesn't handle it
- `update_trailing_stop()` — ATR-based trailing stop updates

**Dependencies:** `MetaTrader5`, `risk_engine`, `utils`

**Strengths:**
- Retry logic on failed orders (`@retry_on_failure`)
- Trade object fully serializable via `to_dict()`
- Distinguishes bid/ask for proper entry pricing

**Weaknesses:**
- Market orders only — no limit/stop-limit entry for better fills
- Slippage not modeled or tracked
- No partial close capability
- Position sizing recalculated on execution (could drift from signal's calc)
- `check_stop_loss_take_profit()` is a polling loop (MT5 should handle SL/TP natively)
- No order book awareness or VWAP execution
- `open_trades` dict is in-memory only (lost on restart)

**Optimization Opportunities:**
- Limit order entry at key price levels
- Partial close at 50% RR target
- Persistent `open_trades` backed by Redis
- Execution quality tracking (fill price vs. signal price)

---

### 6. `data_layer.py` — Data Management
**Purpose:** MT5 connection management, historical data fetching, real-time price, symbol info.

**Key Classes:**
- `MT5Connection` — connection manager with auto-reconnect
- `DataLayer` — `LRUCache`-backed data fetcher

**Key Methods:**
- `get_historical_data()` — fetches OHLCV from MT5, caches 60s
- `get_current_price()` — ask/bid/spread/time
- `get_symbol_info()` — contract specs, pip size, etc.
- `cleanup()` — disconnect MT5

**Dependencies:** `MetaTrader5`, `utils`

**Strengths:**
- `LRUCache` prevents redundant MT5 calls
- `@retry_on_failure` on data fetches
- Auto-reconnection on disconnect

**Weaknesses:**
- No multi-symbol batch fetching (one call per symbol)
- Cache TTL is hardcoded 60s (no dynamic adaptation)
- No data quality validation (gaps, outliers, duplicates)
- Historical data fetched fresh every 60s even if no new bars
- No tick data support
- No alternative data source fallback

**Optimization Opportunities:**
- Batch symbol data requests
- Event-driven updates (subscribe to MT5 tick stream)
- Data quality validation layer
- Redis as L2 cache beyond LRU

---

### 7. `market_intel.py` — Technical Analysis
**Purpose:** Calculates 30+ technical indicators, detects market regime.

**Key Classes:**
- `MarketRegime` (Enum) — TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE, QUIET
- `MarketIntelligence` — full indicator suite + regime detector

**Indicator Categories:**
- Trend: EMA 5/8/13/20/50/200, MACD, ADX, Ichimoku
- Momentum: RSI, Stochastic, Williams %R, MFI, CCI
- Volatility: ATR, Bollinger Bands, Keltner, historical vol
- Volume: OBV, VWAP, CMF, Volume Ratio
- Custom: Price Momentum, Trend Strength, Volatility Regime

**Strengths:**
- Comprehensive indicator library using `ta` package
- `@memoize` decorator for expensive computations
- 5 regime types covers most market conditions

**Weaknesses:**
- No multi-timeframe indicator aggregation
- Regime detection uses simple thresholds (ADX + BB width)
- No Hidden Markov Model or ML-based regime detection
- Ichimoku calculation done but not used in strategies
- Support/Resistance levels computed only in BreakoutStrategy, not globally
- No divergence detection (RSI/MACD vs price)
- Volume profile (POC/VAH/VAL) not implemented

**Optimization Opportunities:**
- HMM-based regime detection
- Global S/R level repository fed by all strategies
- Volume profile (VPVR) implementation
- Multi-timeframe indicator consensus scoring

---

### 8. `databases.py` — Persistence
**Purpose:** SQLite for trade history, Redis for real-time caching.

**Key Classes:**
- `DatabaseManager` — saves trades, stats, performance metrics

**Strengths:**
- WAL mode SQLite for concurrent writes
- Async Telegram notification queue
- Batch write support

**Weaknesses:**
- No data migration/versioning strategy
- Statistics queries are full table scans (no indexes)
- Redis used only for Telegram queue, not for trade state persistence

---

### 9. `backtester.py` — Backtesting
**Purpose:** Walk-forward optimization, Monte Carlo simulation, strategy evaluation.

**Strengths:**
- Walk-forward prevents overfitting
- Monte Carlo provides confidence intervals
- Sharpe, Sortino, Calmar, Max DD metrics

**Weaknesses:**
- No realistic spread modeling per hour-of-day
- No tick-level backtesting (bar-based only)
- Slippage is fixed, not adaptive
- No correlation between simultaneous positions

---

### 10. `utils.py` — Utilities
**Key Features:**
- `@retry_on_failure` — exponential backoff
- `@safe_execution` — exception swallowing with default
- `@memoize` — TTL-based memoization
- `LRUCache` — thread-safe LRU cache
- `PerformanceTimer` — context manager for timing
- `is_trading_time()`, `is_news_time()` — time filters

**Weaknesses:**
- `is_news_time()` is a placeholder (no actual news feed)
- No distributed locking for multi-process scenarios

---

## Dependency Graph

```
main.py
├── config_loader.py
├── utils.py
├── data_layer.py ──────────── utils.py, config_loader.py
├── market_intel.py ─────────── utils.py
├── strategy_engine.py ─────── market_intel.py, utils.py
├── risk_engine.py
├── ai_optimization.py ─────── utils.py, strategy_engine.py
├── execution_engine.py ────── strategy_engine.py, risk_engine.py, utils.py
├── databases.py
└── telegram_notify.py
```

---

## Summary: Top Weaknesses Across All Files

| Rank | Issue | Files Affected | Impact |
|------|-------|----------------|--------|
| 1 | Single-symbol operation | `main.py`, `execution_engine.py` | High |
| 2 | No multi-timeframe confirmation within strategies | `strategy_engine.py` | High |
| 3 | Fixed-percentage sizing (no Kelly/ML sizing) | `risk_engine.py` | High |
| 4 | Single XGBoost model (no ensemble) | `ai_optimization.py` | High |
| 5 | In-memory `open_trades` (lost on restart) | `execution_engine.py` | High |
| 6 | No correlation awareness | `risk_engine.py`, `main.py` | Medium |
| 7 | Regime detection too simplistic | `market_intel.py` | Medium |
| 8 | No real-time news filter | `utils.py`, `strategy_engine.py` | Medium |
| 9 | Market orders only | `execution_engine.py` | Medium |
| 10 | No tick/volume profile analysis | `market_intel.py` | Medium |
