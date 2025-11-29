"""
main.py
Heidi RPA 主入口 v8.0 - Chrome 注入版

运行方式: python main.py
"""
import sys
import os
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

# 加载环境
load_dotenv(override=True)
sys.path.insert(0, os.getcwd())

from core.rpa_automation import RPAWorkflow

console = Console()


def main():
    try:
        workflow = RPAWorkflow()

        while True:
            console.clear()
            console.print(Panel.fit(
                "[bold cyan]🏥 Heidi EMR Automation v8.0[/bold cyan]\n"
                "[dim]Hard Coords: Active | Chrome Injection: Enabled[/dim]\n\n"
                "[1] 📋 [bold]批量日程 (Batch -> Web)[/bold]\n"
                "    EMR 列表读取 -> 生成 JSON -> Chrome 注入\n\n"
                "[2] 🎯 [bold]精准 Consultations[/bold] [green]推荐[/green]\n"
                "    AI/硬坐标双重定位 -> 病人 -> Consultations -> 提取 -> 注入 Web\n\n"
                "[3] 💉 [bold]单人 Context 注入[/bold]\n"
                "    EMR 点击 -> AI 提取病历 -> Chrome 注入\n\n"
                "[4] ⚡ [bold]智能点击 (Auto-Correct)[/bold]\n"
                "    AI定位 + 硬坐标纠偏 -> Heidi API 上传\n\n"
                "[5] 🔧 [bold]更多选项[/bold]\n"
                "    批量建档 / 极速模式 / 旧版菜单\n\n"
                "[q] 退出",
                title="主菜单", border_style="blue"
            ))

            choice = input("请选择功能: ").strip().lower()

            if choice == '1':
                workflow.run_batch_pipeline()
                input("\n按回车键返回...")

            elif choice == '2':
                workflow.run_precise_consultations_pipeline()
                input("\n按回车键返回...")

            elif choice == '3':
                workflow.run_single_pipeline()
                input("\n按回车键返回...")

            elif choice == '4':
                workflow.run_smart_click_auto()
                input("\n按回车键返回...")

            elif choice == '5':
                # 子菜单
                console.clear()
                console.print(Panel.fit(
                    "[bold]更多选项[/bold]\n\n"
                    "[a] 批量建档 (Heidi API)\n"
                    "[b] 极速批量 (无确认)\n"
                    "[c] 精准深挖 (v5.0)\n"
                    "[d] 旧版菜单 (heidi_menu.py)\n"
                    "[q] 返回",
                    border_style="dim"
                ))
                sub = input("选择: ").strip().lower()
                if sub == 'a':
                    workflow.run_batch_all()
                elif sub == 'b':
                    workflow.run_fast_batch_import()
                elif sub == 'c':
                    workflow.run_smart_single()
                elif sub == 'd':
                    import subprocess
                    subprocess.run([sys.executable, "heidi_menu.py"])
                input("\n按回车键返回...")

            elif choice == 'q':
                console.print("👋 Bye!")
                sys.exit()

            else:
                console.print("[red]无效选项[/red]")
                import time
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
