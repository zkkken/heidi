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
        [Step 2] 视觉定位：找到列表中的第一个病人
        """
        base64_image = self._encode_image(screenshot_path)

        system_prompt = f"""
        你是一个 GUI 自动化助手。当前屏幕分辨率为 {self.screen_width}x{self.screen_height}。
        你的任务是分析 EMR (电子病历) 系统的病人列表界面。

        请找到列表内容区域的"第一行"或"第一位病人"的位置。
        注意：请忽略表头（Header），只关注数据行。

        请返回点击该行的中心坐标 (x, y)，格式为纯 JSON：
        {{ "found": true, "x": 123, "y": 456 }}
        如果没找到，返回 {{ "found": false }}。
        """

        try:
            if DEBUG_MODE:
                console.print(f"[dim]AI 定位请求中 ({self.model})...[/dim]")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64_image}},
                        {"type": "text", "text": "请找到第一个病人的点击位置。"}
                    ]
                }]
            )

            content = response.content[0].text.strip()

            # 清理 JSON 标记
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]

            result = json.loads(content)

            if result.get("found"):
                return (result.get("x"), result.get("y"))
            return None

        except Exception as e:
            console.print(f"[red]AI 定位失败: {e}[/red]")
            if DEBUG_MODE:
                import traceback
                console.print(traceback.format_exc())
            return None

    def extract_page_data(self, screenshot_path: str, context_data: Optional[Dict] = None) -> Dict:
        """
        [Step 3] 智能提取接口 (保留了循环的口子)

        参数:
            screenshot_path: 当前截图
            context_data: (可选) 上一轮循环已获取的数据，用于告诉 AI 缺什么

        返回:
            JSON Dict: {
                "patient_info": { ...提取到的字段... },
                "is_complete": bool,  <-- 循环控制开关
                "next_action": {      <-- 循环操作指令
                    "type": "finish" | "click" | "scroll",
                    "reason": "需要点击 History 标签",
                    "x": 100, "y": 200
                }
            }
        """
        base64_image = self._encode_image(screenshot_path)
        context_str = json.dumps(context_data, ensure_ascii=False) if context_data else "None"

        system_prompt = """
        你是一个医疗数据录入专家。任务是从当前屏幕提取病人信息。

        【提取规则】
        尽可能提取以下字段：first_name, last_name, gender, birth_date (YYYY-MM-DD), ehr_patient_id。

        【循环控制规则】
        你需要判断当前信息是否完整，或者页面是否有更多内容（例如需要滚动或切换标签页）。

        请严格输出以下 JSON 格式：
        {
            "patient_info": {
                "first_name": "...",
                "last_name": "...",
                "gender": "...",
                "birth_date": "...",
                "ehr_patient_id": "..."
            },
            "is_complete": true,  // 如果关键信息已全，设为 true
            "next_action": {
                "type": "finish", // 如果已完成，设为 "finish"。如果需要操作，设为 "click" 或 "scroll"
                "reason": "Data extracted successfully"
            }
        }
        """

        try:
            if DEBUG_MODE:
                console.print(f"[dim]AI 提取请求中... (上下文: {bool(context_data)})[/dim]")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64_image}},
                        {"type": "text", "text": f"当前已知信息: {context_str}。请提取当前页面信息并判断下一步。"}
                    ]
                }]
            )

            content = response.content[0].text.strip()

            # JSON 清理逻辑
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]

            result = json.loads(content)

            if DEBUG_MODE:
                console.print(f"[dim]AI 提取结果: {result.get('patient_info', {})}[/dim]")

            return result

        except Exception as e:
            console.print(f"[red]AI 提取失败: {e}[/red]")
            if DEBUG_MODE:
                import traceback
                console.print(traceback.format_exc())
            return {
                "patient_info": {},
                "is_complete": True,
                "next_action": {"type": "finish", "reason": "提取失败"}
            }
