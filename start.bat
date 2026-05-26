@echo off
chcp 65001 >nul
title VidFetch Pro
color 0A
echo.
echo  ╔══════════════════════════════════════╗
echo  ║       VidFetch Pro — جاهز للتشغيل      ║
echo  ╚══════════════════════════════════════╝
echo.

:: التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python غير مثبت. حمّله من: https://python.org
    pause
    exit
)

:: تثبيت المتطلبات
echo  [*] جارٍ التحقق من المتطلبات...
pip install -r requirements.txt -q

:: التحقق من FFmpeg (للدمج)
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo  [!] تحذير: FFmpeg غير مثبت - دمج الصوت والصورة لن يعمل
    echo  [!] حمّله من: https://ffmpeg.org/download.html
    echo.
)

echo  [✓] جارٍ تشغيل السيرفر...
echo  [✓] افتح المتصفح على: http://localhost:5000
echo  [✓] من أجهزة أخرى على الشبكة: http://YOUR_IP:5000
echo.
python server.py
pause
