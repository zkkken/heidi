"""
heidi_menu.py
Heidi RPA 主控台 - 交互式菜单

运行方式: python heidi_menu.py
"""
import sys
import os
import time
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

# 加载配置
load_dotenv(override=True)

# 确保路径正确
sys.path.insert(0, os.getcwd())
from core.rpa_automation import RPAWorkflow

console = Console()


def main():
    workflow = RPAWorkflow()

    while True:
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]🏥 Heidi EMR Automation Suite[/bold cyan]\n\n"
            "[1] 📋 [bold]批量建档模式[/bold] (识别列表 -> 预览确认 -> 批量导入)\n"
            "[2] 🎯 [bold]精准深挖模式[/bold] (点击首位 -> 提取详情 -> 上传)\n"
            "[3] ⚡ [bold]极速批量模式[/bold] (无需确认，直接导入)\n"
            "[4] 🔍 [bold]精准定位测试[/bold] (仅移动鼠标，不点击)\n"
            "[5] 🚪 退出",
            title="主菜单", border_style="blue"
        ))

        choice = input("请选择功能 (1-5): ").strip()

        if choice == '1':
            workflow.run_batch_import()
            input("\n按回车键返回菜单...")

        elif choice == '2':
            # 可以让用户选择点击第几个病人
            idx_input = input("点击第几位病人? (默认 1): ").strip()
            target_idx = int(idx_input) - 1 if idx_input.isdigit() else 0
            workflow.run_precise_entry(target_index=target_idx)
            input("\n按回车键返回菜单...")

        elif choice == '3':
            workflow.run_fast_batch_import()
            input("\n按回车键返回菜单...")

        elif choice == '4':
            workflow.run_precise_click_demo()
            input("\n按回车键返回菜单...")

        elif choice == '5':
            console.print("👋 再见!")
            sys.exit()

        else:
            console.print("[red]无效选项[/red]")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已终止")
