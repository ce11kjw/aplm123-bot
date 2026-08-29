#!/usr/bin/env python3
"""QQ机器人"""
import os, sys, time, json, requests, websocket, threading, re, random, shutil
from datetime import date, timedelta
sys.path.insert(0, "/root/aplm123-bot")
from downloader import download as download_video
from data_manager import *
from entertainment import *
from games import *

APP_ID = os.getenv("QQ_APP_ID", "")
APP_SECRET = os.getenv("QQ_APP_SECRET", "")
TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
API_BASE = "https://api.sgroup.qq.com"
DL_DIR = os.getenv("DL_DIR", "/root/aplm123-bot/downloads")
os.makedirs(DL_DIR, exist_ok=True)

ADMIN_IDS = [6742479136, "81565FC3F59284EC1DE13E3530927056"]

def is_admin_qq(uid):
    return str(uid) in [str(i) for i in ADMIN_IDS]

class QQBot:
    def __init__(self):
        self.token = None
        self.token_expire = 0
        self.ws = None
        self.seq = None

    def get_token(self):
        if self.token and time.time() < self.token_expire:
            return self.token
        try:
            r = requests.post(TOKEN_URL, json={"appId": APP_ID, "clientSecret": APP_SECRET}, timeout=10)
            data = r.json()
            if "access_token" in data:
                self.token = data["access_token"]
                self.token_expire = time.time() + int(data.get("expires_in", 7200)) - 300
                return self.token
        except: pass
        return None

    def api(self, method, path, data=None):
        token = self.get_token()
        if not token: return {}
        headers = {"Authorization": "QQBot " + token, "Content-Type": "application/json"}
        try:
            r = requests.request(method, API_BASE + path, headers=headers, json=data, timeout=10)
            return r.json() if r.text else {}
        except: return {}

    def reply(self, channel_id, msg_id, content):
        if channel_id:
            if getattr(self, "_c2c", False):
                self.api("POST", "/v2/users/" + channel_id + "/messages", {"content": content, "msg_id": msg_id})
            else:
                self.api("POST", "/channels/" + channel_id + "/messages", {"content": content, "msg_id": msg_id})

    def upload_file(self, channel_id, filepath, file_type=1):
        """上传文件，返回 file_info（C2C 用 JSON base64，频道用 multipart）"""
        token = self.get_token()
        if not token: return None
        headers = {"Authorization": "QQBot " + token}
        try:
            if getattr(self, "_c2c", False):
                # C2C：JSON body + file_data base64
                import base64
                with open(filepath, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                path = f"/v2/users/{channel_id}/files"
                headers["Content-Type"] = "application/json"
                r = requests.post(API_BASE + path, headers=headers,
                    json={"file_type": file_type, "file_data": b64,
                          "srv_send_msg": True, "file_name": os.path.basename(filepath)},
                    timeout=120)
            else:
                # 频道：multipart
                path = f"/channels/{channel_id}/files"
                with open(filepath, "rb") as f:
                    r = requests.post(API_BASE + path, headers=headers,
                        files={"file": (os.path.basename(filepath), f)},
                        data={"srv_send_msg": "true"}, timeout=120)
            data = r.json()
            if r.status_code != 200:
                print(f"[upload err] HTTP {r.status_code} {data.get('err_code','')} {data.get('message','')[:80]}")
                return None
            return data.get("file_info")
        except Exception as e:
            print("[upload err]", str(e)[:80])
            return None

    def send_media(self, channel_id, msg_id, file_info, content=""):
        """发送富媒体消息（msg_type=7），C2C 与频道路径不同"""
        if not file_info: return False
        path = f"/v2/users/{channel_id}/messages" if getattr(self, "_c2c", False) else f"/channels/{channel_id}/messages"
        body = {"msg_type": 7, "media": {"file_info": file_info}}
        if msg_id and msg_id != "0":
            body["msg_id"] = msg_id
        if content:
            body["content"] = content
        if getattr(self, "_c2c", False):
            token = self.get_token()
            if not token: return False
            r = requests.post(API_BASE + path,
                              headers={"Authorization": "QQBot " + token, "Content-Type": "application/json"},
                              json=body, timeout=30)
            return r.status_code == 200
        else:
            r = self.api("POST", path, body)
            return bool(r.get("id"))

    INTENT_MAP = {
        "admin": "/admin", "sign": "/签到", "me": "/我的",
        "rank": "/排行", "lottery": "/抽奖", "lottery_1": "/单抽",
        "lottery_10": "/十连", "vip": "/vip介绍", "shop": "/商城",
        "help": "/帮助", "help_dl": "/下载帮助",
    }

    def handle_command(self, content, channel_id, msg_id, user_id):
        self._c2c = (len(str(channel_id or "")) == 32)  # C2C openid 32位
        text = content.strip()
        d = load_users()
        user = get_user(d, user_id)
        user["username"] = f"qq_{user_id}"
        if not text.startswith("/"):
            try:
                from nlp import recognize
                intent = recognize(text)
                if intent and intent in self.INTENT_MAP:
                    text = self.INTENT_MAP[intent]
            except ImportError:
                pass
        print(f"[QQ] {user_id}: {text}")

        if text in ["/帮助", "/help"]:
            self.reply(channel_id, msg_id,
                "📖 使用帮助\n\n📥 发送链接 - 下载视频\n📝 /签到 - 每日签到+10积分\n💰 /我的 - 查看积分\n🏆 /排行 - 积分排行榜\n🎰 /抽奖 - 积分抽奖\n🎮 /游戏 - 游戏大厅\n🎨 /娱乐 - 娱乐功能\n💎 /商城 - 积分商城\n\n支持国内无水印+国外1752+平台")
        elif text in ["/签到", "/sign"]:
            ok, msg = do_sign(user)
            if ok: save_users(d)
            self.reply(channel_id, msg_id, msg)
        elif text in ["/我的", "/me"]:
            vip = "是 ✅" if is_vip(user) else "否"
            bag = get_bag(user)
            r_p, _ = get_my_rank(user_id, "points")
            r_d, _ = get_my_rank(user_id, "downloads")
            r_s, _ = get_my_rank(user_id, "sign")
            r_p = f"第{r_p}名" if r_p else "未上榜"
            r_d = f"第{r_d}名" if r_d else "未上榜"
            r_s = f"第{r_s}名" if r_s else "未上榜"
            vip_info = f"{vip}（到期：{user.get('vip_until','')}）" if is_vip(user) else vip
            self.reply(channel_id, msg_id,
                f"👤 我的信息\n"
                f"━━━━━━━━━━━━━━\n"
                f"🆔 用户ID：{user_id}\n"
                f"💰 积分：{user['points']}（🏆 {r_p}）\n"
                f"📥 累计下载：{user['downloads_total']}（📊 {r_d}）\n"
                f"📝 连续签到：{user.get('sign_streak',0)}天（🔥 {r_s}）\n"
                f"📥 今日下载：{user['downloads_today']}\n"
                f"👑 VIP：{vip_info}\n"
                f"🎒 背包：下载券{bag.get('download_tickets',0)}张 | 日卡{bag.get('day_cards',0)}张\n"
                f"📅 注册时间：{user.get('created_at','未知')}")
        elif text in ["/排行", "/rank"]:
            ranking = get_ranking("points", 10)
            medals = ["🥇","🥈","🥉"] + [f"{i}." for i in range(4,11)]
            msg = "🏆 积分排行榜\n\n"
            for i, r in enumerate(ranking):
                name = f"@{r['username']}" if r.get('username') else f"用户{r['uid'][-4:]}"
                msg += f"{medals[i]} {name} - {r['points']}分\n"
            self.reply(channel_id, msg_id, msg)
        elif text in ["/排名", "/myrank"]:
            rank, info = get_my_rank(user_id)
            if rank:
                self.reply(channel_id, msg_id, f"📊 你的排名：第{rank}名\n积分：{info['points']}\n下载：{info['downloads_total']}")
            else:
                self.reply(channel_id, msg_id, "暂无排名")
        elif text in ["/抽奖", "/lottery"]:
            self.reply(channel_id, msg_id,
                "🎰 幸运抽奖\n\n单抽50积分，十连450积分\n\n奖品：\n🏆 VIP1月 (0.1%)\n🥇 日卡×3 (3%)\n🥈 日卡×1 (8%)\n🥉 100积分 (15%)\n🎁 50积分 (25%)\n🎫 20积分 (48.9%)\n\n发送 /单抽 或 /十连")
        elif text == "/单抽":
            if user["points"] < 50:
                self.reply(channel_id, msg_id, f"❌ 积分不足（需要50，当前{user['points']}）")
                return
            user["points"] -= 50
            r = random.random() * 100
            if r < 0.1: prize = "🏆VIP1月"; user["vip_until"] = str(date.today() + timedelta(days=30))
            elif r < 3.1: prize = "🥇日卡×3"; add_to_bag(user, "day_cards", 3)
            elif r < 11.1: prize = "🥈日卡×1"; add_to_bag(user, "day_cards", 1)
            elif r < 26.1: prize = "🥉100积分"; user["points"] += 100
            elif r < 51.1: prize = "🎁50积分"; user["points"] += 50
            else: prize = "🎫20积分"; user["points"] += 20
            save_users(d)
            self.reply(channel_id, msg_id, f"🎰 {prize}\n积分：{user['points']}")
        elif text == "/十连":
            if user["points"] < 450:
                self.reply(channel_id, msg_id, f"❌ 积分不足（需要450，当前{user['points']}）")
                return
            user["points"] -= 450
            results = []
            for _ in range(10):
                r = random.random() * 100
                if r < 0.1: results.append("🏆VIP"); user["vip_until"] = str(date.today() + timedelta(days=30))
                elif r < 3.1: results.append("🥇日卡×3"); add_to_bag(user, "day_cards", 3)
                elif r < 11.1: results.append("🥈日卡×1"); add_to_bag(user, "day_cards", 1)
                elif r < 26.1: results.append("🥉100"); user["points"] += 100
                elif r < 51.1: results.append("🎁50"); user["points"] += 50
                else: results.append("🎫20"); user["points"] += 20
            save_users(d)
            self.reply(channel_id, msg_id, f"🎰 十连\n{' '.join(results)}\n积分：{user['points']}")
        elif text in ["/商城", "/shop"]:
            self.reply(channel_id, msg_id,
                "💎 积分商城\n\n1. /买券 - 下载券×10（80积分）\n2. /买卡 - 日卡（200积分）\n3. /背包 - 查看我的物品")
        elif text == "/买券":
            if user["points"] >= 80:
                user["points"] -= 80
                add_to_bag(user, "download_tickets", 10)
                save_users(d)
                self.reply(channel_id, msg_id, f"✅ 购买成功！+10下载券\n积分：{user['points']}")
            else:
                self.reply(channel_id, msg_id, f"❌ 积分不足（需要80，当前{user['points']}）")
        elif text == "/买卡":
            if user["points"] >= 200:
                user["points"] -= 200
                add_to_bag(user, "day_cards", 1)
                save_users(d)
                self.reply(channel_id, msg_id, f"✅ 购买成功！+1日卡\n积分：{user['points']}")
            else:
                self.reply(channel_id, msg_id, f"❌ 积分不足（需要200，当前{user['points']}）")
        elif text in ["/背包", "/bag"]:
            bag = get_bag(user)
            self.reply(channel_id, msg_id, f"🎒 我的背包\n\n下载券：{bag.get('download_tickets',0)}张\n日卡：{bag.get('day_cards',0)}张")
        elif text in ["/游戏", "/games"]:
            self.reply(channel_id, msg_id,
                "🎮 游戏大厅（每次10积分）\n\n🎲 /骰子 - 掷骰子\n🪙 /硬币 - 猜硬币\n✊ /剪刀 - 石头剪刀布\n🎰 /老虎机 - 老虎机\n🔢 /猜数 - 猜数字")
        elif text in ["/骰子", "/dice"]:
            if user["points"] < 10:
                self.reply(channel_id, msg_id, "❌ 积分不足"); return
            user["points"] -= 10
            dice, total, result, prize = roll_dice()
            user["points"] += prize
            save_users(d)
            self.reply(channel_id, msg_id, f"🎲 {' '.join(str(x) for x in dice)}\n{total}（{result}）\n{'🎉+'+str(prize) if prize>10 else '😢'}\n积分：{user['points']}")
        elif text in ["/硬币", "/coin"]:
            if user["points"] < 10:
                self.reply(channel_id, msg_id, "❌ 积分不足"); return
            user["points"] -= 10
            choice = random.choice(["head", "tail"])
            result, win, prize = coinflip(10, choice)
            if win: user["points"] += prize
            save_users(d)
            cn = {"head":"正面","tail":"反面"}
            self.reply(channel_id, msg_id, f"🪙 {cn[result]}\n{'🎉+'+str(prize) if win else '😢'}\n积分：{user['points']}")
        elif text in ["/剪刀", "/rps"]:
            if user["points"] < 10:
                self.reply(channel_id, msg_id, "❌ 积分不足"); return
            user["points"] -= 10
            c = random.choice(["rock","paper","scissors"])
            p1, p2, result, prize = rps(c, 10)
            if prize > 10: user["points"] += prize
            save_users(d)
            self.reply(channel_id, msg_id, f"✊ {p1} vs {p2}\n{result}\n积分：{user['points']}")
        elif text in ["/老虎机", "/slot"]:
            if user["points"] < 10:
                self.reply(channel_id, msg_id, "❌ 积分不足"); return
            user["points"] -= 10
            reels, msg, prize = slot_machine(10)
            user["points"] += prize
            save_users(d)
            self.reply(channel_id, msg_id, f"🎰 {'|'.join(reels)}\n{msg}\n积分：{user['points']}")
        elif text in ["/猜数", "/guess"]:
            if user["points"] < 10:
                self.reply(channel_id, msg_id, "❌ 积分不足"); return
            user["points"] -= 10
            answer, diff, prize, msg = guess_number(10, random.randint(1,100))
            if prize > 0: user["points"] += prize
            save_users(d)
            self.reply(channel_id, msg_id, f"🔢 {msg}\n积分：{user['points']}")
        elif text in ["/娱乐", "/fun"]:
            self.reply(channel_id, msg_id,
                "🎨 娱乐天地\n\n🔮 /运势 - 今日运势\n🃏 /塔罗 - 塔罗牌占卜\n😂 /笑话 - 听个笑话\n📜 /古诗 - 来首古诗\n🎬 /电影 - 推荐电影\n❓ /谜语 - 猜谜语\n💕 /爱情 - 爱情配对\n✨ /昵称 - 趣味昵称")
        elif text in ["/运势", "/fortune"]:
            level, emoji, desc, scores = get_fortune(user_id)
            msg = f"🔮 {emoji} {level}\n{desc}\n\n"
            for k, v in scores.items():
                msg += f"{k}：{'█'*(v//10)}{'░'*(10-v//10)} {v}\n"
            self.reply(channel_id, msg_id, msg)
        elif text in ["/塔罗", "/tarot"]:
            card, pos = get_tarot()
            self.reply(channel_id, msg_id, f"🃏 {card['emoji']} {card['name']}（{pos}）\n{card['meaning']}")
        elif text in ["/笑话", "/joke"]:
            self.reply(channel_id, msg_id, f"😂 {get_joke()}")
        elif text in ["/古诗", "/poem"]:
            p = get_poem()
            self.reply(channel_id, msg_id, f"📜 {p['title']}\n{p['author']}\n\n{p['content']}")
        elif text in ["/电影", "/movie"]:
            m = get_movie()
            self.reply(channel_id, msg_id, f"🎬 《{m['name']}》\n{m['type']}\n{m['desc']}")
        elif text in ["/谜语", "/riddle"]:
            r = get_riddle()
            self.reply(channel_id, msg_id, f"❓ {r['q']}\n\n💡 回复 /答案 查看答案")
            self._last_riddle = r.get("a", "")
        elif text == "/答案":
            if hasattr(self, '_last_riddle'):
                self.reply(channel_id, msg_id, f"💡 答案：{self._last_riddle}")
            else:
                self.reply(channel_id, msg_id, "先发送 /谜语")
        elif text in ["/爱情", "/love"]:
            self.reply(channel_id, msg_id, f"💕 {get_love()}")
        elif text in ["/昵称", "/name"]:
            self.reply(channel_id, msg_id, f"✨ {gen_nickname()}")
        elif text == "/vip介绍":
            self.reply(channel_id, msg_id, "👑 VIP会员\n\n套餐：1.88元/30天\n权益：无限下载次数\n\n联系管理员购买")
        elif text == "/下载帮助":
            self.reply(channel_id, msg_id, "📥 下载帮助\n\n直接发送链接即可下载\n\n国内：抖音/快手/B站/小红书（无水印）\n国外：YouTube/TikTok/Twitter等\n\n每次下载消耗5积分（VIP无限）")

        # 管理员命令（仅当文本是管理指令时才拦截，链接不拦截）
        if is_admin_qq(user_id) and text in ["管理面板", "管理", "后台", "控制台"]:
            text = "/admin"
        elif text == "/用户列表" and is_admin_qq(user_id):
            users = sorted(d.items(), key=lambda x: x[1].get('points', 0), reverse=True)
            msg = f"👥 用户列表（共{len(users)}人）\n\n"
            for i, (uid, u) in enumerate(users[:30]):
                name = u.get('first_name', '') or u.get('username', '') or str(uid)
                pts = u.get('points', 0)
                vip = "👑" if is_vip(u) else ""
                msg += f"{i+1}. {name} {vip} (ID:{uid}) - {pts}分\n"
            if len(users) > 30:
                msg += f"\n...共{len(users)}人，仅显示前30"
            self.reply(channel_id, msg_id, msg)
        elif text == "/admin" and is_admin_qq(user_id):
            self.reply(channel_id, msg_id,
                "🛠️ 管理员面板\n\n📊 /统计 - 数据统计\n💰 /加积分 用户ID 数量\n👑 /给vip 用户ID 天数\n🚫 /封禁 用户ID\n🔓 /解封 用户ID\n📢 /群发 内容\n🎁 /全员抽奖\n⚙️ /状态\n👥 /用户列表 - 查看所有用户\n\n💡 也可发送：管理面板/签到/查积分等自然语言")
        elif text == "/统计" and is_admin_qq(user_id):
            s = get_stats()
            self.reply(channel_id, msg_id, f"📊 用户{s['total_users']} 活跃{s['today_active']}\n下载{s['total_downloads']} VIP{s['vip_count']}")
        elif text.startswith("/加积分") and is_admin_qq(user_id):
            parts = text.split()
            if len(parts) >= 3:
                target = parts[1].lstrip("@")
                amount = int(parts[2])
                found = False
                for uid, u in d.items():
                    if str(uid) == target or u.get("username") == target:
                        add_points(u, amount)
                        save_users(d)
                        self.reply(channel_id, msg_id, f"✅ 用户{uid} +{amount}，当前{u['points']}")
                        found = True
                        break
                if not found:
                    d[target] = get_user(d, target)
                    add_points(d[target], amount)
                    save_users(d)
                    self.reply(channel_id, msg_id, f"✅ 新用户{target} +{amount}，当前{d[target]['points']}")
            else:
                self.reply(channel_id, msg_id, "用法：/加积分 用户ID 数量")
        elif text.startswith("/给vip") and is_admin_qq(user_id):
            parts = text.split()
            if len(parts) >= 3:
                target = parts[1].lstrip("@")
                days = int(parts[2])
                found = False
                for uid, u in d.items():
                    if str(uid) == target or u.get("username") == target:
                        expire = give_vip(u, days)
                        save_users(d)
                        self.reply(channel_id, msg_id, f"✅ 用户{uid} VIP {days}天\n到期：{expire}")
                        found = True
                        break
                if not found:
                    d[target] = get_user(d, target)
                    expire = give_vip(d[target], days)
                    save_users(d)
                    self.reply(channel_id, msg_id, f"✅ 新用户{target} VIP {days}天\n到期：{expire}")
            else:
                self.reply(channel_id, msg_id, "用法：/给vip 用户ID 天数")
        elif text.startswith("/全员抽奖") and is_admin_qq(user_id):
            prizes = {"VIP":0, "100":0, "50":0, "20":0}
            for uid, u in d.items():
                r = random.random() * 100
                if r < 0.5: u["vip_until"] = str(date.today() + timedelta(days=7)); prizes["VIP"] += 1
                elif r < 10: u["points"] += 100; prizes["100"] += 1
                elif r < 30: u["points"] += 50; prizes["50"] += 1
                else: u["points"] += 20; prizes["20"] += 1
            save_users(d)
            self.reply(channel_id, msg_id, "🎁 全员抽奖\n\n" + "\n".join(f"{k}：{v}人" for k,v in prizes.items()))
        elif text == "/状态" and is_admin_qq(user_id):
            import psutil
            self.reply(channel_id, msg_id, f"⚙️ CPU:{psutil.cpu_percent()}% 内存:{psutil.virtual_memory().percent}% 磁盘:{psutil.disk_usage('/').percent}%")
        else:
            urls = re.findall(r"https?://[^\s]+", text)
            if urls:
                bag = get_bag(user)
                if is_vip(user): pass
                elif bag.get("download_tickets", 0) > 0:
                    use_from_bag(user, "download_tickets")
                    self.reply(channel_id, msg_id, "📥 使用下载券")
                else:
                    ok, msg = spend_point(user)
                    if not ok:
                        self.reply(channel_id, msg_id, f"❌ {msg}\n发送 /签到 获得积分")
                        return
                save_users(d)
                print(f"[DL] 开始下载: {urls[0][:50]}")
                result = download_video(urls[0], user_id)
                print(f"[DL] 下载结果: success={result.get('success')} type={result.get('type','')} err={result.get('error','')} paths={len(result.get('paths',[]))}")
                if result["success"]:
                    user["downloads_today"] += 1
                    user["downloads_total"] += 1
                    save_users(d)
                    title = result.get("title", "")
                    paths = result.get("paths", [])
                    if result["type"] == "video":
                        # 视频：上传并发送（QQ 限制 25MB）
                        p = paths[0] if paths else None
                        if p and os.path.exists(p):
                            sz = os.path.getsize(p)
                            print(f"[DL] 视频大小: {sz//1024}KB")
                            if sz > 25 * 1024 * 1024:
                                self.reply(channel_id, msg_id, f"⚠️ 视频过大（{sz//1024//1024}MB > 25MB），无法发送")
                            else:
                                self.reply(channel_id, msg_id, "⏳ 正在上传视频...")
                                print("[DL] 上传视频中...")
                                fi = self.upload_file(channel_id, p, 2)
                                print(f"[DL] 上传结果: {bool(fi)}")
                                if fi:
                                    ok = self.send_media(channel_id, msg_id, fi, title or "")
                                    print(f"[DL] 发送结果: {ok}")
                                else:
                                    self.reply(channel_id, msg_id, "❌ 视频上传失败")
                        else:
                            self.reply(channel_id, msg_id, "❌ 视频文件不存在")
                    elif result["type"] == "image":
                        # 图片：逐张上传发送
                        sent = 0
                        for i, p in enumerate(paths[:10]):
                            if not os.path.exists(p): continue
                            print(f"[DL] 上传图片{i+1}/{len(paths[:10])}...")
                            fi = self.upload_file(channel_id, p)
                            if fi and self.send_media(channel_id, msg_id, fi):
                                sent += 1
                        print(f"[DL] 图片发送完成: {sent}张")
                        self.reply(channel_id, msg_id, f"🖼️ 已发送 {sent} 张图片" if sent else "❌ 图片发送失败")
                    for p in paths:
                        try: os.remove(p)
                        except: pass
                    if result.get("img_dir"):
                        shutil.rmtree(result["img_dir"], ignore_errors=True)
                else:
                    self.reply(channel_id, msg_id, f"❌ {result.get('error', '下载失败')}")
            else:
                self.reply(channel_id, msg_id, "发送链接下载视频，或发送 /帮助 查看命令")

    def on_message(self, event):
        if event.get("op") == 0:
            t = event.get("t")
            d = event.get("d", {})
            self.seq = event.get("s")
            if t in ["MESSAGE_CREATE", "AT_MESSAGE_CREATE"]:
                content = d.get("content", "")
                channel_id = d.get("channel_id")
                user_id = d.get("author", {}).get("id", "0")
                msg_id = d.get("id")
                self.handle_command(content, channel_id, msg_id, user_id)
            elif t == "C2C_MESSAGE_CREATE":
                content = d.get("content", "")
                openid = d.get("author", {}).get("id", "")
                msg_id = d.get("id")
                self.handle_command(content, openid, msg_id, openid)
        elif event.get("op") == 10:
            interval = event.get("d", {}).get("heartbeat_interval", 41250)
            threading.Thread(target=self.heartbeat_loop, args=(interval,), daemon=True).start()

    def heartbeat_loop(self, interval):
        while True:
            time.sleep(interval / 1000)
            if self.ws:
                try: self.ws.send(json.dumps({"op": 1, "d": self.seq}))
                except: pass

    def on_ws_message(self, ws, message):
        try: self.on_message(json.loads(message))
        except: pass

    def on_ws_error(self, ws, error):
        print("[ws error]", error)

    def on_ws_close(self, ws, code, msg):
        print("[ws close]", code, msg)
        if code in [4009, 4001, 4008, 4010]:
            print("[ws] 断线重连...")
            time.sleep(3)
            self.run()

    def on_ws_open(self, ws):
        print("[ws] 已连接")
        token = self.get_token()
        if token:
            ws.send(json.dumps({"op": 2, "d": {"token": "QQBot " + token, "intents": 1 | 4097 | (1 << 25), "shard": [0, 1], "properties": {"os": "linux", "browser": "python", "device": "bot"}}}))

    def run(self):
        print("🚀 启动 QQ 机器人...")
        r = self.api("GET", "/gateway")
        gateway = r.get("url")
        if not gateway:
            print("❌ 获取网关失败:", r)
            return
        print(f"📡 网关: {gateway}")
        self.ws = websocket.WebSocketApp(gateway, on_open=self.on_ws_open, on_message=self.on_ws_message, on_error=self.on_ws_error, on_close=self.on_ws_close)
        self.ws.run_forever()

if __name__ == "__main__":
    QQBot().run()
