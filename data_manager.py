#!/usr/bin/env python3
"""数据管理模块"""
import os, json, time
from datetime import date, timedelta, datetime

DATA_DIR = os.getenv("DATA_DIR", "/root/aplm123-bot/data")
os.makedirs(DATA_DIR, exist_ok=True)

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "6742479136").split(",")]
POINT_PER_SIGN = 10
POINT_PER_DOWNLOAD = 5
POINT_SIGN_STREAK_7 = 50

USERS_FILE = os.path.join(DATA_DIR, "users.json")
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")
BANS_FILE = os.path.join(DATA_DIR, "bans.json")
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")
LOTTERY_POOL_FILE = os.path.join(DATA_DIR, "lottery_pool.json")
WINNERS_FILE = os.path.join(DATA_DIR, "winners.json")
NOTICE_FILE = os.path.join(DATA_DIR, "notice.txt")
CODES_FILE = os.path.join(DATA_DIR, "codes.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

import fcntl

def load_json(path, default=None):
    try:
        with open(path) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            return json.load(f)
    except: return default if default is not None else {}

def save_json(path, data):
    with open(path + ".tmp", "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(path + ".tmp", path)

def load_text(path, default=""):
    try:
        with open(path) as f: return f.read().strip()
    except: return default

def save_text(path, text):
    with open(path + ".tmp", "w") as f:
        f.write(text)
    os.replace(path + ".tmp", path)

def load_users(): return load_json(USERS_FILE, {})
def save_users(d): save_json(USERS_FILE, d)

def get_user(d, uid):
    uid = str(uid)
    if uid not in d:
        d[uid] = {
            "points": 100, "downloads_today": 0, "downloads_total": 0,
            "last_sign": "", "sign_streak": 0, "vip_until": "",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "username": "", "first_name": "",
            "bag": {"download_tickets": 0, "day_cards": 0}
        }
    return d[uid]

def update_user_info(user, update):
    if update.effective_user.username:
        user["username"] = update.effective_user.username
    if update.effective_user.first_name:
        user["first_name"] = update.effective_user.first_name

def is_vip(user):
    return user.get("vip_until", "") >= str(date.today())

def is_admin(uid):
    return int(uid) in ADMIN_IDS

def is_banned(uid):
    bans = load_json(BANS_FILE, {"banned": [], "muted": {}})
    if str(uid) in bans.get("banned", []):
        return True, "你已被封禁"
    mute_until = bans.get("muted", {}).get(str(uid), 0)
    if mute_until > time.time():
        remaining = int((mute_until - time.time()) / 60)
        return True, f"你已被禁言，还需{remaining}分钟"
    return False, ""

def do_sign(user):
    today = str(date.today())
    if user["last_sign"] == today:
        return False, "今天已经签到过了"
    yesterday = str(date.today() - timedelta(days=1))
    if user["last_sign"] == yesterday:
        user["sign_streak"] = user.get("sign_streak", 0) + 1
    else:
        user["sign_streak"] = 1
    user["last_sign"] = today
    user["points"] = user.get("points", 0) + POINT_PER_SIGN
    msg = f"签到成功！+{POINT_PER_SIGN}积分\n当前积分：{user['points']}\n连续签到：{user['sign_streak']}天"
    if user["sign_streak"] % 7 == 0:
        user["points"] += POINT_SIGN_STREAK_7
        msg += f"\n🎉 连续签到{user['sign_streak']}天，额外奖励{POINT_SIGN_STREAK_7}积分！"
    return True, msg

def spend_point(user, amount=None):
    amount = amount or POINT_PER_DOWNLOAD
    if is_vip(user):
        return True, "VIP会员，无限下载"
    if user.get("points", 0) < amount:
        return False, f"积分不足（需要{amount}，当前{user.get('points',0)}）"
    user["points"] = user.get("points", 0) - amount
    return True, f"消耗{amount}积分，剩余{user['points']}"

def add_points(user, amount, reason="管理员操作"):
    user["points"] = user.get("points", 0) + amount
    log_action("add_points", {"amount": amount, "reason": reason})
    return user["points"]

def set_points(user, amount):
    user["points"] = amount
    return user["points"]

def log_action(action, details=None):
    logs = load_json(LOGS_FILE, [])
    logs.append({
        "action": action,
        "details": details or {},
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    if len(logs) > 1000:
        logs = logs[-1000:]
    save_json(LOGS_FILE, logs)

def get_logs(limit=20):
    logs = load_json(LOGS_FILE, [])
    return logs[-limit:]

def get_ranking(rank_type="points", limit=10):
    users = load_users()
    ranking = []
    for uid, u in users.items():
        ranking.append({
            "uid": uid,
            "username": u.get("username", ""),
            "first_name": u.get("first_name", ""),
            "points": u.get("points", 0),
            "downloads_total": u.get("downloads_total", 0),
            "sign_streak": u.get("sign_streak", 0)
        })
    if rank_type == "points":
        ranking.sort(key=lambda x: x["points"], reverse=True)
    elif rank_type == "downloads":
        ranking.sort(key=lambda x: x["downloads_total"], reverse=True)
    elif rank_type == "sign":
        ranking.sort(key=lambda x: x["sign_streak"], reverse=True)
    return ranking[:limit]

def get_my_rank(uid):
    uid = str(uid)
    ranking = get_ranking("points", 9999)
    for i, r in enumerate(ranking):
        if r["uid"] == uid:
            return i + 1, r
    return None, None

def give_vip(user, days):
    today = date.today()
    current = user.get("vip_until", "")
    if current and current >= str(today):
        base = date.fromisoformat(current)
    else:
        base = today
    user["vip_until"] = str(base + timedelta(days=days))
    return user["vip_until"]

def remove_vip(user):
    user["vip_until"] = ""

def get_vip_list():
    users = load_users()
    vip_list = []
    for uid, u in users.items():
        if is_vip(u):
            vip_list.append({
                "uid": uid,
                "username": u.get("username", ""),
                "first_name": u.get("first_name", ""),
                "vip_until": u.get("vip_until", "")
            })
    return vip_list

def ban_user(uid):
    bans = load_json(BANS_FILE, {"banned": [], "muted": {}})
    if str(uid) not in bans["banned"]:
        bans["banned"].append(str(uid))
        save_json(BANS_FILE, bans)
        return True
    return False

def unban_user(uid):
    bans = load_json(BANS_FILE, {"banned": [], "muted": {}})
    if str(uid) in bans["banned"]:
        bans["banned"].remove(str(uid))
        save_json(BANS_FILE, bans)
        return True
    return False

def mute_user(uid, hours):
    bans = load_json(BANS_FILE, {"banned": [], "muted": {}})
    bans["muted"][str(uid)] = time.time() + hours * 3600
    save_json(BANS_FILE, bans)

def get_ban_list():
    bans = load_json(BANS_FILE, {"banned": [], "muted": {}})
    return bans.get("banned", [])

def get_events(): return load_json(EVENTS_FILE, {})

def start_event(event_type):
    events = get_events()
    events[event_type] = {"start_time": datetime.now().strftime("%Y-%m-%d %H:%M"), "active": True}
    save_json(EVENTS_FILE, events)

def end_event(event_type):
    events = get_events()
    if event_type in events:
        events[event_type]["active"] = False
        save_json(EVENTS_FILE, events)

def is_event_active(event_type):
    events = get_events()
    return events.get(event_type, {}).get("active", False)

def get_lottery_pool(): return load_json(LOTTERY_POOL_FILE, {"pool": 1000})

def update_lottery_pool(amount):
    pool = get_lottery_pool()
    pool["pool"] = pool.get("pool", 0) + amount
    save_json(LOTTERY_POOL_FILE, pool)
    return pool["pool"]

def get_winners(): return load_json(WINNERS_FILE, [])

def add_winner(uid, username, prize):
    winners = get_winners()
    winners.append({"uid": uid, "username": username, "prize": prize,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
    if len(winners) > 100:
        winners = winners[-100:]
    save_json(WINNERS_FILE, winners)

def get_notice(): return load_text(NOTICE_FILE, "暂无公告")
def set_notice(text): save_text(NOTICE_FILE, text)

def get_stats():
    users = load_users()
    today = str(date.today())
    return {
        "total_users": len(users),
        "today_active": sum(1 for u in users.values() if u.get("last_sign") == today),
        "total_downloads": sum(u.get("downloads_total", 0) for u in users.values()),
        "total_points": sum(u.get("points", 0) for u in users.values()),
        "vip_count": sum(1 for u in users.values() if is_vip(u))
    }

def get_bag(user):
    return user.get("bag", {"download_tickets": 0, "day_cards": 0})

def add_to_bag(user, item, count=1):
    bag = user.get("bag", {"download_tickets": 0, "day_cards": 0})
    if item in bag:
        bag[item] += count
    else:
        bag[item] = count
    user["bag"] = bag

def use_from_bag(user, item, count=1):
    bag = user.get("bag", {"download_tickets": 0, "day_cards": 0})
    if bag.get(item, 0) >= count:
        bag[item] -= count
        user["bag"] = bag
        return True
    return False

def get_invite_count(d, uid):
    return sum(1 for u in d.values() if u.get("invited_by") == str(uid))

def set_invited_by(d, uid, inviter_uid):
    user = get_user(d, uid)
    if not user.get("invited_by") and str(uid) != str(inviter_uid):
        user["invited_by"] = str(inviter_uid)
        inviter = get_user(d, inviter_uid)
        inviter["points"] += 20
        return True
    return False

def load_codes(): return load_json(CODES_FILE, {})

def create_code(code, points, count):
    codes = load_codes()
    codes[code] = {"points": points, "remaining": count, "used": []}
    save_json(CODES_FILE, codes)

def use_code(code, uid):
    codes = load_codes()
    if code not in codes: return False, "兑换码不存在"
    c = codes[code]
    if uid in c.get("used", []): return False, "你已使用过该兑换码"
    if c["remaining"] <= 0: return False, "兑换码已用完"
    c["used"] = c.get("used", []) + [uid]
    c["remaining"] -= 1
    save_json(CODES_FILE, codes)
    return True, c["points"]

def add_history(uid, url, title="", status="success"):
    history = load_json(HISTORY_FILE, [])
    history.append({"uid": str(uid), "url": url, "title": title, "status": status,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    if len(history) > 5000:
        history = history[-5000:]
    save_json(HISTORY_FILE, history)

def get_user_history(uid, limit=10):
    history = load_json(HISTORY_FILE, [])
    return [h for h in history if h["uid"] == str(uid)][-limit:]

# 初始化抽奖池
pool = get_lottery_pool()
if "pool" not in pool:
    pool["pool"] = 1000
    save_json(LOTTERY_POOL_FILE, pool)
