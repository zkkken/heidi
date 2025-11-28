#!/usr/bin/env python3
"""
EMR to Heidi Integration - 独立命令行工具
主程序入口

使用方法:
    python integrations/standalone/main.py [options]

示例:
    # 运行一次完整流程
    python integrations/standalone/main.py

    # 使用自定义截图区域
    python integrations/standalone/main.py --region 100 200 800 600

    # 跳过用户确认
    python integrations/standalone/main.py --yes

    # 预览截图（测试截图配置）
    python integrations/standalone/main.py --preview

    # 获取屏幕坐标（配置截图区域）
    python integrations/standalone/main.py --coords

    # 显示配置信息
    python integrations/standalone/main.py --show-config
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel

from core.config import get_config_summary, DEBUG_MODE
from core.capture import get_screen_coordinates_helper, preview_screenshot_region
from integrations.standalone.pipeline import run_emr_to_heidi_pipeline

console = Console()


def print_banner():
    """打印欢迎横幅"""
    banner_text = """
[bold cyan]╔═══════════════════════════════════════════════════╗
║   EMR → Heidi Health Integration                 ║
║   版本: 1.0.0 (Phase 1 MVP)                      ║
║   混合方案 - 独立命令行工具                         ║
╚═══════════════════════════════════════════════════╝[/bold cyan]

[dim]从本地 EMR 界面截图 → OCR 识别 → 调用 Heidi API[/dim]
"""
    console.print(banner_text)


def setup_argparse() -> argparse.ArgumentParser:
    """配置命令行参数"""
    parser = argparse.ArgumentParser(
        description="EMR to Heidi Health Integration - 独立命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s                              # 运行一次完整流程
  %(prog)s --region 100 200 800 600     # 使用自定义截图区域
  %(prog)s --yes                        # 跳过确认，直接执行
  %(prog)s --preview                    # 预览截图区域（测试配置）
  %(prog)s --coords 15                  # 获取屏幕坐标（15 秒）
  %(prog)s --show-config                # 显示当前配置

更多信息请参阅 README.md
        """
    )

    # 主要功能
    parser.add_argument(
        "--region",
        nargs=4,
        type=int,
        metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"),
        help="自定义截图区域坐标 (覆盖 config.py 中的配置)"
    )

    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="跳过用户确认，直接执行"
    )

    parser.add_argument(
        "--no-manual",
        action="store_true",
        help="禁用手动修正功能"
    )

    parser.add_argument(
        "--preview-screenshot",
        action="store_true",
        help="截图后打开预览"
    )

    parser.add_argument(
        "--smart",
        action="store_true",
        help="启用智能模式（自动截全屏并识别EMR系统）"
    )

    # 工具功能
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览截图区域（用于验证配置）"
    )

    parser.add_argument(
        "--coords",
        type=int,
        metavar="DURATION",
        nargs="?",
        const=10,
        help="获取屏幕坐标（默认 10 秒）"
    )

    parser.add_argument(
        "--show-config",
        action="store_true",
        help="显示当前配置"
    )

    # 调试选项
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="EMR to Heidi Integration v1.0.0 (Phase 1 MVP)"
    )

    return parser


def main():
    """主函数"""
    parser = setup_argparse()
    args = parser.parse_args()

    # 启用调试模式
    if args.debug:
        import core.config as config
        config.DEBUG_MODE = True

    # 打印横幅
    if not any([args.preview, args.coords, args.show_config]):
        print_banner()

    # ============================================
    # 工具功能
    # ============================================

    # 显示配置
    if args.show_config:
        console.print("\n" + get_config_summary())
        return 0

    # 获取屏幕坐标
    if args.coords is not None:
        duration = args.coords
        get_screen_coordinates_helper(duration=duration)
        return 0

    # 预览截图区域
    if args.preview:
        region = tuple(args.region) if args.region else None
        preview_screenshot_region(region=region)
        return 0

    # ============================================
    # 主流程
    # ============================================

    try:
        # 准备参数
        screenshot_region = tuple(args.region) if args.region else None
        skip_confirmation = args.yes
        allow_manual = not args.no_manual
        preview_screenshot = args.preview_screenshot
        smart_mode = args.smart

        # 执行流程
        result = run_emr_to_heidi_pipeline(
            screenshot_region=screenshot_region,
            skip_confirmation=skip_confirmation,
            allow_manual=allow_manual,
            preview_screenshot=preview_screenshot,
            smart_mode=smart_mode
        )

        # 根据结果返回退出代码
        if result["success"]:
            console.print("\n[bold green]✨ 任务完成！[/bold green]\n")
            return 0
        else:
            console.print(f"\n[bold red]❌ 任务失败: {result.get('error', '未知错误')}[/bold red]\n")
            return 1

    except KeyboardInterrupt:
        console.print("\n\n[yellow]⏹️  用户中断操作[/yellow]\n")
        return 130  # 标准的 Ctrl+C 退出代码

    except Exception as e:
        console.print(f"\n[bold red]❌ 程序错误: {str(e)}[/bold red]\n")
        if DEBUG_MODE or args.debug:
            import traceback
            console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
