"""
OCR 识别和病人信息解析模块
使用 PaddleOCR 识别 EMR 界面文字，并解析为结构化病人信息
"""

import re
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from pathlib import Path

from .config import (
    OCR_LANGUAGE,
    OCR_USE_ANGLE_CLS,
    OCR_USE_GPU,
    OCR_CONFIDENCE_THRESHOLD,
    CURRENT_EMR_SYSTEM,
    DEBUG_MODE
)

# 延迟导入 PaddleOCR（避免启动时就加载模型）
_ocr_engine = None


def _get_ocr_engine():
    """获取 OCR 引擎实例（单例模式）"""
    global _ocr_engine

    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR

            print("🔄 正在初始化 PaddleOCR 引擎...")
            print("   （首次运行会下载模型文件，约 200MB，请耐心等待）")

            # PaddleOCR 3.x 版本会自动检测 GPU，不再需要 use_gpu 参数
            _ocr_engine = PaddleOCR(
                use_angle_cls=OCR_USE_ANGLE_CLS,
                lang=OCR_LANGUAGE
            )

            print("✅ OCR 引擎初始化完成")

        except ImportError:
            raise ImportError(
                "PaddleOCR 未安装。请运行: pip install paddleocr"
            )
        except Exception as e:
            raise RuntimeError(f"OCR 引擎初始化失败: {str(e)}")

    return _ocr_engine


def run_ocr(image_path: str) -> str:
    """
    使用 PaddleOCR 对指定图片进行 OCR 识别

    参数:
        image_path: 图片文件路径

    返回:
        str: 识别出的原始文本字符串（按识别顺序拼接）

    异常:
        FileNotFoundError: 图片文件不存在
        RuntimeError: OCR 识别失败

    示例:
        >>> text = run_ocr("./screenshot.png")
        >>> print(text)
        姓名: 张三
        性别: 男
        出生日期: 1970-01-01
        病历号: EMR123456
    """
    # 检查文件是否存在
    if not Path(image_path).exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    try:
        ocr_engine = _get_ocr_engine()

        if DEBUG_MODE:
            print(f"🔍 开始 OCR 识别: {image_path}")

        # 执行 OCR
        result = ocr_engine.ocr(image_path, cls=OCR_USE_ANGLE_CLS)

        # 提取文本
        text_lines = []
        for line in result:
            if line is None:
                continue
            for word_info in line:
                # word_info 格式: [[box], (text, confidence)]
                text = word_info[1][0]
                confidence = word_info[1][1]

                # 过滤低置信度的识别结果
                if confidence >= OCR_CONFIDENCE_THRESHOLD:
                    text_lines.append(text)
                elif DEBUG_MODE:
                    print(f"⚠️  低置信度识别（{confidence:.2f}）: {text}")

        ocr_text = "\n".join(text_lines)

        if DEBUG_MODE:
            print(f"✅ OCR 识别完成，共识别 {len(text_lines)} 行文字")
            print(f"\n识别结果:\n{ocr_text}\n")

        return ocr_text

    except Exception as e:
        raise RuntimeError(f"OCR 识别失败: {str(e)}") from e


def parse_patient_info(ocr_text: str,
                       emr_system: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    从 OCR 识别的文本中解析病人基础信息

    参数:
        ocr_text: OCR 识别的原始文本
        emr_system: EMR 系统类型，如果为 None 则使用 config 中的配置

    返回:
        Dict: 病人信息字典，包含以下字段:
            - first_name: 名
            - last_name: 姓
            - birth_date: 出生日期 (YYYY-MM-DD)
            - gender: 性别 (MALE, FEMALE, OTHER)
            - ehr_patient_id: EMR 病人 ID
            - additional_context: 原始 OCR 文本（可选）

    示例:
        >>> ocr_text = "姓名: 张三\\n性别: 男\\n出生日期: 1970-01-01\\n病历号: EMR123456"
        >>> info = parse_patient_info(ocr_text)
        >>> print(info)
        {
            'first_name': '三',
            'last_name': '张',
            'birth_date': '1970-01-01',
            'gender': 'MALE',
            'ehr_patient_id': 'EMR123456',
            'additional_context': '...'
        }
    """
    emr_system = emr_system or CURRENT_EMR_SYSTEM

    if DEBUG_MODE:
        print(f"📋 使用解析规则: {emr_system}")

    # 根据 EMR 系统类型选择解析规则
    if emr_system == "generic_cn":
        return _parse_generic_cn(ocr_text)
    elif emr_system == "generic_en":
        return _parse_generic_en(ocr_text)
    else:
        # 自定义规则（可扩展）
        return _parse_generic_cn(ocr_text)


def _parse_generic_cn(ocr_text: str) -> Dict[str, Optional[str]]:
    """
    解析通用中文 EMR 格式

    支持的格式:
        - 姓名: 张三 / 姓名：张三
        - 性别: 男 / 性别：男
        - 出生日期: 1970-01-01 / 出生日期：1970-01-01
        - 病历号: EMR123456 / 病历号：EMR123456
    """
    patient_info = {
        "first_name": None,
        "last_name": None,
        "birth_date": None,
        "gender": None,
        "ehr_patient_id": None,
        "additional_context": ocr_text
    }

    # 1. 提取姓名
    name_patterns = [
        r"姓名[:：]\s*([^\n\s]+)",
        r"患者姓名[:：]\s*([^\n\s]+)",
        r"病人姓名[:：]\s*([^\n\s]+)",
        r"Name[:：]\s*([^\n\s]+)",
    ]

    for pattern in name_patterns:
        match = re.search(pattern, ocr_text)
        if match:
            full_name = match.group(1).strip()
            # 中文姓名拆分：假设第一个字为姓，其余为名
            if len(full_name) > 0:
                patient_info["last_name"] = full_name[0]
                patient_info["first_name"] = full_name[1:] if len(full_name) > 1 else ""
            break

    # 2. 提取性别
    gender_patterns = [
        r"性别[:：]\s*([男女]|Male|Female|MALE|FEMALE)",
        r"Sex[:：]\s*([男女]|Male|Female|MALE|FEMALE)",
    ]

    for pattern in gender_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            gender_raw = match.group(1).strip()
            patient_info["gender"] = _normalize_gender(gender_raw)
            break

    # 3. 提取出生日期
    birth_date_patterns = [
        r"出生日期[:：]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"出生[:：]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"DOB[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        r"Birth\s*Date[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        # 宽松模式：匹配任何日期格式
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    ]

    for pattern in birth_date_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            date_raw = match.group(1).strip()
            patient_info["birth_date"] = _normalize_date(date_raw)
            break

    # 4. 提取病历号
    ehr_id_patterns = [
        r"病历号[:：]\s*([A-Z0-9]+)",
        r"患者编号[:：]\s*([A-Z0-9]+)",
        r"病人ID[:：]\s*([A-Z0-9]+)",
        r"MRN[:：]\s*([A-Z0-9]+)",
        r"Patient\s*ID[:：]\s*([A-Z0-9]+)",
        # 宽松模式：查找 EMR/HIS 开头的编号
        r"(EMR\d+|HIS\d+|P\d{6,})",
    ]

    for pattern in ehr_id_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            patient_info["ehr_patient_id"] = match.group(1).strip().upper()
            break

    # 数据验证和警告
    _validate_patient_info(patient_info)

    return patient_info


def _parse_generic_en(ocr_text: str) -> Dict[str, Optional[str]]:
    """
    解析通用英文 EMR 格式

    支持的格式:
        - Name: John Doe / First Name: John, Last Name: Doe
        - Gender: Male / Sex: M
        - Date of Birth: 1970-01-01 / DOB: 01/01/1970
        - Patient ID: P123456 / MRN: 123456
    """
    patient_info = {
        "first_name": None,
        "last_name": None,
        "birth_date": None,
        "gender": None,
        "ehr_patient_id": None,
        "additional_context": ocr_text
    }

    # 1. 提取姓名（分离 first/last name）
    # 尝试分离的格式
    first_name_match = re.search(r"First\s*Name[:：]\s*([^\n,]+)", ocr_text, re.IGNORECASE)
    last_name_match = re.search(r"Last\s*Name[:：]\s*([^\n,]+)", ocr_text, re.IGNORECASE)

    if first_name_match and last_name_match:
        patient_info["first_name"] = first_name_match.group(1).strip()
        patient_info["last_name"] = last_name_match.group(1).strip()
    else:
        # 尝试完整姓名格式: Name: John Doe
        name_match = re.search(r"Name[:：]\s*([A-Za-z]+)\s+([A-Za-z]+)", ocr_text, re.IGNORECASE)
        if name_match:
            patient_info["first_name"] = name_match.group(1).strip()
            patient_info["last_name"] = name_match.group(2).strip()

    # 2. 性别
    gender_match = re.search(r"(?:Gender|Sex)[:：]\s*([MFmf]|Male|Female)", ocr_text, re.IGNORECASE)
    if gender_match:
        patient_info["gender"] = _normalize_gender(gender_match.group(1).strip())

    # 3. 出生日期
    dob_match = re.search(
        r"(?:DOB|Date\s*of\s*Birth|Birth\s*Date)[:：]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        ocr_text,
        re.IGNORECASE
    )
    if dob_match:
        patient_info["birth_date"] = _normalize_date(dob_match.group(1).strip())

    # 4. 病历号
    ehr_match = re.search(r"(?:Patient\s*ID|MRN|Medical\s*Record)[:：]\s*([A-Z0-9]+)", ocr_text, re.IGNORECASE)
    if ehr_match:
        patient_info["ehr_patient_id"] = ehr_match.group(1).strip().upper()

    _validate_patient_info(patient_info)

    return patient_info


def _normalize_gender(gender_raw: str) -> str:
    """
    标准化性别值

    参数:
        gender_raw: 原始性别字符串（如 "男", "Female", "M"）

    返回:
        str: 标准化的性别 (MALE, FEMALE, OTHER)
    """
    gender_map = {
        # 中文
        "男": "MALE",
        "女": "FEMALE",
        # 英文完整
        "male": "MALE",
        "female": "FEMALE",
        # 英文缩写
        "m": "MALE",
        "f": "FEMALE",
    }

    gender_normalized = gender_map.get(gender_raw.lower(), "OTHER")
    return gender_normalized


def _normalize_date(date_raw: str) -> str:
    """
    标准化日期格式为 YYYY-MM-DD

    支持的输入格式:
        - 1970-01-01
        - 1970/01/01
        - 01/01/1970 (美国格式)
        - 1970年01月01日

    参数:
        date_raw: 原始日期字符串

    返回:
        str: 标准化的日期 (YYYY-MM-DD)
    """
    # 移除中文字符
    date_clean = date_raw.replace("年", "-").replace("月", "-").replace("日", "")

    # 尝试不同的日期格式
    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",  # 美国格式
        "%d/%m/%Y",  # 欧洲格式
        "%Y%m%d",
    ]

    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_clean, fmt)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # 如果无法解析，返回原始值并在 DEBUG 模式下警告
    if DEBUG_MODE:
        print(f"⚠️  无法解析日期格式: {date_raw}，使用原始值")

    return date_raw


def _validate_patient_info(patient_info: Dict[str, Optional[str]]) -> None:
    """
    验证病人信息完整性并打印警告

    参数:
        patient_info: 病人信息字典
    """
    required_fields = ["first_name", "last_name", "birth_date", "gender", "ehr_patient_id"]

    missing_fields = [
        field for field in required_fields
        if not patient_info.get(field)
    ]

    if missing_fields and DEBUG_MODE:
        print(f"⚠️  以下字段未识别: {', '.join(missing_fields)}")
        print("   建议:")
        print("   1. 检查截图区域是否完整包含病人信息")
        print("   2. 调整解析规则（在 ocr_parser.py 中）")
        print("   3. 使用 --manual 参数手动输入缺失字段")


def extract_patient_info_from_image(image_path: str,
                                     emr_system: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    便捷函数：从图片直接提取病人信息（OCR + 解析一步完成）

    参数:
        image_path: 图片路径
        emr_system: EMR 系统类型

    返回:
        Dict: 病人信息字典

    示例:
        >>> info = extract_patient_info_from_image("./screenshot.png")
        >>> print(info)
    """
    ocr_text = run_ocr(image_path)
    patient_info = parse_patient_info(ocr_text, emr_system)
    return patient_info


# 方便导入
__all__ = [
    "run_ocr",
    "parse_patient_info",
    "extract_patient_info_from_image",
]


if __name__ == "__main__":
    # 测试模块
    import sys

    print("=== OCR 解析模块测试 ===\n")

    # 测试数据
    test_ocr_text_cn = """
    患者基本信息
    姓名: 张三
    性别: 男
    出生日期: 1970年01月15日
    病历号: HIS123456
    电话: 138****1234
    """

    test_ocr_text_en = """
    Patient Information
    First Name: John
    Last Name: Doe
    Gender: Male
    Date of Birth: 01/15/1970
    Patient ID: P123456
    """

    print("测试中文解析:")
    print("-" * 50)
    result_cn = parse_patient_info(test_ocr_text_cn, "generic_cn")
    for key, value in result_cn.items():
        if key != "additional_context":
            print(f"  {key}: {value}")

    print("\n测试英文解析:")
    print("-" * 50)
    result_en = parse_patient_info(test_ocr_text_en, "generic_en")
    for key, value in result_en.items():
        if key != "additional_context":
            print(f"  {key}: {value}")

    print("\n\n如需测试真实图片，运行:")
    print("  python -m core.ocr_parser <image_path>")
