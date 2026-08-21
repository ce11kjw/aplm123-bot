#!/bin/bash
# ============================================
# aplm123 视频下载机器人 一键安装脚本
# 用法: bash install.sh
# ============================================
set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok(){ echo -e "${GREEN}✅ $1${NC}"; }
warn(){ echo -e "${YELLOW}⚠️  $1${NC}"; }
err(){ echo -e "${RED}❌ $1${NC}"; exit 1; }

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ "$(id -u)" != "0" ]; then err "请用 root 运行: sudo bash install.sh"; fi

echo "=============================================="
echo "  aplm123 视频下载机器人 安装向导"
echo "=============================================="
echo ""
echo "【必填】Telegram Bot Token（@BotFather → /newbot 获取）"
read -rp "TG_TOKEN: " TG_TOKEN
[ -z "$TG_TOKEN" ] && err "TG_TOKEN 不能为空"

echo ""
echo "【必填】管理员 Telegram ID（数字，多个逗号分隔）"
read -rp "ADMIN_IDS: " ADMIN_IDS
[ -z "$ADMIN_IDS" ] && err "ADMIN_IDS 不能为空"

echo ""
echo "【可选】QQ Bot AppID（不填则跳过 QQ 机器人）"
read -rp "QQ_APP_ID: " QQ_APP_ID
if [ -n "$QQ_APP_ID" ]; then
    read -rp "QQ_APP_SECRET: " QQ_APP_SECRET
fi

echo ""
echo "【可选】Telegram API ID/HASH（用户查询功能，my.telegram.org 获取；不填则无查询功能）"
read -rp "TG_API_ID: " TG_API_ID
read -rp "TG_API_HASH: " TG_API_HASH

echo ""
echo "=============================================="
echo "配置确认："
echo "  TG_TOKEN:   ${TG_TOKEN:0:10}..."
echo "  ADMIN_IDS:  $ADMIN_IDS"
echo "  QQ_APP_ID:  ${QQ_APP_ID:-未设置}"
echo "  TG_API_ID:  ${TG_API_ID:-未设置}"
read -rp "确认无误？[y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { warn "已取消"; exit 0; }

# ---------- 写入 .env ----------
cat > .env << ENVEOF
TG_TOKEN=$TG_TOKEN
QQ_APP_ID=${QQ_APP_ID:-}
QQ_APP_SECRET=${QQ_APP_SECRET:-}
ADMIN_IDS=$ADMIN_IDS
TG_API_ID=${TG_API_ID:-}
TG_API_HASH=${TG_API_HASH:-}
DATA_DIR=$DIR/data
DL_DIR=$DIR/downloads
ENVEOF
chmod 600 .env
ok "已写入 .env"

# ---------- 安装依赖 ----------
ok "安装系统依赖..."
apt-get update -qq 2>/dev/null || true
apt-get install -y python3 python3-pip ffmpeg curl >/dev/null 2>&1 || true

ok "安装 Python 依赖..."
pip3 install --break-system-packages python-telegram-bot requests websocket-client psutil yt-dlp gallery-dl >/dev/null 2>&1 || true
pip3 install --break-system-packages telethon >/dev/null 2>&1 || true

# ---------- 创建 systemd 服务 ----------
ok "配置 systemd 服务..."
mkdir -p "$DIR/data" "$DIR/downloads"
cat > /etc/systemd/system/aplm123-tg.service << SVC
[Unit]
Description=aplm123 Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$DIR
EnvironmentFile=$DIR/.env
ExecStart=/usr/bin/python3 -u $DIR/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC

if [ -n "$QQ_APP_ID" ]; then
cat > /etc/systemd/system/aplm123-qq.service << SVC
[Unit]
Description=aplm123 QQ Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$DIR
EnvironmentFile=$DIR/.env
ExecStart=/usr/bin/python3 -u $DIR/qq_bot_dl.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC
fi

systemctl daemon-reload
systemctl enable aplm123-tg >/dev/null 2>&1 || true
systemctl start aplm123-tg || warn "TG 启动失败，查看 journalctl -u aplm123-tg"
ok "Telegram 机器人已启动"

if [ -n "$QQ_APP_ID" ]; then
    systemctl enable aplm123-qq >/dev/null 2>&1 || true
    systemctl start aplm123-qq || warn "QQ 启动失败，查看 journalctl -u aplm123-qq"
    ok "QQ 机器人已启动"
fi

echo ""
echo "=============================================="
echo "  🎉 安装完成！"
echo "=============================================="
echo "状态: systemctl status aplm123-tg"
echo "日志: journalctl -u aplm123-tg -f"
echo "重启: systemctl restart aplm123-tg"
echo "=============================================="
