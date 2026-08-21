#!/usr/bin/env python3
"""统一下载实现（同步）。bot.py 用 asyncio.to_thread 包装调用。"""
import os, subprocess, shutil
from video_parser import parse as parse_video, download as dl_video, detect as detect_platform

DL_DIR = os.getenv("DL_DIR", "/root/aplm123-bot/downloads")
os.makedirs(DL_DIR, exist_ok=True)

VIDEO_EXT = (".mp4", ".webm", ".mkv", ".mov")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def ensure_h264(fp):
    """HEVC/VP9 转 H264，保持原画质不压缩。"""
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-select_streams", "v:0",
                            "-show_entries", "stream=codec_name", "-of", "csv=p=0", fp],
                           capture_output=True, text=True, timeout=15)
        if r.stdout.strip() in ("h264", "avc1"):
            return fp
        new_fp = fp + ".h264.mp4"
        subprocess.run(["ffmpeg", "-y", "-i", fp, "-c:v", "libx264", "-preset", "fast",
                        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy",
                        "-movflags", "+faststart", new_fp],
                       capture_output=True, text=True, timeout=600)
        if os.path.exists(new_fp) and os.path.getsize(new_fp) > 0:
            os.remove(fp)
            return new_fp
    except Exception:
        pass
    return fp


def download(url, uid):
    fn = str(uid) + "_" + os.urandom(4).hex()

    # 1. 国内平台直链解析
    if detect_platform(url):
        result = parse_video(url)
        if result.get("success"):
            fp = os.path.join(DL_DIR, fn + ".mp4")
            if dl_video(result["url"], fp, result.get("referer")):
                return {"success": True, "paths": [fp], "type": "video",
                        "title": result.get("title", "")}

    # 2. yt-dlp（TikTok 图集 /photo/ 跳过，交给 gallery-dl）
    u = (url or "").lower()
    is_tt_photo = "tiktok.com" in u and "/photo/" in u
    if not is_tt_photo:
        out = os.path.join(DL_DIR, fn + ".%(ext)s")
        try:
            r = subprocess.run(["yt-dlp", "--no-warnings", "-S", "vcodec:h264,res",
                                "-f", "b[ext=mp4]/b", "--no-playlist", "-o", out, url],
                               capture_output=True, text=True, timeout=180)
            if r.returncode == 0:
                for f in os.listdir(DL_DIR):
                    if f.startswith(fn + "."):
                        fp = os.path.join(DL_DIR, f)
                        ft = "video" if os.path.splitext(f)[1].lower() in VIDEO_EXT else "image"
                        if ft == "video":
                            fp = ensure_h264(fp)
                        return {"success": True, "paths": [fp], "type": ft}
        except Exception:
            pass

    # 3. gallery-dl（图片/图集）
    img_dir = os.path.join(DL_DIR, fn + "_imgs")
    os.makedirs(img_dir, exist_ok=True)
    try:
        subprocess.run(["gallery-dl", "-D", img_dir, url],
                       capture_output=True, text=True, timeout=120)
        imgs = []
        for root, _, files in os.walk(img_dir):
            for f in sorted(files):
                if f.lower().endswith(IMAGE_EXT):
                    imgs.append(os.path.join(root, f))
        if imgs:
            return {"success": True, "paths": imgs, "type": "image", "img_dir": img_dir}
    except Exception:
        pass
    shutil.rmtree(img_dir, ignore_errors=True)
    return {"success": False, "error": "下载失败"}
