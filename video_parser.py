#!/usr/bin/env python3
"""国内平台视频解析"""
import requests, re, json, os

H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"}

def resolve(url):
    try:
        r = requests.get(url, headers=H, allow_redirects=False, timeout=10)
        if r.status_code in [301,302,303,307,308]:
            return r.headers.get("Location", url)
        r = requests.get(url, headers=H, allow_redirects=True, timeout=10)
        return r.url
    except: return url

def detect(url):
    u = url.lower()
    if "douyin.com" in u: return "douyin"
    if "kuaishou.com" in u or "gifshow.com" in u: return "kuaishou"
    if "ixigua.com" in u or "toutiao.com" in u: return "xigua"
    if "xiaohongshu.com" in u or "xhslink.com" in u: return "xiaohongshu"
    if "weibo.cn" in u or "weibo.com" in u: return "weibo"
    if "pipix.com" in u: return "pipix"
    if "b23.tv" in u or "bilibili.com" in u: return "bilibili"
    return None

def parse_douyin(url):
    try:
        r = requests.get(url, headers=H, allow_redirects=True, timeout=10)
        m = re.search(r'/video/(\d+)', r.url) or re.search(r'/note/(\d+)', r.url)
        if not m: return {"success": False, "error": "ID not found"}
        vid = m.group(1)
        api = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={vid}"
        data = requests.get(api, headers=H, timeout=10).json()
        if "item_list" in data and data["item_list"]:
            item = data["item_list"][0]
            urls = item.get("video",{}).get("play_addr",{}).get("url_list",[])
            if urls:
                return {"success": True, "url": urls[0].replace("playwm","play"), "title": item.get("desc","")}
    except: pass
    return {"success": False, "error": "douyin failed"}

def parse_kuaishou(url):
    try:
        r = requests.get(url, headers=H, allow_redirects=True, timeout=10)
        m = re.search(r'/video/(\d+)', r.url) or re.search(r'/photo/(\d+)', r.url)
        if not m: return {"success": False, "error": "ID not found"}
        pid = m.group(1)
        api = f"https://m.gifshow.com/rest/n/photo/videoInfo2?photoId={pid}"
        data = requests.get(api, headers=H, timeout=10).json()
        if "photo" in data:
            p = data["photo"]
            return {"success": True, "url": p.get("mainMvUrl",""), "title": p.get("caption","")}
    except: pass
    return {"success": False, "error": "kuaishou failed"}

def parse_xigua(url):
    try:
        r = requests.get(url, headers=H, allow_redirects=True, timeout=10)
        m = re.search(r'/video/(\d+)', r.url)
        if not m: return {"success": False, "error": "ID not found"}
        vid = m.group(1)
        api = f"https://ib.365yg.com/api/news/feed/v88/?group_id={vid}&item_id={vid}"
        data = requests.get(api, headers=H, timeout=10).json()
        if "data" in data:
            for item in data["data"]:
                vl = item.get("video_list",{})
                if "720p" in vl:
                    return {"success": True, "url": vl["720p"].get("main_url",""), "title": item.get("title","")}
    except: pass
    return {"success": False, "error": "xigua failed"}

def parse_xiaohongshu(url):
    try:
        r = requests.get(url, headers=H, allow_redirects=True, timeout=10)
        m = re.search(r'/explore/([a-f0-9]+)', r.url) or re.search(r'/discovery/item/([a-f0-9]+)', r.url)
        if not m: return {"success": False, "error": "ID not found"}
        nid = m.group(1)
        r2 = requests.get(f"https://www.xiaohongshu.com/explore/{nid}", headers=H, timeout=10)
        vm = re.search(r'"og:video" content="(.*?)"', r2.text)
        if vm:
            title = "小红书"
            tm = re.search(r'"og:title" content="(.*?)"', r2.text)
            if tm: title = tm.group(1)
            return {"success": True, "url": vm.group(1), "title": title}
    except: pass
    return {"success": False, "error": "xiaohongshu failed"}

def parse_weibo(url):
    try:
        r = requests.get(url, headers=H, allow_redirects=True, timeout=10)
        m = re.search(r'/video/(\d+)', r.url) or re.search(r'mid=(\d+)', r.url)
        if not m: return {"success": False, "error": "ID not found"}
        vid = m.group(1)
        api = f"https://m.weibo.cn/statuses/show?id={vid}"
        data = requests.get(api, headers=H, timeout=10).json()
        if "data" in data:
            pi = data["data"].get("page_info",{})
            if pi.get("type") == "video":
                vu = pi.get("urls",{}).get("mp4_720p_mp4","") or pi.get("urls",{}).get("mp4_hd_mp4","")
                return {"success": True, "url": vu, "title": data["data"].get("text","")[:50]}
    except: pass
    return {"success": False, "error": "weibo failed"}

def parse_pipix(url):
    try:
        r = requests.get(url, headers=H, allow_redirects=True, timeout=10)
        m = re.search(r'/item/(\d+)', r.url)
        if not m: return {"success": False, "error": "ID not found"}
        iid = m.group(1)
        api = f"https://h5.pipix.com/bds/feed/item/{iid}"
        data = requests.get(api, headers=H, timeout=10).json()
        if "data" in data:
            item = data["data"].get("item",{})
            vu = item.get("video",{}).get("download_url","")
            return {"success": True, "url": vu, "title": item.get("content","")[:50]}
    except: pass
    return {"success": False, "error": "pipix failed"}

def parse_bilibili(url):
    try:
        r = requests.get(url, headers=H, allow_redirects=True, timeout=10)
        m = re.search(r'/video/(BV\w+)', r.url)
        if not m: return {"success": False, "error": "ID not found"}
        bvid = m.group(1)
        api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        data = requests.get(api, headers=H, timeout=10).json()
        if data.get("code") == 0:
            d = data["data"]
            cid = d.get("cid",0)
            aid = d.get("aid",0)
            play = f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=80"
            bh = dict(H)
            bh["Referer"] = "https://www.bilibili.com/"
            pd = requests.get(play, headers=bh, timeout=10).json()
            if pd.get("code") == 0:
                return {"success": True, "url": pd["data"]["durl"][0]["url"], "title": d.get("title",""), "referer": "https://www.bilibili.com/"}
    except: pass
    return {"success": False, "error": "bilibili failed"}

def parse(url):
    p = detect(url)
    if p == "douyin": return parse_douyin(url)
    if p == "kuaishou": return parse_kuaishou(url)
    if p == "xigua": return parse_xigua(url)
    if p == "xiaohongshu": return parse_xiaohongshu(url)
    if p == "weibo": return parse_weibo(url)
    if p == "pipix": return parse_pipix(url)
    if p == "bilibili": return parse_bilibili(url)
    return {"success": False, "error": "unsupported platform"}

def download(url, path, referer=None):
    headers = dict(H)
    if referer:
        headers["Referer"] = referer
    tmp = path + ".part"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, stream=True, timeout=90)
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            with open(tmp, "rb") as f:
                head = f.read(512).lower()
            is_html = head.startswith(b"<!doctype") or head.startswith(b"<html") or head.startswith(b"<?xml")
            if is_html or os.path.getsize(tmp) == 0:
                os.remove(tmp)
                continue
            os.replace(tmp, path)
            return True
        except Exception:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except: pass
            continue
    return False
