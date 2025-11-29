"""
core/web_bridge.py
Chrome Direct Injector - 使用 macOS AppleScript 直接操控浏览器 DOM
"""
import subprocess
import time
from rich.console import Console

console = Console()


class WebBridge:
    def _run_applescript(self, js_code: str) -> bool:
        """
        通过 AppleScript 在当前 Chrome 活动标签页执行 JS
        """
        # 转义 JS 代码中的双引号和反斜杠，防止 AppleScript 报错
        js_safe = js_code.replace('\\', '\\\\').replace('"', '\\"')

        script = f'''
        tell application "Google Chrome"
            if (count of windows) > 0 then
                execute front window's active tab javascript "{js_safe}"
            end if
        end tell
        '''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[red]注入失败: {result.stderr}[/red]")
                return False
            return True
        except Exception as e:
            console.print(f"[red]系统错误: {e}[/red]")
            return False

    def focus_chrome(self):
        """将 Chrome 窗口置顶"""
        script = 'tell application "Google Chrome" to activate'
        subprocess.run(['osascript', '-e', script])
        time.sleep(0.5)

    def inject_batch_schedule(self, json_data: str):
        """
        [批量模式] 注入 JSON 并点击生成
        目标：左侧 Textarea + "生成 Schedule" 按钮
        """
        # 转义 JSON 中的特殊字符
        safe_json = json_data.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

        js = f'''
        (function() {{
            // 1. 找输入框 (假设页面左侧主要是一个 Textarea)
            var textareas = document.querySelectorAll('textarea');
            var input = textareas[0]; // 默认取第一个

            if (input) {{
                input.value = `{safe_json}`;
                // 触发 React/Vue 的输入事件
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }} else {{
                console.log("RPA Error: 找不到输入框");
                return;
            }}

            // 2. 找按钮 (通过文字内容)
            var buttons = document.querySelectorAll('button');
            var targetBtn = Array.from(buttons).find(b => b.textContent.includes("生成 Schedule") || b.textContent.includes("Generate"));

            if (targetBtn) {{
                setTimeout(() => targetBtn.click(), 200);
            }} else {{
                console.log("RPA Warning: 找不到'生成 Schedule'按钮");
            }}
        }})();
        '''
        self.focus_chrome()
        self._run_applescript(js)
        console.print("[green]⚡️ 数据已光速注入 Web 界面[/green]")

    def inject_single_context(self, context_text: str):
        """
        [精准模式] 注入 Context 并点击填入
        目标：右侧 Textarea + "填入 Context" 按钮
        """
        # 转义特殊字符
        safe_text = context_text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

        js = f'''
        (function() {{
            // 1. 找输入框 (策略：找第二个 textarea，或者 placeholder 包含 '详细内容' 的)
            var textareas = document.querySelectorAll('textarea');
            // 通常第二个 textarea 是右边的 Context 输入框
            var input = textareas.length > 1 ? textareas[1] : textareas[0];

            if (input) {{
                input.value = `{safe_text}`;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}

            // 2. 找按钮
            var buttons = document.querySelectorAll('button');
            var targetBtn = Array.from(buttons).find(b => b.textContent.includes("填入 Context") || b.textContent.includes("Update Context") || b.textContent.includes("Submit"));

            if (targetBtn) {{
                setTimeout(() => targetBtn.click(), 200);
            }}
        }})();
        '''
        self.focus_chrome()
        self._run_applescript(js)
        console.print("[green]⚡️ Context 已注入 Web 界面[/green]")

    def inject_text_to_input(self, text: str, input_selector: str = "textarea", button_text: str = None):
        """
        [通用方法] 注入文本到指定输入框
        """
        safe_text = text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

        button_js = ""
        if button_text:
            button_js = f'''
            var buttons = document.querySelectorAll('button');
            var targetBtn = Array.from(buttons).find(b => b.textContent.includes("{button_text}"));
            if (targetBtn) {{ setTimeout(() => targetBtn.click(), 200); }}
            '''

        js = f'''
        (function() {{
            var input = document.querySelector('{input_selector}');
            if (input) {{
                input.value = `{safe_text}`;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            {button_js}
        }})();
        '''
        self.focus_chrome()
        self._run_applescript(js)
        console.print("[green]⚡️ 数据已注入[/green]")
