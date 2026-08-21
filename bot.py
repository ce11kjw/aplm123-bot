#!/usr/bin/env python3
"""aplm123 视频下载机器人"""
import os, re, random, asyncio, shutil
from datetime import date, timedelta, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler, filters

from downloader import download as _download_sync
from data_manager import *
from games import roll_dice, coinflip, rps, slot_machine, guess_number
from entertainment import get_fortune, get_tarot, get_joke, get_poem, get_movie, get_riddle, get_love, gen_nickname
from nlp import recognize
from user_query import register_query_handlers, query_user, query_common_chats, query_chat, get_my_info

TOKEN = os.getenv("TG_TOKEN", "")
DL_DIR = os.getenv("DL_DIR", "/root/aplm123-bot/downloads")
os.makedirs(DL_DIR, exist_ok=True)

async def download(url, uid):
    return await asyncio.to_thread(_download_sync, url, uid)

admin_state = {}

def set_admin_state(uid, action, step=1, data=None):
    admin_state[uid] = {"action": action, "step": step, "data": data or {}}

def get_admin_state(uid):
    return admin_state.get(uid)

def clear_admin_state(uid):
    if uid in admin_state:
        del admin_state[uid]

def admin_only(func):
    async def wrapper(update: Update, ctx: CallbackContext):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ 无权限，仅管理员可用")
            return
        return await func(update, ctx)
    return wrapper

def get_username_display(user):
    if user.get("username"):
        return f"@{user['username']}"
    return user.get("first_name", f"用户{user.get('uid','')[-4:]}")

def main_menu():
    kb = [
        [InlineKeyboardButton("💰 我的积分", callback_data="points"),
         InlineKeyboardButton("📝 每日签到", callback_data="sign")],
        [InlineKeyboardButton("🏆 排行榜", callback_data="ranking"),
         InlineKeyboardButton("🎁 积分商城", callback_data="shop")],
        [InlineKeyboardButton("🎰 幸运抽奖", callback_data="lottery"),
         InlineKeyboardButton("👑 VIP会员", callback_data="vip")],
        [InlineKeyboardButton("📊 我的排名", callback_data="my_rank"),
         InlineKeyboardButton("📖 使用帮助", callback_data="help")]
    ]
    notice = get_notice()
    text = (
        "🤖 aplm123 视频下载机器人\n\n"
        "📥 发送链接 - 下载视频/图片\n"
        "📝 /sign - 每日签到+10积分\n"
        "💰 /me - 查看积分\n"
        "🏆 /rank - 排行榜\n\n"
        f"📢 公告：{notice}\n\n"
        "支持平台：\n"
        "• 国内：抖音/快手/西瓜/小红书/微博/B站\n"
        "• 国外：YouTube/TikTok/Twitter等1752+平台\n\n"
        "🎁 新用户赠送100积分"
    )
    return text, InlineKeyboardMarkup(kb)

def admin_menu():
    kb = [
        [InlineKeyboardButton("📊 数据统计", callback_data="admin_stats"),
         InlineKeyboardButton("🏆 排行榜", callback_data="admin_ranking")],
        [InlineKeyboardButton("💰 积分管理", callback_data="admin_points"),
         InlineKeyboardButton("👑 VIP管理", callback_data="admin_vip")],
        [InlineKeyboardButton("🚫 用户管理", callback_data="admin_user"),
         InlineKeyboardButton("🎁 福利活动", callback_data="admin_event")],
        [InlineKeyboardButton("📢 消息推送", callback_data="admin_msg"),
         InlineKeyboardButton("⚙️ 系统管理", callback_data="admin_sys")],
        [InlineKeyboardButton("← 返回用户菜单", callback_data="back")]
    ]
    return "🛠️ 管理员控制台\n\n选择要管理的功能：", InlineKeyboardMarkup(kb)

async def cmd_admin(update: Update, ctx: CallbackContext):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ 无权限，仅管理员可用")
        return
    text, kb = admin_menu()
    await update.message.reply_text(text, reply_markup=kb)

async def cmd_start(update: Update, ctx: CallbackContext):
    d = load_users()
    user = get_user(d, update.effective_user.id)
    update_user_info(user, update)
    banned, msg = is_banned(update.effective_user.id)
    if banned:
        await update.message.reply_text(f"⛔ {msg}")
        return
    save_users(d)
    text, kb = main_menu()
    await update.message.reply_text(text, reply_markup=kb)

async def cmd_sign(update: Update, ctx: CallbackContext):
    d = load_users()
    user = get_user(d, update.effective_user.id)
    update_user_info(user, update)
    ok, msg = do_sign(user)
    if ok: save_users(d)
    await update.message.reply_text(msg)

async def cmd_me(update: Update, ctx: CallbackContext):
    d = load_users()
    user = get_user(d, update.effective_user.id)
    update_user_info(user, update)
    vip = "是 ✅" if is_vip(user) else "否"
    await update.message.reply_text(
        f"💰 我的积分：{user.get('points',0)}\n"
        f"📥 今日下载：{user.get('downloads_today',0)}\n"
        f"📊 累计下载：{user.get('downloads_total',0)}\n"
        f"📝 连续签到：{user.get('sign_streak',0)}天\n"
        f"👑 VIP会员：{vip}")

async def cmd_rank(update: Update, ctx: CallbackContext):
    ranking = get_ranking("points", 10)
    if not ranking:
        await update.message.reply_text("暂无数据")
        return
    text = "🏆 积分排行榜 TOP10\n\n"
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i, r in enumerate(ranking):
        text += f"{medals[i]} {get_username_display(r)} - {r['points']}分\n"
    await update.message.reply_text(text)

async def cmd_help(update: Update, ctx: CallbackContext):
    await update.message.reply_text(
        "📖 使用帮助\n\n"
        "📥 发送链接即可下载视频/图片\n"
        "📝 /sign - 每日签到+10积分\n"
        "💰 /me - 查看我的信息\n"
        "🏆 /rank - 积分排行榜\n"
        "🎰 /lottery - 抽奖（50积分）\n"
        "💎 /shop - 积分商城\n\n"
        "每次下载消耗5积分（VIP无限）")

# ===== 游戏/娱乐 =====
async def game_dice(update, ctx):
    d = load_users()
    user = get_user(d, update.effective_user.id)
    if user.get("points", 0) < 10:
        await update.message.reply_text("❌ 积分不足（需要10）"); return
    user["points"] -= 10
    dice, total, result, prize = roll_dice()
    user["points"] += prize
    save_users(d)
    await update.message.reply_text(f"🎲 {' '.join(str(x) for x in dice)}\n{total}（{result}）\n{'🎉+'+str(prize) if prize>10 else '😢'}\n积分：{user['points']}")

async def game_coin(update, ctx):
    d = load_users()
    user = get_user(d, update.effective_user.id)
    if user.get("points", 0) < 10:
        await update.message.reply_text("❌ 积分不足"); return
    user["points"] -= 10
    choice = random.choice(["head", "tail"])
    result, win, prize = coinflip(10, choice)
    if win: user["points"] += prize
    save_users(d)
    cn = {"head":"正面","tail":"反面"}
    await update.message.reply_text(f"🪙 {cn[result]}\n{'🎉+'+str(prize) if win else '😢'}\n积分：{user['points']}")

async def game_rps(update, ctx):
    d = load_users()
    user = get_user(d, update.effective_user.id)
    if user.get("points", 0) < 10:
        await update.message.reply_text("❌ 积分不足"); return
    user["points"] -= 10
    c = random.choice(["rock","paper","scissors"])
    p1, p2, result, prize = rps(c, 10)
    if prize > 10: user["points"] += prize
    save_users(d)
    await update.message.reply_text(f"✊ {p1} vs {p2}\n{result}\n积分：{user['points']}")

async def game_slot(update, ctx):
    d = load_users()
    user = get_user(d, update.effective_user.id)
    if user.get("points", 0) < 10:
        await update.message.reply_text("❌ 积分不足"); return
    user["points"] -= 10
    reels, msg, prize = slot_machine(10)
    user["points"] += prize
    save_users(d)
    await update.message.reply_text(f"🎰 {'|'.join(reels)}\n{msg}\n积分：{user['points']}")

async def game_guess(update, ctx):
    d = load_users()
    user = get_user(d, update.effective_user.id)
    if user.get("points", 0) < 10:
        await update.message.reply_text("❌ 积分不足"); return
    user["points"] -= 10
    answer, diff, prize, msg = guess_number(10, random.randint(1,100))
    if prize > 0: user["points"] += prize
    save_users(d)
    await update.message.reply_text(f"🔢 {msg}\n积分：{user['points']}")

async def fun_fortune(update, ctx):
    level, emoji, desc, scores = get_fortune(update.effective_user.id)
    msg = f"🔮 {emoji} {level}\n{desc}\n\n"
    for k, v in scores.items():
        msg += f"{k}：{'█'*(v//10)}{'░'*(10-v//10)} {v}\n"
    await update.message.reply_text(msg)

async def fun_tarot(update, ctx):
    card, pos = get_tarot()
    await update.message.reply_text(f"🃏 {card['emoji']} {card['name']}（{pos}）\n{card['meaning']}")

async def fun_poem(update, ctx):
    p = get_poem()
    await update.message.reply_text(f"📜 {p['title']}\n{p['author']}\n\n{p['content']}")

async def fun_movie(update, ctx):
    m = get_movie()
    await update.message.reply_text(f"🎬 《{m['name']}》\n{m['type']}\n{m['desc']}")

async def fun_riddle(update, ctx):
    r = get_riddle()
    await update.message.reply_text(f"❓ {r['q']}\n\n💡 回复 /答案 查看答案")
    ctx.user_data["riddle"] = r.get("a", "")

# ===== 管理员命令 =====
@admin_only
async def cmd_stats(update: Update, ctx: CallbackContext):
    stats = get_stats()
    await update.message.reply_text(
        f"📊 数据统计\n\n👥 总用户数：{stats['total_users']}\n"
        f"🔥 今日活跃：{stats['today_active']}\n"
        f"📥 总下载量：{stats['total_downloads']}\n"
        f"💰 总积分流通：{stats['total_points']}\n"
        f"👑 VIP会员：{stats['vip_count']}")

@admin_only
async def cmd_addpoint(update: Update, ctx: CallbackContext):
    if len(ctx.args) < 2:
        await update.message.reply_text("用法：/addpoint @用户 数量")
        return
    target = ctx.args[0].lstrip("@")
    amount = int(ctx.args[1])
    d = load_users()
    for uid, u in d.items():
        if u.get("username") == target:
            add_points(u, amount, "管理员发放")
            save_users(d)
            await update.message.reply_text(f"✅ 已给 @{target} 添加 {amount} 积分")
            return
    await update.message.reply_text(f"❌ 未找到用户 @{target}")

@admin_only
async def cmd_delpoint(update: Update, ctx: CallbackContext):
    if len(ctx.args) < 2:
        await update.message.reply_text("用法：/delpoint @用户 数量")
        return
    target = ctx.args[0].lstrip("@")
    amount = int(ctx.args[1])
    d = load_users()
    for uid, u in d.items():
        if u.get("username") == target:
            u["points"] = max(0, u.get("points", 0) - amount)
            save_users(d)
            await update.message.reply_text(f"✅ 已扣除 @{target} {amount} 积分")
            return
    await update.message.reply_text(f"❌ 未找到用户 @{target}")

@admin_only
async def cmd_setpoint(update: Update, ctx: CallbackContext):
    if len(ctx.args) < 2:
        await update.message.reply_text("用法：/setpoint @用户 数量")
        return
    target = ctx.args[0].lstrip("@")
    amount = int(ctx.args[1])
    d = load_users()
    for uid, u in d.items():
        if u.get("username") == target:
            set_points(u, amount)
            save_users(d)
            await update.message.reply_text(f"✅ 已设置 @{target} 积分为 {amount}")
            return
    await update.message.reply_text(f"❌ 未找到用户 @{target}")

@admin_only
async def cmd_batch_addall(update: Update, ctx: CallbackContext):
    if not ctx.args:
        await update.message.reply_text("用法：/batch_addall 数量")
        return
    amount = int(ctx.args[0])
    d = load_users()
    count = 0
    for uid, u in d.items():
        u["points"] = u.get("points", 0) + amount
        count += 1
    save_users(d)
    await update.message.reply_text(f"✅ 已给 {count} 位用户每人发放 {amount} 积分")

@admin_only
async def cmd_points_log(update: Update, ctx: CallbackContext):
    logs = get_logs(10)
    if not logs:
        await update.message.reply_text("暂无日志")
        return
    text = "📝 积分变动日志（最近10条）\n\n"
    for log in reversed(logs):
        text += f"[{log['time']}] {log['action']}\n"
    await update.message.reply_text(text)

@admin_only
async def cmd_givevip(update: Update, ctx: CallbackContext):
    if len(ctx.args) < 2:
        await update.message.reply_text("用法：/givevip @用户 天数")
        return
    target = ctx.args[0].lstrip("@")
    days = int(ctx.args[1])
    d = load_users()
    for uid, u in d.items():
        if u.get("username") == target:
            expire = give_vip(u, days)
            save_users(d)
            await update.message.reply_text(f"✅ 已给 @{target} 授予VIP {days}天\n到期时间：{expire}")
            return
    await update.message.reply_text(f"❌ 未找到用户 @{target}")

@admin_only
async def cmd_revipvip(update: Update, ctx: CallbackContext):
    if not ctx.args:
        await update.message.reply_text("用法：/revipvip @用户")
        return
    target = ctx.args[0].lstrip("@")
    d = load_users()
    for uid, u in d.items():
        if u.get("username") == target:
            remove_vip(u)
            save_users(d)
            await update.message.reply_text(f"✅ 已撤销 @{target} 的VIP")
            return
    await update.message.reply_text(f"❌ 未找到用户 @{target}")

@admin_only
async def cmd_vip_list(update: Update, ctx: CallbackContext):
    vip_list = get_vip_list()
    if not vip_list:
        await update.message.reply_text("暂无VIP用户")
        return
    text = "👑 VIP用户列表\n\n"
    for v in vip_list:
        text += f"• {get_username_display(v)} - 到期：{v['vip_until']}\n"
    await update.message.reply_text(text)

@admin_only
async def cmd_ban(update: Update, ctx: CallbackContext):
    if not ctx.args:
        await update.message.reply_text("用法：/ban @用户")
        return
    target = ctx.args[0].lstrip("@")
    d = load_users()
    for uid, u in d.items():
        if u.get("username") == target:
            ban_user(uid)
            save_users(d)
            await update.message.reply_text(f"✅ 已封禁 @{target}")
            return
    await update.message.reply_text(f"❌ 未找到用户 @{target}")

@admin_only
async def cmd_unban(update: Update, ctx: CallbackContext):
    if not ctx.args:
        await update.message.reply_text("用法：/unban @用户")
        return
    target = ctx.args[0].lstrip("@")
    d = load_users()
    for uid, u in d.items():
        if u.get("username") == target:
            unban_user(uid)
            save_users(d)
            await update.message.reply_text(f"✅ 已解封 @{target}")
            return
    await update.message.reply_text(f"❌ 未找到用户 @{target}")

@admin_only
async def cmd_ban_list(update: Update, ctx: CallbackContext):
    bans = get_ban_list()
    if not bans:
        await update.message.reply_text("暂无封禁用户")
        return
    text = "🚫 封禁用户列表\n\n"
    for uid in bans:
        text += f"• {uid}\n"
    await update.message.reply_text(text)

@admin_only
async def cmd_mute(update: Update, ctx: CallbackContext):
    if len(ctx.args) < 2:
        await update.message.reply_text("用法：/mute @用户 小时")
        return
    target = ctx.args[0].lstrip("@")
    hours = int(ctx.args[1])
    d = load_users()
    for uid, u in d.items():
        if u.get("username") == target:
            mute_user(uid, hours)
            save_users(d)
            await update.message.reply_text(f"✅ 已禁言 @{target} {hours}小时")
            return
    await update.message.reply_text(f"❌ 未找到用户 @{target}")

@admin_only
async def cmd_broadcast(update: Update, ctx: CallbackContext):
    if not ctx.args:
        await update.message.reply_text("用法：/broadcast 内容")
        return
    content = " ".join(ctx.args)
    d = load_users()
    success = fail = 0
    for uid in d.keys():
        try:
            await ctx.bot.send_message(int(uid), f"📢 系统公告\n\n{content}")
            success += 1
        except:
            fail += 1
    await update.message.reply_text(f"✅ 群发完成\n成功：{success}，失败：{fail}")

@admin_only
async def cmd_notice(update: Update, ctx: CallbackContext):
    if not ctx.args:
        notice = get_notice()
        await update.message.reply_text(f"当前公告：{notice}\n\n用法：/notice 新公告内容")
        return
    content = " ".join(ctx.args)
    set_notice(content)
    await update.message.reply_text(f"✅ 公告已更新为：{content}")

@admin_only
async def cmd_lottery_all(update: Update, ctx: CallbackContext):
    d = load_users()
    count = 0
    prizes = {"VIP": 0, "100积分": 0, "50积分": 0, "20积分": 0}
    for uid, u in d.items():
        r = random.random() * 100
        if r < 0.5:
            u["vip_until"] = str(date.today() + timedelta(days=7)); prizes["VIP"] += 1
        elif r < 10:
            u["points"] = u.get("points", 0) + 100; prizes["100积分"] += 1
        elif r < 30:
            u["points"] = u.get("points", 0) + 50; prizes["50积分"] += 1
        else:
            u["points"] = u.get("points", 0) + 20; prizes["20积分"] += 1
        count += 1
    save_users(d)
    text = f"🎁 全员抽奖完成！\n\n参与人数：{count}\n\n中奖情况：\n"
    for k, v in prizes.items():
        text += f"• {k}：{v}人\n"
    await update.message.reply_text(text)

@admin_only
async def cmd_status(update: Update, ctx: CallbackContext):
    import psutil
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    await update.message.reply_text(
        f"⚙️ 系统状态\n\nCPU使用率：{cpu}%\n"
        f"内存使用：{mem.percent}% ({mem.used//1024//1024}MB/{mem.total//1024//1024}MB)\n"
        f"磁盘使用：{disk.percent}% ({disk.used//1024//1024}MB/{disk.total//1024//1024}MB)")

# ===== 管理员交互输入 =====
async def handle_admin_input(update: Update, ctx: CallbackContext, text, state):
    uid = update.effective_user.id
    action = state["action"]
    step = state["step"]
    data = state["data"]
    text = text.strip()

    if step == 1 and action in ["points_add", "points_del", "points_set",
                                 "vip_give", "vip_revoke",
                                 "user_ban", "user_unban", "user_mute"]:
        try:
            target_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ 请输入数字ID")
            return
        data["target_id"] = target_id
        if action in ["points_add", "points_del", "points_set"]:
            set_admin_state(uid, action, 2, data)
            names = {"points_add": "➕ 加积分", "points_del": "➖ 扣积分", "points_set": "✏️ 设置积分"}
            await update.message.reply_text(f"{names[action]}\n\n✅ 找到用户：{target_id}\n\n请输入数量：\n例如：8888")
        elif action == "vip_give":
            set_admin_state(uid, action, 2, data)
            await update.message.reply_text(f"👑 授予VIP\n\n✅ 找到用户：{target_id}\n\n请输入天数：\n例如：30")
        elif action == "user_mute":
            set_admin_state(uid, action, 2, data)
            await update.message.reply_text(f"🔇 禁言用户\n\n✅ 找到用户：{target_id}\n\n请输入禁言小时数：\n例如：24")
        else:
            names = {"vip_revoke": "❌ 撤销VIP", "user_ban": "🚫 封禁", "user_unban": "✅ 解封"}
            kb = [[InlineKeyboardButton("✅ 确认", callback_data=f"confirm_{action}"),
                   InlineKeyboardButton("❌ 取消", callback_data="admin_back")]]
            await update.message.reply_text(f"{names[action]}\n\n✅ 找到用户：{target_id}\n\n确认执行？", reply_markup=InlineKeyboardMarkup(kb))

    elif step == 2 and action in ["points_add", "points_del", "points_set"]:
        try:
            amount = int(text)
        except ValueError:
            await update.message.reply_text("❌ 请输入数字")
            return
        data["amount"] = amount
        d = load_users()
        target_id = data["target_id"]
        user = get_user(d, target_id)
        if action == "points_add":
            user["points"] = user.get("points", 0) + amount
            result = f"✅ {target_id} +{amount}积分完成"
        elif action == "points_del":
            user["points"] = max(0, user.get("points", 0) - amount)
            result = f"✅ {target_id} -{amount}积分完成"
        else:
            user["points"] = amount
            result = f"✅ {target_id} 积分设置为 {amount}"
        save_users(d)
        clear_admin_state(uid)
        await update.message.reply_text(f"用户：{target_id}\n{result}\n当前积分：{user.get('points', 0)}")

    elif step == 2 and action == "vip_give":
        try:
            days = int(text)
        except ValueError:
            await update.message.reply_text("❌ 请输入天数")
            return
        data["days"] = days
        d = load_users()
        target_id = data["target_id"]
        user = get_user(d, target_id)
        expire = give_vip(user, days)
        save_users(d)
        clear_admin_state(uid)
        await update.message.reply_text(f"👑 VIP授予完成\n\n用户：{target_id}\n天数：{days}\n到期：{expire}")

    elif step == 2 and action == "user_mute":
        try:
            hours = int(text)
        except ValueError:
            await update.message.reply_text("❌ 请输入小时数")
            return
        data["hours"] = hours
        d = load_users()
        target_id = data["target_id"]
        mute_user(target_id, hours)
        save_users(d)
        clear_admin_state(uid)
        await update.message.reply_text(f"🔇 禁言完成\n\n用户：{target_id}\n时长：{hours}小时")

    elif step == 1 and action == "points_batch":
        try:
            amount = int(text)
        except ValueError:
            await update.message.reply_text("❌ 请输入数字")
            return
        d = load_users()
        count = 0
        for uid_str, user in d.items():
            user["points"] = user.get("points", 0) + amount
            count += 1
        save_users(d)
        clear_admin_state(uid)
        await update.message.reply_text(f"📦 全员发放完成\n\n发放数量：{amount}积分\n发放人数：{count}人")

# ===== 回调按钮 =====
async def callback(update: Update, ctx: CallbackContext):
    q = update.callback_query
    await q.answer()
    d = load_users()
    user = get_user(d, q.from_user.id)
    data = q.data

    banned, msg = is_banned(q.from_user.id)
    if banned:
        await q.edit_message_text(f"⛔ {msg}")
        return

    if data == "points":
        vip = "是 ✅" if is_vip(user) else "否"
        await q.edit_message_text(f"💰 我的积分：{user.get('points',0)}\n📥 今日下载：{user.get('downloads_today',0)}\n👑 VIP：{vip}")
    elif data == "sign":
        ok, msg = do_sign(user)
        if ok: save_users(d)
        await q.edit_message_text(msg)
    elif data == "ranking":
        ranking = get_ranking("points", 10)
        medals = ["🥇", "🥈", "🥉"] + ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        text = "🏆 积分排行榜 TOP10\n\n"
        for i, r in enumerate(ranking):
            text += f"{medals[i]} {get_username_display(r)} - {r['points']}分\n"
        kb = [[InlineKeyboardButton("返回", callback_data="back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "my_rank":
        rank, info = get_my_rank(q.from_user.id)
        text = f"📊 我的排名：第{rank}名\n积分：{info['points']}\n下载：{info['downloads_total']}" if rank else "暂无排名数据"
        kb = [[InlineKeyboardButton("返回", callback_data="back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "shop":
        kb = [
            [InlineKeyboardButton("10次下载券 - 80积分", callback_data="buy_ticket")],
            [InlineKeyboardButton("日卡 - 200积分", callback_data="buy_day")],
            [InlineKeyboardButton("返回", callback_data="back")]
        ]
        await q.edit_message_text("🎁 积分商城\n\n10次下载券 - 80积分\n日卡 - 200积分", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "buy_ticket":
        if user.get("points", 0) >= 80:
            user["points"] -= 80
            add_to_bag(user, "download_tickets", 10)
            save_users(d)
            await q.edit_message_text("✅ 购买成功！获得10次免费下载")
        else:
            await q.edit_message_text(f"❌ 积分不足（需要80，当前{user.get('points',0)}）")
    elif data == "buy_day":
        if user.get("points", 0) >= 200:
            user["points"] -= 200
            expire = give_vip(user, 1)
            save_users(d)
            await q.edit_message_text(f"✅ 购买成功！获得1天VIP\n到期时间：{expire}")
        else:
            await q.edit_message_text(f"❌ 积分不足（需要200，当前{user.get('points',0)}）")
    elif data == "lottery":
        kb = [
            [InlineKeyboardButton("单抽 - 50积分", callback_data="lottery_1")],
            [InlineKeyboardButton("十连 - 450积分", callback_data="lottery_10")],
            [InlineKeyboardButton("返回", callback_data="back")]
        ]
        await q.edit_message_text("🎰 幸运抽奖\n\n单抽：50积分\n十连：450积分\n\n奖品：\n🏆 VIP1月(0.1%)\n🥇日卡×3(3%)\n🥈日卡×1(8%)\n🥉100积分(15%)\n🎁50积分(25%)\n🎫20积分(48.9%)", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "lottery_1":
        if user.get("points", 0) < 50:
            await q.edit_message_text(f"❌ 积分不足（需要50，当前{user.get('points',0)}）")
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
        kb = [[InlineKeyboardButton("继续抽奖", callback_data="lottery"), InlineKeyboardButton("返回", callback_data="back")]]
        await q.edit_message_text(f"🎰 {prize}\n积分：{user['points']}", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "lottery_10":
        if user.get("points", 0) < 450:
            await q.edit_message_text(f"❌ 积分不足（需要450，当前{user.get('points',0)}）")
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
        kb = [[InlineKeyboardButton("继续抽奖", callback_data="lottery"), InlineKeyboardButton("返回", callback_data="back")]]
        await q.edit_message_text(f"🎰 十连\n{' '.join(results)}\n积分：{user['points']}", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "vip":
        await q.edit_message_text("👑 VIP会员\n\n套餐：1.88元/30天\n权益：无限下载\n\n联系管理员购买")
    elif data == "help":
        await q.edit_message_text("📖 使用帮助\n\n📥 发送链接下载\n📝 /sign 签到\n💰 /me 积分\n🏆 /rank 排行榜")
    elif data == "back":
        text, kb = main_menu()
        await q.edit_message_text(text, reply_markup=kb)

    elif data == "admin_stats" and is_admin(q.from_user.id):
        stats = get_stats()
        text = f"📊 数据统计\n\n👥 总用户：{stats['total_users']}\n🔥 今日活跃：{stats['today_active']}\n📥 总下载：{stats['total_downloads']}\n💰 总积分：{stats['total_points']}\n👑 VIP：{stats['vip_count']}"
        kb = [[InlineKeyboardButton("返回", callback_data="admin_back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "admin_ranking" and is_admin(q.from_user.id):
        ranking = get_ranking("points", 10)
        medals = ["🥇","🥈","🥉"] + ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        text = "🏆 排行榜\n\n"
        for i, r in enumerate(ranking):
            text += f"{medals[i]} {get_username_display(r)} - {r['points']}分\n"
        kb = [[InlineKeyboardButton("返回", callback_data="admin_back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "admin_points" and is_admin(q.from_user.id):
        kb = [
            [InlineKeyboardButton("➕ 加积分", callback_data="points_add"),
             InlineKeyboardButton("➖ 扣积分", callback_data="points_del")],
            [InlineKeyboardButton("✏️ 设置积分", callback_data="points_set")],
            [InlineKeyboardButton("📊 积分日志", callback_data="points_log"),
             InlineKeyboardButton("📦 全员发放", callback_data="points_batch")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]
        ]
        await q.edit_message_text("💰 积分管理\n\n请选择操作：", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "admin_vip" and is_admin(q.from_user.id):
        kb = [
            [InlineKeyboardButton("👑 授予VIP", callback_data="vip_give"),
             InlineKeyboardButton("❌ 撤销VIP", callback_data="vip_revoke")],
            [InlineKeyboardButton("📋 VIP列表", callback_data="vip_list")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]
        ]
        await q.edit_message_text("👑 VIP管理\n\n请选择操作：", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "admin_user" and is_admin(q.from_user.id):
        kb = [
            [InlineKeyboardButton("🚫 封禁用户", callback_data="user_ban"),
             InlineKeyboardButton("✅ 解封用户", callback_data="user_unban")],
            [InlineKeyboardButton("🔇 禁言用户", callback_data="user_mute"),
             InlineKeyboardButton("📋 封禁列表", callback_data="ban_list")],
            [InlineKeyboardButton("👥 用户列表", callback_data="user_list"),
             InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]
        ]
        await q.edit_message_text("🚫 用户管理\n\n请选择操作：", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "admin_event" and is_admin(q.from_user.id):
        kb = [
            [InlineKeyboardButton("🎰 全员抽奖", callback_data="event_lottery_all")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]
        ]
        await q.edit_message_text("🎁 福利活动\n\n请选择操作：", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "admin_msg" and is_admin(q.from_user.id):
        text = "📢 消息推送命令\n\n/broadcast 内容 - 群发消息\n/notice 内容 - 设置公告"
        kb = [[InlineKeyboardButton("返回", callback_data="admin_back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "admin_sys" and is_admin(q.from_user.id):
        text = "⚙️ 系统管理命令\n\n/status - 系统状态"
        kb = [[InlineKeyboardButton("返回", callback_data="admin_back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "points_add" and is_admin(q.from_user.id):
        set_admin_state(q.from_user.id, "points_add", 1, {})
        await q.edit_message_text("➕ 加积分\n\n请输入用户ID（数字）：\n例如：6742479136\n\n发送 /cancel 取消")
    elif data == "points_del" and is_admin(q.from_user.id):
        set_admin_state(q.from_user.id, "points_del", 1, {})
        await q.edit_message_text("➖ 扣积分\n\n请输入用户ID（数字）：\n例如：6742479136\n\n发送 /cancel 取消")
    elif data == "points_set" and is_admin(q.from_user.id):
        set_admin_state(q.from_user.id, "points_set", 1, {})
        await q.edit_message_text("✏️ 设置积分\n\n请输入用户ID（数字）：\n例如：6742479136\n\n发送 /cancel 取消")
    elif data == "points_log" and is_admin(q.from_user.id):
        logs = get_logs(10)
        text = "📝 积分变动日志（最近10条）\n\n" + "\n".join(f"[{l['time']}] {l['action']}" for l in reversed(logs)) if logs else "暂无日志"
        kb = [[InlineKeyboardButton("返回", callback_data="admin_back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "points_batch" and is_admin(q.from_user.id):
        set_admin_state(q.from_user.id, "points_batch", 1, {})
        await q.edit_message_text("📦 全员发放积分\n\n请输入数量：\n例如：100\n\n发送 /cancel 取消")
    elif data == "vip_give" and is_admin(q.from_user.id):
        set_admin_state(q.from_user.id, "vip_give", 1, {})
        await q.edit_message_text("👑 授予VIP\n\n请输入用户ID（数字）：\n例如：6742479136\n\n发送 /cancel 取消")
    elif data == "vip_revoke" and is_admin(q.from_user.id):
        set_admin_state(q.from_user.id, "vip_revoke", 1, {})
        await q.edit_message_text("❌ 撤销VIP\n\n请输入用户ID（数字）：\n例如：6742479136\n\n发送 /cancel 取消")
    elif data == "vip_list" and is_admin(q.from_user.id):
        vip_list = get_vip_list()
        text = "👑 VIP用户列表\n\n" + "\n".join(f"• {get_username_display(v)} - 到期：{v['vip_until']}" for v in vip_list) if vip_list else "暂无VIP用户"
        kb = [[InlineKeyboardButton("返回", callback_data="admin_back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "user_ban" and is_admin(q.from_user.id):
        set_admin_state(q.from_user.id, "user_ban", 1, {})
        await q.edit_message_text("🚫 封禁用户\n\n请输入用户ID（数字）：\n例如：6742479136\n\n发送 /cancel 取消")
    elif data == "user_unban" and is_admin(q.from_user.id):
        set_admin_state(q.from_user.id, "user_unban", 1, {})
        await q.edit_message_text("✅ 解封用户\n\n请输入用户ID（数字）：\n例如：6742479136\n\n发送 /cancel 取消")
    elif data == "user_mute" and is_admin(q.from_user.id):
        set_admin_state(q.from_user.id, "user_mute", 1, {})
        await q.edit_message_text("🔇 禁言用户\n\n请输入用户ID（数字）：\n例如：6742479136\n\n发送 /cancel 取消")
    elif data == "ban_list" and is_admin(q.from_user.id):
        bans = get_ban_list()
        text = "🚫 封禁用户列表\n\n" + "\n".join(f"• {uid}" for uid in bans) if bans else "暂无封禁用户"
        kb = [[InlineKeyboardButton("返回", callback_data="admin_back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "user_list" and is_admin(q.from_user.id):
        users = sorted(d.items(), key=lambda x: x[1].get('points', 0), reverse=True)
        text = f"👥 用户列表（共{len(users)}人）\n\n"
        for i, (uid, u) in enumerate(users[:30]):
            name = u.get('first_name', '') or u.get('username', '') or uid
            vip = "👑" if is_vip(u) else ""
            text += f"{i+1}. {name} {vip} (ID:{uid}) - {u.get('points',0)}分\n"
        if len(users) > 30:
            text += f"\n...共{len(users)}人，仅显示前30"
        kb = [[InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == "event_lottery_all" and is_admin(q.from_user.id):
        await cmd_lottery_all(q.from_user, q.bot)
    elif data == "admin_back":
        text, kb = admin_menu()
        await q.edit_message_text(text, reply_markup=kb)
    elif data == "show_admin" and is_admin(q.from_user.id):
        text, kb = admin_menu()
        await q.edit_message_text(text, reply_markup=kb)

    save_users(d)

# ===== 消息处理 =====
async def handle_msg(update: Update, ctx: CallbackContext):
    text = update.message.text
    if not text: return

    banned, msg = is_banned(update.effective_user.id)
    if banned:
        await update.message.reply_text(f"⛔ {msg}")
        return

    if text.strip() == "/cancel":
        if get_admin_state(update.effective_user.id):
            clear_admin_state(update.effective_user.id)
            await update.message.reply_text("❌ 已取消")
        else:
            await update.message.reply_text("无进行中的操作")
        return

    state = get_admin_state(update.effective_user.id)
    if state and is_admin(update.effective_user.id):
        await handle_admin_input(update, ctx, text, state)
        return

    if text in ["/骰子", "🎲 掷骰子", "/dice"]:
        await game_dice(update, ctx); return
    if text in ["/硬币", "🪙 猜硬币", "/coin"]:
        await game_coin(update, ctx); return
    if text in ["/剪刀", "✊ 石头剪刀布", "/rps"]:
        await game_rps(update, ctx); return
    if text in ["/老虎机", "🎰 老虎机", "/slot"]:
        await game_slot(update, ctx); return
    if text in ["/猜数", "🔢 猜数字", "/guess"]:
        await game_guess(update, ctx); return
    if text in ["/游戏", "/games", "游戏"]:
        await update.message.reply_text("🎮 游戏大厅（每次10积分）\n\n🎲 /骰子 - 掷骰子\n🪙 /硬币 - 猜硬币\n✊ /剪刀 - 石头剪刀布\n🎰 /老虎机 - 老虎机\n🔢 /猜数 - 猜数字")
        return
    if text in ["/运势", "🔮 今日运势", "/fortune"]:
        await fun_fortune(update, ctx); return
    if text in ["/塔罗", "🃏 塔罗牌", "/tarot"]:
        await fun_tarot(update, ctx); return
    if text in ["/笑话", "😂 听笑话", "/joke"]:
        await update.message.reply_text(f"😂 {get_joke()}"); return
    if text in ["/古诗", "📜 来首古诗", "/poem"]:
        await fun_poem(update, ctx); return
    if text in ["/电影", "🎬 推荐电影", "/movie"]:
        await fun_movie(update, ctx); return
    if text in ["/谜语", "❓ 猜谜语", "/riddle"]:
        await fun_riddle(update, ctx); return
    if text == "/答案":
        riddle = ctx.user_data.get("riddle", "")
        await update.message.reply_text(f"💡 答案：{riddle}" if riddle else "先发送 /谜语")
        return
    if text in ["/爱情", "💕 爱情配对", "/love"]:
        await update.message.reply_text(f"💕 {get_love()}"); return
    if text in ["/昵称", "✨ 趣味昵称", "/name"]:
        await update.message.reply_text(f"✨ {gen_nickname()}"); return
    if text in ["/娱乐", "/fun", "娱乐"]:
        await update.message.reply_text("🎨 娱乐天地\n\n🔮 /运势 - 今日运势\n🃏 /塔罗 - 塔罗牌占卜\n😂 /笑话 - 听个笑话\n📜 /古诗 - 来首古诗\n🎬 /电影 - 推荐电影\n❓ /谜语 - 猜谜语\n💕 /爱情 - 爱情配对\n✨ /昵称 - 趣味昵称")
        return

    intent = recognize(text)
    if intent:
        uid = update.effective_user.id
        if intent == "admin":
            if is_admin(uid):
                txt, kb = admin_menu()
                await update.message.reply_text(txt, reply_markup=kb)
            else:
                await update.message.reply_text("⛔ 无权限，仅管理员可用")
            return
        elif intent == "sign":
            await cmd_sign(update, ctx); return
        elif intent == "me":
            await cmd_me(update, ctx); return
        elif intent == "rank":
            await update.message.reply_text("🏆 排行榜功能请发送 /rank"); return
        elif intent in ("lottery", "lottery_1"):
            await update.message.reply_text("🎰 抽奖请发送 /lottery 或点击菜单的抽奖按钮"); return
        elif intent == "lottery_10":
            await update.message.reply_text("🎰 十连请发送 /lottery 然后选十连"); return
        elif intent == "vip":
            await update.message.reply_text("👑 VIP会员\n\n套餐：1.88元/30天\n权益：无限下载次数\n\n联系管理员购买"); return
        elif intent == "shop":
            await update.message.reply_text("🎁 积分商城\n\n10次下载券 - 80积分\nVIP会员 - 通过积分或付费购买"); return
        elif intent == "help":
            await update.message.reply_text("📖 使用帮助\n\n📥 发送链接下载\n📝 /sign 签到\n💰 /me 积分\n\n可直接说：管理面板、签到、查积分等"); return
        elif intent == "help_dl":
            await update.message.reply_text("📥 下载帮助\n\n直接发送链接即可下载\n\n国内：抖音/快手/小红书/微博/B站（无水印）\n国外：YouTube/TikTok/Twitter等"); return

    urls = re.findall(r"https?://[^\s]+", text)
    if urls:
        d = load_users()
        user = get_user(d, update.effective_user.id)
        ok, msg = spend_point(user)
        if not ok:
            await update.message.reply_text(f"❌ {msg}\n/sign 签到获得积分")
            return
        save_users(d)
        msg_obj = await update.message.reply_text("⏳ 正在下载...")
        result = await download(urls[0], update.effective_user.id)
        if result["success"]:
            user["downloads_today"] = user.get("downloads_today", 0) + 1
            user["downloads_total"] = user.get("downloads_total", 0) + 1
            save_users(d)
            try:
                paths = result.get("paths", [])
                if result["type"] == "video":
                    with open(paths[0], "rb") as f:
                        await update.message.reply_video(f)
                elif len(paths) == 1:
                    with open(paths[0], "rb") as f:
                        await update.message.reply_photo(f)
                else:
                    media = [InputMediaPhoto(open(p, "rb")) for p in paths[:10]]
                    await update.message.reply_media_group(media)
                    for m in media:
                        m.media.close()
                await msg_obj.delete()
                for p in paths:
                    try: os.remove(p)
                    except: pass
                if result.get("img_dir"):
                    shutil.rmtree(result["img_dir"], ignore_errors=True)
            except Exception as e:
                await msg_obj.edit_text(f"❌ 发送失败: {str(e)[:80]}")
        else:
            await msg_obj.edit_text(f"❌ {result.get('error', '下载失败')}")

def main():
    print("🚀 启动 Telegram 机器人...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("sign", cmd_sign))
    app.add_handler(CommandHandler("me", cmd_me))
    app.add_handler(CommandHandler("rank", cmd_rank))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("addpoint", cmd_addpoint))
    app.add_handler(CommandHandler("delpoint", cmd_delpoint))
    app.add_handler(CommandHandler("setpoint", cmd_setpoint))
    app.add_handler(CommandHandler("batch_addall", cmd_batch_addall))
    app.add_handler(CommandHandler("points_log", cmd_points_log))
    app.add_handler(CommandHandler("givevip", cmd_givevip))
    app.add_handler(CommandHandler("revipvip", cmd_revipvip))
    app.add_handler(CommandHandler("vip_list", cmd_vip_list))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("ban_list", cmd_ban_list))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("notice", cmd_notice))
    app.add_handler(CommandHandler("lottery_all", cmd_lottery_all))
    app.add_handler(CommandHandler("status", cmd_status))

    register_query_handlers(app)
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

    print("✅ Telegram 机器人已启动")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
