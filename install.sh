#!/bin/bash
# ============================================
# EMR to Heidi Integration - 自动安装脚本
# ============================================

set -e  # 遇到错误立即退出

echo "🚀 开始安装 EMR to Heidi Integration 依赖..."
echo ""

# 检查 Python 版本
echo "📍 检查 Python 环境..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python 版本: $PYTHON_VERSION"
echo ""

# 升级 pip
echo "📦 升级 pip..."
python3 -m pip install --upgrade pip
echo ""

# 安装依赖（分阶段）
echo "📥 安装核心依赖..."

echo "   1/8 安装 pyautogui..."
pip3 install pyautogui || echo "⚠️  pyautogui 安装失败（可能需要系统依赖）"

echo "   2/8 安装 Pillow..."
pip3 install Pillow

echo "   3/8 安装 requests..."
pip3 install requests

echo "   4/8 安装 python-dotenv..."
pip3 install python-dotenv

echo "   5/8 安装 rich..."
pip3 install rich

echo "   6/8 安装 pyyaml..."
pip3 install pyyaml

echo "   7/8 安装 screeninfo..."
pip3 install screeninfo

echo "   8/8 安装 PaddleOCR（这可能需要几分钟）..."
echo "       注意：即使 pymupdf 失败也没关系！"
pip3 install paddleocr || {
    echo "⚠️  PaddleOCR 完整安装失败，尝试最小化安装..."
    pip3 install paddleocr --no-deps
    pip3 install paddlepaddle opencv-python shapely scikit-image imgaug pyclipper lmdb tqdm numpy visualdl rapidfuzz beautifulsoup4 fonttools
}

echo ""
echo "✅ 依赖安装完成！"
echo ""

# 验证安装
echo "🔍 验证安装..."
python3 -c "import pyautogui; print('✅ pyautogui')" 2>/dev/null || echo "❌ pyautogui"
python3 -c "import PIL; print('✅ Pillow')" 2>/dev/null || echo "❌ Pillow"
python3 -c "import requests; print('✅ requests')" 2>/dev/null || echo "❌ requests"
python3 -c "import dotenv; print('✅ python-dotenv')" 2>/dev/null || echo "❌ python-dotenv"
python3 -c "import rich; print('✅ rich')" 2>/dev/null || echo "❌ rich"
python3 -c "import yaml; print('✅ pyyaml')" 2>/dev/null || echo "❌ pyyaml"
python3 -c "import screeninfo; print('✅ screeninfo')" 2>/dev/null || echo "❌ screeninfo"
python3 -c "from paddleocr import PaddleOCR; print('✅ paddleocr')" 2>/dev/null || echo "❌ paddleocr"

echo ""
echo "🎉 安装完成！"
echo ""
echo "📚 下一步："
echo "   1. 配置环境变量: cp .env.example .env"
echo "   2. 编辑 .env 文件，填写 HEIDI_API_KEY"
echo "   3. 运行: python3 integrations/standalone/main.py --show-config"
echo ""
