#!/usr/bin/env python3
"""aplm123 Web 站点 —— 落地页 / 在线下载 / 数据看板 / 管理后台（四合一）。
复用机器人的 data_manager + downloader，数据完全打通。
绑定方案 A：网页填 TG ID → bot 私聊发验证码 → 网页验证 → 用该账号积分。
"""
import os, sys, time, random, asyncio, shutil, secrets, json
sys.path.insert(0, "/root/aplm123-bot")

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import requests as _rq

from data_manager import (
    load_users, save_users, get_user, is_vip, is_admin, is_banned,
    do_sign, spend_point, add_points, set_points, get_ranking, get_my_rank,
    give_vip, remove_vip, get_vip_list, ban_user, unban_user, mute_user,
    get_ban_list, get_notice, set_notice, get_stats, get_bag, add_to_bag,
    use_from_bag, get_logs, get_user_history, create_code, use_code,
    ADMIN_IDS,
)
from downloader import download as _dl_sync

import hashlib

TG_TOKEN = os.getenv("TG_TOKEN", "")
WEB_ADMIN_PASS = os.getenv("WEB_ADMIN_PASS", os.getenv("ADMIN_PASS", "zxasqw12"))
DL_DIR = os.getenv("DL_DIR", "/root/aplm123-bot/downloads")
COOKIE_FILE = "/root/aplm123-bot/cookies.txt"
ROOT = "/root/aplm123-bot/webroot"
WEBAUTH_FILE = "/root/aplm123-bot/data/webauth.json"

app = FastAPI(title="aplm123")

# ---- 内存态：用户会话 / 管理会话 ----
_sessions = {}    # token -> uid
_admin_tokens = set()


def _load_auth():
    try:
        with open(WEBAUTH_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_auth(a):
    os.makedirs(os.path.dirname(WEBAUTH_FILE), exist_ok=True)
    with open(WEBAUTH_FILE + ".tmp", "w") as f:
        json.dump(a, f, ensure_ascii=False, indent=2)
    os.replace(WEBAUTH_FILE + ".tmp", WEBAUTH_FILE)


def _hash(pw):
    return hashlib.sha256(("aplm123$" + pw).encode()).hexdigest()


def _tg_send(uid, text):
    if not TG_TOKEN:
        return False
    try:
        r = _rq.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                     json={"chat_id": int(uid), "text": text}, timeout=10)
        return r.json().get("ok", False)
    except Exception:
        return False


def _uid_from_req(request: Request):
    tok = request.headers.get("X-Session", "") or request.cookies.get("session", "")
    return _sessions.get(tok)


def _is_admin_req(request: Request):
    # 管理会话 token，或已登录用户本身是管理员
    tok = request.headers.get("X-Admin", "") or request.cookies.get("admin", "")
    if tok in _admin_tokens:
        return True
    uid = _uid_from_req(request)
    return bool(uid and is_admin(uid))


# ============ 页面 ============
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join(ROOT, "index.html"))


# ============ 注册 / 登录（网页原生账号）============
@app.post("/api/register")
def register(username: str = Form(...), password: str = Form(...)):
    username = username.strip()
    if len(username) < 3 or len(username) > 20:
        return JSONResponse({"ok": False, "msg": "用户名需 3-20 位"})
    if len(password) < 6:
        return JSONResponse({"ok": False, "msg": "密码至少 6 位"})
    auth = _load_auth()
    if username.lower() in auth:
        return JSONResponse({"ok": False, "msg": "用户名已存在"})
    uid = "w_" + username.lower()
    auth[username.lower()] = {"uid": uid, "pass": _hash(password), "name": username}
    _save_auth(auth)
    d = load_users(); u = get_user(d, uid)
    u["username"] = username; u["first_name"] = username
    save_users(d)
    tok = secrets.token_urlsafe(24)
    _sessions[tok] = uid
    return JSONResponse({"ok": True, "token": tok, "msg": "注册成功，赠送 100 积分"})


@app.post("/api/login")
def login(username: str = Form(...), password: str = Form(...)):
    username = username.strip().lower()
    auth = _load_auth()
    rec = auth.get(username)
    if not rec or rec["pass"] != _hash(password):
        return JSONResponse({"ok": False, "msg": "用户名或密码错误"})
    banned, m = is_banned(rec["uid"])
    if banned:
        return JSONResponse({"ok": False, "msg": m})
    tok = secrets.token_urlsafe(24)
    _sessions[tok] = rec["uid"]
    return JSONResponse({"ok": True, "token": tok, "msg": "登录成功"})


# ============ 绑定 Telegram（设置里，可选）============
_bind_codes = {}  # webuser -> (tg_uid, code, expire)


@app.post("/api/bind/tg/request")
def bind_tg_request(request: Request, tg_uid: str = Form(...)):
    webuser = _webuser_from_req(request)
    if not webuser:
        return JSONResponse({"ok": False, "msg": "请先登录网页账号"})
    if not tg_uid.isdigit():
        return JSONResponse({"ok": False, "msg": "请输入正确的 Telegram 数字 ID"})
    code = f"{random.randint(100000, 999999)}"
    _bind_codes[webuser] = (tg_uid, code, time.time() + 300)
    if _tg_send(tg_uid, f"🔗 网页账号绑定验证码：{code}\n5 分钟内有效。绑定后你的网页与 TG 数据将合并。"):
        return JSONResponse({"ok": True, "msg": "验证码已发送到 Telegram"})
    return JSONResponse({"ok": False, "msg": "发送失败：请先给 @aplm12345bot 发过 /start"})


@app.post("/api/bind/tg/verify")
def bind_tg_verify(request: Request, code: str = Form(...)):
    webuser = _webuser_from_req(request)
    if not webuser:
        return JSONResponse({"ok": False, "msg": "请先登录"})
    rec = _bind_codes.get(webuser)
    if not rec or rec[2] < time.time():
        return JSONResponse({"ok": False, "msg": "验证码不存在或已过期"})
    tg_uid, real_code, _ = rec
    if code.strip() != real_code:
        return JSONResponse({"ok": False, "msg": "验证码错误"})
    _bind_codes.pop(webuser, None)
    # 合并：把网页账号指向 TG uid；旧 w_ 数据的积分并入（可选：这里直接切换指向）
    auth = _load_auth()
    if webuser not in auth:
        return JSONResponse({"ok": False, "msg": "账号异常"})
    old_uid = auth[webuser]["uid"]
    d = load_users()
    # 若旧 w_ 账号有积分，合并到 TG 账号
    if old_uid.startswith("w_") and old_uid in d:
        tg_u = get_user(d, tg_uid)
        old = d[old_uid]
        tg_u["points"] = tg_u.get("points", 0) + old.get("points", 0)
        tg_u["downloads_total"] = tg_u.get("downloads_total", 0) + old.get("downloads_total", 0)
        del d[old_uid]
        save_users(d)
    auth[webuser]["uid"] = tg_uid
    _save_auth(auth)
    # 刷新当前会话指向
    for t, u in list(_sessions.items()):
        if u == old_uid:
            _sessions[t] = tg_uid
    return JSONResponse({"ok": True, "msg": "绑定成功！网页与 Telegram 账号已合并"})


@app.post("/api/bind/tg/unbind")
def bind_tg_unbind(request: Request):
    webuser = _webuser_from_req(request)
    if not webuser:
        return JSONResponse({"ok": False, "msg": "请先登录"})
    auth = _load_auth()
    rec = auth.get(webuser)
    if not rec or str(rec["uid"]).startswith("w_"):
        return JSONResponse({"ok": False, "msg": "当前未绑定 TG"})
    # 解绑：新建独立 w_ 账号（不动 TG 数据）
    new_uid = "w_" + webuser
    d = load_users()
    nu = get_user(d, new_uid)
    nu["username"] = webuser; nu["first_name"] = webuser
    save_users(d)
    auth[webuser]["uid"] = new_uid
    _save_auth(auth)
    for t, u in list(_sessions.items()):
        if u == rec["uid"]:
            _sessions[t] = new_uid
    return JSONResponse({"ok": True, "msg": "已解绑，恢复为独立网页账号"})


# ============ 用户中心（登录后） ============
def _webuser_from_req(request: Request):
    """从会话反查网页用户名（用于绑定操作）。"""
    uid = _uid_from_req(request)
    if not uid:
        return None
    auth = _load_auth()
    for name, rec in auth.items():
        if rec["uid"] == uid:
            return name
    return None


def _need_user(request):
    uid = _uid_from_req(request)
    if not uid:
        raise HTTPException(401, "未登录")
    return uid


@app.get("/api/me")
def api_me(request: Request):
    uid = _need_user(request)
    d = load_users(); u = get_user(d, uid); save_users(d)
    rp, _ = get_my_rank(uid, "points")
    rd, _ = get_my_rank(uid, "downloads")
    rs, _ = get_my_rank(uid, "sign")
    bag = get_bag(u)
    return {
        "uid": uid, "points": u.get("points", 0),
        "downloads_today": u.get("downloads_today", 0),
        "downloads_total": u.get("downloads_total", 0),
        "sign_streak": u.get("sign_streak", 0),
        "vip": is_vip(u), "vip_until": u.get("vip_until", ""),
        "username": u.get("username", ""), "first_name": u.get("first_name", ""),
        "created_at": u.get("created_at", ""),
        "bound_tg": (not str(uid).startswith("w_")),
        "bag": bag, "rank_points": rp, "rank_downloads": rd, "rank_sign": rs,
        "is_admin": is_admin(uid),
    }


@app.post("/api/sign")
def api_sign(request: Request):
    uid = _need_user(request)
    d = load_users(); u = get_user(d, uid)
    ok, msg = do_sign(u)
    if ok:
        save_users(d)
    return {"ok": ok, "msg": msg, "points": u.get("points", 0)}


@app.post("/api/download")
async def api_download(request: Request, url: str = Form(...)):
    uid = _need_user(request)
    banned, m = is_banned(uid)
    if banned:
        return {"ok": False, "msg": m}
    d = load_users(); u = get_user(d, uid)
    ok, msg = spend_point(u)
    if not ok:
        return {"ok": False, "msg": msg + "，请签到或下载券"}
    save_users(d)
    result = await asyncio.to_thread(_dl_sync, url, uid)
    if not result.get("success"):
        return {"ok": False, "msg": result.get("error", "下载失败")}
    u["downloads_today"] = u.get("downloads_today", 0) + 1
    u["downloads_total"] = u.get("downloads_total", 0) + 1
    save_users(d)
    # 生成可访问的临时链接
    files = []
    pub = os.path.join(ROOT, "dl")
    os.makedirs(pub, exist_ok=True)
    for p in result.get("paths", [])[:10]:
        if not os.path.exists(p):
            continue
        name = secrets.token_hex(6) + os.path.splitext(p)[1]
        dst = os.path.join(pub, name)
        shutil.move(p, dst)
        files.append("/dl/" + name)
    if result.get("img_dir"):
        shutil.rmtree(result["img_dir"], ignore_errors=True)
    return {"ok": True, "type": result["type"], "files": files,
            "title": result.get("title", ""), "points": u.get("points", 0)}


@app.get("/dl/{name}")
def serve_dl(name: str):
    p = os.path.join(ROOT, "dl", os.path.basename(name))
    if not os.path.exists(p):
        raise HTTPException(404)
    return FileResponse(p)


@app.post("/api/lottery")
def api_lottery(request: Request, mode: str = Form("1")):
    uid = _need_user(request)
    d = load_users(); u = get_user(d, uid)
    cost = 450 if mode == "10" else 50
    if u.get("points", 0) < cost:
        return {"ok": False, "msg": f"积分不足（需要{cost}）"}
    u["points"] -= cost
    from datetime import date, timedelta
    def draw():
        r = random.random() * 100
        if r < 0.1:
            u["vip_until"] = str(date.today() + timedelta(days=30)); return "🏆VIP1月"
        if r < 3.1:
            add_to_bag(u, "day_cards", 3); return "🥇日卡×3"
        if r < 11.1:
            add_to_bag(u, "day_cards", 1); return "🥈日卡×1"
        if r < 26.1:
            u["points"] += 100; return "🥉100积分"
        if r < 51.1:
            u["points"] += 50; return "🎁50积分"
        u["points"] += 20; return "🎫20积分"
    results = [draw() for _ in range(10 if mode == "10" else 1)]
    save_users(d)
    return {"ok": True, "results": results, "points": u.get("points", 0)}


@app.post("/api/shop/buy")
def api_shop(request: Request, item: str = Form(...)):
    uid = _need_user(request)
    d = load_users(); u = get_user(d, uid)
    from datetime import date, timedelta
    if item == "ticket":
        if u.get("points", 0) < 80:
            return {"ok": False, "msg": "积分不足（需要80）"}
        u["points"] -= 80; add_to_bag(u, "download_tickets", 10)
        msg = "购买成功！+10 下载券"
    elif item == "daycard":
        if u.get("points", 0) < 200:
            return {"ok": False, "msg": "积分不足（需要200）"}
        u["points"] -= 200; add_to_bag(u, "day_cards", 1)
        msg = "购买成功！+1 日卡"
    else:
        return {"ok": False, "msg": "未知商品"}
    save_users(d)
    return {"ok": True, "msg": msg, "points": u.get("points", 0)}


@app.post("/api/game")
def api_game(request: Request, game: str = Form(...)):
    uid = _need_user(request)
    d = load_users(); u = get_user(d, uid)
    if u.get("points", 0) < 10:
        return {"ok": False, "msg": "积分不足（需要10）"}
    u["points"] -= 10
    from games import roll_dice, coinflip, rps, slot_machine, guess_number
    out = ""
    if game == "dice":
        dice, total, res, prize = roll_dice(); u["points"] += prize
        out = f"🎲 {'+'.join(map(str,dice))}={total}（{res}）{'赢'+str(prize) if prize>10 else '未中'}"
    elif game == "coin":
        res, win, prize = coinflip(10, random.choice(["head","tail"]))
        if win: u["points"] += prize
        out = f"🪙 {'正面' if res=='head' else '反面'} {'赢'+str(prize) if win else '未中'}"
    elif game == "slot":
        reels, msg, prize = slot_machine(10); u["points"] += prize
        out = f"🎰 {'|'.join(reels)} {msg}"
    elif game == "guess":
        ans, diff, prize, msg = guess_number(10, random.randint(1,100))
        if prize>0: u["points"] += prize
        out = f"🔢 {msg}"
    elif game == "rps":
        p1,p2,res,prize = rps(random.choice(["rock","paper","scissors"]),10)
        if prize>10: u["points"] += prize
        out = f"✊ {p1} vs {p2} {res}"
    else:
        return {"ok": False, "msg": "未知游戏"}
    save_users(d)
    return {"ok": True, "result": out, "points": u.get("points", 0)}


@app.get("/api/fun/{kind}")
def api_fun(kind: str, request: Request):
    _need_user(request)
    from entertainment import get_joke, get_poem, get_movie, get_riddle, get_love, gen_nickname, get_tarot
    if kind == "joke": return {"text": get_joke()}
    if kind == "poem":
        p = get_poem(); return {"text": f"《{p['title']}》 {p['author']}\n{p['content']}"}
    if kind == "movie":
        m = get_movie(); return {"text": f"《{m['name']}》 {m['type']}\n{m['desc']}"}
    if kind == "riddle":
        r = get_riddle(); return {"text": f"{r['q']}\n答案：{r['a']}"}
    if kind == "love": return {"text": get_love()}
    if kind == "nick": return {"text": gen_nickname()}
    if kind == "tarot":
        c, pos = get_tarot(); return {"text": f"{c['emoji']} {c['name']}（{pos}）\n{c['meaning']}"}
    return {"text": "未知"}


@app.get("/api/history")
def api_history(request: Request):
    uid = _need_user(request)
    return {"history": get_user_history(uid, 20)}


# ============ 数据看板（公开只读） ============
@app.get("/api/stats")
def api_stats():
    s = get_stats()
    top_p = get_ranking("points", 10)
    top_d = get_ranking("downloads", 10)
    top_s = get_ranking("sign", 10)
    def clean(lst):
        return [{"name": r.get("username") or r.get("first_name") or ("用户"+r["uid"][-4:]),
                 "points": r["points"], "downloads": r["downloads_total"],
                 "sign": r["sign_streak"]} for r in lst]
    return {"stats": s, "top_points": clean(top_p),
            "top_downloads": clean(top_d), "top_sign": clean(top_s),
            "notice": get_notice()}


# ============ 管理后台 ============
@app.post("/api/admin/login")
def admin_login(password: str = Form(...)):
    if password == WEB_ADMIN_PASS:
        tok = secrets.token_urlsafe(24)
        _admin_tokens.add(tok)
        return {"ok": True, "token": tok}
    return {"ok": False, "msg": "密码错误"}


def _need_admin(request):
    if not _is_admin_req(request):
        raise HTTPException(403, "需管理员登录")


@app.get("/api/admin/overview")
def admin_overview(request: Request):
    _need_admin(request)
    ck_exists = os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 20
    ck_sess = ck_exists and "sessionid" in open(COOKIE_FILE).read()
    import psutil
    return {"stats": get_stats(), "notice": get_notice(),
            "cookie": {"exists": ck_exists, "has_session": ck_sess},
            "logs": get_logs(20),
            "sys": {"cpu": psutil.cpu_percent(), "mem": psutil.virtual_memory().percent,
                    "disk": psutil.disk_usage("/").percent}}


@app.get("/api/admin/users")
def admin_users(request: Request, q: str = ""):
    _need_admin(request)
    d = load_users()
    rows = []
    for uid, u in sorted(d.items(), key=lambda x: x[1].get("points", 0), reverse=True):
        name = u.get("first_name", "") or u.get("username", "") or ""
        if q and q not in uid and q not in name:
            continue
        rows.append({"uid": uid, "name": name, "points": u.get("points", 0),
                     "vip": is_vip(u), "vip_until": u.get("vip_until", ""),
                     "downloads": u.get("downloads_total", 0),
                     "banned": str(uid) in get_ban_list()})
    return {"users": rows[:200], "total": len(d)}


@app.post("/api/admin/action")
def admin_action(request: Request, act: str = Form(...), uid: str = Form(""),
                 amount: str = Form(""), text: str = Form("")):
    _need_admin(request)
    d = load_users()
    try:
        if act == "add_points":
            u = get_user(d, uid); add_points(u, int(amount)); save_users(d)
            return {"ok": True, "msg": f"{uid} +{amount}积分 → {u['points']}"}
        if act == "del_points":
            u = get_user(d, uid); u["points"] = max(0, u.get("points",0)-int(amount)); save_users(d)
            return {"ok": True, "msg": f"{uid} -{amount}积分 → {u['points']}"}
        if act == "set_points":
            u = get_user(d, uid); set_points(u, int(amount)); save_users(d)
            return {"ok": True, "msg": f"{uid} 积分设为 {amount}"}
        if act == "batch_all":
            n = 0
            for _, u in d.items():
                u["points"] = u.get("points",0)+int(amount); n += 1
            save_users(d)
            return {"ok": True, "msg": f"全员 +{amount}积分（{n}人）"}
        if act == "give_vip":
            u = get_user(d, uid); exp = give_vip(u, int(amount)); save_users(d)
            return {"ok": True, "msg": f"{uid} VIP {amount}天 → {exp}"}
        if act == "revoke_vip":
            u = get_user(d, uid); remove_vip(u); save_users(d)
            return {"ok": True, "msg": f"{uid} VIP 已撤销"}
        if act == "ban":
            ban_user(uid); return {"ok": True, "msg": f"{uid} 已封禁"}
        if act == "unban":
            unban_user(uid); return {"ok": True, "msg": f"{uid} 已解封"}
        if act == "mute":
            mute_user(uid, int(amount)); return {"ok": True, "msg": f"{uid} 禁言{amount}小时"}
        if act == "delete":
            if not uid or uid not in d:
                return {"ok": False, "msg": "用户不存在"}
            del d[uid]
            save_users(d)
            # 同步删除网页登录账号（若有）
            try:
                auth = _load_auth()
                for name in [k for k, v in auth.items() if v.get("uid") == uid]:
                    del auth[name]
                _save_auth(auth)
            except Exception:
                pass
            return {"ok": True, "msg": f"用户 {uid} 已删除"}
        if act == "notice":
            set_notice(text); return {"ok": True, "msg": "公告已更新"}
        if act == "broadcast":
            n = 0
            for u2 in d.keys():
                if str(u2).isdigit() and _tg_send(u2, f"📢 系统公告\n\n{text}"):
                    n += 1
            return {"ok": True, "msg": f"群发完成，成功 {n}（仅 TG 用户）"}
        if act == "lottery_all":
            from datetime import date, timedelta
            pr = {"VIP":0,"100":0,"50":0,"20":0}
            for _, u in d.items():
                r = random.random()*100
                if r<0.5: u["vip_until"]=str(date.today()+timedelta(days=7)); pr["VIP"]+=1
                elif r<10: u["points"]=u.get("points",0)+100; pr["100"]+=1
                elif r<30: u["points"]=u.get("points",0)+50; pr["50"]+=1
                else: u["points"]=u.get("points",0)+20; pr["20"]+=1
            save_users(d)
            return {"ok": True, "msg": f"全员抽奖：VIP{pr['VIP']} 100分{pr['100']} 50分{pr['50']} 20分{pr['20']}"}
        if act == "gen_code":
            code = secrets.token_hex(4).upper()
            create_code(code, int(amount), 100)
            return {"ok": True, "msg": f"兑换码：{code}（{amount}积分/100次）"}
    except Exception as e:
        return {"ok": False, "msg": str(e)[:80]}
    return {"ok": False, "msg": "未知操作"}


@app.post("/api/admin/cookie")
def admin_cookie(request: Request, act: str = Form(...), raw: str = Form("")):
    _need_admin(request)
    if act == "set":
        if "=" not in raw:
            return {"ok": False, "msg": "格式错误"}
        lines = ["# Netscape HTTP Cookie File"]
        n = 0
        for part in raw.split(";"):
            part = part.strip()
            if "=" not in part: continue
            k, v = part.split("=", 1)
            k, v = k.strip(), v.strip()
            if not k: continue
            lines.append(f".tiktok.com\tTRUE\t/\tTRUE\t2000000000\t{k}\t{v}")
            n += 1
        with open(COOKIE_FILE, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(COOKIE_FILE, 0o600)
        return {"ok": True, "msg": f"Cookie 已保存（{n}条，{'含' if 'sessionid' in raw else '无'} sessionid）"}
    if act == "clear":
        if os.path.exists(COOKIE_FILE):
            os.remove(COOKIE_FILE)
        return {"ok": True, "msg": "Cookie 已清除"}
    return {"ok": False, "msg": "未知操作"}


if __name__ == "__main__":
    import uvicorn
    os.makedirs(os.path.join(ROOT, "dl"), exist_ok=True)
    uvicorn.run(app, host="127.0.0.1", port=25774)
