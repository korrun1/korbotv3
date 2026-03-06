# 📚 KorBot X Enhanced - API Documentation

نسخة: 2.0  
تاريخ: 16 فبراير 2026

---

## 📋 جدول المحتويات

1. [نظرة عامة](#نظرة-عامة)
2. [Data Layer API](#data-layer-api)
3. [Market Intelligence API](#market-intelligence-api)
4. [Strategy Engine API](#strategy-engine-api)
5. [Risk Engine API](#risk-engine-api)
6. [Execution Engine API](#execution-engine-api)
7. [AI Optimization API](#ai-optimization-api)
8. [Database API](#database-api)
9. [Telegram Notifications API](#telegram-notifications-api)
10. [Dashboard API](#dashboard-api)

---

## 🌟 نظرة عامة

هذا التوثيق يغطي جميع APIs المتاحة في KorBot X Enhanced.

### المبادئ الأساسية:
- **Thread-Safe**: جميع APIs آمنة للاستخدام في بيئات متعددة الخيوط
- **Error Handling**: معالجة أخطاء شاملة مع logging
- **Type Hints**: دعم كامل لـ type hints
- **Async Support**: دعم async/await حيث يلزم

---

## 📡 Data Layer API

### `DataLayer`

طبقة البيانات الأساسية للاتصال مع MetaTrader 5.

#### التهيئة

```python
from data_layer import DataLayer
from config_loader import get_config

config = get_config()
data_layer = DataLayer(config)
```

#### Methods

##### `get_current_price(symbol: str) -> Optional[Dict[str, float]]`

احصل على السعر الحالي لرمز معين.

**Parameters:**
- `symbol` (str): رمز التداول (مثل: "AUDCAD")

**Returns:**
- `Dict` مع keys: `bid`, `ask`, `spread`, `timestamp`
- `None` في حالة الخطأ

**Example:**
```python
price_data = data_layer.get_current_price("AUDCAD")
print(f"Bid: {price_data['bid']}")
print(f"Ask: {price_data['ask']}")
```

##### `get_historical_data(symbol: str, timeframe: str, bars: int = 1000) -> Optional[pd.DataFrame]`

احصل على بيانات تاريخية OHLCV.

**Parameters:**
- `symbol` (str): رمز التداول
- `timeframe` (str): الإطار الزمني ('M1', 'M5', 'H1', 'H4', 'D1')
- `bars` (int): عدد الشموع المطلوبة

**Returns:**
- `pd.DataFrame` مع columns: Open, High, Low, Close, Volume
- `None` في حالة الخطأ

**Example:**
```python
df = data_layer.get_historical_data("AUDCAD", "H1", 200)
print(df.tail())
```

##### `get_symbol_info(symbol: str) -> Optional[Dict]`

احصل على معلومات الرمز.

**Returns:**
Dictionary مع:
- `name`: اسم الرمز
- `point`: قيمة النقطة
- `digits`: عدد المنازل العشرية
- `spread`: السبريد
- `min_lot`: الحجم الأدنى
- `max_lot`: الحجم الأقصى
- `lot_step`: خطوة الحجم

##### `get_account_info() -> Optional[Dict]`

احصل على معلومات الحساب.

**Returns:**
Dictionary مع:
- `balance`: الرصيد
- `equity`: القيمة
- `margin`: الهامش
- `free_margin`: الهامش الحر
- `profit`: الربح/الخسارة
- `leverage`: الرافعة المالية

##### `calculate_lot_size(symbol: str, risk_amount: float, stop_loss_pips: float) -> float`

احسب حجم الصفقة بناءً على المخاطرة.

**Parameters:**
- `symbol`: رمز التداول
- `risk_amount`: المبلغ المراد المخاطرة به
- `stop_loss_pips`: مسافة وقف الخسارة بالنقاط

**Returns:**
- حجم اللوت المحسوب

---

## 🧠 Market Intelligence API

### `MarketIntelligence`

ذكاء السوق المتقدم مع مؤشرات فنية.

#### التهيئة

```python
from market_intel import MarketIntelligence

market_intel = MarketIntelligence(config)
```

#### Methods

##### `calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame`

احسب جميع المؤشرات الفنية.

**Parameters:**
- `df`: DataFrame مع بيانات OHLCV

**Returns:**
- DataFrame مع 25+ مؤشر مضاف

**Indicators Added:**
- **Trend**: EMA (5,13,20,50,100,200), MACD, ADX, Ichimoku
- **Momentum**: RSI, Stochastic, Williams %R, ROC, MFI
- **Volatility**: Bollinger Bands, ATR, Keltner Channels
- **Volume**: Volume MA, OBV, ADL, CMF, VPT

**Example:**
```python
df = data_layer.get_historical_data("AUDCAD", "H1", 200)
df = market_intel.calculate_all_indicators(df)
print(df[['Close', 'RSI', 'MACD', 'ATR']].tail())
```

##### `detect_market_regime(df: pd.DataFrame) -> MarketRegime`

اكتشف نظام السوق الحالي.

**Returns:**
- `MarketRegime.TRENDING_UP`
- `MarketRegime.TRENDING_DOWN`
- `MarketRegime.RANGING`
- `MarketRegime.VOLATILE`
- `MarketRegime.QUIET`

**Example:**
```python
regime = market_intel.detect_market_regime(df)
print(f"Market regime: {regime.value}")
```

##### `calculate_rsi_divergence(df: pd.DataFrame, lookback: int = 20) -> Dict`

اكتشف تباعد RSI.

**Returns:**
Dictionary مع:
- `bullish` (bool): تباعد صعودي
- `bearish` (bool): تباعد هبوطي

##### `detect_price_patterns(df: pd.DataFrame) -> Dict[str, bool]`

اكتشف أنماط الأسعار الشائعة.

**Returns:**
Dictionary مع patterns:
- `bullish_pin_bar`
- `bearish_pin_bar`
- `bullish_engulfing`
- `bearish_engulfing`
- `doji`

---

## 🎯 Strategy Engine API

### `StrategyEngine`

محرك الاستراتيجيات الرئيسي.

#### التهيئة

```python
from strategy_engine import StrategyEngine

strategy_engine = StrategyEngine(config)
```

#### Methods

##### `generate_signals(symbol: str, df_dict: Dict[str, pd.DataFrame], regime: MarketRegime, price_data: Dict) -> List[Signal]`

ولّد إشارات التداول من جميع الاستراتيجيات.

**Parameters:**
- `symbol`: رمز التداول
- `df_dict`: Dictionary من DataFrames لكل إطار زمني
- `regime`: نظام السوق الحالي
- `price_data`: بيانات السعر الحالي

**Returns:**
- قائمة من كائنات `Signal`

**Example:**
```python
df_dict = {
    'M1': data_layer.get_historical_data("AUDCAD", "M1", 200),
    'M5': data_layer.get_historical_data("AUDCAD", "M5", 200),
    'H1': data_layer.get_historical_data("AUDCAD", "H1", 200),
    'H4': data_layer.get_historical_data("AUDCAD", "H4", 200)
}

# Calculate indicators for all
for tf in df_dict:
    df_dict[tf] = market_intel.calculate_all_indicators(df_dict[tf])

regime = market_intel.detect_market_regime(df_dict['H1'])
price_data = data_layer.get_current_price("AUDCAD")

signals = strategy_engine.generate_signals("AUDCAD", df_dict, regime, price_data)

for signal in signals:
    print(f"Strategy: {signal.strategy}")
    print(f"Type: {signal.type.value}")
    print(f"Confidence: {signal.confidence}")
```

### `Signal` Class

كائن إشارة التداول.

**Attributes:**
- `type` (SignalType): BUY أو SELL
- `strategy` (str): اسم الاستراتيجية
- `confidence` (float): مستوى الثقة (0-1)
- `entry_price` (float): سعر الدخول
- `stop_loss` (float): وقف الخسارة
- `take_profit` (float): جني الأرباح
- `reasons` (List[str]): أسباب الإشارة
- `timestamp` (str): وقت الإشارة

---

## 🛡️ Risk Engine API

### `RiskEngine`

محرك إدارة المخاطر المتقدم.

#### التهيئة

```python
from risk_engine import RiskEngine

risk_engine = RiskEngine(config)
```

#### Methods

##### `can_trade(account_info: Dict) -> Tuple[bool, Optional[str]]`

تحقق إذا كان التداول مسموحاً.

**Returns:**
- `(True, None)` إذا كان التداول مسموحاً
- `(False, reason)` إذا كان ممنوعاً

**Example:**
```python
account_info = data_layer.get_account_info()
can_trade, reason = risk_engine.can_trade(account_info)

if not can_trade:
    print(f"Trading not allowed: {reason}")
```

##### `can_open_position(symbol: str, open_positions: List[Dict], account_info: Dict) -> Tuple[bool, Optional[str]]`

تحقق إذا كان يمكن فتح صفقة جديدة.

##### `calculate_position_size(symbol: str, entry_price: float, stop_loss: float, account_info: Dict, symbol_info: Dict, confidence: float = 0.7) -> float`

احسب حجم الصفقة الأمثل.

**Example:**
```python
lot_size = risk_engine.calculate_position_size(
    symbol="AUDCAD",
    entry_price=0.91000,
    stop_loss=0.90800,
    account_info=account_info,
    symbol_info=symbol_info,
    confidence=0.75
)
print(f"Calculated lot size: {lot_size:.2f}")
```

##### `calculate_dynamic_stop_loss(entry_price: float, direction: str, atr: float, symbol: str) -> float`

احسب وقف خسارة ديناميكي بناءً على ATR.

##### `calculate_take_profit(entry_price: float, stop_loss: float, direction: str) -> float`

احسب هدف الربح بناءً على نسبة Risk:Reward.

##### `update_metrics(trade_result: Dict)`

حدّث مقاييس الأداء بعد الصفقة.

##### `get_metrics_summary() -> Dict`

احصل على ملخص مقاييس المخاطر.

**Returns:**
Dictionary مع:
- `state`: حالة التداول
- `total_trades`: إجمالي الصفقات
- `win_rate`: نسبة النجاح
- `consecutive_losses`: الخسائر المتتالية
- `daily_pnl`: الربح/الخسارة اليومي
- `max_drawdown`: الانخفاض الأقصى
- `circuit_breaker_active`: حالة Circuit Breaker

---

## ⚡ Execution Engine API

### `ExecutionEngine`

محرك تنفيذ الصفقات.

#### التهيئة

```python
from execution_engine import ExecutionEngine

execution_engine = ExecutionEngine(config, data_layer, risk_engine)
```

#### Methods

##### `execute_signal(signal: Signal, account_info: Dict, symbol_info: Dict) -> Optional[Trade]`

نفّذ إشارة تداول.

**Returns:**
- كائن `Trade` إذا نجح التنفيذ
- `None` إذا فشل

**Example:**
```python
trade = execution_engine.execute_signal(signal, account_info, symbol_info)

if trade:
    print(f"Trade opened: {trade.trade_id}")
    print(f"Entry: {trade.entry_price}")
    print(f"SL: {trade.stop_loss}")
    print(f"TP: {trade.take_profit}")
```

##### `close_position(ticket: int, reason: str = "Manual close") -> bool`

أغلق صفقة.

##### `check_stop_loss_take_profit()`

تحقق من جميع الصفقات المفتوحة لضرب SL/TP.

##### `update_trailing_stop()`

حدّث وقف الخسارة المتحرك للصفقات المفتوحة.

##### `get_open_positions(symbol: Optional[str] = None) -> List[Dict]`

احصل على الصفقات المفتوحة.

##### `get_account_summary() -> Dict`

احصل على ملخص الحساب.

---

## 🤖 AI Optimization API

### `AIOptimizationEngine`

محرك تحسين AI.

#### التهيئة

```python
from ai_optimization import AIOptimizationEngine

ai_engine = AIOptimizationEngine(config)
```

#### Methods

##### `enhance_signal(signal: Signal, df: pd.DataFrame) -> Signal`

عزز الإشارة بالثقة من AI.

**Example:**
```python
enhanced_signal = ai_engine.enhance_signal(signal, df)
print(f"Original confidence: {signal.confidence}")
print(f"Enhanced confidence: {enhanced_signal.confidence}")
```

##### `should_exit_position(position_data: Dict, df: pd.DataFrame) -> bool`

حدد إذا كان يجب الخروج من الصفقة (PPO).

---

## 💾 Database API

### `DatabaseManager`

مدير قواعد البيانات الموحد.

#### التهيئة

```python
from databases import DatabaseManager

db_manager = DatabaseManager(config)
```

#### Methods

##### `save_trade(trade_data: Dict)`

احفظ صفقة في SQLite وRedis.

##### `get_trades(**kwargs) -> List[Dict]`

احصل على الصفقات من SQLite.

**Parameters:**
- `symbol` (Optional[str]): فلتر حسب الرمز
- `strategy` (Optional[str]): فلتر حسب الاستراتيجية
- `limit` (int): الحد الأقصى للنتائج

##### `get_statistics(days: int = 30) -> Dict`

احصل على إحصائيات التداول.

**Example:**
```python
stats = db_manager.get_statistics(days=7)
print(f"Win rate: {stats['win_rate']:.1f}%")
print(f"Total P/L: ${stats['total_pnl']:.2f}")
```

---

## 📱 Telegram Notifications API

### `TelegramNotifier`

مدير إشعارات Telegram.

#### التهيئة

```python
from telegram_notify import TelegramNotifier

notifier = TelegramNotifier(config)
```

#### Methods

##### `send(message: str, parse_mode: str = 'HTML')`

أرسل رسالة.

##### `notify_trade_opened(trade_data: Dict)`

أرسل إشعار فتح صفقة.

##### `notify_trade_closed(trade_data: Dict)`

أرسل إشعار إغلاق صفقة.

##### `notify_daily_summary(stats: Dict)`

أرسل ملخص يومي.

##### `notify_circuit_breaker(reason: str)`

أرسل إشعار تفعيل Circuit Breaker.

---

## 🎨 Dashboard API

### `KorBotDashboard`

واجهة المستخدم الرسومية.

#### التشغيل

```python
from dashboard import KorBotDashboard
from PyQt6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
dashboard = KorBotDashboard()
dashboard.show()
sys.exit(app.exec())
```

#### Features

- **أوضاع التداول**: أمان، متوازن، مخاطرة، تلقائي
- **تحكم كامل**: تشغيل/إيقاف/إيقاف مؤقت
- **إعدادات مباشرة**: تغيير المخاطرة والاستراتيجيات
- **مراقبة real-time**: الحساب، الأداء، الصفقات
- **رسوم بيانية**: منحنى القيمة والإحصائيات

---

## 📝 Examples

### مثال كامل: بوت تداول بسيط

```python
from config_loader import get_config
from data_layer import DataLayer
from market_intel import MarketIntelligence
from strategy_engine import StrategyEngine
from risk_engine import RiskEngine
from execution_engine import ExecutionEngine
from databases import DatabaseManager
from telegram_notify import TelegramNotifier

# Initialize
config = get_config()
data_layer = DataLayer(config)
market_intel = MarketIntelligence(config)
strategy_engine = StrategyEngine(config)
risk_engine = RiskEngine(config)
execution_engine = ExecutionEngine(config, data_layer, risk_engine)
db_manager = DatabaseManager(config)
notifier = TelegramNotifier(config)

# Main loop
symbol = "AUDCAD"

while True:
    # Get data
    df = data_layer.get_historical_data(symbol, "H1", 200)
    df = market_intel.calculate_all_indicators(df)
    
    # Detect regime
    regime = market_intel.detect_market_regime(df)
    
    # Get signals
    df_dict = {'H1': df}
    price_data = data_layer.get_current_price(symbol)
    signals = strategy_engine.generate_signals(symbol, df_dict, regime, price_data)
    
    # Execute signals
    account_info = data_layer.get_account_info()
    symbol_info = data_layer.get_symbol_info(symbol)
    
    for signal in signals:
        trade = execution_engine.execute_signal(signal, account_info, symbol_info)
        
        if trade:
            db_manager.save_trade(trade.to_dict())
            notifier.notify_trade_opened(trade.to_dict())
    
    # Check existing positions
    execution_engine.check_stop_loss_take_profit()
    
    time.sleep(60)  # Wait 1 minute
```

---

## ⚠️ Error Handling

جميع APIs تستخدم معالجة أخطاء شاملة:

```python
try:
    result = api_function()
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    # Handle error
```

---

## 📞 Support

للدعم والمساعدة:
- راجع README.md
- راجع INSTALLATION.md
- افتح Issue في GitHub

---

<div align="center">

**📚 KorBot X Enhanced API Documentation**

Version 2.0 | Complete & Comprehensive

</div>
