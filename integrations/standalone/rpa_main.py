#!/usr/bin/env python3
"""
RPA 自动化主程序
端到端自动化：启动应用 → 点击病人 → 提取数据 → 发送到 Heidi
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel

from core.rpa_automation import RPAWorkflow
from core.config import DEBUG_MODE

console = Console()


def print_banner():
    """打印欢迎横幅"""
    banner_text = """
[bold cyan]╔═══════════════════════════════════════════════════╗
║   EMR → Heidi RPA Automation                     ║
║   端到端自动化流程                                  ║
║   版本: 2.0.0 (RPA Mode)                         ║
╚═══════════════════════════════════════════════════╝[/bold cyan]

[dim]自动化流程:
1. 启动 EMR 和 Heidi 浏览器
2. 识别并点击第一个病人
3. 截图并提取数据
4. 自动发送到 Heidi[/dim]
"""
    console.print(banner_text)


def setup_argparse() -> argparse.ArgumentParser:
    """配置命令行参数"""
    parser = argparse.ArgumentParser(
        description="EMR to Heidi RPA Automation - 端到端自动化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s                                    # 运行完整 RPA 流程
  %(prog)s --emr-path /path/to/emr.app       # 指定 EMR 应用路径
  %(prog)s --heidi-url https://app.heidi.com # 指定 Heidi URL
  %(prog)s --debug                            # 调试模式

注意:
  - 首次使用建议手动打开 EMR 应用
  - 确保 EMR 界面显示病人列表
  - 确保网络连接正常（访问 Heidi API）

更多信息请参阅 RPA自动化使用说明.md
        """
    )

    parser.add_argument(
        "--emr-path",
        type=str,
        metavar="PATH",
        help="EMR 应用程序路径（可选，留空则需手动打开）"
    )

    parser.add_argument(
        "--heidi-url",
        type=str,
        default="https://www.heidihealth.com",
        metavar="URL",
        help="Heidi 网址（默认: https://www.heidihealth.com）"
    )

    parser.add_argument(
        "--skip-launch",
        action="store_true",
        help="跳过应用启动步骤（假设应用已打开）"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="EMR to Heidi RPA Automation v2.0.0"
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
    print_banner()

    # 提示用户
    console.print("\n[bold yellow]⚠️  注意事项：[/bold yellow]")
    console.print("1. 确保 EMR 系统可以正常访问")
    console.print("2. 确保配置了 Heidi API Key (.env 文件)")
    console.print("3. RPA 流程会自动控制鼠标和键盘")
    console.print("4. 执行过程中请勿移动鼠标或操作键盘\n")

    # 询问是否继续
    try:
        user_input = input("是否继续？(y/n) [y]: ").strip().lower()
        if user_input and user_input not in ['y', 'yes']:
            console.print("\n[yellow]⏸️  已取消操作[/yellow]")
            return 0
    except KeyboardInterrupt:
        console.print("\n\n[yellow]⏸️  已取消操作[/yellow]")
        return 130

    # 创建 RPA 工作流
    workflow = RPAWorkflow(
        emr_app_path=args.emr_path,
        heidi_url=args.heidi_url
    )

    try:
        # 执行完整工作流
        result = workflow.run_full_workflow()

        # 显示结果
        if result["success"]:
            console.print("\n" + "="*50)
            console.print("[bold green]🎉 RPA 自动化执行成功！[/bold green]")
            console.print("="*50)

            if result["patient_data"]:
                console.print("\n[cyan]病人信息:[/cyan]")
                for key, value in result["patient_data"].items():
                    if key != "additional_context" and value:
                        console.print(f"  {key}: {value}")

            return 0
        else:
            console.print("\n" + "="*50)
            console.print(f"[bold red]❌ RPA 执行失败[/bold red]")
            console.print("="*50)
            console.print(f"\n[red]错误: {result['error']}[/red]")
            console.print(f"\n[dim]已完成步骤: {', '.join(result['steps_completed'])}[/dim]")

            return 1

    except KeyboardInterrupt:
        console.print("\n\n[yellow]⏹️  用户中断操作[/yellow]")
        return 130

    except Exception as e:
        console.print(f"\n[bold red]❌ 程序错误: {str(e)}[/bold red]\n")
        if DEBUG_MODE or args.debug:
            import traceback
            console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
