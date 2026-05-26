# VidFetch Pro 🎬

محمّل فيديو احترافي يعمل على أي جهاز في شبكتك المنزلية.

---

## 📋 المتطلبات

| البرنامج | الإصدار | الوصف |
|---------|---------|-------|
| Python  | 3.8+    | لتشغيل السيرفر |
| FFmpeg  | أي      | لدمج الصوت والصورة |

---

## 🚀 التثبيت والتشغيل

### Windows
```
1. نقر مزدوج على: start.bat
```

### macOS / Linux
```bash
chmod +x start.sh
./start.sh
```

### يدوياً (أي نظام)
```bash
pip install -r requirements.txt
python server.py
```

---

## 🌐 الوصول من أجهزة أخرى

بعد تشغيل السيرفر، افتح المتصفح على أي جهاز في نفس الشبكة:

```
http://YOUR_COMPUTER_IP:5000
```

مثال: `http://192.168.1.10:5000`

> عرض IP جهازك:
> - Windows: `ipconfig` في CMD
> - macOS/Linux: `ifconfig` أو `ip addr`

---

## ⚡ تثبيت FFmpeg

### Windows
1. حمّل من: https://ffmpeg.org/download.html
2. أضف مجلد `bin` إلى متغير البيئة PATH

أو عبر winget:
```
winget install ffmpeg
```

### macOS
```bash
brew install ffmpeg
```

### Ubuntu/Debian
```bash
sudo apt update && sudo apt install ffmpeg
```

---

## 📁 هيكل الملفات

```
vidfetch/
├── server.py          ← السيرفر الرئيسي
├── requirements.txt   ← متطلبات Python
├── start.bat          ← تشغيل Windows
├── start.sh           ← تشغيل Mac/Linux
├── static/
│   └── index.html     ← الواجهة
└── downloads/         ← ملفات محمّلة (تُنشأ تلقائياً)
```

---

## 🎯 المميزات

- ✅ تحميل من YouTube, Facebook, TikTok, X, Instagram وأكثر من 1000 موقع
- ✅ جودة تصل إلى 8K مع دمج الصوت والصورة تلقائياً
- ✅ تحميل متعدد في نفس الوقت
- ✅ شريط تقدم حي مع السرعة والوقت المتبقي
- ✅ يعمل على الشبكة المحلية من أي جهاز
- ✅ واجهة عربية كاملة وجميلة

---

## 🔧 إعدادات متقدمة

لتغيير منفذ السيرفر، عدّل آخر سطر في `server.py`:
```python
app.run(host="0.0.0.0", port=5000)  # غيّر 5000 لأي منفذ
```

لتغيير مجلد التحميل:
```python
DOWNLOAD_DIR = Path("downloads")  # غيّر لمجلد آخر
```
