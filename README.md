# aplm123 视频下载机器人

Telegram + QQ 双平台视频/图片下载机器人，支持积分、签到、抽奖、VIP、游戏、娱乐等功能。

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📥 视频下载 | 抖音/快手/B站/小红书/微博（无水印）+ YouTube/TikTok/Twitter 等 1752+ 平台 |
| 🖼️ 图片下载 | gallery-dl 支持 4816 个图片站点（Danbooru/Instagram/Pinterest 等） |
| 📝 签到积分 | 每日签到 +10 积分，连续 7 天额外奖励 |
| 🎰 抽奖系统 | 单抽 50 积分 / 十连 450 积分 |
| 👑 VIP 会员 | 无限下载次数 |
| 💎 积分商城 | 下载券/日卡兑换 |
| 🎮 游戏娱乐 | 骰子/硬币/剪刀石头布/老虎机/猜数字 + 运势/塔罗/笑话/古诗 |
| 💬 自然语言 | 说"签到""查积分""管理面板"即可触发命令 |

## 🚀 一键安装

```bash
git clone https://github.com/ce11kjw/aplm123-bot.git
cd aplm123-bot
bash install.sh
```

安装向导会询问：
- **TG_TOKEN**（必填）：@BotFather → /newbot 获取
- **ADMIN_IDS**（必填）：你的 Telegram 数字 ID
- **QQ_APP_ID/SECRET**（可选）：QQ 开放平台
- **TG_API_ID/HASH**（可选）：my.telegram.org（用户查询功能）

## 📝 手动配置

```bash
cp .env.example .env
# 编辑 .env 填入你的配置
bash install.sh  # 或手动安装依赖后运行
```

## 🛠️ 常用命令

```bash
systemctl status aplm123-tg     # 查看 TG 机器人状态
systemctl status aplm123-qq     # 查看 QQ 机器人状态
journalctl -u aplm123-tg -f     # 实时日志
systemctl restart aplm123-tg    # 重启
```

## 📁 项目结构

```
aplm123-bot/
├── bot.py              # Telegram 机器人主程序
├── qq_bot_dl.py        # QQ 机器人
├── downloader.py       # 统一下载实现（视频/图片）
├── video_parser.py     # 国内平台解析
├── data_manager.py     # 数据管理（积分/VIP/用户）
├── nlp.py              # 自然语言识别
├── games.py            # 游戏模块
├── entertainment.py    # 娱乐模块
├── user_query.py       # Telegram 用户查询（可选）
├── install.sh          # 一键安装脚本
└── .env.example        # 配置模板
```

## ⚙️ 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| TG_TOKEN | ✅ | Telegram Bot Token |
| ADMIN_IDS | ✅ | 管理员 ID，逗号分隔 |
| QQ_APP_ID | - | QQ 机器人 AppID |
| QQ_APP_SECRET | - | QQ 机器人密钥 |
| TG_API_ID | - | 用户查询功能 API ID |
| TG_API_HASH | - | 用户查询功能 API Hash |
