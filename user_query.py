#!/usr/bin/env python3
"""Telegram 用户信息查询（Telethon）"""
import asyncio, os
from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel, Chat, User

API_ID = int(os.getenv("TG_API_ID", "0") or 0)
API_HASH = os.getenv("TG_API_HASH", "")
SESSION = "user_query_session"

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def query_user(target):
    try:
        async with TelegramClient(SESSION, API_ID, API_HASH) as client:
            user = await client.get_entity(target)
            full = await client(GetFullUserRequest(user.id))
            photos = []
            try:
                for p in await client.get_profile_photos(user.id):
                    photos.append({"date": p.date.strftime("%Y-%m-%d")})
            except: pass
            return {
                "username": user.username or "",
                "id": user.id,
                "name": (user.first_name or "") + ((" " + user.last_name) if user.last_name else ""),
                "premium": bool(getattr(user, "premium", False)),
                "verified": bool(getattr(user, "verified", False)),
                "scam": bool(getattr(user, "scam", False)),
                "lang": getattr(user, "lang_code", "") or "未知",
                "bio": (full.full_user.about or "无") if full.full_user else "无",
                "photos": photos,
                "common_chats": len(full.full_user.common_chats_count) if hasattr(full.full_user, "common_chats_count") else 0,
            }
    except Exception as e:
        return {"error": str(e)[:100]}

async def query_chat(link):
    try:
        async with TelegramClient(SESSION, API_ID, API_HASH) as client:
            chat = await client.get_entity(link)
            full = await client(GetFullChannelRequest(chat.id)) if isinstance(chat, (Channel,)) else None
            return {
                "title": chat.title if isinstance(chat, (Channel, Chat)) else str(chat),
                "username": getattr(chat, "username", "") or "",
                "id": chat.id,
                "type": type(chat).__name__,
                "members": full.full_chat.participants_count if full else "未知",
                "verified": bool(getattr(chat, "verified", False)),
                "scam": bool(getattr(chat, "scam", False)),
                "desc": full.full_chat.about if full else "无",
            }
    except Exception as e:
        return {"error": str(e)[:100]}

async def get_my_info():
    try:
        async with TelegramClient(SESSION, API_ID, API_HASH) as client:
            me = await client.get_me()
            return {
                "username": me.username or "",
                "id": me.id,
                "name": (me.first_name or "") + ((" " + me.last_name) if me.last_name else ""),
                "premium": bool(getattr(me, "premium", False)),
                "lang": getattr(me, "lang_code", "") or "未知",
            }
    except Exception as e:
        return {"error": str(e)[:100]}

async def query_common_chats(target):
    try:
        async with TelegramClient(SESSION, API_ID, API_HASH) as client:
            user = await client.get_entity(target)
            full = await client(GetFullUserRequest(user.id))
            return full.full_user.common_chats_count
    except Exception as e:
        return {"error": str(e)[:100]}

def register_query_handlers(app):
    from telegram.ext import CommandHandler

    app.add_handler(CommandHandler("userinfo", cmd_query))
    app.add_handler(CommandHandler("myinfo", cmd_myinfo))
    app.add_handler(CommandHandler("chatinfo", cmd_chatinfo))

async def cmd_query(update, ctx):
    if not ctx.args:
        await update.message.reply_text("用法：/userinfo @用户名 或 /userinfo 用户ID")
        return
    target = ctx.args[0]
    msg = await update.message.reply_text("🔍 查询中...")
    info = run_async(query_user(target))
    if "error" in info:
        await msg.edit_text(f"❌ 查询失败：{info['error']}")
        return
    text = f"👤 用户信息\n\n• 用户名：@{info.get('username','无')}\n• 用户ID：{info.get('id')}\n• 昵称：{info.get('name','')}\n• 状态：{'⭐ Premium' if info.get('premium') else '普通用户'}\n• 语言：{info.get('lang','未知')}\n• 共同群：{info.get('common_chats',0)}\n📝 简介：{info.get('bio','无')}"
    await msg.edit_text(text)

async def cmd_myinfo(update, ctx):
    msg = await update.message.reply_text("🔍 查询中...")
    info = run_async(get_my_info())
    if "error" in info:
        await msg.edit_text(f"❌ 查询失败：{info['error']}")
        return
    text = f"👤 我的信息\n\n• 用户名：@{info.get('username','无')}\n• 用户ID：{info.get('id')}\n• 昵称：{info.get('name','')}\n• 状态：{'⭐ Premium' if info.get('premium') else '普通用户'}\n• 语言：{info.get('lang','未知')}"
    await msg.edit_text(text)

async def cmd_chatinfo(update, ctx):
    if not ctx.args:
        await update.message.reply_text("用法：/chatinfo 群链接")
        return
    msg = await update.message.reply_text("🔍 查询中...")
    info = run_async(query_chat(ctx.args[0]))
    if "error" in info:
        await msg.edit_text(f"❌ 查询失败：{info['error']}")
        return
    text = f"💬 群组信息\n\n• 名称：{info.get('title')}\n• 用户名：@{info.get('username','无')}\n• ID：{info.get('id')}\n• 类型：{info.get('type')}\n• 成员数：{info.get('members','未知')}\n📝 描述：{info.get('desc','无')}"
    await msg.edit_text(text)
