#!/bin/bash
clear
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║       VidFetch Pro — جاهز للتشغيل      ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# التحقق من Python
if ! command -v python3 &> /dev/null; then
    echo "  [!] Python3 غير مثبت"
    echo "      macOS:  brew install python3"
    echo "      Ubuntu: sudo apt install python3 python3-pip"
    exit 1
fi

# تثبيت المتطلبات
echo "  [*] جارٍ التحقق من المتطلبات..."
pip3 install -r requirements.txt -q 2>/dev/null || pip install -r requirements.txt -q

# التحقق من FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "  [!] تحذير: FFmpeg غير مثبت — دمج الصوت والصورة لن يعمل"
    echo "      macOS:  brew install ffmpeg"
    echo "      Ubuntu: sudo apt install ffmpeg"
    echo ""
fi

# جلب IP المحلي
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0 2>/dev/null)

echo "  [✓] جارٍ تشغيل السيرفر..."
echo "  [✓] محلي:   http://localhost:5000"
if [ ! -z "$LOCAL_IP" ]; then
    echo "  [✓] شبكة:   http://$LOCAL_IP:5000"
fi
echo ""

python3 server.py
