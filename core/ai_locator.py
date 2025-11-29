"""
core/ai_locator.py
AI 视觉定位器 - 调用 Claude API 分析屏幕截图并返回坐标
"""

import os
import base64
import json
import time
from typing import Dict, Optional, Tuple
import pyautogui
from anthropic import Anthropic
from rich.console import Console

# 引用现有配置
from .config import DEBUG_MODE

console = Console()

class AINavigator:
    def __init__(self, api_key: Optional[str] = None):
        # 优先使用传入的 Key，否则读取环境变量
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 ANTHROPIC_API_KEY，请在 .env 文件中配置")

        self.client = Anthropic(api_key=self.api_key)
        self.model = os.getenv("AI_MODEL_NAME", "claude-3-5-sonnet-20241022")

        # 获取当前屏幕物理分辨率，用于坐标校准（如果需要）
        self.screen_width, self.screen_height = pyautogui.size()

    def _encode_image(self, image_path: str) -> str:
        """将图片转换为 base64 编码"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def locate_target(self, screenshot_path: str, prompt_instruction: str) -> Optional[Dict]:
        """
        通用的 AI 视觉定位函数

        参数:
            screenshot_path: 截图路径
            prompt_instruction: 告诉 AI 要找什么（例如："找到病人列表的第一行"）

        返回:
            Dict: {found: bool, x: int, y: int, reason: str}
        """
        base64_image = self._encode_image(screenshot_path)

        # 系统提示词：强制输出 JSON 格式的坐标
        system_prompt = f"""
        你是一个精通 GUI 自动化的 AI 助手。你的任务是分析屏幕截图，找到用户指定的 UI 元素，并返回其中心点的像素坐标。

        当前屏幕分辨率为: {self.screen_width}x{self.screen_height}。

        请严格遵守以下输出格式，只返回纯 JSON，不要包含任何 Markdown 标记或额外解释：
        {{
            "found": true,
            "x": 123,
            "y": 456,
            "reason": "简短描述你找到了什么，例如 'Found patient list, row 1'"
        }}

        如果画面中完全找不到目标元素，返回：
        {{
            "found": false,
            "reason": "未找到目标元素的描述"
        }}
        """

        user_message = f"请在截图中找到以下目标：{prompt_instruction}。请给出点击该位置的精确坐标(x, y)。"

        try:
            start_time = time.time()
            if DEBUG_MODE:
                console.print(f"[dim]正在请求 {self.model} 进行视觉定位...[/dim]")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": user_message
                            }
                        ]
                    }
                ]
            )

            duration = time.time() - start_time
            content = response.content[0].text.strip()

            # 清理可能的 Markdown 标记
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            result = json.loads(content)

            if DEBUG_MODE:
                console.print(f"[dim]AI 响应 ({duration:.2f}s): {result}[/dim]")

            return result

        except Exception as e:
            console.print(f"[bold red]AI 定位请求失败: {e}[/bold red]")
            if DEBUG_MODE:
                import traceback
                console.print(traceback.format_exc())
            return None

    def locate_emr_patient_row(self, screenshot_path: str) -> Optional[Tuple[int, int]]:
        """
        专门用于定位 EMR 病人列表第一行的辅助函数
        """
        instruction = "EMR/EHR 系统中的病人列表区域。请找到列表中的'第一位病人'（通常在表头下方的第一行），并给出该行的中心位置以便点击进入详情页。"

        result = self.locate_target(screenshot_path, instruction)

        if result and result.get("found"):
            return (result["x"], result["y"])
        return None
