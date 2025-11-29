"""
test_precision.py
精准识别测试脚本 - 验证 AI 视觉定位准确性

运行: python test_precision.py
"""
from core.rpa_automation import RPAWorkflow
from dotenv import load_dotenv

# 重新加载配置，确保 Key 生效
load_dotenv(override=True)

if __name__ == "__main__":
    workflow = RPAWorkflow()
    # 运行新的精准模式
    workflow.run_identify_and_click_first()
