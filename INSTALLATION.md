# 📦 دليل تثبيت KorBot X Enhanced

هذا الدليل يشرح كيفية تثبيت وإعداد KorBot X Enhanced خطوة بخطوة.

---

## 📋 المتطلبات الأساسية

### 1. النظام
- **نظام التشغيل:** Windows 10/11، Linux (Ubuntu 20.04+)، macOS
- **Python:** 3.10 أو أحدث
- **RAM:** 4 GB كحد أدنى (8 GB موصى به)
- **مساحة التخزين:** 2 GB

### 2. البرامج المطلوبة
- ✅ MetaTrader 5
- ✅ Redis Server
- ✅ Git (اختياري)

---

## 🚀 خطوات التثبيت

### الخطوة 1: تحميل المشروع

#### الطريقة 1: استخدام Git
```bash
git clone https://github.com/yourusername/KorBot-X-Enhanced.git
cd KorBot-X-Enhanced
```

#### الطريقة 2: تحميل ZIP
1. حمّل المشروع كملف ZIP
2. فك الضغط في المجلد المطلوب
3. افتح Terminal/CMD في مجلد المشروع

---

### الخطوة 2: إنشاء البيئة الافتراضية

```bash
# إنشاء البيئة الافتراضية
python -m venv venv

# تفعيل البيئة
# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate
```

---

### الخطوة 3: تثبيت المتطلبات

```bash
# تحديث pip
python -m pip install --upgrade pip

# تثبيت المكتبات
pip install -r requirements.txt
```

**ملاحظة:** إذا واجهت مشاكل في التثبيت، قم بتثبيت المكتبات واحدة تلو الأخرى:

```bash
pip install MetaTrader5
pip install redis pandas numpy
pip install ta scipy
pip install xgboost scikit-learn
pip install stable-baselines3 gymnasium
pip install PyQt6
pip install python-telegram-bot
pip install python-dotenv PyYAML
```

---

### الخطوة 4: تثبيت Redis

#### Windows:
1. حمّل Redis من: https://github.com/microsoftarchive/redis/releases
2. ثبّت Redis
3. شغّل Redis Server:
```bash
redis-server
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

#### macOS:
```bash
brew install redis
brew services start redis
```

**تحقق من التثبيت:**
```bash
redis-cli ping
# يجب أن تحصل على: PONG
```

---

### الخطوة 5: تثبيت MetaTrader 5

1. **حمّل MT5:**
   - Windows: https://www.metatrader5.com/en/download
   - Linux: استخدم Wine
   - macOS: استخدم Wine أو CrossOver

2. **افتح حساب Demo:**
   - افتح MT5
   - File → Open an Account
   - اختر وسيط
   - افتح حساب Demo

3. **حفظ بيانات الدخول:**
   - رقم الحساب (Login)
   - كلمة المرور (Password)
   - اسم الخادم (Server)

---

### الخطوة 6: إعداد Telegram Bot (اختياري)

1. **إنشاء Bot:**
   - ابحث عن `@BotFather` في Telegram
   - أرسل `/newbot`
   - اتبع التعليمات
   - احفظ الـ TOKEN

2. **الحصول على Chat ID:**
   - ابحث عن `@userinfobot`
   - ابدأ محادثة
   - احفظ Chat ID

---

### الخطوة 7: إعداد المتغيرات البيئية

1. **انسخ ملف المثال:**
```bash
cp .env.example .env
```

2. **حرر ملف .env:**
```bash
# Windows:
notepad .env

# Linux/macOS:
nano .env
```

3. **املأ البيانات:**
```bash
# MetaTrader 5
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Demo

# Telegram
TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# Trading Mode
TRADING_MODE=paper  # ابدأ بـ paper!

# Log Level
LOG_LEVEL=INFO
```

4. **احفظ الملف**

---

### الخطوة 8: تعديل الإعدادات (اختياري)

حرر `config/config.yaml` لتخصيص:
- الرمز (Symbol)
- المخاطر (Risk parameters)
- الاستراتيجيات (Strategies)

```yaml
# مثال: تغيير الرمز
trading:
  symbol: "EURUSD"  # غيّر من AUDCAD إلى EURUSD

# تقليل المخاطر
risk:
  base_risk_percent: 0.5  # كان 0.8
```

---

### الخطوة 9: اختبار التثبيت

```bash
# اختبر الاتصال بـ MT5
python -c "import MetaTrader5 as mt5; print('MT5 OK' if mt5.initialize() else 'MT5 Failed')"

# اختبر Redis
python -c "import redis; r = redis.Redis(); print('Redis OK' if r.ping() else 'Redis Failed')"

# اختبر الإعدادات
python src/python_controller/config_loader.py
```

---

## 🎯 التشغيل

### التشغيل الأساسي

```bash
# تفعيل البيئة الافتراضية
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# تشغيل البوت
python src/python_controller/main.py
```

### التشغيل مع GUI (قريباً)

```bash
python src/python_controller/dashboard.py
```

---

## 🧪 اختبار النظام

### 1. اختبار Data Layer
```bash
python src/python_controller/data_layer.py
```

### 2. اختبار الاستراتيجيات
```bash
python src/python_controller/strategy_engine.py
```

### 3. اختبار Backtesting
```bash
python src/python_controller/backtester.py
```

### 4. اختبار Telegram
```bash
python src/python_controller/telegram_notify.py
```

---

## ❗ حل المشاكل الشائعة

### مشكلة 1: MT5 لا يتصل

**الحل:**
```bash
# تحقق من تشغيل MT5
# تحقق من بيانات الدخول في .env
# جرب الاتصال يدوياً من MT5
```

### مشكلة 2: Redis Error

**الحل:**
```bash
# تحقق من تشغيل Redis
redis-cli ping

# إعادة تشغيل Redis
# Windows:
redis-server
# Linux:
sudo systemctl restart redis
```

### مشكلة 3: ModuleNotFoundError

**الحل:**
```bash
# تحقق من تفعيل البيئة الافتراضية
# أعد تثبيت المكتبات
pip install -r requirements.txt
```

### مشكلة 4: Permission Denied

**الحل:**
```bash
# Linux/macOS:
chmod +x src/python_controller/main.py

# أو شغّل بـ sudo
sudo python src/python_controller/main.py
```

---

## 🔄 التحديثات

```bash
# سحب آخر التحديثات (إذا كنت تستخدم Git)
git pull origin main

# إعادة تثبيت المتطلبات
pip install -r requirements.txt --upgrade
```

---

## 📞 الدعم

إذا واجهت مشاكل:
1. راجع قسم حل المشاكل أعلاه
2. تحقق من ملفات الـ logs في `logs/`
3. افتح Issue في GitHub
4. اقرأ README.md للمزيد من المعلومات

---

## ✅ قائمة التحقق

قبل التشغيل، تأكد من:
- [ ] Python 3.10+ مثبت
- [ ] البيئة الافتراضية منشأة ومفعلة
- [ ] جميع المكتبات مثبتة
- [ ] Redis يعمل
- [ ] MT5 مثبت ومتصل
- [ ] ملف .env معبأ بالبيانات الصحيحة
- [ ] اختبرت الاتصالات الأساسية
- [ ] الوضع على "paper" للبداية

---

## 🎉 الخطوة التالية

بعد التثبيت الناجح:
1. اقرأ README.md الكامل
2. راجع config/config.yaml
3. شغّل في Paper Mode لمدة 3 أشهر
4. راقب الأداء والنتائج
5. اضبط المعاملات حسب الحاجة

**تهانينا! 🎊 KorBot X Enhanced جاهز الآن!**
