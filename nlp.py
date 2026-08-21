#!/usr/bin/env python3
KEYWORDS = {
    "admin": ["admin", "管理", "管理面板", "后台", "管理员", "控制台"],
    "sign": ["sign", "签到", "打卡", "签个到", "我要签到", "今日签到"],
    "me": ["me", "我的", "积分", "查积分", "我的积分", "看下积分", "查看积分"],
    "rank": ["rank", "排行", "排行榜", "排名", "看看榜", "积分榜"],
    "lottery": ["lottery", "抽奖", "抽一次", "幸运抽奖", "抽个奖", "我要抽奖"],
    "lottery_1": ["单抽", "抽一次", "单次抽奖"],
    "lottery_10": ["十连", "十连抽", "抽十次"],
    "vip": ["vip", "会员", "开通vip", "买会员", "vip会员"],
    "shop": ["shop", "商城", "商店", "积分商城", "兑换"],
    "help": ["help", "帮助", "怎么用", "使用帮助", "说明", "指令"],
    "help_dl": ["下载", "下载帮助", "怎么下载", "下载教程"],
}

def recognize(text):
    text = text.lower().strip()
    for intent, keywords in KEYWORDS.items():
        if text in keywords:
            return intent
    for intent, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return intent
    return None
