"""
配置管理模块
集中管理所有配置项，支持从环境变量和配置文件读取
"""

import os
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ============================================
# Heidi Health API 配置
# ============================================

# Heidi API 基础 URL（根据官方文档调整）
HEIDI_BASE_URL: str = os.getenv("HEIDI_BASE_URL", "https://api.heidihealth.com")

# Heidi API Key 环境变量名称
HEIDI_API_KEY_ENV_NAME: str = "HEIDI_API_KEY"

# 从环境变量读取 API Key
HEIDI_API_KEY: Optional[str] = os.getenv(HEIDI_API_KEY_ENV_NAME)

# 认证相关配置（使用 shared API key 换取 JWT）
HEIDI_AUTH_EMAIL: str = os.getenv("HEIDI_AUTH_EMAIL", "emr-demo@example.com")
HEIDI_AUTH_INTERNAL_ID: int = int(os.getenv("HEIDI_AUTH_INTERNAL_ID", "1"))

# ============================================
# 截图配置
# ============================================

# 截图区域配置 (left, top, width, height)
# 默认值为示例，用户需要根据自己的 EMR 系统和屏幕分辨率调整
#
# 如何获取正确的坐标：
# 1. 打开 EMR 系统，切到病人详情页面
# 2. 运行 get_screen_coordinates_helper() 函数（在 capture.py 中）
# 3. 根据鼠标位置记录下病人信息区域的 left, top, width, height
#
# 示例：
# - left=100: 距离屏幕左边 100 像素
# - top=200: 距离屏幕顶部 200 像素
# - width=800: 截图宽度 800 像素
# - height=400: 截图高度 400 像素

DEFAULT_SCREENSHOT_REGION: Tuple[int, int, int, int] = (
    int(os.getenv("SCREENSHOT_LEFT", "100")),
    int(os.getenv("SCREENSHOT_TOP", "200")),
    int(os.getenv("SCREENSHOT_WIDTH", "800")),
    int(os.getenv("SCREENSHOT_HEIGHT", "400"))
)

# 截图保存目录
SCREENSHOT_OUTPUT_DIR: Path = Path(os.getenv("SCREENSHOT_OUTPUT_DIR", "./tmp/screenshots"))

# 确保输出目录存在
SCREENSHOT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# OCR 配置
# ============================================

# OCR 语言设置
# 'ch': 中文, 'en': 英文, 'ch_en': 中英文混合
OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "ch")

# 是否使用角度分类器（提高识别准确率，但速度稍慢）
OCR_USE_ANGLE_CLS: bool = os.getenv("OCR_USE_ANGLE_CLS", "True").lower() == "true"

# 是否使用 GPU 加速
OCR_USE_GPU: bool = os.getenv("OCR_USE_GPU", "False").lower() == "true"

# OCR 识别置信度阈值（0-1，越高越严格）
OCR_CONFIDENCE_THRESHOLD: float = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.6"))

# ============================================
# EMR 解析规则配置
# ============================================

# 支持的 EMR 系统类型
class EMRSystemType:
    GENERIC_CN = "generic_cn"      # 通用中文 EMR
    GENERIC_EN = "generic_en"      # 通用英文 EMR
    CUSTOM = "custom"               # 自定义规则

# 当前使用的 EMR 系统类型
CURRENT_EMR_SYSTEM: str = os.getenv("EMR_SYSTEM_TYPE", EMRSystemType.GENERIC_CN)

# EMR 解析规则配置文件路径
EMR_PARSING_RULES_FILE: Optional[Path] = None
if os.getenv("EMR_PARSING_RULES_FILE"):
    EMR_PARSING_RULES_FILE = Path(os.getenv("EMR_PARSING_RULES_FILE"))

# ============================================
# 日志配置
# ============================================

# 日志级别：DEBUG, INFO, WARNING, ERROR
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# 是否启用详细日志（调试模式）
DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"

# 日志输出目录
LOG_OUTPUT_DIR: Path = Path(os.getenv("LOG_OUTPUT_DIR", "./tmp/logs"))
LOG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# 高级配置
# ============================================

# 请求超时时间（秒）
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

# API 调用重试次数
API_RETRY_COUNT: int = int(os.getenv("API_RETRY_COUNT", "3"))

# OCR 识别失败后是否允许手动输入
ALLOW_MANUAL_INPUT: bool = os.getenv("ALLOW_MANUAL_INPUT", "True").lower() == "true"


# ============================================
# 配置验证函数
# ============================================

def validate_config() -> Dict[str, Any]:
    """
    验证配置是否完整和有效
    返回验证结果字典
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": []
    }

    # 检查 Heidi API Key
    if not HEIDI_API_KEY:
        results["valid"] = False
        results["errors"].append(
            f"未找到 Heidi API Key。请在 .env 文件中设置 {HEIDI_API_KEY_ENV_NAME}=your_api_key"
        )

    # 检查截图区域配置
    left, top, width, height = DEFAULT_SCREENSHOT_REGION
    if width <= 0 or height <= 0:
        results["valid"] = False
        results["errors"].append(
            f"截图区域配置无效：width={width}, height={height}。请检查 config.py 或环境变量。"
        )

    # 警告：使用默认截图区域
    if DEFAULT_SCREENSHOT_REGION == (100, 200, 800, 400):
        results["warnings"].append(
            "您正在使用默认截图区域 (100, 200, 800, 400)。"
            "请根据您的 EMR 系统和屏幕分辨率调整 config.py 中的 SCREENSHOT_REGION。"
        )

    # 检查 Heidi base URL
    if not HEIDI_BASE_URL.startswith("http"):
        results["valid"] = False
        results["errors"].append(
            f"Heidi base URL 格式无效：{HEIDI_BASE_URL}"
        )

    return results


def get_config_summary() -> str:
    """
    获取配置摘要（用于调试）
    """
    return f"""
=== EMR to Heidi Integration - 配置摘要 ===

Heidi API:
  - Base URL: {HEIDI_BASE_URL}
  - API Key: {'已设置' if HEIDI_API_KEY else '未设置'}
  - Auth Email: {HEIDI_AUTH_EMAIL}
  - Auth Internal ID: {HEIDI_AUTH_INTERNAL_ID}

截图配置:
  - 区域 (L,T,W,H): {DEFAULT_SCREENSHOT_REGION}
  - 输出目录: {SCREENSHOT_OUTPUT_DIR}

OCR 配置:
  - 语言: {OCR_LANGUAGE}
  - 使用角度分类: {OCR_USE_ANGLE_CLS}
  - 使用 GPU: {OCR_USE_GPU}
  - 置信度阈值: {OCR_CONFIDENCE_THRESHOLD}

EMR 系统:
  - 类型: {CURRENT_EMR_SYSTEM}
  - 自定义规则文件: {EMR_PARSING_RULES_FILE or '未设置'}

日志:
  - 级别: {LOG_LEVEL}
  - 调试模式: {DEBUG_MODE}
  - 输出目录: {LOG_OUTPUT_DIR}

高级:
  - 请求超时: {REQUEST_TIMEOUT}s
  - API 重试次数: {API_RETRY_COUNT}
  - 允许手动输入: {ALLOW_MANUAL_INPUT}
==========================================
"""


if __name__ == "__main__":
    # 测试配置
    print(get_config_summary())

    validation = validate_config()
    if not validation["valid"]:
        print("\n❌ 配置验证失败：")
        for error in validation["errors"]:
            print(f"  - {error}")

    if validation["warnings"]:
        print("\n⚠️  配置警告：")
        for warning in validation["warnings"]:
            print(f"  - {warning}")

    if validation["valid"]:
        print("\n✅ 配置验证通过！")
