"""
core/ai_locator.py
AI Vision Core - Table Grid Analysis & Visual Debugging
"""
import os
import base64
import json
import time
from typing import Dict, Optional, Tuple, List
import pyautogui
from anthropic import Anthropic
from rich.console import Console
from PIL import Image, ImageDraw

# 引用配置
from .config import DEBUG_MODE, SCREENSHOT_OUTPUT_DIR

console = Console()


class AINavigator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            console.print("[yellow]⚠️  未配置 ANTHROPIC_API_KEY，AI 功能将不可用[/yellow]")

        self.client = Anthropic(api_key=self.api_key) if self.api_key else None
        self.model = os.getenv("AI_MODEL_NAME", "claude-3-5-sonnet-20241022")
        self.screen_w, self.screen_h = pyautogui.size()

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _debug_draw_points(self, image_path: str, coords: List[Dict], tag: str = "debug"):
        """
        [调试神器] 在截图上画出 AI 识别到的点，保存到 tmp/screenshots/
        """
        if not DEBUG_MODE:
            return

        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)

            # 画点和文字
            for idx, item in enumerate(coords):
                x = item['x']
                y = item['y']
                name = item.get('name', 'Unknown')

                # 画一个红圈
                r = 10
                draw.ellipse((x-r, y-r, x+r, y+r), outline="red", width=3)
                # 写上序号和名字
                draw.text((x+15, y), f"#{idx+1}: {name}", fill="red")

            # 确保目录存在
            save_path = SCREENSHOT_OUTPUT_DIR / f"ai_vision_{tag}_{int(time.time())}.png"
            img.save(save_path)
            console.print(f"[yellow]🔍 [Debug] 视觉识别结果已保存: {save_path}[/yellow]")
            console.print("[dim]请打开该图片检查 AI 定位是否准确[/dim]")
        except Exception as e:
            console.print(f"[red]画图失败: {e}[/red]")

    def _call_claude_json(self, image_path: str, prompt: str) -> Optional[Dict]:
        """发送请求并获取 JSON"""
        if not self.client:
            console.print("[red]❌ AI 客户端未初始化[/red]")
            return None

        b64_data = self._encode_image(image_path)
        try:
            if DEBUG_MODE:
                console.print(f"[dim]正在请求 AI 分析 ({self.model})...[/dim]")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system="You are a UI Automation Agent. Output strictly in JSON format. No markdown.",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64_data}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            content = response.content[0].text.strip()
            # 兼容 Markdown 代码块
            if "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            return json.loads(content)
        except Exception as e:
            console.print(f"[red]AI Request Error: {e}[/red]")
            return None

    def locate_all_visible_patients(self, screenshot_path: str) -> List[Dict]:
        """
        [精准批量识别]
        返回列表: [{'name': 'Diana', 'x': 100, 'y': 200}, ...]
        """
        # 使用"表格列对齐"的强提示词
        prompt = f"""
        Analyze this EMR Patient List screenshot (Resolution: {self.screen_w}x{self.screen_h}).

        Your Goal: Identify **ALL patient rows** in the main table.

        **Visual Reasoning Steps (CoT):**
        1.  **Find Header**: Locate the table header row containing "Name", "DOB", "Gender".
        2.  **Column Alignment**: Identify the "Name" column. Patient names are vertically aligned under the "Name" header.
        3.  **Row Scanning**: Scan downwards from the header. Extract every visible patient name in that column.
        4.  **Ignore**: Ignore the header itself. Ignore buttons like "+ New patient".
        5.  **Coordinates**: Return the **Center (x,y)** of each name text as **Relative Percentages (0.0-1.0)**.

        **Output JSON Format:**
        {{
            "patients": [
                {{ "name": "Diana Rossi", "x_percent": 0.12, "y_percent": 0.25 }},
                {{ "name": "Elena Martinez", "x_percent": 0.12, "y_percent": 0.35 }},
                ...
            ]
        }}
        """

        data = self._call_claude_json(screenshot_path, prompt)

        results = []
        if data and "patients" in data:
            for p in data["patients"]:
                # 将相对坐标转为绝对坐标
                abs_x = int(p["x_percent"] * self.screen_w)
                abs_y = int(p["y_percent"] * self.screen_h)

                results.append({
                    "name": p.get("name", "Unknown"),
                    "x": abs_x,
                    "y": abs_y
                })

        # [Debug] 画出来看看准不准
        if results:
            self._debug_draw_points(screenshot_path, results, tag="patients")

        return results

    def locate_patient_row_universal(self, screenshot_path: str) -> Optional[Tuple[int, int]]:
        """
        [Single Mode] Locate the FIRST patient row using CoT.
        """
        prompt = f"""
        Analyze this EMR screenshot (Resolution: {self.screen_w}x{self.screen_h}).
        Find the **First Patient Row** in the main data table.

        **Steps:**
        1. Identify the main table headers (e.g., "Name", "DOB", "Gender").
        2. Locate the **first data row** directly below the headers.
        3. Identify the patient's name text (usually blue/clickable) in that row.
        4. Calculate the center coordinates of this name text as **relative percentages (0.0-1.0)**.

        **Output JSON:**
        {{
            "found": true,
            "x_percent": 0.15,
            "y_percent": 0.25,
            "reason": "Found 'Diana Rossi' in the first row."
        }}
        """
        data = self._call_claude_json(screenshot_path, prompt)
        if data and data.get("found"):
            return int(data["x_percent"] * self.screen_w), int(data["y_percent"] * self.screen_h)
        return None

    def extract_patient_details(self, screenshot_path: str) -> Optional[Dict]:
        """
        [Data Extraction] Extract structured patient info from detail page.
        """
        prompt = """
        Extract patient details from this profile page.
        Required Fields: first_name, last_name, gender (MALE/FEMALE/OTHER), birth_date (YYYY-MM-DD), ehr_patient_id.
        Output JSON only.
        """
        return self._call_claude_json(screenshot_path, prompt)

    def find_tab_or_button(self, screenshot_path: str, target_name: str) -> Optional[Tuple[int, int]]:
        """
        [Deep Dive] Find specific UI elements like 'History' tabs.
        """
        prompt = f"""
        Find the clickable button, tab, or link labeled **"{target_name}"**.
        It might be in a sidebar, top menu, or card header.

        Return relative coordinates (0.0-1.0).
        JSON: {{ "found": true, "x_percent": ..., "y_percent": ... }}
        """
        data = self._call_claude_json(screenshot_path, prompt)
        if data and data.get("found"):
            return int(data["x_percent"] * self.screen_w), int(data["y_percent"] * self.screen_h)
        return None

    def extract_free_text(self, screenshot_path: str) -> str:
        """
        [Deep Dive] Extract raw text context from a history/document page.
        """
        if not self.client:
            console.print("[red]❌ AI 客户端未初始化[/red]")
            return ""

        b64 = self._encode_image(screenshot_path)
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                        {"type": "text", "text": "OCR this image. Extract all clinical notes, history, or medical text visible. Output text only."}
                    ]
                }]
            )
            return resp.content[0].text
        except Exception as e:
            console.print(f"[red]AI Error: {e}[/red]")
            return ""

    # ==========================================
    # Legacy methods for backwards compatibility
    # ==========================================

    def locate_with_layout_analysis(self, screenshot_path: str, user_target_desc: str) -> Optional[Tuple[int, int]]:
        """
        [高级定位] 引入思维链 (CoT) 的视觉定位 - 兼容旧接口
        """
        return self.locate_patient_row_universal(screenshot_path)

    def extract_page_data(self, screenshot_path: str, context_data: Optional[Dict] = None) -> Dict:
        """
        [Step 3] 智能提取接口 - 兼容旧接口
        """
        data = self.extract_patient_details(screenshot_path)
        if data:
            return {
                "patient_info": data,
                "is_complete": True,
                "next_action": {"type": "finish", "reason": "Data extracted successfully"}
            }
        return {
            "patient_info": {},
            "is_complete": True,
            "next_action": {"type": "finish", "reason": "Extraction failed"}
        }
