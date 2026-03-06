# ⚡ دليل البدء السريع - KorBot X Enhanced

**للذين يريدون البدء بسرعة! 🚀**

---

## 📌 الخطوات الأساسية (30 دقيقة)

### 1️⃣ تثبيت Python (5 دقائق)

```bash
# تنزيل Python 3.10+ من:
https://www.python.org/downloads/

# ✅ مهم: فعّل "Add Python to PATH" أثناء التثبيت!

# اختبار:
python --version
pip --version
```

---

### 2️⃣ إعداد المشروع (5 دقائق)

```bash
# إنشاء مجلد
mkdir C:\KorBot
cd C:\KorBot

# ضع جميع الملفات هنا (27 ملف)
# الهيكل:
KorBot-X-Enhanced/
├── config/
├── src/
├── tests/
├── .env.example
├── requirements.txt
└── ...
```

---

### 3️⃣ تثبيت المكتبات (10 دقائق)

```bash
cd KorBot-X-Enhanced

# إنشاء البيئة الافتراضية
python -m venv venv

# تفعيلها
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# تثبيت المكتبات
pip install --upgrade pip
pip install -r requirements.txt

# ⏱️ انتظر 5-10 دقائق...
```

---

### 4️⃣ تثبيت MT5 (5 دقائق)

```bash
# 1. تنزيل من:
https://www.metatrader5.com/en/download

# 2. تثبيت

# 3. افتح حساب Demo:
File → Open an Account → Demo
الرصيد: 10,000$

# 4. احفظ:
Login: xxxxx
Password: xxxxx
Server: BrokerName-Demo
```

---

### 5️⃣ تثبيت Redis (5 دقائق)

**Windows:**
```bash
# تنزيل من:
https://github.com/microsoftarchive/redis/releases
# اختر: Redis-x64-3.0.504.msi
# ثبّت وشغّل

# اختبار:
redis-cli ping
# يجب أن يظهر: PONG
```

**Linux:**
```bash
sudo apt install redis-server
sudo systemctl start redis
redis-cli ping
```

---

### 6️⃣ إعداد Telegram Bot (5 دقائق)

```bash
# 1. في Telegram ابحث عن: @BotFather
# 2. أرسل: /newbot
# 3. اتبع التعليمات
# 4. احفظ الـ TOKEN

# 5. للحصول على Chat ID:
# ابحث عن: @userinfobot
# ابدأ محادثة
# احفظ Chat ID
```

---

### 7️⃣ إعداد .env (2 دقيقة)

```bash
# نسخ الملف
copy .env.example .env

# تحرير:
notepad .env
```

```bash
# املأ:
MT5_LOGIN=12345678
MT5_PASSWORD=YourPassword
MT5_SERVER=BrokerName-Demo

TELEGRAM_TOKEN=123456:ABCdef...
TELEGRAM_CHAT_ID=987654321

TRADING_MODE=paper  # ← مهم جداً!
```

---

### 8️⃣ اختبار سريع (3 دقائق)

```bash
cd src/python_controller

# اختبار MT5
python data_layer.py

# اختبار Telegram  
python telegram_notify.py

# اختبار الإعدادات
python config_loader.py
```

✅ **إذا عمل كل شيء → جاهز للتشغيل!**

---

### 9️⃣ التشغيل! (الآن)

```bash
# طريقة 1: مع GUI (موصى به)
python dashboard.py

# اختر "🛡️ وضع الأمان"
# اضغط "▶️ تشغيل"

# طريقة 2: بدون GUI
python main.py
```

---

## 🎯 أول يوم: ماذا تتوقع؟

### في أول ساعة:
- البوت يحلل السوق
- قد يفتح صفقة أو لا (عادي)
- ستصلك إشعارات Telegram

### في أول يوم:
- 0-3 صفقات (وضع أمان)
- P/L: $-50 إلى $+100 (paper money)
- راقب Dashboard

### في أول أسبوع:
- 5-15 صفقة
- Win rate: 50-70%
- تعلم كيف يعمل

---

## ⚠️ قواعد ذهبية

### ✅ افعل:
1. **ابدأ بـ Paper Mode** (3 أشهر!)
2. **راقب يومياً**
3. **احفظ نسخة احتياطية من .env**
4. **اقرأ السجلات logs/**
5. **اصبر!**

### ❌ لا تفعل:
1. **لا تشغّل على حساب حقيقي فوراً!**
2. **لا تزد المخاطرة قبل 3 أشهر**
3. **لا تترك البوت دون مراقبة**
4. **لا تتجاهل Circuit Breaker**
5. **لا تستثمر أكثر مما تستطيع خسارته**

---

## 🔧 حل سريع للمشاكل

### مشكلة: MT5 لا يتصل
```bash
# تحقق:
1. MT5 مفتوح؟
2. بيانات الدخول صحيحة في .env؟
3. الإنترنت متصل؟

# الحل:
python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.last_error())"
```

### مشكلة: Redis error
```bash
# Windows: 
# ابحث في Services عن Redis
# أعد تشغيله

# Linux:
sudo systemctl restart redis
```

### مشكلة: ModuleNotFoundError
```bash
# تأكد من البيئة مفعلة (يجب أن ترى venv)
# أعد تثبيت:
pip install -r requirements.txt
```

---

## 📊 النتائج المتوقعة

### بعد أسبوع Paper:
- Total Trades: 10-20
- Win Rate: 55-65%
- Max Drawdown: 3-8%

### بعد شهر Paper:
- Total Trades: 50-100
- Win Rate: 60-70%
- Max Drawdown: 3-6%

### بعد 3 أشهر Paper:
- **إذا كانت النتائج جيدة:**
  - Win Rate: 65%+
  - Drawdown: <8%
  - **→ يمكنك الانتقال للحقيقي!**

---

## 🚀 الانتقال للحقيقي (بعد 3 أشهر)

### الخطوات:
1. **افتح حساب حقيقي صغير** (25-100$)
2. **غيّر في .env:**
   ```bash
   MT5_LOGIN=حساب_حقيقي
   MT5_PASSWORD=كلمة_مرور_حقيقية
   MT5_SERVER=BrokerName-Live
   TRADING_MODE=live  # احذر!
   ```
3. **خفّض المخاطرة:**
   ```yaml
   # في config.yaml
   risk:
     base_risk_percent: 0.3  # ابدأ بـ 0.3% فقط!
   ```
4. **شغّل بوضع أمان**
5. **راقب كل دقيقة!**

---

## 💡 نصائح للنجاح

### للحسابات الصغيرة (25-100$):
- **الوضع:** 🛡️ أمان
- **Risk:** 0.3%
- **Positions:** 1
- **استراتيجيات:** Mean Reversion + Swing فقط

### للحسابات المتوسطة (100-500$):
- **الوضع:** ⚖️ متوازن
- **Risk:** 0.8%
- **Positions:** 2
- **استراتيجيات:** جميعها

### للحسابات الكبيرة (500$+):
- **الوضع:** 🚀 مخاطرة
- **Risk:** 1.5%
- **Positions:** 3
- **استراتيجيات:** جميعها + Aggressive

---

## 📞 الدعم

- راجع: **FULL_INSTALLATION_GUIDE.md** للتفاصيل الكاملة
- راجع: **API_DOCUMENTATION.md** للـ APIs
- راجع: **logs/korbot.log** للأخطاء
- شغّل: `pytest tests/` للاختبار

---

## ✅ Checklist البدء السريع

- [ ] Python 3.10+ مثبت
- [ ] المشروع منسوخ بالكامل
- [ ] البيئة الافتراضية منشأة
- [ ] المكتبات مثبتة
- [ ] MT5 متصل
- [ ] Redis يعمل
- [ ] Telegram bot جاهز
- [ ] ملف .env معبأ
- [ ] TRADING_MODE=paper
- [ ] الاختبارات تمر
- [ ] **جاهز للتشغيل!** 🚀

---

<div align="center">

# ⚡ KorBot X Enhanced

**من الصفر للتشغيل في 30 دقيقة!**

**Paper Mode → 3 أشهر → Live Trading!**

**Let's go! 🚀💰**

</div>
