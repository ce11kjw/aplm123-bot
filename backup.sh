#!/bin/bash
# ============================================
# aplm123-bot WebDAV 自动备份脚本
# 上传到 WebDAV 根目录（该服务不支持建子目录）
# ============================================
# 从 .backup.env 读取凭据（不入 git）
source "$(dirname "$0")/.backup.env"
: "${WEBDAV_BASE:?需要在 .backup.env 配置 WEBDAV_BASE}"
: "${WEBDAV_USER:?需要在 .backup.env 配置 WEBDAV_USER}"
: "${WEBDAV_PASS:?需要在 .backup.env 配置 WEBDAV_PASS}"
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/aplm123_backup"
mkdir -p "$BACKUP_DIR"

# 1. 打包（排除 .git / downloads / __pycache__）
TARBALL="$BACKUP_DIR/aplm123-bot_${STAMP}.tar.gz"
tar czf "$TARBALL" -C /root \
    --exclude='aplm123-bot/.git' \
    --exclude='aplm123-bot/downloads' \
    --exclude='__pycache__' \
    aplm123-bot

SIZE=$(du -h "$TARBALL" | cut -f1)

# 2. 上传到根目录
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -u "$WEBDAV_USER:$WEBDAV_PASS" \
    -T "$TARBALL" "${WEBDAV_BASE}aplm123-bot_${STAMP}.tar.gz" --max-time 300)

# 3. 清理本地临时
rm -f "$TARBALL"

if [ "$HTTP" = "201" ] || [ "$HTTP" = "204" ]; then
    echo "[$(date '+%F %T')] ✅ 备份成功: aplm123-bot_${STAMP}.tar.gz (${SIZE}) HTTP $HTTP"
    logger -t aplm123-backup "backup OK ${STAMP} ${SIZE}"
else
    echo "[$(date '+%F %T')] ❌ 备份失败 HTTP $HTTP"
    logger -t aplm123-backup "backup FAIL HTTP $HTTP"
    exit 1
fi
