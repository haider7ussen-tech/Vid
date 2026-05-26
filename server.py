"""
VidFetch Pro — Backend Server
تشغيل: python server.py
يعمل على: http://localhost:5000  أو  http://YOUR_IP:5000
"""

import os
import re
import json
import uuid
import threading
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS

try:
    import yt_dlp
except ImportError:
    print("❌ yt-dlp غير مثبت. شغّل: pip install yt-dlp")
    exit(1)

# ─── إعداد التطبيق ───────────────────────────────────────
app = Flask(__name__, static_folder="static")
CORS(app)

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# قاموس لتتبع حالة كل تحميل
downloads = {}   # { job_id: { status, progress, speed, eta, title, filepath, error } }

# ─── صفحة الواجهة ────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# ─── تحليل الرابط وجلب المعلومات ─────────────────────────
@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    url  = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "الرابط فارغ"}), 400

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extractor_args": {"youtube": {"skip": ["dash", "hls"]}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # بناء قائمة الصيغ
    formats_raw = info.get("formats", [])
    seen = set()
    formats = []

    # صيغ الفيديو بترتيب تنازلي
    for f in sorted(formats_raw, key=lambda x: (x.get("height") or 0), reverse=True):
        height = f.get("height")
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        if not height or vcodec == "none":
            continue
        label = f"{height}p"
        if label in seen:
            continue
        seen.add(label)
        size_bytes = f.get("filesize") or f.get("filesize_approx") or 0
        formats.append({
            "id":      f["format_id"],
            "quality": label,
            "height":  height,
            "type":    "video",
            "codec":   vcodec.split(".")[0].upper(),
            "fps":     f.get("fps"),
            "size":    _fmt_size(size_bytes),
            "size_bytes": size_bytes,
            "ext":     f.get("ext", "mp4"),
            "badge":   _quality_badge(height),
        })

    # صيغ الصوت
    for f in sorted(formats_raw, key=lambda x: x.get("abr") or 0, reverse=True):
        acodec = f.get("acodec", "none")
        vcodec = f.get("vcodec", "none")
        if acodec == "none" or vcodec != "none":
            continue
        abr = int(f.get("abr") or 0)
        label = f"audio_{abr}"
        if label in seen or abr == 0:
            continue
        seen.add(label)
        size_bytes = f.get("filesize") or f.get("filesize_approx") or 0
        formats.append({
            "id":      f["format_id"],
            "quality": f"MP3 {abr}k" if abr else "MP3",
            "type":    "audio",
            "codec":   acodec.upper(),
            "fps":     None,
            "size":    _fmt_size(size_bytes),
            "size_bytes": size_bytes,
            "ext":     "mp3",
            "badge":   None,
        })

    # إذا لم تُعثر على صيغ نضع خياراً افتراضياً
    if not formats:
        formats = [{"id":"bestvideo+bestaudio/best","quality":"أفضل جودة","type":"video","codec":"AUTO","fps":None,"size":"—","badge":"AUTO","ext":"mp4"}]

    thumbnail = info.get("thumbnail") or ""
    # نحاول الحصول على مصغرة أوضح (YouTube)
    thumbs = info.get("thumbnails") or []
    for t in reversed(thumbs):
        if t.get("width", 0) >= 640:
            thumbnail = t["url"]
            break

    return jsonify({
        "title":     info.get("title", "بدون عنوان"),
        "uploader":  info.get("uploader") or info.get("channel") or "—",
        "duration":  _fmt_duration(info.get("duration")),
        "view_count":_fmt_views(info.get("view_count")),
        "thumbnail": thumbnail,
        "platform":  _detect_platform(url),
        "formats":   formats,
    })

# ─── بدء التحميل ──────────────────────────────────────────
@app.route("/api/download", methods=["POST"])
def start_download():
    data      = request.get_json(force=True)
    url       = (data.get("url") or "").strip()
    fmt_id    = data.get("format_id", "bestvideo+bestaudio/best")
    merge_av  = data.get("merge_av", True)
    job_id    = str(uuid.uuid4())

    if not url:
        return jsonify({"error": "الرابط فارغ"}), 400

    downloads[job_id] = {
        "status": "waiting", "progress": 0, "speed": "—",
        "eta": "—", "title": "جارٍ التحميل…", "filepath": None,
        "error": None, "phase": "video", "merge_av": merge_av,
    }

    thread = threading.Thread(target=_do_download, args=(job_id, url, fmt_id, merge_av), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})

# ─── حالة التحميل (polling) ───────────────────────────────
@app.route("/api/status/<job_id>")
def job_status(job_id):
    job = downloads.get(job_id)
    if not job:
        return jsonify({"error": "لا يوجد تحميل بهذا المعرف"}), 404
    return jsonify(job)

# ─── SSE: بث حالة التحميل ─────────────────────────────────
@app.route("/api/stream/<job_id>")
def stream_status(job_id):
    def generate():
        while True:
            job = downloads.get(job_id)
            if not job:
                yield f"data: {json.dumps({'error':'not found'})}\n\n"
                break
            yield f"data: {json.dumps(job)}\n\n"
            if job["status"] in ("done", "error"):
                break
            time.sleep(0.5)
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ─── تحميل الملف ──────────────────────────────────────────
@app.route("/api/file/<job_id>")
def serve_file(job_id):
    job = downloads.get(job_id)
    if not job or not job.get("filepath"):
        return jsonify({"error": "الملف غير جاهز"}), 404
    fp = Path(job["filepath"])
    if not fp.exists():
        return jsonify({"error": "الملف غير موجود على الخادم"}), 404
    return send_file(fp, as_attachment=True, download_name=fp.name)

# ─── قائمة التحميلات ──────────────────────────────────────
@app.route("/api/downloads")
def list_downloads():
    return jsonify({jid: {k:v for k,v in job.items() if k != "filepath"}
                    for jid, job in downloads.items()})

# ─── حذف تحميل ────────────────────────────────────────────
@app.route("/api/delete/<job_id>", methods=["DELETE"])
def delete_job(job_id):
    job = downloads.pop(job_id, None)
    if job and job.get("filepath"):
        try: Path(job["filepath"]).unlink(missing_ok=True)
        except: pass
    return jsonify({"ok": True})

# ═══════════════════════════════════════════════════════════
# منطق التحميل الداخلي
# ═══════════════════════════════════════════════════════════
def _do_download(job_id, url, fmt_id, merge_av):
    job = downloads[job_id]
    job["status"] = "downloading"

    out_tmpl = str(DOWNLOAD_DIR / "%(title).80s [%(id)s].%(ext)s")

    def progress_hook(d):
        if d["status"] == "downloading":
            job["status"]   = "downloading"
            job["progress"] = _parse_percent(d.get("_percent_str", "0%"))
            job["speed"]    = d.get("_speed_str", "—").strip()
            job["eta"]      = d.get("_eta_str", "—").strip()
            job["title"]    = d.get("info_dict", {}).get("title", job["title"])
        elif d["status"] == "finished":
            job["phase"]    = "merging" if merge_av else "done"
            job["status"]   = "merging" if merge_av else "done"
            job["progress"] = 99 if merge_av else 100
            job["filepath"] = d.get("filename") or d.get("info_dict", {}).get("_filename")
        elif d["status"] == "error":
            job["status"] = "error"
            job["error"]  = str(d.get("error", "خطأ غير معروف"))

    ydl_opts = {
        "format": fmt_id if not merge_av else f"{fmt_id}+bestaudio/bestvideo+bestaudio/best",
        "outtmpl": out_tmpl,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    if merge_av:
        ydl_opts["merge_output_format"] = "mp4"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            # الحصول على مسار الملف النهائي
            if not job.get("filepath"):
                job["filepath"] = ydl.prepare_filename(info)
            job["status"]   = "done"
            job["progress"] = 100
            job["title"]    = info.get("title", job["title"])
    except Exception as e:
        job["status"] = "error"
        job["error"]  = str(e)

# ═══════════════════════════════════════════════════════════
# دوال مساعدة
# ═══════════════════════════════════════════════════════════
def _fmt_size(b):
    if not b: return "—"
    for unit in ("B","KB","MB","GB"):
        if b < 1024: return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

def _fmt_duration(secs):
    if not secs: return "—"
    h, r = divmod(int(secs), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def _fmt_views(n):
    if not n: return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M مشاهدة"
    if n >= 1_000:     return f"{n/1_000:.0f}K مشاهدة"
    return f"{n} مشاهدة"

def _detect_platform(url):
    u = url.lower()
    if "youtube" in u or "youtu.be" in u: return "YouTube"
    if "facebook" in u or "fb.watch"  in u: return "Facebook"
    if "tiktok"   in u: return "TikTok"
    if "twitter"  in u or "x.com"     in u: return "X (Twitter)"
    if "instagram"in u: return "Instagram"
    return "Other"

def _quality_badge(height):
    if height >= 2160: return "4K"
    if height >= 1440: return "2K"
    if height >= 1080: return "FHD"
    return None

def _parse_percent(s):
    try: return float(re.sub(r"[^\d.]", "", s))
    except: return 0

# ─── تشغيل السيرفر ───────────────────────────────────────
if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    try: local_ip = socket.gethostbyname(hostname)
    except: local_ip = "127.0.0.1"

    print("\n" + "═"*55)
    print("  🎬  VidFetch Pro — جاهز للاستخدام")
    print("═"*55)
    print(f"  🖥  محلي:    http://localhost:5000")
    print(f"  🌐  شبكة:    http://{local_ip}:5000")
    print("  📱  افتح الرابط من أي جهاز على نفس الشبكة")
    print("═"*55 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
