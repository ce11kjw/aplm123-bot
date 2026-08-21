#!/bin/bash
# ============================================
# aplm123-bot WebDAV 自动备份脚本
# 上传到 WebDAV 根目录（该服务不支持建子目录）
# ============================================
WEBDAV_BASE="https://aplm123.dpdns.org/dav/%E7%A7%81%E6%9C%89/%E8%93%9D%E5%A5%8F%E4%BA%91%E4%BC%98%E4%BA%AB%E7%89%88%282TB%29/"
WEBDAV_USER="aplm123"
WEBDAV_PASS="zxasqw12"
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
