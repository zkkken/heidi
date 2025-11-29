"""
core/web_bridge.py
Web Injector v3.0 - React-Compatible JS Injection (无鼠标纯代码版)
"""
import subprocess
import time
from rich.console import Console

console = Console()


class WebBridge:
    def _run_applescript(self, js_code: str):
        """
        通过 AppleScript 在 Chrome 执行 JS
        """
        # 转义 JS 代码中的双引号和反斜杠
        js_safe = js_code.replace('\\', '\\\\').replace('"', '\\"')

        script = f'''
        tell application "Google Chrome"
            if (count of windows) > 0 then
                execute front window's active tab javascript "{js_safe}"
            end if
        end tell
        '''
        try:
            # 这里的 capture_output=True 会捕获错误，如果没报错但没反应，通常是 JS 逻辑问题
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[red]AppleScript 错误: {result.stderr}[/red]")
                return False
            return True
        except Exception as e:
            console.print(f"[red]系统错误: {e}[/red]")
            return False

    def focus_chrome(self):
        """激活 Chrome"""
        subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to activate'])
        time.sleep(0.2)

    def inject_batch_schedule(self, json_data: str):
        """
        [批量模式] 注入 JSON
        """
        # React 专用注入脚本
        js = f'''
        (function() {{
            console.log("RPA: 开始注入 Batch 数据...");

            // 1. 找输入框 (策略: 找页面上第一个 visible 的 textarea)
            var textareas = Array.from(document.querySelectorAll('textarea'));
            var input = textareas.find(t => t.offsetParent !== null); // 找可见的

            if (!input) input = textareas[0]; // 保底

            if (input) {{
                // ★★★ 核心修复：React 兼容写法 ★★★
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                nativeInputValueSetter.call(input, `{json_data}`);

                // 必须触发 input 事件，React 才会监听到变化
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                console.log("RPA: 数据注入成功");
            }} else {{
                console.error("RPA: 未找到 Textarea");
                alert("RPA Error: 找不到输入框");
            }}

            // 2. 找按钮并点击
            setTimeout(() => {{
                var buttons = Array.from(document.querySelectorAll('button'));
                var targetBtn = buttons.find(b => b.innerText.includes("生成 Schedule") || b.innerText.includes("Generate"));

                if (targetBtn) {{
                    targetBtn.click();
                    console.log("RPA: 按钮已点击");
                }} else {{
                    console.error("RPA: 未找到生成按钮");
                }}
            }}, 200); // 稍微延迟，确保数据已同步
        }})();
        '''
        self.focus_chrome()
        self._run_applescript(js)
        console.print("[green]⚡️ JS 指令已发送 (React 模式)[/green]")

    def inject_single_context(self, context_text: str):
        """
        [精准模式] 注入 Context
        """
        js = f'''
        (function() {{
            console.log("RPA: 开始注入 Context...");

            // 1. 找输入框 (策略: 找第二个 textarea，或者 placeholder 包含 Context 的)
            var textareas = Array.from(document.querySelectorAll('textarea'));
            // 假设布局是：左边一个(Batch)，右边一个(Context) -> 取最后一个
            var input = textareas[textareas.length - 1];

            if (input) {{
                // ★★★ 核心修复：React 兼容写法 ★★★
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                nativeInputValueSetter.call(input, `{context_text}`);

                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                console.log("RPA: Context 注入成功");
            }}

            // 2. 找按钮
            setTimeout(() => {{
                var buttons = Array.from(document.querySelectorAll('button'));
                var targetBtn = buttons.find(b => b.innerText.includes("填入 Context") || b.innerText.includes("Update"));

                if (targetBtn) {{
                    targetBtn.click();
                    console.log("RPA: 按钮已点击");
                }}
            }}, 200);
        }})();
        '''
        self.focus_chrome()
        self._run_applescript(js)
        console.print("[green]⚡️ JS 指令已发送 (React 模式)[/green]")
