#!/bin/bash
# ============================================
# 智能运行脚本 - EMR to Heidi 智能模式
# ============================================
#
# 功能：使用智能模式自动完成全部流程
# 特点：
#   - 自动截取全屏（无需配置截图区域）
#   - 自动识别EMR系统类型
#   - 自动定位并提取病人信息
#   - 自动传输到 Heidi Health API
#   - 全程无需手动确认
#
# 使用方法：
#   bash smart-run.sh
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
    echo "  然后编辑 .env 文件，填写 HEIDI_API_KEY"
    echo ""
    echo "💡 智能模式不需要配置截图区域，将自动截取全屏"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

echo "✅ 虚拟环境已激活"
echo "🤖 启动智能模式..."
echo ""
echo "💡 智能模式将："
echo "   1. 自动截取全屏"
echo "   2. 自动识别 EMR 系统类型"
echo "   3. 自动提取病人信息"
echo "   4. 自动传输到 Heidi API"
echo ""

# 运行程序，使用智能模式 + 跳过确认
python integrations/standalone/main.py --smart --yes

# 显示完成信息
echo ""
echo "================================================"
echo "✨ 智能流程执行完毕！"
echo "================================================"

# 注意：虚拟环境会在脚本结束后自动退出
