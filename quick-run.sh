#!/bin/bash
# ============================================
# 一键运行脚本 - EMR to Heidi 自动化流程
# ============================================
#
# 功能：自动完成从获取信息到传输到 Heidi 的全部流程
# 特点：
#   - 自动跳过所有确认提示
#   - 使用默认配置
#   - 适合日常快速使用
#
# 使用方法：
#   bash quick-run.sh
#
# ============================================

set -e

# 进入项目目录
cd "$(dirname "$0")"

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在！"
    echo "请先运行安装脚本: bash install-venv.sh"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 配置文件 .env 不存在！"
    echo "请先创建配置文件："
    echo "  cp .env.example .env"
    echo "  然后编辑 .env 文件，填写必要的配置"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

echo "✅ 虚拟环境已激活"
echo "🚀 开始一键运行流程..."
echo ""

# 运行程序，使用 --yes 参数跳过所有确认
python integrations/standalone/main.py --yes

# 显示完成信息
echo ""
echo "================================================"
echo "✨ 流程执行完毕！"
echo "================================================"

# 注意：虚拟环境会在脚本结束后自动退出
