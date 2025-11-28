#!/bin/bash
# ============================================
# EMR to Heidi Integration - 虚拟环境安装脚本
# ============================================

set -e

echo "🚀 开始安装 EMR to Heidi Integration（使用虚拟环境）..."
echo ""

# 进入项目目录
cd /Users/k.zhan/Desktop/workspace/heidi

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ 虚拟环境已存在"
fi

echo ""
echo "🔄 激活虚拟环境并安装依赖..."
echo ""

# 激活虚拟环境并安装
source venv/bin/activate

# 升级 pip
echo "📦 升级 pip..."
pip install --upgrade pip

echo ""
echo "📥 安装核心依赖..."

echo "   1/8 pyautogui..."
pip install pyautogui

echo "   2/8 Pillow..."
pip install Pillow

echo "   3/8 requests..."
pip install requests

echo "   4/8 python-dotenv..."
pip install python-dotenv

echo "   5/8 rich..."
pip install rich

echo "   6/8 pyyaml..."
pip install pyyaml

echo "   7/8 screeninfo..."
pip install screeninfo

echo "   8/8 PaddleOCR（这可能需要几分钟，首次会下载模型）..."
echo "       注意：即使看到 pymupdf/muPDF 错误也没关系！"
pip install paddleocr 2>&1 | grep -v "pymupdf" || true

echo ""
echo "✅ 依赖安装完成！"
echo ""

# 验证安装
echo "🔍 验证安装..."
python -c "import pyautogui; print('✅ pyautogui')" || echo "❌ pyautogui"
python -c "import PIL; print('✅ Pillow')" || echo "❌ Pillow"
python -c "import requests; print('✅ requests')" || echo "❌ requests"
python -c "import dotenv; print('✅ python-dotenv')" || echo "❌ python-dotenv"
python -c "import rich; print('✅ rich')" || echo "❌ rich"
python -c "import yaml; print('✅ pyyaml')" || echo "❌ pyyaml"
python -c "import screeninfo; print('✅ screeninfo')" || echo "❌ screeninfo"
python -c "from paddleocr import PaddleOCR; print('✅ paddleocr（可能会下载模型）')" || echo "❌ paddleocr"

echo ""
echo "🎉 安装完成！"
echo ""
echo "📚 下一步："
echo "   1. 每次使用前激活虚拟环境："
echo "      source venv/bin/activate"
echo ""
echo "   2. 配置环境变量:"
echo "      cp .env.example .env"
echo "      # 然后编辑 .env 文件"
echo ""
echo "   3. 运行程序:"
echo "      python integrations/standalone/main.py --show-config"
echo ""
echo "   4. 退出虚拟环境:"
echo "      deactivate"
echo ""
