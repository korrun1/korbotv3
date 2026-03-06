# 🛡️ ANALYSIS_RISK_MANAGEMENT.md
## KorBot X Enhanced — Risk Management Analysis
**Version:** 2.0 | **Analysis Date:** March 2026

---

## Current Risk Architecture

```
RiskEngine
├── CircuitBreaker
│   ├── Trigger: consecutive_losses >= 3
│   ├── Cooldown: 60 minutes
│   └── Reset: automatic after cooldown
├── Position Sizing
│   └── (balance × risk%) / SL_distance_in_currency
├── Drawdown Control
│   ├── Max drawdown: 5% → STOP trading
│   └── Max daily loss: 3% → PAUSE trading
├── Exposure Control
│   ├── Max concurrent positions: 3
│   └── Max per-symbol exposure: 3%
└── Stop Loss / Take Profit
    ├── SL: ATR × 2.0 (or fixed pips)
    ├── TP: SL × RR ratio (2.5 default)
    └── Trailing: ATR × 1.5 step
```

---

## 1. Position Sizing Analysis

### Current Algorithm
```python
def calculate_position_size(signal, account_info, symbol_info):
    risk_amount = account_balance * (risk_percent / 100)
    sl_distance = abs(entry_price - stop_loss)
    sl_in_currency = sl_distance * symbol_info['contract_size'] * symbol_info['lot_size_min']
    lot_size = risk_amount / sl_in_currency
    # Clamp to min/max lot sizes
    return max(min_lot, min(lot_size, max_lot))
```

**Formula:** `lot = (balance × 0.8%) / SL_distance_in_account_currency`

### Assessment
- ✅ Risk-per-trade capped at 0.8% of balance — conservative
- ❌ Fixed 0.8% regardless of signal quality (high-confidence signals deserve more)
- ❌ Fixed 0.8% regardless of volatility regime (should reduce in high-vol)
- ❌ No Kelly Criterion integration
- ❌ No drawdown-based scaling (doesn't automatically reduce during losing streaks)

### Kelly Criterion Comparison
```
Current:  f = 0.8% (fixed)
Kelly:    f* = (p × b - q) / b
          where p = win prob, b = R:R ratio, q = 1 - p

Example:  p=0.60, b=2.5, q=0.40
          f* = (0.60×2.5 - 0.40) / 2.5 = (1.5 - 0.4) / 2.5 = 0.44 (44%)
          Fractional Kelly (0.25): 11% — too aggressive
          Fractional Kelly (0.05): 2.2% — reasonable upper bound

Recommended: Fractional Kelly (0.1×f*) capped at 2% per trade
```

---

## 2. Stop Loss Analysis

### Current Methods
| Method | Config | Notes |
|--------|--------|-------|
| ATR-based | ATR × 2.0 | ✅ Volatility-adaptive |
| Fixed pips | 10–50 pip range | ❌ Ignores volatility |

### ATR-Based SL (in use)
```python
if signal_type == BUY:
    stop_loss = entry_price - (ATR × 2.0)
```

**Strengths:**
- Adapts to market volatility automatically
- Prevents stops being placed in normal price noise

**Weaknesses:**
- Uniform ATR multiplier across all strategies (2.0 is too tight for swing trades)
- No structure-based SL (previous swing low/high)
- No gap risk handling (SL could be jumped on news)
- ATR period fixed at 14 (could be more adaptive)

### Recommended SL Enhancements
1. **Structure-based SL**: Place SL below/above nearest swing high/low
2. **Strategy-specific ATR multipliers**: Scalping 1.5×, Swing 3.0×
3. **Maximum % risk cap**: SL distance never exceeds 1.5% of price
4. **Gap protection**: Reduce lot size when economic news within 30 minutes

---

## 3. Take Profit Analysis

### Current Methods
```python
take_profit = entry + (abs(entry - stop_loss) × RR_ratio)
# Default RR = 2.5 for most strategies
```

**Assessment:**
- ✅ Fixed RR ensures consistent risk-reward discipline
- ❌ Single TP — no partial close at first target
- ❌ TP not adjusted for proximity to S/R levels
- ❌ No distinction between trending (trail) vs reverting (fixed) strategies

### Recommended TP Enhancement
```python
# Partial close system:
# At 1:1 RR → close 40% of position, move SL to breakeven
# At 2:1 RR → close additional 30%, trail remaining 30%
# Remaining → trail with ATR-based trailing stop
```

---

## 4. Circuit Breaker Analysis

### Current Triggers
| Trigger | Threshold | Response |
|---------|-----------|----------|
| Consecutive losses | ≥ 3 | 60-min pause |
| Max drawdown | ≥ 5% | Full stop |
| Daily loss | ≥ 3% | Pause until next day |

### Assessment
- ✅ Multi-tier response (pause vs stop)
- ✅ Automatic recovery after cooldown
- ❌ Only consecutive losses trigger CB, not rapid losses (3 fast losses vs 3 spread over a day are different)
- ❌ No gradual position size reduction before triggering CB
- ❌ No volatility spike detection (VIX equivalent for forex)
- ❌ No news event detection to preemptively pause

### Recommended Enhancements
```python
# Gradual reduction before hard stop:
if consecutive_losses >= 2:
    position_size_multiplier = 0.5   # Reduce to 50%
if consecutive_losses >= 3:
    position_size_multiplier = 0.25  # Reduce to 25%
if consecutive_losses >= 4:
    trading_paused = True             # Full pause

# Add loss rate trigger:
if losses_last_2_hours >= 2:
    position_size_multiplier = 0.5

# Add daily loss rate:
if daily_loss_rate > 1.5% and time < 12:00:
    extra_caution_mode = True  # Tighter thresholds
```

---

## 5. Correlation Management (Currently Missing)

### Problem
The bot can simultaneously hold EURUSD long and GBPUSD long, which are ~85% correlated. This effectively doubles the risk.

### Proposed Correlation Matrix
```python
# Correlation groups (approximate):
CORR_GROUPS = {
    "USD_base": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"],  # All negatively correlated with USD
    "USD_quote": ["USDCAD", "USDJPY", "USDCHF"],             # Positively correlated with USD
    "risk_on": ["AUDUSD", "NZDUSD", "AUDJPY"],               # Risk-on currencies
}

def check_correlation_exposure(symbol, open_positions):
    group = get_correlation_group(symbol)
    same_direction_exposure = sum(
        pos.lot_size for pos in open_positions
        if get_correlation_group(pos.symbol) == group
        and pos.direction == current_direction
    )
    MAX_CORRELATED_EXPOSURE = 2.0  # percent
    if same_direction_exposure > MAX_CORRELATED_EXPOSURE:
        return False, "Correlated exposure limit reached"
    return True, None
```

---

## 6. Portfolio-Level VaR (Currently Missing)

### Proposed Implementation
```python
def calculate_portfolio_var(open_positions, confidence=0.95):
    """
    Calculate 1-day 95% VaR for current portfolio.
    Uses historical simulation with correlation.
    """
    position_returns = []
    for pos in open_positions:
        hist_returns = get_historical_returns(pos.symbol, days=252)
        position_returns.append(hist_returns * pos.exposure_percent)
    
    # Aggregate with correlation
    portfolio_returns = np.sum(position_returns, axis=0)
    var_95 = np.percentile(portfolio_returns, 5)  # 5th percentile
    return var_95

MAX_PORTFOLIO_VAR = -2.0  # Max 2% daily VaR
```

---

## 7. Risk Metrics Gaps

### Currently Tracked
- `consecutive_losses`, `daily_pnl`, `total_pnl`, `max_drawdown`
- `current_drawdown`, `open_exposure`

### Missing Metrics
| Metric | Importance | Notes |
|--------|-----------|-------|
| Sharpe ratio (rolling) | High | Real-time performance quality |
| Profit factor (rolling) | High | Win/loss ratio momentum |
| Average trade duration | Medium | Identifies regime changes |
| MAE (Max Adverse Excursion) | High | Optimizes stop placement |
| MFE (Max Favorable Excursion) | High | Optimizes TP placement |
| Expectancy per strategy | High | Identify failing strategies |
| Win rate per market session | Medium | Session-specific optimization |

---

## Risk Management Score Card

| Category | Current Score | Target Score | Priority |
|----------|--------------|--------------|----------|
| Position Sizing | 6/10 | 9/10 | HIGH |
| Stop Loss Design | 6/10 | 9/10 | HIGH |
| Take Profit Design | 5/10 | 8/10 | HIGH |
| Circuit Breaker | 7/10 | 9/10 | MEDIUM |
| Correlation Management | 2/10 | 8/10 | HIGH |
| Portfolio VaR | 0/10 | 7/10 | MEDIUM |
| Drawdown Recovery | 6/10 | 9/10 | HIGH |
| **Overall** | **5/10** | **8.5/10** | — |

---

## Summary of Critical Risk Improvements

1. **ML-powered position sizing** using XGBoost-predicted win probability in Kelly formula
2. **Correlation-aware exposure limits** to prevent correlated pair overexposure
3. **Partial close at 1:1 RR** with trailing stop on remainder
4. **Gradual position reduction** before circuit breaker triggers
5. **Structure-based stop losses** using swing highs/lows
6. **Volatility-regime size scaling** (reduce 30–50% in high-vol periods)
7. **Strategy-level performance gates** (disable strategy if Sharpe < 0.5 over 30 days)
