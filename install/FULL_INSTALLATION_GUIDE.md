# 📘 دليل التثبيت الشامل لـ KorBot X Enhanced
## من الصفر حتى أول صفقة حقيقية 🚀

**تاريخ:** 16 فبراير 2026  
**النسخة:** 2.0  
**الوقت المتوقع:** 2-3 ساعات

---

## 📋 جدول المحتويات

1. [المتطلبات الأساسية](#المتطلبات-الأساسية)
2. [تنزيل وإعداد المشروع](#تنزيل-وإعداد-المشروع)
3. [تثبيت Python والمكتبات](#تثبيت-python-والمكتبات)
4. [تثبيت وإعداد MetaTrader 5](#تثبيت-وإعداد-metatrader-5)
5. [تثبيت وإعداد Redis](#تثبيت-وإعداد-redis)
6. [إعداد Telegram Bot](#إعداد-telegram-bot)
7. [إعداد ملفات الإعدادات](#إعداد-ملفات-الإعدادات)
8. [الاختبار الأولي](#الاختبار-الأولي)
9. [التشغيل في Paper Mode](#التشغيل-في-paper-mode)
10. [المراقبة والتحليل](#المراقبة-والتحليل)
11. [الانتقال للتداول الحقيقي](#الانتقال-للتداول-الحقيقي)
12. [حل المشاكل](#حل-المشاكل)

---

## 1️⃣ المتطلبات الأساسية

### أ) متطلبات الجهاز:

| المكون | الحد الأدنى | الموصى به |
|--------|------------|-----------|
| **المعالج** | Intel i3 / AMD Ryzen 3 | Intel i5 / AMD Ryzen 5+ |
| **الذاكرة** | 4 GB RAM | 8 GB RAM |
| **التخزين** | 10 GB | 20 GB SSD |
| **الإنترنت** | 2 Mbps | 10+ Mbps |
| **نظام التشغيل** | Windows 10/11، Linux Ubuntu 20.04+ | - |

### ب) البرامج المطلوبة:

- [ ] Python 3.10 أو أحدث
- [ ] MetaTrader 5
- [ ] Redis Server
- [ ] محرر نصوص (VS Code، Notepad++، إلخ)
- [ ] Git (اختياري)

### ج) المتطلبات المالية:

⚠️ **مهم جداً:**
- حساب تجريبي Demo (للبداية): مجاني
- حساب حقيقي (بعد 3 أشهر): 
  - الحد الأدنى: 25$ (وضع أمان)
  - موصى به: 100$+ (وضع متوازن)

---

## 2️⃣ تنزيل وإعداد المشروع

### الخطوة 1: إنشاء مجلد العمل

```bash
# Windows (في Command Prompt أو PowerShell)
cd C:\
mkdir KorBot
cd KorBot

# Linux/Mac (في Terminal)
cd ~
mkdir KorBot
cd KorBot
```

### الخطوة 2: تنزيل الملفات

**الطريقة 1: باستخدام Git**
```bash
git clone https://github.com/yourusername/KorBot-X-Enhanced.git
cd KorBot-X-Enhanced
```

**الطريقة 2: تنزيل يدوي**
1. حمّل جميع الملفات (27 ملف) من هذه المحادثة
2. ضعها في المجلد بالهيكل التالي:

```
C:\KorBot\KorBot-X-Enhanced\
├── config\
│   └── config.yaml
├── src\
│   ├── python_controller\
│   │   ├── utils.py
│   │   ├── config_loader.py
│   │   ├── data_layer.py
│   │   ├── market_intel.py
│   │   ├── strategy_engine.py
│   │   ├── risk_engine.py
│   │   ├── ai_optimization.py
│   │   ├── execution_engine.py
│   │   ├── backtester.py
│   │   ├── databases.py
│   │   ├── telegram_notify.py
│   │   ├── dashboard.py
│   │   └── main.py
│   └── rust_core\
│       ├── Cargo.toml
│       └── src\
│           └── lib.rs
├── tests\
│   └── test_core.py
├── docs\
│   └── API_DOCUMENTATION.md
├── data\          (سيُنشأ تلقائياً)
├── logs\          (سيُنشأ تلقائياً)
├── models\        (سيُنشأ تلقائياً)
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
├── README.md
└── INSTALLATION.md
```

### الخطوة 3: التحقق من الهيكل

```bash
# Windows
dir /s

# Linux/Mac
ls -R
```

✅ **تحقق:** يجب أن ترى جميع المجلدات والملفات

---

## 3️⃣ تثبيت Python والمكتبات

### الخطوة 1: تثبيت Python

#### Windows:
1. اذهب إلى: https://www.python.org/downloads/
2. حمّل Python 3.10 أو أحدث
3. **مهم:** أثناء التثبيت، فعّل "Add Python to PATH"
4. اضغط "Install Now"

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip
```

#### macOS:
```bash
# باستخدام Homebrew
brew install python@3.10
```

### الخطوة 2: التحقق من التثبيت

```bash
python --version
# يجب أن يظهر: Python 3.10.x أو أحدث

pip --version
# يجب أن يظهر: pip 23.x أو أحدث
```

### الخطوة 3: إنشاء البيئة الافتراضية

```bash
# في مجلد المشروع
cd C:\KorBot\KorBot-X-Enhanced

# إنشاء البيئة
python -m venv venv

# تفعيل البيئة
# Windows (CMD):
venv\Scripts\activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Linux/Mac:
source venv/bin/activate
```

✅ **تحقق:** يجب أن ترى `(venv)` في بداية السطر

### الخطوة 4: تحديث pip

```bash
python -m pip install --upgrade pip
```

### الخطوة 5: تثبيت المكتبات

```bash
# تثبيت جميع المكتبات
pip install -r requirements.txt
```

⏱️ **ملاحظة:** قد يستغرق 5-10 دقائق

### الخطوة 6: التحقق من التثبيت

```bash
# اختبر المكتبات الأساسية
python -c "import MetaTrader5 as mt5; print('MT5 OK')"
python -c "import redis; print('Redis module OK')"
python -c "import pandas; print('Pandas OK')"
python -c "import PyQt6; print('PyQt6 OK')"
```

✅ **كل شيء يجب أن يطبع "OK"**

---

## 4️⃣ تثبيت وإعداد MetaTrader 5

### الخطوة 1: تنزيل MT5

#### Windows:
1. اذهب إلى: https://www.metatrader5.com/en/download
2. حمّل MT5 for Windows
3. شغّل الملف وثبّت

#### Linux:
```bash
# باستخدام Wine
sudo apt install wine64
wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe
wine mt5setup.exe
```

### الخطوة 2: فتح حساب Demo

1. **افتح MT5**
2. اذهب إلى: `File` → `Open an Account`
3. اختر وسيط (مثل: XM، Pepperstone، IC Markets)
4. اختر `Open a demo account`
5. املأ البيانات:
   - الاسم: أي اسم
   - البريد: بريدك
   - نوع الحساب: Standard
   - الرافعة: 1:100 أو 1:500
   - الرصيد: 10,000$ (أو حسب رغبتك)
6. اضغط `Next`

### الخطوة 3: حفظ بيانات الحساب

بعد إنشاء الحساب، ستحصل على:

```
Login: 12345678
Password: YourPassword123
Server: BrokerName-Demo
```

⚠️ **مهم جداً:** احفظ هذه البيانات في ملف نصي آمن!

### الخطوة 4: اختبار الاتصال

1. في MT5، اذهب إلى: `Tools` → `Options` → `Community`
2. فعّل `Allow automated trading`
3. اضغط `OK`
4. أعد تشغيل MT5

### الخطوة 5: اختبار من Python

```bash
# في مجلد المشروع (مع البيئة المفعلة)
python
```

```python
import MetaTrader5 as mt5

# تهيئة
if mt5.initialize():
    print("✅ MT5 initialized successfully!")
    
    # معلومات الحساب
    account_info = mt5.account_info()
    if account_info:
        print(f"Balance: {account_info.balance}")
        print(f"Equity: {account_info.equity}")
    
    # إغلاق
    mt5.shutdown()
else:
    print("❌ MT5 initialization failed")
    print(mt5.last_error())
```

✅ **يجب أن ترى رصيد حسابك**

---

## 5️⃣ تثبيت وإعداد Redis

### Windows:

#### الطريقة 1: باستخدام MSI Installer (موصى به)
1. اذهب إلى: https://github.com/microsoftarchive/redis/releases
2. حمّل: `Redis-x64-3.0.504.msi`
3. ثبّت بالإعدادات الافتراضية
4. Redis سيعمل تلقائياً كخدمة

#### الطريقة 2: Memurai (بديل حديث)
1. اذهب إلى: https://www.memurai.com/get-memurai
2. حمّل Memurai Developer Edition (مجاني)
3. ثبّت وشغّل

### Linux (Ubuntu/Debian):

```bash
# تثبيت Redis
sudo apt update
sudo apt install redis-server

# تفعيل Redis ليعمل عند بدء التشغيل
sudo systemctl enable redis-server

# تشغيل Redis
sudo systemctl start redis-server

# التحقق من الحالة
sudo systemctl status redis-server
```

### macOS:

```bash
# باستخدام Homebrew
brew install redis

# تشغيل Redis
brew services start redis
```

### اختبار Redis:

```bash
# في Terminal/CMD
redis-cli ping
```

✅ **يجب أن يظهر:** `PONG`

#### اختبار من Python:

```bash
python
```

```python
import redis

# الاتصال
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# اختبار
r.ping()  # يجب أن يرجع True

# اختبار حفظ واسترجاع
r.set('test', 'Hello KorBot!')
print(r.get('test'))  # يجب أن يطبع: Hello KorBot!

# حذف
r.delete('test')
```

✅ **إذا عمل كل شيء، Redis جاهز!**

---

## 6️⃣ إعداد Telegram Bot

### الخطوة 1: إنشاء Bot

1. **افتح Telegram** على هاتفك أو الكمبيوتر
2. **ابحث عن:** `@BotFather`
3. **ابدأ محادثة:** اضغط `Start`
4. **أرسل:** `/newbot`
5. **اتبع التعليمات:**
   - أدخل اسم البوت (مثل: `KorBot Trading`)
   - أدخل username للبوت (يجب أن ينتهي بـ `bot`)
     - مثال: `korbot_trading_bot`
6. **احفظ الـ TOKEN** الذي ستحصل عليه:
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
   ```

### الخطوة 2: الحصول على Chat ID

#### الطريقة 1: باستخدام بوت
1. ابحث في Telegram عن: `@userinfobot`
2. ابدأ محادثة معه
3. سيعطيك Chat ID مثل: `987654321`

#### الطريقة 2: يدوياً
1. أرسل رسالة لبوتك الجديد: `/start`
2. افتح المتصفح واذهب إلى:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   استبدل `<YOUR_TOKEN>` بالـ TOKEN الخاص بك
3. ابحث عن `"chat":{"id":123456789`
4. الرقم بعد `"id":` هو Chat ID

### الخطوة 3: حفظ البيانات

احفظ:
```
TOKEN: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
CHAT_ID: 987654321
```

### الخطوة 4: اختبار

```python
from telegram import Bot

TOKEN = "YOUR_TOKEN_HERE"
CHAT_ID = "YOUR_CHAT_ID_HERE"

bot = Bot(token=TOKEN)
bot.send_message(chat_id=CHAT_ID, text="🤖 KorBot X Test!")
```

✅ **يجب أن تصلك رسالة في Telegram!**

---

## 7️⃣ إعداد ملفات الإعدادات

### الخطوة 1: إنشاء ملف .env

```bash
# في مجلد المشروع
cd C:\KorBot\KorBot-X-Enhanced

# نسخ الملف المثالي
# Windows:
copy .env.example .env

# Linux/Mac:
cp .env.example .env
```

### الخطوة 2: تحرير ملف .env

افتح `.env` بمحرر نصوص:

```bash
# Windows:
notepad .env

# Linux:
nano .env

# أو استخدم VS Code:
code .env
```

### الخطوة 3: املأ البيانات

```bash
# MetaTrader 5 Configuration
MT5_LOGIN=12345678                           # ← ضع رقم حسابك من MT5
MT5_PASSWORD=YourPassword123                  # ← كلمة المرور
MT5_SERVER=BrokerName-Demo                    # ← اسم الخادم

# Telegram Bot Configuration
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNO    # ← الـ TOKEN من BotFather
TELEGRAM_CHAT_ID=987654321                    # ← Chat ID الخاص بك

# Redis Configuration (اتركها كما هي إذا كنت تستخدم الإعدادات الافتراضية)
REDIS_PASSWORD=

# Trading Mode
TRADING_MODE=paper                            # ← مهم جداً! ابدأ بـ paper

# Log Level
LOG_LEVEL=INFO
```

⚠️ **مهم جداً:**
- لا تضع مسافات حول `=`
- لا تضع علامات اقتباس حول القيم
- `TRADING_MODE=paper` للبداية (ليس حقيقي!)

### الخطوة 4: احفظ الملف

اضغط `Ctrl+S` أو `Save`

### الخطوة 5: مراجعة config.yaml (اختياري)

إذا أردت تغيير إعدادات متقدمة:

```bash
code config/config.yaml
```

**يمكنك تعديل:**
- رمز التداول (symbol: "AUDCAD")
- نسبة المخاطرة (base_risk_percent: 0.8)
- الاستراتيجيات المفعلة

**الإعدادات الافتراضية جيدة للبداية!**

---

## 8️⃣ الاختبار الأولي

### الخطوة 1: اختبار الإعدادات

```bash
# في مجلد المشروع مع البيئة المفعلة
cd src/python_controller

# اختبار تحميل الإعدادات
python config_loader.py
```

✅ **يجب أن ترى:** "Configuration loaded successfully!"

### الخطوة 2: اختبار الاتصال بـ MT5

```bash
python data_layer.py
```

✅ **يجب أن ترى:**
- "Connected to MT5: Account xxxxx"
- معلومات الحساب
- أسعار حالية

### الخطوة 3: اختبار Redis

```bash
python databases.py
```

✅ **يجب أن ترى:**
- "SQLite Manager initialized"
- "Redis Manager initialized"
- "Test trade saved"

### الخطوة 4: اختبار Telegram

```bash
python telegram_notify.py
```

✅ **يجب أن تصلك رسالة اختبار في Telegram!**

### الخطوة 5: اختبار الاستراتيجيات

```bash
python strategy_engine.py
```

✅ **يجب أن ترى:**
- "Strategy Engine initialized with X strategies"
- إشارات مولّدة (إن وُجدت)

### الخطوة 6: تشغيل Unit Tests

```bash
cd ../..
pytest tests/ -v
```

✅ **يجب أن تمر جميع الاختبارات** (أو معظمها)

---

## 9️⃣ التشغيل في Paper Mode

### ⚠️ تحذير مهم جداً:

**لا تشغّل على حساب حقيقي قبل:**
1. ✅ اختبار Paper Mode لمدة 3 أشهر على الأقل
2. ✅ فهم كامل لكيفية عمل البوت
3. ✅ win rate مستقر >60%
4. ✅ drawdown <10%

### الخطوة 1: التحقق من الوضع

افتح `.env` وتأكد:
```bash
TRADING_MODE=paper
```

### الخطوة 2: التشغيل بدون GUI

```bash
cd src/python_controller
python main.py
```

**ماذا يحدث:**
- البوت سيبدأ التشغيل
- سيتصل بـ MT5
- سيبدأ مراقبة الأسواق
- سيولّد إشارات
- سيفتح صفقات وهمية (Paper)
- ستصلك إشعارات في Telegram

**للإيقاف:** اضغط `Ctrl+C`

### الخطوة 3: التشغيل مع GUI (موصى به)

```bash
python dashboard.py
```

**ستفتح نافذة Dashboard:**

1. **اختر وضع التداول:**
   - للبداية: اختر "🛡️ وضع الأمان"

2. **راجع الإعدادات:**
   - Risk: 0.3-0.8%
   - Max Positions: 1-2
   - Confidence: 70%+

3. **اضغط "▶️ تشغيل البوت"**

4. **راقب:**
   - معلومات الحساب (وهمية)
   - الصفقات المفتوحة
   - السجلات
   - الإحصائيات

### الخطوة 4: المراقبة والتحليل

#### أ) مراقبة يومية:

**في Dashboard:**
- تحقق من Win Rate (يجب أن يزيد تدريجياً)
- راقب Drawdown (يجب أن يبقى <5%)
- انظر للصفقات المغلقة

**في Telegram:**
- ستصلك إشعارات:
  - 📈 Trade Opened
  - ✅/❌ Trade Closed
  - 📊 Daily Summary

#### ب) مراجعة أسبوعية:

```bash
# احصل على إحصائيات
python
```

```python
from databases import DatabaseManager
from config_loader import get_config

config = get_config()
db = DatabaseManager(config)

# إحصائيات آخر 7 أيام
stats = db.get_statistics(days=7)
print(f"Win Rate: {stats['win_rate']:.1f}%")
print(f"Total P/L: ${stats['total_pnl']:.2f}")
print(f"Total Trades: {stats['total_trades']}")
```

#### ج) المؤشرات المطلوبة بعد شهر:

| المؤشر | الهدف |
|--------|-------|
| Win Rate | >60% |
| Total Trades | >50 |
| Profit Factor | >1.5 |
| Max Drawdown | <8% |
| Avg Trade Duration | <24h |

### الخطوة 5: التحسين

إذا كانت النتائج دون المطلوب:

#### أ) تقليل المخاطرة:
```yaml
# في config.yaml
risk:
  base_risk_percent: 0.5  # قلّل من 0.8 إلى 0.5
```

#### ب) تشديد الثقة:
```yaml
# في config.yaml
ai:
  xgboost:
    min_confidence: 0.75  # زد من 0.65 إلى 0.75
```

#### ج) تعطيل استراتيجية:
في Dashboard:
- أوقف الاستراتيجيات الضعيفة
- ركّز على الأفضل

---

## 🔟 المراقبة والتحليل

### أ) السجلات (Logs)

```bash
# عرض السجلات
# Windows:
type logs\korbot.log

# Linux/Mac:
tail -f logs/korbot.log

# آخر 100 سطر:
tail -n 100 logs/korbot.log
```

### ب) قاعدة البيانات

```bash
# فتح قاعدة البيانات
sqlite3 data/historical.sqlite

# استعلامات مفيدة:
```

```sql
-- إجمالي الصفقات
SELECT COUNT(*) FROM trades;

-- Win rate
SELECT 
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
FROM trades
WHERE status = 'closed';

-- أفضل استراتيجية
SELECT strategy, COUNT(*) as trades, AVG(pnl) as avg_pnl
FROM trades
WHERE status = 'closed'
GROUP BY strategy
ORDER BY avg_pnl DESC;

-- الخروج
.quit
```

### ج) التحليل البصري

استخدم Dashboard:
- علامة تبويب "📈 الأداء": منحنى القيمة
- علامة تبويب "📊 الإحصائيات": جداول تفصيلية
- علامة تبويب "💼 الصفقات": سجل كامل

---

## 1️⃣1️⃣ الانتقال للتداول الحقيقي

### ⚠️ شروط صارمة:

**لا تنتقل للحساب الحقيقي قبل:**

1. ✅ **3 أشهر في Paper Mode على الأقل**
2. ✅ **Win Rate مستقر >65%**
3. ✅ **Drawdown <8%**
4. ✅ **500+ صفقة ناجحة**
5. ✅ **فهم كامل للبوت**
6. ✅ **خطة إدارة مخاطر واضحة**

### الخطوة 1: فتح حساب حقيقي صغير

1. **افتح حساب مع وسيط موثوق:**
   - XM
   - Pepperstone
   - IC Markets
   - FXCM
   - (وسطاء آخرون مرخصون)

2. **إيداع صغير:**
   - **الحد الأدنى:** 25$ (وضع أمان فقط)
   - **موصى به:** 100-200$ (وضع متوازن)
   - **لا تبدأ بأكثر من 500$!**

3. **احفظ بيانات الحساب الحقيقي**

### الخطوة 2: تحديث الإعدادات

#### أ) تحديث .env:

```bash
# MT5 - بيانات الحساب الحقيقي
MT5_LOGIN=98765432              # ← حساب حقيقي
MT5_PASSWORD=RealPassword        # ← كلمة مرور حقيقية
MT5_SERVER=BrokerName-Live       # ← خادم حقيقي

# تغيير الوضع
TRADING_MODE=live                # ← احذر! حقيقي الآن!
```

#### ب) تحديث config.yaml:

```yaml
trading:
  mode: "live"  # ← احذر!

risk:
  base_risk_percent: 0.3  # ← ابدأ بـ 0.3% فقط!
  max_positions: 1        # ← صفقة واحدة فقط!
  
  circuit_breaker:
    enabled: true         # ← مهم جداً!
    max_consecutive_losses: 2  # ← احذر!
```

### الخطوة 3: التشغيل الحذر

```bash
# شغّل Dashboard
python dashboard.py
```

1. **اختر "🛡️ وضع الأمان"**
2. **اضبط Risk على 0.3%**
3. **Max Positions: 1**
4. **Min Confidence: 80%**
5. **راقب كل دقيقة!**

### الخطوة 4: المراقبة المكثفة

**أول أسبوع:**
- راقب 24/7 (أو قدر المستطاع)
- لا تترك البوت يعمل وأنت نائم
- تحقق من كل صفقة يدوياً
- توقف فوراً عند أي مشكلة

**أول شهر:**
- راقب يومياً
- راجع الصفقات الأسبوعية
- اضبط الإعدادات حسب الأداء

**بعد 3 أشهر:**
- إذا كانت النتائج إيجابية:
  - يمكنك زيادة Risk تدريجياً
  - يمكنك زيادة Max Positions
  - يمكنك الانتقال لوضع متوازن

### الخطوة 5: توسيع نطاق التداول (بحذر)

**عند وصول الحساب لـ 200$:**
```yaml
risk:
  base_risk_percent: 0.5  # زد بحذر
  max_positions: 2
```

**عند وصول الحساب لـ 500$:**
```yaml
risk:
  base_risk_percent: 0.8  # وضع متوازن
  max_positions: 2
```

**عند وصول الحساب لـ 1000$+:**
```yaml
risk:
  base_risk_percent: 1.0  # يمكنك الآن المخاطرة أكثر
  max_positions: 3
```

---

## 1️⃣2️⃣ حل المشاكل

### مشكلة: MT5 لا يتصل

**الحلول:**
```bash
# 1. تحقق من MT5 مفتوح
# 2. تحقق من الاتصال بالإنترنت
# 3. تحقق من بيانات الدخول في .env

# اختبار:
python
>>> import MetaTrader5 as mt5
>>> mt5.initialize()
>>> mt5.last_error()  # شاهد الخطأ
```

**أخطاء شائعة:**
- `-2`: بيانات دخول خاطئة
- `-10005`: MT5 غير مفتوح
- `None`: مشكلة في المكتبة

### مشكلة: Redis error

```bash
# تحقق من تشغيل Redis
# Windows:
tasklist | findstr redis

# Linux:
systemctl status redis

# إعادة تشغيل Redis
# Windows: أعد تشغيل خدمة Redis من Services
# Linux:
sudo systemctl restart redis
```

### مشكلة: Telegram لا يرسل

```python
# اختبار يدوي
from telegram import Bot

TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

try:
    bot = Bot(token=TOKEN)
    bot.send_message(chat_id=CHAT_ID, text="Test")
    print("✅ نجح!")
except Exception as e:
    print(f"❌ فشل: {e}")
```

### مشكلة: ModuleNotFoundError

```bash
# تأكد من البيئة الافتراضية مفعلة
# يجب أن ترى (venv) في السطر

# أعد تثبيت المكتبة المفقودة
pip install [اسم المكتبة]

# أو أعد تثبيت الكل
pip install -r requirements.txt
```

### مشكلة: البوت لا يفتح صفقات

**تحقق من:**
1. الوضع paper أو live؟
2. الاستراتيجيات مفعلة؟
3. Confidence threshold معقول؟
4. Market regime مناسب؟
5. هل هناك إشارات أصلاً؟

```bash
# اختبار توليد الإشارات
python strategy_engine.py
```

### مشكلة: Win rate منخفض

**الحلول:**
1. زد min_confidence إلى 0.75 أو 0.80
2. قلّل عدد الصفقات (focus على الجودة)
3. عطّل الاستراتيجيات الضعيفة
4. اختبر على رموز مختلفة

### مشكلة: Dashboard لا يفتح

```bash
# تحقق من PyQt6
pip install PyQt6 pyqtgraph --upgrade

# جرّب بدون GUI
python main.py
```

---

## 📝 Checklist النهائي

قبل التشغيل، تأكد:

### الإعداد الأولي:
- [ ] Python 3.10+ مثبت
- [ ] البيئة الافتراضية منشأة ومفعلة
- [ ] جميع المكتبات من requirements.txt مثبتة
- [ ] MT5 مثبت ومتصل
- [ ] Redis يعمل
- [ ] Telegram bot جاهز

### الإعدادات:
- [ ] ملف .env معبأ بالبيانات الصحيحة
- [ ] TRADING_MODE=paper (للبداية!)
- [ ] config.yaml مراجع
- [ ] Risk settings معقولة

### الاختبارات:
- [ ] config_loader.py يعمل
- [ ] data_layer.py يتصل بـ MT5
- [ ] databases.py يحفظ البيانات
- [ ] telegram_notify.py يرسل رسائل
- [ ] pytest tests/ يمر (معظم الاختبارات)

### قبل التشغيل الحقيقي:
- [ ] 3+ أشهر Paper Mode ناجح
- [ ] Win rate >65%
- [ ] Drawdown <8%
- [ ] 500+ صفقة paper ناجحة
- [ ] فهم كامل للبوت
- [ ] حساب حقيقي صغير (25-100$)
- [ ] وضع أمان مفعل
- [ ] Risk 0.3% فقط

---

## 🎊 تهانينا!

إذا وصلت هنا ونجحت في جميع الخطوات:

✅ **أنت جاهز الآن!**

**الخطوة التالية:**
1. شغّل في Paper Mode
2. راقب لمدة 3 أشهر
3. حلل النتائج
4. اضبط الإعدادات
5. عندما تكون جاهزاً... انتقل للحقيقي!

---

## 📞 الدعم

إذا واجهت مشاكل:
1. راجع قسم [حل المشاكل](#حل-المشاكل)
2. اقرأ API_DOCUMENTATION.md
3. شغّل `pytest tests/` لاكتشاف المشاكل
4. تحقق من logs/korbot.log

---

## ⚠️ تحذيرات أخيرة

1. **لا تتعجل** - خذ وقتك في Paper Mode
2. **ابدأ صغيراً** - 25-100$ فقط
3. **راقب دائماً** - لا تترك البوت دون مراقبة
4. **توقف عند الخسارة** - Circuit Breaker موجود لحمايتك
5. **تعلم باستمرار** - افهم كل إشارة وصفقة

---

<div align="center">

# 🤖 KorBot X Enhanced

**من الصفر إلى أول صفقة حقيقية! 🚀**

**Good luck and happy trading! 💰📈**

</div>
