# aplm123 万能下载器

**Telegram 机器人 + QQ 机器人 + 网页端** 三终端视频/图片下载平台，共享同一套积分/VIP/用户体系。

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📥 视频下载 | 抖音/快手/B站/小红书/微博（无水印）+ YouTube/Twitter 等 1752+ 平台 |
| 🎵 TikTok | **自研解析器**，直连官方、无第三方依赖、无水印、自动选最高画质；配 Cookie 可解锁高清/图集 |
| 🖼️ 图片下载 | gallery-dl 支持 4816 个图片站点（Danbooru/Instagram/Pinterest 等） |
| 📝 签到积分 | 每日签到 +10 积分，连续 7 天额外奖励 |
| 🎰 抽奖系统 | 单抽 50 积分 / 十连 450 积分 |
| 👑 VIP 会员 | 无限下载次数 |
| 💎 积分商城 | 下载券/日卡兑换 |
| 🎮 游戏娱乐 | 骰子/硬币/剪刀石头布/老虎机/猜数字 + 运势/塔罗/笑话/古诗 |
| 💬 自然语言 | 说"签到""查积分""管理面板"即可触发命令 |
| 🛠️ 管理面板 | 积分/VIP/用户管理、删除用户、群发、全员抽奖、**TikTok Cookie 管理**、系统状态 |
| 📎 粘整段文案 | 直接粘分享文案（含表情/置乱码）自动提取链接 |

## 🌐 网页端

除 Telegram/QQ 机器人外，还内置一个**手机优先**的网页端（FastAPI + 单文件前端，无构建）。

| 页面 | 内容 |
|------|------|
| 🏠 首页 | 功能介绍、支持平台、引导加 Bot |
| ⬇ 下载 | 粘链接直接下载（消耗积分，VIP 免费）+ 抽奖 + 下载历史 |
| 📊 数据 | 用户/下载/VIP 统计 + 积分榜/下载榜图表 + 签到榜 |
| 👤 我的 | 个人信息、签到、积分商城、绑定 Telegram、管理入口 |
| 🛠️ 管理 | 全功能后台（仅管理员可见） |

**特点**
- 底部 Tab Bar 导航 + 纯线性 SVG 图标，深色科技风
- 网页原生注册/登录（用户名+密码，注册送 100 积分）
- **可选绑定 Telegram**：设置里填 TG ID → Bot 发验证码 → 数据合并（不绑也能用全部功能）
- **管理员自动识别**：登录的账号在 `ADMIN_IDS` 内，自动显示管理入口、免密码进后台
- 与机器人**共用同一份数据**（`data/users.json`），双向同步

默认监听 `127.0.0.1:25774`，建议配 Cloudflare Tunnel / Nginx 反代对外。

```bash
systemctl status aplm123-web     # 网页服务状态
```

## 🚀 一键部署

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ce11kjw/aplm123-bot/main/install.sh)
```

一条命令自动完成：拉取代码 → 安装依赖 → 交互式填写 Token → 配置 systemd → 启动。

安装向导会询问：
- **TG_TOKEN**（必填）：@BotFather → /newbot 获取
- **ADMIN_IDS**（必填）：你的 Telegram 数字 ID
- **QQ_APP_ID/SECRET**（可选）：QQ 开放平台，不填则跳过 QQ 机器人
- **TG_API_ID/HASH**（可选）：my.telegram.org（用户查询功能）

> 默认**不带 TikTok Cookie**（免登录解析，画质受限）。需要高清/图集时，在聊天里的管理面板配置 Cookie。

## 🍪 TikTok Cookie 管理（聊天面板）

TikTok 高清版和部分图集需要登录态。**无需碰服务器**，在 Telegram 里管理：

1. 发送 `/admin` 或"管理面板" → **⚙️ 系统管理**
2. 三个按钮：
   - 🍪 **Cookie状态** — 查看是否已配置
   - 🔑 **设置Cookie** — 粘贴浏览器导出的 cookie 字符串（`key=value; ...`），自动保存
   - 🗑 **清除Cookie** — 回到免登录模式

导出 cookie：浏览器登录 tiktok.com → 装 "Get cookies.txt LOCALLY" 扩展导出，或开发者工具复制。**建议用小号。**

## 🛠️ 常用命令

```bash
systemctl status aplm123-tg     # TG 机器人状态
systemctl status aplm123-qq     # QQ 机器人状态
systemctl status aplm123-web    # 网页端状态
journalctl -u aplm123-tg -f     # 实时日志
systemctl restart aplm123-tg    # 重启
```

## 📁 项目结构

```
aplm123-bot/
├── bot.py              # Telegram 机器人主程序
├── qq_bot_dl.py        # QQ 机器人
├── downloader.py       # 统一下载入口（TikTok→国内平台→yt-dlp→gallery-dl）
├── tiktok_dl.py        # 自研 TikTok 解析器（官方网页 __UNIVERSAL_DATA）
├── video_parser.py     # 国内平台解析（抖音/快手/B站等）
├── data_manager.py     # 数据管理（积分/VIP/用户）
├── nlp.py              # 自然语言识别
├── games.py            # 游戏模块
├── entertainment.py    # 娱乐模块
├── user_query.py       # Telegram 用户查询（可选）
├── web.py              # 网页端后端（FastAPI）
├── webroot/
│   └── index.html      # 网页端前端（单文件，Alpine.js + Chart.js）
├── install.sh          # 一键部署脚本
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
| WEB_ADMIN_PASS | - | 网页后台备用密码（管理员账号登录时无需）|

## 🔒 安全说明

以下文件不入库（`.gitignore` 排除），仅存于服务器本地：
- `.env` — Bot Token 等凭据
- `cookies.txt` — TikTok 登录 Cookie
- `backup.sh` / `.backup.env` — 备份脚本与 WebDAV 凭据
- `data/` — 用户数据、网页账号密码哈希
- `webroot/dl/` — 网页下载的临时文件

## ⚠️ 已知限制

- **抖音**：平台已关闭免登录接口，无 Cookie 时无法下载
- **TikTok 高清**：部分视频的 720p/1080p 需登录态，未配 Cookie 时取最高可用画质
