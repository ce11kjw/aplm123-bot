#!/usr/bin/env python3
"""自研 TikTok 解析下载器（直连官方网页 __UNIVERSAL_DATA，无第三方依赖）。
- 视频：解析 bitrateInfo，选最高码率档（带 cookie 可解锁真 HD）
- 图集：解析 imagePost.images
- 无水印，直连 TikTok CDN
"""
import os, re, json, shutil, requests

COOKIE_FILE = "/root/aplm123-bot/cookies.txt"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
H = {"User-Agent": UA, "Referer": "https://www.tiktok.com/",
     "Accept-Language": "en-US,en;q=0.9"}


def _load_cookies():
    ck = {}
    if not os.path.exists(COOKIE_FILE):
        return ck
    try:
        for line in open(COOKIE_FILE):
            if line.startswith("#") or "\t" not in line:
                continue
            p = line.strip().split("\t")
            if len(p) == 7:
                ck[p[5]] = p[6]
    except Exception:
        pass
    return ck


def _find(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                return v
            r = _find(v, key)
            if r is not None:
                return r
    elif isinstance(o, list):
        for it in o:
            r = _find(it, key)
            if r is not None:
                return r
    return None


def _fetch_item(url, sess):
    r = sess.get(url, headers=H, allow_redirects=True, timeout=20)
    html = r.text
    m = re.search(
        r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        html, re.S)
    if not m:
        m = re.search(r'<script id="SIGI_STATE"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None, ""
    try:
        data = json.loads(m.group(1))
    except Exception:
        return None, ""
    item = _find(data, "itemStruct")
    if item is None:
        info = _find(data, "itemInfo")
        if isinstance(info, dict):
            item = info.get("itemStruct")
    title = item.get("desc", "") if isinstance(item, dict) else ""
    return item, title


def _download(url, path, sess):
    tmp = path + ".part"
    try:
        r = sess.get(url, headers=H, stream=True, timeout=120)
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        with open(tmp, "rb") as f:
            head = f.read(64).lower()
        if head.startswith((b"<!doctype", b"<html")) or os.path.getsize(tmp) == 0:
            os.remove(tmp)
            return False
        os.replace(tmp, path)
        return True
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False


def _gallery_images(url, dl_dir, fn):
    """图集回退：gallery-dl 带 cookie 下图（网页数据无 imagePost 时用）。"""
    import subprocess
    img_dir = os.path.join(dl_dir, fn + "_imgs")
    os.makedirs(img_dir, exist_ok=True)
    cmd = ["gallery-dl", "-D", img_dir]
    if os.path.exists(COOKIE_FILE):
        cmd += ["--cookies", COOKIE_FILE]
    cmd.append(url)
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception:
        pass
    imgs = []
    for root, _, files in os.walk(img_dir):
        for f in sorted(files):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                imgs.append(os.path.join(root, f))
    if imgs:
        return {"success": True, "paths": imgs, "type": "image", "img_dir": img_dir}
    shutil.rmtree(img_dir, ignore_errors=True)
    return None


def download(url, dl_dir, fn):
    """
    返回 dict 或 None。
    视频: {"success":True,"paths":[mp4],"type":"video","title":...}
    图集: {"success":True,"paths":[jpg...],"type":"image","img_dir":...,"title":...}
    非 TikTok / 失败: None
    """
    u = (url or "").lower()
    if "tiktok.com" not in u:
        return None

    sess = requests.Session()
    ck = _load_cookies()
    if ck:
        sess.cookies.update(ck)

    try:
        item, title = _fetch_item(url, sess)
    except Exception:
        item, title = None, ""
    # 网页无 itemStruct（多为图集页）→ 直接走 gallery-dl 图集
    if not item or not isinstance(item, dict):
        return _gallery_images(url, dl_dir, fn)

    # 图集：网页数据里 imagePost 若有则直接用，否则回退 gallery-dl
    image_post = item.get("imagePost") or {}
    images = image_post.get("images") or []
    if images:
        img_dir = os.path.join(dl_dir, fn + "_imgs")
        os.makedirs(img_dir, exist_ok=True)
        paths = []
        for i, img in enumerate(images):
            ul = (img.get("imageURL", {}) or {}).get("urlList", []) or []
            if not ul:
                continue
            p = os.path.join(img_dir, f"{i+1:02d}.jpg")
            if _download(ul[0], p, sess):
                paths.append(p)
        if paths:
            return {"success": True, "paths": paths, "type": "image",
                    "img_dir": img_dir, "title": title}
        shutil.rmtree(img_dir, ignore_errors=True)
        return None

    # 视频：从 bitrateInfo 选最高码率（DataSize 最大）
    video = item.get("video") or {}
    candidates = []
    for b in (video.get("bitrateInfo") or []):
        pa = b.get("PlayAddr", {}) or {}
        urls = pa.get("UrlList", []) or []
        try:
            size = int(pa.get("DataSize", 0) or 0)
        except (ValueError, TypeError):
            size = 0
        if urls:
            candidates.append((size, urls))
    for key in ("playAddr", "downloadAddr"):
        v = video.get(key)
        if isinstance(v, str) and v:
            candidates.append((0, [v]))

    if not candidates:
        # 既非可解析视频，也无 imagePost → 最后试 gallery-dl（可能是图集）
        return _gallery_images(url, dl_dir, fn)
    candidates.sort(key=lambda x: x[0], reverse=True)

    fp = os.path.join(dl_dir, fn + ".mp4")
    for _, urls in candidates:
        for vurl in urls:
            if _download(vurl, fp, sess):
                return {"success": True, "paths": [fp], "type": "video",
                        "title": title}
    return None
