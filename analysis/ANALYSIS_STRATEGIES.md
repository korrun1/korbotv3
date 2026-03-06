# 🎯 ANALYSIS_STRATEGIES.md
## KorBot X Enhanced — Strategy Deep Analysis
**Version:** 2.0 | **Analysis Date:** March 2026

---

## Strategy Overview

| Strategy | Timeframe | Market Regime | Expected Win Rate | R:R | Notes |
|----------|-----------|--------------|-------------------|-----|-------|
| Scalping | M1 | Trending Only | 55–60% | 2.5:1 | Noise-prone on M1 |
| Mean Reversion | M5 | Ranging/Quiet | 60–65% | ~1.5:1 | Good in tight ranges |
| Breakout | H1 | Any | 45–55% | 3.0:1 | Lower win rate, higher R:R |
| Adaptive Swing | H4 | Trending Only | 55–60% | 2.0:1 | Best risk-adjusted |

---

## Strategy 1: Scalping (M1)

### Core Logic
```
Entry (BUY):
  1. EMA_5 crosses above EMA_13 (current bar)
  2. Bullish candle (Close > Open)
  3. ADX > 20 (trend exists)
  4. RSI < 70 (not overbought)
  5. Volume_Ratio > 1.5 (volume confirmation)
  6. ATR > 0.0005 (minimum volatility)

Entry (SELL): Mirror conditions with bearish crossover

SL: entry - (ATR × 2.0)
TP: entry + (ATR × 5.0)  → R:R = 2.5:1
```

### Market Conditions Performance
| Condition | Expected Performance |
|-----------|---------------------|
| Strong trending (ADX > 30) | ✅ Excellent |
| Weak trending (ADX 20–30) | ⚠️ Moderate |
| Ranging | ❌ Poor (filtered by regime check) |
| High volatility (news) | ⚠️ Risky (time filter partially helps) |
| Asian session (low vol) | ❌ Poor (ATR filter should catch this) |

### Weaknesses
1. **M1 noise**: EMA crossovers on M1 are prone to whipsaws in all but the strongest trends
2. **No higher-timeframe filter**: A scalp signal could fire against an H4 downtrend
3. **Volume unreliable for forex**: MT5 volume is tick count, not real volume
4. **No entry optimization**: Pure market order, no limit entry at EMA level

### Enhancement Recommendations
1. Add H1 trend filter: only scalp in direction of H1 EMA alignment
2. Add 15-min consolidation check: avoid scalping during sideways M15 consolidation
3. Implement micro-structure filter: check bid-ask spread < threshold before entry
4. Consider limit orders at EMA level for better entry prices

---

## Strategy 2: Mean Reversion (M5)

### Core Logic
```
Entry (BUY — Oversold):
  1. RSI < 30
  2. BB_pct < 0.1 (price in lower 10% of BB)
  3. Stochastic_K < 20
  4. Stochastic bullish crossover (K crosses above D)
  5. Volume_Ratio > 1.0

Entry (SELL — Overbought): Mirror conditions

SL: BB lower band (BUY) / BB upper band (SELL)
TP: BB middle band (mean reversion target)
```

### Market Conditions Performance
| Condition | Expected Performance |
|-----------|---------------------|
| Tight range (BB width low) | ✅ Excellent |
| Wide range | ⚠️ Moderate (wider SL) |
| Trending market | ❌ Poor (filtered by regime check) |
| High volatility | ❌ Very poor (oversold stays oversold) |

### Weaknesses
1. **TP = BB midline only**: Leaves money on the table in strong mean reversions
2. **Triple condition AND gate**: RSI < 30 AND BB < 0.1 AND Stoch < 20 is very restrictive — few signals
3. **No momentum confirmation**: Price could be in slow bleed, not a snap reversal
4. **Stochastic crossover sensitive**: On M5 this fires frequently; needs confirmation candle

### Enhancement Recommendations
1. Add candlestick reversal pattern filter (hammer, engulfing)
2. Allow TP beyond BB midline with trailing stop
3. Add CCI divergence as additional confirmation
4. Widen signal conditions slightly to increase signal frequency

---

## Strategy 3: Breakout (H1)

### Core Logic
```
Entry (BUY — Bullish Breakout):
  1. Current price breaks above 50-bar high
  2. ATR expansion ratio > 1.5x ATR-20 MA
  3. Volume_Ratio > 2.0
  4. ADX > 20
  5. Bullish candle

Entry (SELL): Mirror conditions with 50-bar low break

SL: recent_high - (ATR × 1.5)   [tight, below breakout level]
TP: entry + (ATR × 3.0)          → R:R ~3:1
```

### Market Conditions Performance
| Condition | Expected Performance |
|-----------|---------------------|
| True breakout with volume | ✅ Excellent |
| False breakout | ❌ Poor (main risk) |
| Range expansion | ✅ Good |
| Low volatility drift | ❌ Poor (ATR filter helps) |

### Weaknesses
1. **False breakouts**: Major weakness of breakout strategies; no retest confirmation
2. **SL below breakout is tight**: If price retests breakout level, SL may be hit
3. **Volume proxy issue**: MT5 tick volume ≠ true volume; surge may be spurious
4. **50-bar lookback fixed**: Could miss short-term consolidation breakouts

### Enhancement Recommendations
1. Add "retest" filter: wait for pullback to breakout level, then re-breakout
2. Use time-based exit if momentum doesn't continue within N bars
3. Adaptive lookback based on volatility regime
4. Add Level 2 order flow check (if available)

---

## Strategy 4: Adaptive Swing (H4)

### Core Logic
```
Entry (BUY):
  1. EMA_20 > EMA_50 (uptrend)
  2. Regime = TRENDING_UP
  3. ADX > 25 (strong trend)
  4. MACD bullish crossover (MACD crosses above signal)
  5. RSI in range 40–70 (not extreme)

Entry (SELL): Mirror conditions

SL: entry - (ATR × 2.5)
TP: entry + (ATR × 5.0)  → R:R = 2:1 on paper, varies
```

### Market Conditions Performance
| Condition | Expected Performance |
|-----------|---------------------|
| Strong sustained trend | ✅ Excellent |
| Trend with pullbacks | ⚠️ Moderate (MACD may whipsaw) |
| Weak trend | ❌ Poor (ADX filter should catch) |
| Range-bound | ❌ Poor (regime filter) |

### Weaknesses
1. **MACD on H4 is slow**: Signals often appear after 30–40% of the move is done
2. **No entry timing refinement**: Better to enter on H1 pullback within H4 trend
3. **R:R 2:1 for 4-hour trade**: Many pairs would offer better than 5×ATR target
4. **RSI filter 40–70 excludes strong trend continuations** (RSI often > 70 in strong trends)

### Enhancement Recommendations
1. Multi-timeframe entry: H4 trend + H1 entry timing (MACD cross on H1)
2. Wider TP for swing trades (7×ATR or trail to EMA_50)
3. Relax RSI upper bound to 80 for trend following
4. Add Parabolic SAR trailing for extended trend captures

---

## Strategy Interaction & Signal Conflicts

### Current Behavior
```
Signals are generated independently per strategy.
If both Scalping and Breakout fire BUY simultaneously → TWO trades opened.
If Scalping fires SELL while Swing fires BUY → TWO opposing trades opened.
```

### Risks
- Opposing signals waste capital and net to zero
- Correlated signals double risk unnecessarily
- No signal priority or hierarchical weighting

### Recommended Resolution
```python
# Signal aggregation logic (v2)
def resolve_signals(signals: List[Signal]) -> List[Signal]:
    # Group by direction
    buys = [s for s in signals if s.type == SignalType.BUY]
    sells = [s for s in signals if s.type == SignalType.SELL]
    
    # Conflict detection: both directions present
    if buys and sells:
        # Take highest confidence direction
        buy_conf = max(s.confidence for s in buys)
        sell_conf = max(s.confidence for s in sells)
        if buy_conf > sell_conf:
            return [max(buys, key=lambda s: s.confidence)]
        else:
            return [max(sells, key=lambda s: s.confidence)]
    
    # Same direction: combine/take best
    all_same = buys or sells
    return [max(all_same, key=lambda s: s.confidence)]
```

---

## Multi-Timeframe Confirmation (Missing Feature)

### Current State
Each strategy uses only its designated timeframe. No cross-timeframe validation.

### Proposed MTF Scoring System (v2)
```
For each signal:
  1. Check H4 trend direction → +3 if aligned, -3 if against
  2. Check H1 momentum → +2 if aligned
  3. Check M15 entry timing → +1 if aligned
  
  Total MTF Score → Adjusts confidence:
  Score +5 to +6: confidence × 1.3
  Score +3 to +4: confidence × 1.1
  Score 0 to +2:  confidence × 1.0 (no change)
  Score < 0:      confidence × 0.5 (strongly discourage)
```

---

## Performance Metrics Estimation (Current vs Target)

| Metric | Scalping | Mean Rev | Breakout | Swing | Target v2 |
|--------|----------|----------|----------|-------|-----------|
| Win Rate | ~55% | ~62% | ~48% | ~58% | 70–75% |
| R:R | 2.5:1 | 1.5:1 | 3.0:1 | 2.0:1 | 2.5:1+ avg |
| Profit Factor | ~1.4 | ~1.5 | ~1.7 | ~1.6 | 2.0+ |
| Sharpe (est.) | ~1.2 | ~1.4 | ~1.6 | ~1.5 | 2.5+ |
| Max DD (est.) | 8% | 6% | 9% | 7% | <5% |

---

## Proposed New Strategies for v2

### Strategy 5: Volume Profile Reversal
```
Uses VPVR (Volume-at-Price) to identify Point of Control (POC) and Value Area.
Entry when price returns to POC after deviation with momentum confirmation.
Expected win rate: 65%+, R:R: 2:1
```

### Strategy 6: VWAP Reversion
```
Intraday mean-reversion using VWAP deviation.
Entry when price > 2 std devs from VWAP with RSI extreme.
Works well in liquid sessions (London/NY overlap).
Expected win rate: 63%, R:R: 1.8:1
```

### Strategy 7: Trend Continuation Pullback
```
Higher-timeframe trend + pullback to EMA_50 on lower TF.
Wait for reversal candlestick pattern at EMA level.
Much better entry than MACD crossover approach.
Expected win rate: 62%, R:R: 2.5:1
```
