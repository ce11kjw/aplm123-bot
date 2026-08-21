#!/usr/bin/env python3
"""游戏模块"""
import random

def roll_dice(bet=10):
    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)
    if total >= 16: prize = bet * 3; result = "大"
    elif total <= 6: prize = bet * 3; result = "小"
    elif total % 2 == 0: prize = bet * 2; result = "偶"
    else: prize = bet * 2; result = "奇"
    return dice, total, result, prize

def coinflip(bet=10, choice="head"):
    result = random.choice(["head", "tail"])
    win = (choice == result)
    prize = bet * 2 if win else 0
    return result, win, prize

def rps(player_choice, bet=10):
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    cn = {"rock": "🪨石头", "paper": "📄布", "scissors": "✂️剪刀"}
    if player_choice == bot_choice:
        result = "平局"; prize = bet
    elif wins[player_choice] == bot_choice:
        result = "赢了"; prize = bet * 2
    else:
        result = "输了"; prize = 0
    return cn[player_choice], cn[bot_choice], result, prize

def slot_machine(bet=10):
    symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    weights = [30, 25, 20, 15, 8, 2]
    reels = [random.choices(symbols, weights=weights, k=1)[0] for _ in range(3)]
    if reels[0] == reels[1] == reels[2]:
        if reels[0] == "7️⃣": prize = bet * 50; msg = "🎰🎰🎰 JACKPOT!!!"
        elif reels[0] == "💎": prize = bet * 30; msg = "💎💎💎 钻石大奖！"
        else: prize = bet * 10; msg = "🎉 三连！"
    elif reels[0] == reels[1] or reels[1] == reels[2]:
        prize = bet * 2; msg = "😏 两个一样"
    else:
        prize = 0; msg = "😢 没中"
    return reels, msg, prize

def guess_number(bet=10, player_guess=50):
    answer = random.randint(1, 100)
    diff = abs(player_guess - answer)
    if diff == 0: prize = bet * 10; msg = "🎯 完美命中！"
    elif diff <= 5: prize = bet * 5; msg = f"🔥 太接近了！答案是{answer}"
    elif diff <= 10: prize = bet * 3; msg = f"👍 很接近！答案是{answer}"
    elif diff <= 20: prize = bet * 2; msg = f"🤔 还行！答案是{answer}"
    else: prize = 0; msg = f"😅 差远了！答案是{answer}"
    return answer, diff, prize, msg

def trivia():
    questions = [
        {"q": "世界上最长的河流是？", "a": "尼罗河", "opts": ["亚马逊河", "尼罗河", "长江", "黄河"]},
        {"q": "HTTP默认端口号是？", "a": "80", "opts": ["21", "80", "8080", "443"]},
        {"q": "太阳系最大的行星是？", "a": "木星", "opts": ["土星", "木星", "天王星", "海王星"]},
        {"q": "Python的创始人是？", "a": "Guido", "opts": ["Linus", "Guido", "James", "Dennis"]},
        {"q": "一年有多少天？", "a": "365", "opts": ["360", "365", "366", "364"]},
    ]
    q = random.choice(questions)
    random.shuffle(q["opts"])
    return q

def math_challenge():
    ops = ["+", "-", "×"]
    op = random.choice(ops)
    if op == "+":
        a, b = random.randint(10, 100), random.randint(10, 100); answer = a + b
    elif op == "-":
        a, b = random.randint(50, 100), random.randint(10, 50); answer = a - b
    else:
        a, b = random.randint(2, 20), random.randint(2, 20); answer = a * b
    return f"{a} {op} {b}", answer
