#!/bin/bash
# setup.sh — 股票分析师 Skill 环境初始化（只需运行一次）
# 自动检测环境 → 测速选源 → 安装依赖 → 输出后续使用的 Python 命令
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔍 检测 Python 环境..."

# 1. 检查 venv 是否已就绪
if [ -f "venv/bin/python" ] && venv/bin/python -c "import pandas, matplotlib, akshare, markdown" 2>/dev/null; then
    echo "✅ venv 已就绪"
    echo ""
    echo "━━━ 后续使用方式 ━━━"
    echo "  PYTHON=./venv/bin/python"
    echo "  \$PYTHON fetch_all.py 0700.HK"
    echo "  \$PYTHON md2html.py ..."
    echo "  \$PYTHON export_report.py ..."
    exit 0
fi

# 2. 创建 venv
if command -v python3 &>/dev/null; then
    echo "📦 创建虚拟环境 (venv)..."
    python3 -m venv venv
    PIP="./venv/bin/pip"
elif command -v python &>/dev/null; then
    echo "⚠️ 未找到 python3，使用 python..."
    PIP="pip"
else
    echo "❌ 未找到可用的 Python 环境"
    exit 1
fi

# 3. 测速选源 —— 默认源 vs 清华 vs 阿里云，选最快的
echo "🌐 测速 pip 镜像源..."

MIRRORS=(
    "default|https://pypi.org/simple/"
    "清华 TUNA|https://pypi.tuna.tsinghua.edu.cn/simple"
    "阿里云|https://mirrors.aliyun.com/pypi/simple/"
)

best_mirror=""
best_time=9999
best_name=""

for entry in "${MIRRORS[@]}"; do
    name="${entry%%|*}"
    url="${entry##*|}"
    sec=$(curl -o /dev/null -s -w '%{time_total}' --connect-timeout 5 --max-time 8 "$url" 2>/dev/null || echo "99.99")
    printf "  %-12s %ss\n" "$name" "$sec"
    if awk "BEGIN{exit !($sec < $best_time)}" 2>/dev/null; then
        best_time="$sec"
        best_mirror="$url"
        best_name="$name"
    fi
done

if [ "$best_name" = "default" ]; then
    echo "✅ 最快镜像: 默认源 PyPI (${best_time}s)"
    INDEX_URL=""
else
    best_host=$(echo "$best_mirror" | sed 's|https\?://||;s|/.*||')
    echo "✅ 最快镜像: $best_name (${best_time}s)"
    INDEX_URL="--index-url $best_mirror --trusted-host $best_host"
fi

# 4. 安装依赖
echo ""
echo "📥 安装依赖..."
# shellcheck disable=SC2086
$PIP install $INDEX_URL -r requirements.txt

echo ""
echo "✅ 安装完成！"
echo ""
if [ "$PIP" = "./venv/bin/pip" ]; then
    echo "━━━ 后续使用方式 ━━━"
    echo "  PYTHON=./venv/bin/python"
    echo "  \$PYTHON fetch_all.py 0700.HK"
    echo "  \$PYTHON md2html.py ..."
    echo "  \$PYTHON export_report.py ..."
else
    echo "━━━ 后续使用方式 ━━━"
    echo "  python fetch_all.py 0700.HK"
    echo "  python md2html.py ..."
    echo "  python export_report.py ..."
fi
