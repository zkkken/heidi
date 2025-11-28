"""
独立版本 - 主流程编排
串联：截图 → OCR → 解析 → Heidi API
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt

from core.config import (
    DEFAULT_SCREENSHOT_REGION,
    HEIDI_API_KEY,
    ALLOW_MANUAL_INPUT,
    DEBUG_MODE,
    validate_config
)
from core.capture import capture_emr_region, preview_screenshot_region
from core.ocr_parser import run_ocr, parse_patient_info
from core.heidi_client import HeidiClient, PatientProfile, HeidiAPIError
from core.smart_capture import smart_capture_and_extract

# Rich console（美化终端输出）
console = Console()


def run_emr_to_heidi_pipeline(
    screenshot_region: Optional[tuple] = None,
    skip_confirmation: bool = False,
    allow_manual: bool = True,
    preview_screenshot: bool = False,
    smart_mode: bool = False
) -> Dict[str, Any]:
    """
    主流程：EMR 截图 → OCR 识别 → 调用 Heidi API

    流程步骤:
        1. 配置验证
        2. 提示用户打开 EMR 界面
        3. 截图（智能模式会自动截全屏并识别EMR系统）
        4. OCR 识别
        5. 解析病人信息
        6. （可选）用户确认/修正
        7. 调用 Heidi API
        8. 返回结果

    参数:
        screenshot_region: 截图区域 (left, top, width, height)，None 则使用默认配置
        skip_confirmation: 是否跳过用户确认步骤
        allow_manual: 是否允许用户手动输入/修正识别结果
        preview_screenshot: 是否在截图后预览
        smart_mode: 是否启用智能模式（自动截全屏并识别EMR系统）

    返回:
        Dict: 执行结果，包含:
            - success: bool, 是否成功
            - patient_info: dict, 病人信息
            - heidi_result: dict, Heidi API 返回
            - screenshot_path: str, 截图保存路径
            - ocr_text: str, OCR 识别文本
            - emr_system: dict, EMR系统检测结果（仅智能模式）
            - error: str, 错误信息（如果失败）

    异常:
        不会抛出异常，所有错误都会捕获并在返回值中体现
    """
    result = {
        "success": False,
        "patient_info": None,
        "heidi_result": None,
        "screenshot_path": None,
        "ocr_text": None,
        "emr_system": None,
        "error": None
    }

    try:
        # ============================================
        # 步骤 1: 配置验证
        # ============================================
        console.print("\n[bold cyan]🔍 检查配置...[/bold cyan]")

        validation = validate_config()

        if not validation["valid"]:
            console.print("\n[bold red]❌ 配置验证失败！[/bold red]\n")
            for error in validation["errors"]:
                console.print(f"  [red]• {error}[/red]")
            result["error"] = "配置验证失败"
            return result

        if validation["warnings"]:
            console.print("\n[yellow]⚠️  配置警告：[/yellow]")
            for warning in validation["warnings"]:
                console.print(f"  [yellow]• {warning}[/yellow]")

        console.print("[green]✅ 配置验证通过[/green]\n")

        # ============================================
        # 智能模式：自动截屏并识别
        # ============================================
        if smart_mode:
            console.print("\n[bold cyan]🤖 智能模式已启用[/bold cyan]")
            console.print("[dim]将自动截取全屏 → 识别EMR系统 → 提取病人信息[/dim]\n")

            if not skip_confirmation:
                console.print(Panel.fit(
                    "[bold yellow]请确保：[/bold yellow]\n\n"
                    "1. 已经打开 EMR 系统\n"
                    "2. 切换到病人详情页面\n"
                    "3. 病人基本信息区域可见\n"
                    "4. 没有遮挡或弹窗",
                    title="📋 准备工作",
                    border_style="yellow"
                ))

                if not Confirm.ask("\n是否已经准备好？", default=True):
                    console.print("\n[yellow]⏸️  已取消操作[/yellow]")
                    result["error"] = "用户取消"
                    return result

            # 使用智能捕获
            smart_result = smart_capture_and_extract(
                display_prompt=False,  # 已经显示过提示
                countdown=3 if not skip_confirmation else 0
            )

            if not smart_result["success"]:
                console.print(f"\n[red]❌ 智能捕获失败: {smart_result['error']}[/red]")
                result["error"] = smart_result["error"]
                return result

            # 更新结果
            result["screenshot_path"] = smart_result["screenshot_path"]
            result["ocr_text"] = smart_result["ocr_text"]
            result["emr_system"] = smart_result["emr_system"]
            patient_info_dict = smart_result["patient_info"]

            # 显示检测到的EMR系统
            if smart_result["emr_system"]:
                emr_info = smart_result["emr_system"]
                console.print(f"\n[green]✅ 检测到 EMR 系统: {emr_info['description']}[/green]")
                console.print(f"[dim]   置信度: {emr_info['confidence']:.0%}[/dim]")

        else:
            # ============================================
            # 常规模式：使用配置的区域截图
            # ============================================
            # 步骤 2: 提示用户准备 EMR 界面
            if not skip_confirmation:
                console.print(Panel.fit(
                    "[bold yellow]请确保：[/bold yellow]\n\n"
                    "1. 已经打开 EMR 系统\n"
                    "2. 切换到病人详情页面\n"
                    "3. 病人基本信息区域可见\n"
                    "4. 没有遮挡或弹窗",
                    title="📋 准备工作",
                    border_style="yellow"
                ))

                if not Confirm.ask("\n是否已经准备好？", default=True):
                    console.print("\n[yellow]⏸️  已取消操作[/yellow]")
                    result["error"] = "用户取消"
                    return result

            # 步骤 3: 截图
            console.print("\n[bold cyan]📸 正在截图...[/bold cyan]")

            region = screenshot_region or DEFAULT_SCREENSHOT_REGION
            screenshot_path = capture_emr_region(region=region)

            console.print(f"[green]✅ 截图成功：{screenshot_path}[/green]")
            result["screenshot_path"] = screenshot_path

            # 可选：预览截图
            if preview_screenshot:
                from PIL import Image
                img = Image.open(screenshot_path)
                img.show()
                console.print("[dim]已打开截图预览[/dim]")

            # 步骤 4: OCR 识别
            console.print("\n[bold cyan]🔍 正在识别文字 (OCR)...[/bold cyan]")

            ocr_text = run_ocr(screenshot_path)
            result["ocr_text"] = ocr_text

            if DEBUG_MODE:
                console.print(Panel(
                    ocr_text,
                    title="OCR 识别结果",
                    border_style="dim"
                ))

            console.print(f"[green]✅ OCR 识别完成，共识别 {len(ocr_text.splitlines())} 行文字[/green]")

            # 步骤 5: 解析病人信息
            console.print("\n[bold cyan]📋 正在解析病人信息...[/bold cyan]")

            patient_info_dict = parse_patient_info(ocr_text)

        # 显示识别结果
        _display_patient_info(patient_info_dict)

        # ============================================
        # 步骤 6: 用户确认/修正
        # ============================================
        if allow_manual and ALLOW_MANUAL_INPUT:
            patient_info_dict = _confirm_and_correct_patient_info(patient_info_dict)

        # 检查必填字段
        required_fields = ["first_name", "last_name", "birth_date", "gender", "ehr_patient_id"]
        missing_fields = [f for f in required_fields if not patient_info_dict.get(f)]

        if missing_fields:
            console.print(f"\n[red]❌ 缺少必填字段: {', '.join(missing_fields)}[/red]")
            result["error"] = f"缺少必填字段: {', '.join(missing_fields)}"
            return result

        result["patient_info"] = patient_info_dict

        # ============================================
        # 步骤 7: 调用 Heidi API
        # ============================================
        console.print("\n[bold cyan]🚀 正在调用 Heidi Health API...[/bold cyan]")

        # 创建 PatientProfile 对象
        patient_profile = PatientProfile(
            first_name=patient_info_dict["first_name"],
            last_name=patient_info_dict["last_name"],
            birth_date=patient_info_dict["birth_date"],
            gender=patient_info_dict["gender"],
            ehr_patient_id=patient_info_dict["ehr_patient_id"],
            additional_context=f"来自 EMR OCR 识别\n原始文本:\n{ocr_text[:500]}"
        )

        # 初始化 Heidi 客户端
        with HeidiClient() as heidi_client:
            # 认证
            console.print("[dim]正在认证...[/dim]")
            heidi_client.authenticate()
            console.print("[green]✅ 认证成功[/green]")

            # 创建/更新 patient profile
            console.print("[dim]正在创建/更新 patient profile...[/dim]")
            heidi_result = heidi_client.create_or_update_patient_profile(patient_profile)

            result["heidi_result"] = heidi_result
            result["success"] = True

            # 显示结果
            _display_heidi_result(heidi_result)

        console.print("\n[bold green]🎉 流程执行成功！[/bold green]")

        return result

    except HeidiAPIError as e:
        console.print(f"\n[bold red]❌ Heidi API 错误: {str(e)}[/bold red]")
        result["error"] = f"Heidi API 错误: {str(e)}"
        return result

    except Exception as e:
        console.print(f"\n[bold red]❌ 发生错误: {str(e)}[/bold red]")
        if DEBUG_MODE:
            import traceback
            console.print(traceback.format_exc())
        result["error"] = str(e)
        return result


def _display_patient_info(patient_info: Dict[str, Optional[str]]) -> None:
    """显示识别的病人信息（表格形式）"""
    table = Table(title="📋 识别的病人信息", show_header=True, header_style="bold magenta")

    table.add_column("字段", style="cyan", width=20)
    table.add_column("值", style="green")
    table.add_column("状态", justify="center", width=10)

    fields_cn = {
        "last_name": "姓",
        "first_name": "名",
        "birth_date": "出生日期",
        "gender": "性别",
        "ehr_patient_id": "病历号",
    }

    for field, label in fields_cn.items():
        value = patient_info.get(field) or "[dim]未识别[/dim]"
        status = "✅" if patient_info.get(field) else "⚠️"
        table.add_row(label, str(value), status)

    console.print("\n", table, "\n")


def _confirm_and_correct_patient_info(
    patient_info: Dict[str, Optional[str]]
) -> Dict[str, Optional[str]]:
    """允许用户确认和修正识别结果"""

    if not Confirm.ask("识别结果是否正确？", default=True):
        console.print("\n[yellow]请修正错误的字段（留空跳过）：[/yellow]\n")

        fields_cn = {
            "last_name": "姓",
            "first_name": "名",
            "birth_date": "出生日期 (YYYY-MM-DD)",
            "gender": "性别 (MALE/FEMALE/OTHER)",
            "ehr_patient_id": "病历号",
        }

        for field, label in fields_cn.items():
            current_value = patient_info.get(field) or ""
            new_value = Prompt.ask(
                f"  {label}",
                default=current_value
            )
            if new_value:
                patient_info[field] = new_value

        console.print("\n[green]✅ 已更新信息[/green]")

    return patient_info


def _display_heidi_result(heidi_result: Dict[str, Any]) -> None:
    """显示 Heidi API 调用结果"""
    action = heidi_result.get("action", "unknown")
    action_text = "创建" if action == "created" else "更新"

    patient_id = (
        heidi_result.get("id") or
        heidi_result.get("patient_profile_id") or
        heidi_result.get("patient_id") or
        "未知"
    )

    console.print(Panel.fit(
        f"[bold green]{action_text}成功！[/bold green]\n\n"
        f"操作: {action}\n"
        f"Patient Profile ID: {patient_id}",
        title="✅ Heidi API 响应",
        border_style="green"
    ))


# 方便导入
__all__ = [
    "run_emr_to_heidi_pipeline",
]


if __name__ == "__main__":
    # 测试流程
    print("=== 测试主流程 ===\n")
    result = run_emr_to_heidi_pipeline(
        skip_confirmation=False,
        allow_manual=True
    )

    print(f"\n结果: {'成功' if result['success'] else '失败'}")
    if result["error"]:
        print(f"错误: {result['error']}")
