#!/bin/bash
# 测试虚拟环境中的 PaddleOCR

cd "$(dirname "$0")"

echo "📍 激活虚拟环境..."
source venv/bin/activate

echo "📍 Python 路径: $(which python)"
echo "📍 pip 路径: $(which pip)"
echo ""

echo "🔍 检查已安装的包..."
pip list | grep -E "(paddle|ocr|PIL|pyautogui)" || echo "未找到相关包"
echo ""

echo "🧪 测试导入 PaddleOCR..."
python << 'PYEOF'
import sys
print(f"Python 版本: {sys.version}")
print(f"Python 路径: {sys.executable}")
print("")

try:
    from paddleocr import PaddleOCR
    print("✅ PaddleOCR 导入成功！")
except ImportError as e:
    print(f"❌ PaddleOCR 导入失败: {e}")
    sys.exit(1)

try:
    import PIL
    print("✅ Pillow 导入成功！")
except ImportError as e:
    print(f"❌ Pillow 导入失败: {e}")
    sys.exit(1)

try:
    import pyautogui
    print("✅ pyautogui 导入成功！")
except ImportError as e:
    print(f"❌ pyautogui 导入失败: {e}")
    sys.exit(1)

print("")
print("🎉 所有核心模块导入正常！")
PYEOF

echo ""
echo "✅ 测试完成"
