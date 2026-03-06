# 🔧 دليل حل المشاكل - KorBot X Enhanced

**حلول لجميع المشاكل الشائعة! 🛠️**

---

## 📋 المحتويات

1. [مشاكل التثبيت](#مشاكل-التثبيت)
2. [مشاكل MT5](#مشاكل-mt5)
3. [مشاكل Redis](#مشاكل-redis)
4. [مشاكل Telegram](#مشاكل-telegram)
5. [مشاكل التشغيل](#مشاكل-التشغيل)
6. [مشاكل الأداء](#مشاكل-الأداء)
7. [مشاكل الصفقات](#مشاكل-الصفقات)

---

## 1️⃣ مشاكل التثبيت

### ❌ مشكلة: "Python is not recognized"

**السبب:** Python غير مضاف للـ PATH

**الحل:**

**Windows:**
```bash
# الطريقة 1: إعادة تثبيت Python
# فعّل "Add Python to PATH" أثناء التثبيت

# الطريقة 2: إضافة يدوية
# 1. ابحث عن مكان Python:
where python

# 2. انسخ المسار (مثل: C:\Python310)
# 3. اضغط Win+R → اكتب: sysdm.cpl
# 4. Advanced → Environment Variables
# 5. أضف المسار للـ PATH
```

**Linux/Mac:**
```bash
# أضف للـ .bashrc أو .zshrc:
export PATH="/usr/local/bin/python3:$PATH"
source ~/.bashrc
```

---

### ❌ مشكلة: "pip install fails"

**السبب:** مشاكل في الشبكة أو الصلاحيات

**الحلول:**

```bash
# 1. تحديث pip
python -m pip install --upgrade pip

# 2. استخدم --user
pip install --user [package_name]

# 3. جرب mirror مختلف
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple [package_name]

# 4. Windows: شغّل CMD كـ Administrator

# 5. Linux: استخدم sudo
sudo pip install [package_name]
```

---

### ❌ مشكلة: "Building wheel failed"

**السبب:** بعض المكتبات تحتاج C++ compiler

**الحل:**

**Windows:**
```bash
# 1. ثبّت Visual Studio Build Tools:
https://visualstudio.microsoft.com/downloads/
# اختر: Build Tools for Visual Studio
# فعّل: C++ build tools

# 2. أو استخدم pre-built wheels:
# للـ TA-Lib:
pip install TA-Lib‑0.4.24‑cp310‑cp310‑win_amd64.whl
# حمّل من: https://www.lfd.uci.edu/~gohlke/pythonlibs/
```

**Linux:**
```bash
# ثبّت build tools:
sudo apt-get install build-essential python3-dev
```

---

### ❌ مشكلة: "No module named 'MetaTrader5'"

**الحل:**
```bash
# تأكد من البيئة الافتراضية مفعلة
# يجب أن ترى (venv)

# أعد التثبيت:
pip uninstall MetaTrader5
pip install MetaTrader5

# Windows: قد تحتاج النسخة الصحيحة
pip install MetaTrader5==5.0.4430
```

---

## 2️⃣ مشاكل MT5

### ❌ مشكلة: "MT5 initialization failed"

**التشخيص:**
```python
import MetaTrader5 as mt5

mt5.initialize()
error = mt5.last_error()
print(f"Error code: {error[0]}")
print(f"Error message: {error[1]}")
```

**الأخطاء الشائعة:**

#### Error -2: "Invalid account"
```bash
السبب: بيانات دخول خاطئة

الحل:
1. تحقق من .env:
   MT5_LOGIN=رقم_صحيح (أرقام فقط!)
   MT5_PASSWORD=كلمة_مرور_صحيحة
   MT5_SERVER=اسم_خادم_صحيح

2. في MT5:
   Tools → Options → Server
   تأكد من نفس الخادم
```

#### Error -10005: "Terminal not running"
```bash
السبب: MT5 غير مفتوح

الحل:
1. افتح MT5
2. تأكد من أنه يعمل (ليس مجمد)
3. انتظر حتى يتصل بالخادم
```

#### Error -10004: "Terminal initialization failed"
```bash
السبب: مشكلة في ملفات MT5

الحل:
1. أعد تشغيل MT5
2. أو أعد تثبيت MT5
3. حذف مجلد: C:\Users\[User]\AppData\Roaming\MetaQuotes
```

---

### ❌ مشكلة: "No price data"

**الحل:**
```python
# تحقق من الرمز متاح:
import MetaTrader5 as mt5

mt5.initialize()

# قائمة الرموز:
symbols = mt5.symbols_get()
print([s.name for s in symbols])

# تحقق من رمز محدد:
symbol_info = mt5.symbol_info("AUDCAD")
if symbol_info:
    print("✅ الرمز موجود")
    print(f"Visible: {symbol_info.visible}")
    
    # إذا غير مرئي:
    if not symbol_info.visible:
        mt5.symbol_select("AUDCAD", True)
else:
    print("❌ الرمز غير موجود")
    print("جرب: EURUSD, GBPUSD, USDJPY")
```

---

### ❌ مشكلة: "Trade disabled"

**الحل:**
```bash
# في MT5:
Tools → Options → Expert Advisors
✅ فعّل: Allow automated trading
✅ فعّل: Allow DLL imports
✅ فعّل: Allow WebRequest

# ثم أعد تشغيل MT5
```

---

## 3️⃣ مشاكل Redis

### ❌ مشكلة: "Connection refused [Errno 111]"

**السبب:** Redis غير شغال

**الحل:**

**Windows:**
```bash
# 1. افتح Services (Win+R → services.msc)
# 2. ابحث عن "Redis"
# 3. اضغط يمين → Start

# أو من CMD:
net start Redis
```

**Linux:**
```bash
# تشغيل Redis:
sudo systemctl start redis

# تفعيل عند بدء التشغيل:
sudo systemctl enable redis

# التحقق:
sudo systemctl status redis
```

---

### ❌ مشكلة: "NOAUTH Authentication required"

**السبب:** Redis محمي بكلمة مرور

**الحل:**
```bash
# في .env:
REDIS_PASSWORD=كلمة_المرور

# أو عطّل كلمة المرور:
# في ملف redis.conf:
# علّق السطر:
# requirepass your_password
```

---

### ❌ مشكلة: Redis بطيء جداً

**الحل:**
```bash
# تحقق من الذاكرة:
redis-cli
> INFO memory

# إذا كانت ممتلئة، امسح القديم:
> FLUSHDB  # احذر! يحذف كل شيء

# أو زد maxmemory في redis.conf:
maxmemory 256mb
maxmemory-policy allkeys-lru
```

---

## 4️⃣ مشاكل Telegram

### ❌ مشكلة: "Unauthorized"

**السبب:** TOKEN خاطئ

**الحل:**
```bash
# تحقق من .env:
TELEGRAM_TOKEN=123456:ABCdef...
# لا مسافات قبل أو بعد =
# لا علامات اقتباس

# اختبار:
curl https://api.telegram.org/bot<TOKEN>/getMe
```

---

### ❌ مشكلة: "Chat not found"

**السبب:** CHAT_ID خاطئ

**الحل:**
```bash
# احصل على Chat ID:
# 1. أرسل رسالة لبوتك: /start

# 2. افتح:
https://api.telegram.org/bot<TOKEN>/getUpdates

# 3. ابحث عن:
"chat":{"id":123456789

# 4. الرقم هو Chat ID
```

---

### ❌ مشكلة: "No notifications received"

**الحلول:**
```python
# اختبار يدوي:
from telegram import Bot

TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

try:
    bot = Bot(token=TOKEN)
    bot.send_message(chat_id=CHAT_ID, text="🧪 Test")
    print("✅ نجح!")
except Exception as e:
    print(f"❌ فشل: {e}")

# تحقق من:
1. TOKEN صحيح
2. CHAT_ID صحيح
3. البوت غير محظور
4. الإنترنت متصل
```

---

## 5️⃣ مشاكل التشغيل

### ❌ مشكلة: "Config file not found"

**الحل:**
```bash
# تأكد من الهيكل:
KorBot-X-Enhanced/
├── config/
│   └── config.yaml  # ← هنا!

# المسار الصحيح:
cd C:\KorBot\KorBot-X-Enhanced
python src/python_controller/main.py
```

---

### ❌ مشكلة: ".env file not found"

**الحل:**
```bash
# إنشاء من المثال:
copy .env.example .env

# تحقق من وجوده:
# Windows:
dir .env

# Linux:
ls -la .env
```

---

### ❌ مشكلة: "Permission denied"

**Linux/Mac:**
```bash
# أعطِ صلاحيات:
chmod +x src/python_controller/main.py

# أو شغّل بـ sudo:
sudo python src/python_controller/main.py
```

**Windows:**
```bash
# شغّل CMD كـ Administrator
```

---

### ❌ مشكلة: Dashboard لا يفتح

**الحلول:**
```bash
# 1. تحقق من PyQt6:
pip install PyQt6 pyqtgraph --upgrade

# 2. إذا فشل، جرب بدون GUI:
python main.py

# 3. Linux: قد تحتاج:
sudo apt-get install python3-pyqt6
# أو
sudo apt-get install libxcb-xinerama0
```

---

## 6️⃣ مشاكل الأداء

### ❌ مشكلة: البوت بطيء جداً

**التشخيص:**
```python
# في logs/korbot.log
# ابحث عن:
# "Indicator calculation took X seconds"
```

**الحلول:**

**1. استخدم Rust (أسرع 15x):**
```bash
cd src/rust_core
cargo build --release
cp target/release/libkorbot_core.so ../../
```

**2. قلل عدد الشموع:**
```yaml
# في config.yaml
# بدلاً من:
bars: 1000
# استخدم:
bars: 200
```

**3. زد Cache TTL:**
```yaml
# في config.yaml
performance:
  cache:
    ttl: 300  # 5 دقائق
```

---

### ❌ مشكلة: استهلاك RAM عالي

**الحل:**
```bash
# 1. قلل عدد الاستراتيجيات المفعلة
# في Dashboard أو config.yaml

# 2. قلل Cache size:
# في config.yaml:
performance:
  cache:
    max_size: 500  # من 1000
```

---

### ❌ مشكلة: CPU 100%

**الحل:**
```bash
# 1. تحقق من infinite loop في logs

# 2. زد data_refresh_interval:
# في config.yaml:
system:
  data_refresh_interval: 5  # من 1 إلى 5 ثواني

# 3. عطّل بعض المؤشرات غير المهمة
```

---

## 7️⃣ مشاكل الصفقات

### ❌ مشكلة: البوت لا يفتح صفقات

**التشخيص:**
```python
# شغّل strategy_engine.py:
python strategy_engine.py

# شاهد output:
# - هل هناك إشارات؟
# - ما confidence الإشارات؟
```

**الأسباب والحلول:**

**1. Confidence منخفض:**
```yaml
# في config.yaml خفّض:
ai:
  xgboost:
    min_confidence: 0.60  # من 0.75
```

**2. Market regime غير مناسب:**
```python
# في logs ابحث عن:
# "Market regime: RANGING"
# "Strategy X disabled in RANGING market"

# بعض الاستراتيجيات لا تعمل في أسواق معينة
```

**3. Risk limits:**
```python
# في logs:
# "Cannot open position: Max positions reached"
# "Cannot trade: Daily loss limit reached"

# الحل: انتظر أو زد الحدود
```

**4. Circuit Breaker مفعل:**
```python
# في logs:
# "Circuit breaker triggered"

# الحل: انتظر cooldown (60 دقيقة)
# أو أعد تعيين يدوياً
```

---

### ❌ مشكلة: Win rate منخفض جداً (<50%)

**التشخيص:**
```bash
# احصل على إحصائيات:
python
```

```python
from databases import DatabaseManager
from config_loader import get_config

db = DatabaseManager(get_config())
stats = db.get_statistics(days=7)

print(f"Win Rate: {stats['win_rate']:.1f}%")
print(f"Avg Win: ${stats.get('avg_win', 0):.2f}")
print(f"Avg Loss: ${stats.get('avg_loss', 0):.2f}")

# تحقق من كل استراتيجية:
trades = db.get_trades(limit=1000)
for strategy in ['Scalping', 'Mean Reversion', 'Breakout', 'Swing']:
    strategy_trades = [t for t in trades if t['strategy'] == strategy]
    wins = sum(1 for t in strategy_trades if t['pnl'] > 0)
    wr = wins / len(strategy_trades) * 100 if strategy_trades else 0
    print(f"{strategy}: {wr:.1f}%")
```

**الحلول:**

**1. عطّل الاستراتيجيات الضعيفة:**
```yaml
# في config.yaml أو Dashboard
# عطّل الاستراتيجية بـ win rate <50%
```

**2. شدد شروط الدخول:**
```yaml
# زد min_confidence:
ai:
  xgboost:
    min_confidence: 0.75  # أو أعلى
```

**3. وسّع Stop Loss:**
```yaml
risk:
  stop_loss:
    atr_multiplier: 2.5  # من 2.0
```

**4. جرب رمز مختلف:**
```yaml
trading:
  symbol: "EURUSD"  # بدلاً من AUDCAD
```

---

### ❌ مشكلة: Drawdown كبير (>10%)

**الحل الفوري:**
```bash
# أوقف البوت فوراً!
# Ctrl+C

# في config.yaml:
risk:
  base_risk_percent: 0.3  # قلّل المخاطرة!
  
  circuit_breaker:
    max_consecutive_losses: 2  # من 3
```

**الحلول طويلة المدى:**

**1. Dynamic position sizing:**
```yaml
risk:
  use_dynamic_sizing: true
  kelly_fraction: 0.25
```

**2. Trailing stop:**
```yaml
risk:
  take_profit:
    use_trailing: true
    trailing_atr_multiplier: 1.5
```

**3. Max exposure:**
```yaml
risk:
  max_symbol_exposure_percent: 2.0  # من 3.0
```

---

### ❌ مشكلة: الصفقات تُغلق بسرعة

**السبب:** Stop loss ضيق جداً

**الحل:**
```yaml
risk:
  stop_loss:
    atr_multiplier: 3.0  # وسّعه
    min_pips: 15         # من 10
```

---

### ❌ مشكلة: الصفقات تبقى مفتوحة طويلاً

**الحل:**
```yaml
risk:
  take_profit:
    risk_reward_ratio: 2.0  # من 2.5 (أقرب)
    
  # أو أضف max duration:
  max_trade_duration_hours: 48
```

---

## 🆘 أدوات التشخيص

### 1. فحص شامل:
```bash
# شغّل جميع الاختبارات:
pytest tests/ -v

# شاهد الفشل:
pytest tests/ -v --tb=long
```

### 2. فحص logs:
```bash
# Windows:
type logs\korbot.log | findstr ERROR

# Linux:
grep ERROR logs/korbot.log

# آخر 50 سطر:
tail -n 50 logs/korbot.log
```

### 3. فحص database:
```bash
sqlite3 data/historical.sqlite

-- أحدث 10 صفقات:
SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10;

-- الصفقات الخاسرة:
SELECT * FROM trades WHERE pnl < 0 AND status = 'closed';
```

### 4. Memory usage:
```python
import psutil
import os

process = psutil.Process(os.getpid())
print(f"RAM: {process.memory_info().rss / 1024 / 1024:.1f} MB")
print(f"CPU: {process.cpu_percent()}%")
```

---

## 📞 الدعم

إذا لم تجد الحل هنا:

1. **راجع logs/korbot.log** - معظم الأخطاء موثقة
2. **راجع FULL_INSTALLATION_GUIDE.md** - تفاصيل أكثر
3. **شغّل pytest** - اكتشف المشاكل
4. **ابحث في GitHub Issues** - قد يكون شخص واجه نفس المشكلة

---

<div align="center">

# 🔧 KorBot X Enhanced

**حل لكل مشكلة! 🛠️**

**إذا فشل كل شيء... أعد التثبيت من الصفر! 😅**

</div>
