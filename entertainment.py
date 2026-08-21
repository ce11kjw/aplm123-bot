#!/usr/bin/env python3
import random

JOKES = [
    "程序员A：你知道世界上最短的笑话是什么吗？\n程序员B：什么？\n程序员A：需求不改了。",
    "小明：妈妈，为什么我叫小明？\n妈妈：因为你出生那天阳光明媚。\n小明：那弟弟为什么叫小雨？\n妈妈：因为那天下雨。",
    "面试官：你最大的缺点是什么？\n我：太诚实了。\n面试官：这不算缺点。\n我：我不在乎你觉得。",
    "我问朋友：你存了多少钱？\n朋友：4000万。\n我：哇！怎么存的？\n朋友：梦里。",
    "小王：我失恋了。\n小李：天涯何处无芳草。\n小王：可我就是那棵草啊！",
]

POEMS = [
    {"author": "李白", "title": "静夜思", "content": "床前明月光，疑是地上霜。\n举头望明月，低头思故乡。"},
    {"author": "杜甫", "title": "春望", "content": "国破山河在，城春草木深。\n感时花溅泪，恨别鸟惊心。"},
    {"author": "王维", "title": "相思", "content": "红豆生南国，春来发几枝。\n愿君多采撷，此物最相思。"},
    {"author": "孟浩然", "title": "春晓", "content": "春眠不觉晓，处处闻啼鸟。\n夜来风雨声，花落知多少。"},
    {"author": "苏轼", "title": "水调歌头", "content": "明月几时有？把酒问青天。\n不知天上宫阙，今夕是何年。"},
]

MOVIES = [
    {"name": "肖申克的救赎", "type": "剧情", "desc": "希望让人自由"},
    {"name": "霸王别姬", "type": "剧情/爱情", "desc": "风华绝代"},
    {"name": "阿甘正传", "type": "剧情", "desc": "一部美国近现代史"},
    {"name": "泰坦尼克号", "type": "爱情", "desc": "失去的才是永恒的"},
    {"name": "千与千寻", "type": "动画", "desc": "最好的宫崎骏"},
]

RIDDLES = [
    {"q": "麻屋子，红帐子，里面住着个白胖子", "a": "花生"},
    {"q": "兄弟七八个，围着柱子坐", "a": "大蒜"},
    {"q": "身穿绿衣裳，肚里水汪汪", "a": "西瓜"},
    {"q": "千条线，万条线，掉到水里看不见", "a": "雨"},
    {"q": "有头无颈，有眼无眉，无脚能走，有翅难飞", "a": "鱼"},
]

TAROTS = [
    {"name": "愚者", "emoji": "🃏", "meaning": "新的开始，冒险精神"},
    {"name": "魔术师", "emoji": "🎭", "meaning": "创造力，自信"},
    {"name": "女祭司", "emoji": "🌙", "meaning": "直觉，神秘"},
    {"name": "恋人", "emoji": "💕", "meaning": "爱情，选择"},
    {"name": "战车", "emoji": "🏆", "meaning": "胜利，意志力"},
    {"name": "力量", "emoji": "🦁", "meaning": "勇气，耐心"},
    {"name": "命运之轮", "emoji": "🎡", "meaning": "转折，机遇"},
    {"name": "星星", "emoji": "⭐", "meaning": "希望，灵感"},
]

LOVE_MATCH = ["💕 天作之合", "💗 情投意合", "💓 心心相印", "💖 相互吸引", "💘 有缘无分"]

FORTUNE_LEVELS = [
    ("大吉", "🎉", "万事如意，好运连连！"),
    ("中吉", "😊", "一切顺利，心想事成"),
    ("小吉", "🙂", "平稳顺利，小有收获"),
    ("末吉", "😐", "平淡无奇，安稳度日"),
    ("凶", "😰", "小心行事，注意安全"),
]

def get_fortune(uid):
    random.seed(uid + hash(str(__import__('datetime').date.today())))
    weight = random.random()
    if weight < 0.15: idx = 0
    elif weight < 0.40: idx = 1
    elif weight < 0.70: idx = 2
    elif weight < 0.90: idx = 3
    else: idx = 4
    level, emoji, desc = FORTUNE_LEVELS[idx]
    aspects = ["事业", "爱情", "财运", "健康", "学习"]
    scores = {a: random.randint(50, 100) for a in aspects}
    random.seed()
    return level, emoji, desc, scores

def get_tarot():
    card = random.choice(TAROTS)
    position = "逆位" if random.random() < 0.3 else "正位"
    return card, position

def get_joke(): return random.choice(JOKES)
def get_poem(): return random.choice(POEMS)
def get_movie(): return random.choice(MOVIES)
def get_riddle(): return random.choice(RIDDLES)
def get_love(): return random.choice(LOVE_MATCH)

def gen_nickname():
    p = ["快乐的","疯狂的","可爱的","霸气的","高冷的","逗比的"]
    a = ["小猫咪","独角兽","皮卡丘","小熊猫","大白鹅"]
    s = ["酱","君","大人","同学","先生"]
    return f"{random.choice(p)}{random.choice(a)}{random.choice(s)}"
