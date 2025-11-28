"""
智能屏幕捕获和EMR系统识别模块
自动截取全屏 → 识别EMR系统类型 → 定位病人信息区域 → 提取数据
"""

import re
from typing import Dict, Optional, Tuple, List
from pathlib import Path
from PIL import Image

from .capture import capture_full_screen
from .ocr_parser import run_ocr, parse_patient_info
from .config import DEBUG_MODE


class EMRSystemDetector:
    """EMR系统类型检测器"""

    # EMR系统特征关键词库
    EMR_SIGNATURES = {
        "generic_cn": {
            "keywords": ["姓名", "性别", "出生日期", "病历号", "患者", "病人"],
            "min_matches": 3,
            "description": "通用中文EMR系统"
        },
        "generic_en": {
            "keywords": ["Name", "Gender", "Date of Birth", "Patient ID", "MRN", "DOB"],
            "min_matches": 3,
            "description": "通用英文EMR系统"
        },
        "his_cn": {
            "keywords": ["HIS", "医院信息系统", "住院", "门诊", "就诊"],
            "min_matches": 2,
            "description": "中文HIS系统"
        },
        "epic": {
            "keywords": ["Epic", "MyChart", "Hyperspace"],
            "min_matches": 1,
            "description": "Epic EMR系统"
        },
        "cerner": {
            "keywords": ["Cerner", "PowerChart", "Millennium"],
            "min_matches": 1,
            "description": "Cerner EMR系统"
        }
    }

    @classmethod
    def detect_emr_system(cls, ocr_text: str) -> Dict[str, any]:
        """
        检测EMR系统类型

        参数:
            ocr_text: OCR识别的文本

        返回:
            Dict: {
                "system_type": str,  # 检测到的系统类型
                "confidence": float,  # 置信度 (0-1)
                "description": str,   # 系统描述
                "matched_keywords": List[str]  # 匹配到的关键词
            }
        """
        best_match = None
        best_score = 0
        best_keywords = []

        for system_type, signature in cls.EMR_SIGNATURES.items():
            matched_keywords = []

            # 检查每个关键词是否出现在OCR文本中
            for keyword in signature["keywords"]:
                if re.search(keyword, ocr_text, re.IGNORECASE):
                    matched_keywords.append(keyword)

            # 计算匹配分数
            match_count = len(matched_keywords)
            required_matches = signature["min_matches"]

            if match_count >= required_matches:
                # 计算置信度：匹配数量 / 总关键词数量
                confidence = match_count / len(signature["keywords"])

                if confidence > best_score:
                    best_score = confidence
                    best_match = system_type
                    best_keywords = matched_keywords

        # 如果没有明确匹配，尝试智能判断
        if best_match is None:
            if any(char >= '\u4e00' and char <= '\u9fff' for char in ocr_text):
                # 包含中文字符，默认为中文系统
                best_match = "generic_cn"
                best_score = 0.5
                best_keywords = ["中文字符检测"]
            else:
                # 英文系统
                best_match = "generic_en"
                best_score = 0.5
                best_keywords = ["英文字符检测"]

        result = {
            "system_type": best_match,
            "confidence": best_score,
            "description": cls.EMR_SIGNATURES.get(best_match, {}).get("description", "未知系统"),
            "matched_keywords": best_keywords
        }

        if DEBUG_MODE:
            print(f"\n🔍 EMR系统检测结果:")
            print(f"   系统类型: {result['system_type']}")
            print(f"   置信度: {result['confidence']:.2%}")
            print(f"   描述: {result['description']}")
            print(f"   匹配关键词: {', '.join(result['matched_keywords'])}")

        return result


class SmartRegionDetector:
    """智能区域检测器 - 定位病人信息区域"""

    # 病人信息相关关键词（用于定位区域）
    PATIENT_INFO_KEYWORDS = [
        "姓名", "性别", "出生", "病历", "患者", "病人",
        "Name", "Gender", "Birth", "Patient", "DOB", "MRN"
    ]

    @classmethod
    def find_patient_info_region(cls, image_path: str, ocr_result: any = None) -> Optional[Tuple[int, int, int, int]]:
        """
        在全屏截图中定位病人信息区域

        参数:
            image_path: 图片路径
            ocr_result: PaddleOCR的完整结果（包含文本位置信息）

        返回:
            Optional[Tuple]: (left, top, width, height) 或 None
        """
        # 这个功能需要OCR的位置信息
        # 在当前实现中，我们先返回None，使用全图识别
        # 后续可以优化为基于OCR位置信息的智能裁剪

        if DEBUG_MODE:
            print("\n📍 智能区域检测:")
            print("   当前使用全图识别，未来版本将支持智能区域裁剪")

        return None


def smart_capture_and_extract(
    display_prompt: bool = True,
    countdown: int = 3
) -> Dict[str, any]:
    """
    智能捕获和提取：全屏截图 → 自动识别EMR系统 → 提取病人信息

    参数:
        display_prompt: 是否显示准备提示
        countdown: 倒计时秒数

    返回:
        Dict: {
            "success": bool,
            "screenshot_path": str,
            "ocr_text": str,
            "emr_system": Dict,  # EMR系统检测结果
            "patient_info": Dict,  # 病人信息
            "detected_region": Optional[Tuple],  # 检测到的区域
            "error": Optional[str]
        }
    """
    import time
    from rich.console import Console

    console = Console()

    result = {
        "success": False,
        "screenshot_path": None,
        "ocr_text": None,
        "emr_system": None,
        "patient_info": None,
        "detected_region": None,
        "error": None
    }

    try:
        # 步骤 1: 提示用户准备
        if display_prompt:
            console.print("\n[bold cyan]🤖 智能模式启动[/bold cyan]")
            console.print("[yellow]请确保 EMR 系统已打开并显示病人信息[/yellow]")
            console.print(f"\n[dim]{countdown} 秒后自动截取全屏...[/dim]")

            for i in range(countdown, 0, -1):
                print(f"\r   {i}...", end="", flush=True)
                time.sleep(1)
            print("\r   ", end="", flush=True)

        # 步骤 2: 全屏截图
        console.print("\n[bold cyan]📸 正在截取全屏...[/bold cyan]")
        screenshot_path = capture_full_screen()
        result["screenshot_path"] = screenshot_path
        console.print(f"[green]✅ 截图成功: {screenshot_path}[/green]")

        # 步骤 3: OCR 识别
        console.print("\n[bold cyan]🔍 正在识别屏幕内容 (OCR)...[/bold cyan]")
        ocr_text = run_ocr(screenshot_path)
        result["ocr_text"] = ocr_text

        if DEBUG_MODE:
            console.print(f"[dim]识别文本长度: {len(ocr_text)} 字符[/dim]")

        console.print(f"[green]✅ OCR 识别完成[/green]")

        # 步骤 4: 检测 EMR 系统类型
        console.print("\n[bold cyan]🔍 正在检测 EMR 系统类型...[/bold cyan]")
        emr_detection = EMRSystemDetector.detect_emr_system(ocr_text)
        result["emr_system"] = emr_detection

        console.print(f"[green]✅ 检测到系统: {emr_detection['description']}[/green]")
        console.print(f"[dim]   置信度: {emr_detection['confidence']:.0%}[/dim]")

        # 步骤 5: 提取病人信息
        console.print("\n[bold cyan]📋 正在提取病人信息...[/bold cyan]")
        patient_info = parse_patient_info(
            ocr_text,
            emr_system=emr_detection['system_type']
        )
        result["patient_info"] = patient_info

        # 检查是否成功提取到关键信息
        required_fields = ["first_name", "last_name", "birth_date", "gender", "ehr_patient_id"]
        extracted_fields = [f for f in required_fields if patient_info.get(f)]

        if len(extracted_fields) >= 3:  # 至少提取到3个关键字段
            result["success"] = True
            console.print(f"[green]✅ 成功提取 {len(extracted_fields)}/{len(required_fields)} 个关键字段[/green]")
        else:
            result["success"] = False
            result["error"] = f"仅提取到 {len(extracted_fields)}/{len(required_fields)} 个关键字段，可能不完整"
            console.print(f"[yellow]⚠️  {result['error']}[/yellow]")

        return result

    except Exception as e:
        result["error"] = str(e)
        if DEBUG_MODE:
            import traceback
            console.print(traceback.format_exc())
        return result


def smart_capture_with_region_detection(
    display_prompt: bool = True,
    countdown: int = 3
) -> Dict[str, any]:
    """
    智能捕获（带区域检测）：
    1. 全屏截图
    2. OCR识别全屏
    3. 检测EMR系统类型
    4. 定位病人信息区域
    5. 重新截图该区域
    6. 提取病人信息

    参数:
        display_prompt: 是否显示准备提示
        countdown: 倒计时秒数

    返回:
        Dict: 与 smart_capture_and_extract 相同
    """
    # 目前先使用全图识别
    # 后续版本可以实现基于OCR位置信息的智能区域裁剪
    return smart_capture_and_extract(display_prompt, countdown)


# 方便导入
__all__ = [
    "EMRSystemDetector",
    "SmartRegionDetector",
    "smart_capture_and_extract",
    "smart_capture_with_region_detection",
]


if __name__ == "__main__":
    # 测试智能捕获
    print("=== 智能捕获模块测试 ===\n")

    result = smart_capture_and_extract(display_prompt=True, countdown=5)

    print("\n" + "="*50)
    print("测试结果:")
    print(f"  成功: {result['success']}")
    print(f"  EMR系统: {result['emr_system']['system_type'] if result['emr_system'] else 'N/A'}")
    print(f"  截图路径: {result['screenshot_path']}")

    if result['patient_info']:
        print("\n病人信息:")
        for key, value in result['patient_info'].items():
            if key != "additional_context" and value:
                print(f"  {key}: {value}")

    if result['error']:
        print(f"\n错误: {result['error']}")
