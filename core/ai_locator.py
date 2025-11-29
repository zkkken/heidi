"""
core/ai_locator.py
AI Vision Core v3.0 - Auto-Scale, Crop & Refine, Batch Extraction
"""
import os
import base64
import json
import time
import re
import io
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
        # 逻辑分辨率 (用于鼠标点击)
        self.screen_w, self.screen_h = pyautogui.size()

    def _get_pixel_scale(self, image: Image.Image) -> float:
        """
        计算物理像素与逻辑像素的比例 (解决 Retina 屏点击不准的核心)
        例如：截图宽 3024，屏幕宽 1512 -> 比例 2.0
        """
        img_w, _ = image.size
        scale = img_w / self.screen_w
        return scale

    def _encode_pil_image(self, image: Image.Image) -> str:
        """将 PIL Image 编码为 base64"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _debug_draw_points(self, image_path: str, coords: List[Dict], tag: str = "debug"):
        """在截图上画出识别点，用于调试"""
        if not DEBUG_MODE: return
        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            for idx, item in enumerate(coords):
                x, y = item['x'], item['y']
                name = item.get('name', 'Unknown')
                r = 10
                draw.ellipse((x-r, y-r, x+r, y+r), outline="red", width=3)
                draw.text((x+15, y), f"#{idx+1}: {name}", fill="red")
            
            save_path = SCREENSHOT_OUTPUT_DIR / f"ai_vision_{tag}_{int(time.time())}.png"
            img.save(save_path)
            console.print(f"[yellow]🔍 [Debug] 视觉标记已保存: {save_path}[/yellow]")
        except Exception as e:
            console.print(f"[red]画图失败: {e}[/red]")

    def _extract_json_from_text(self, text: str) -> Optional[Dict]:
        """
        鲁棒的 JSON 提取器，解决 'Extra data' 问题
        """
        text = text.strip()
        try:
            # 1. 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        try:
            # 2. 提取第一个 { ... } 代码块
            match = re.search(r'(\{.*?\})', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 3. 提取 ```json ... ``` 包裹的内容
            match = re.search(r'```json(.*?)```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1).strip())
        except Exception as e:
            console.print(f"[red]JSON 解析失败: {e}[/red]")
            console.print(f"[dim]原始内容: {text[:100]}...[/dim]")
        return None

    def _call_claude_json(self, image_path: str, prompt: str) -> Optional[Dict]:
        """发送请求并获取 JSON"""
        b64_data = self._encode_image(image_path)
        try:
            if DEBUG_MODE:
                console.print(f"[dim]AI 请求中 ({self.model})...[/dim]")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system="You are a UI Automation Agent. Return ONLY valid JSON. Do not write explanations.",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64_data}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            return self._extract_json_from_text(response.content[0].text)
        except Exception as e:
            console.print(f"[red]AI Request Error: {e}[/red]")
            return None

    def locate_all_visible_patients(self, screenshot_path: str) -> List[Dict]:
        """
        [精准批量识别 - CareFlow 优化版]
        """
        prompt = f"""
        Analyze this **CareFlow EMR** screenshot (Resolution: {self.screen_w}x{self.screen_h}).
        
        **Objective**: Identify all patient rows in the MAIN TABLE.

        **Critical Layout Analysis**:
        1.  **IGNORE the Left Sidebar**: Do NOT select "All Patients" or "Active Patients" in the dark/gray sidebar on the left.
        2.  **Focus on Main Content**: Look for the large white table area on the right.
        3.  **Find the Header**: Locate the row with "Name", "Date of birth", "Gender".
        4.  **Align with "Name"**: The targets are the **Blue Clickable Names** strictly vertically aligned under the "Name" header.

        **Task**:
        - Scan the table from top to bottom.
        - For each row, extract the Patient Name.
        - Return the **Center (x,y)** of the name text as **Relative Percentages (0.0-1.0)**.

        **Output JSON**:
        {{
            "patients": [
                {{ "name": "Diana Rossi", "x_percent": 0.25, "y_percent": 0.35 }},
                ...
            ]
        }}
        """
        
        data = self._call_claude_json(screenshot_path, prompt)
        
        results = []
        if data and "patients" in data:
            for p in data["patients"]:
                results.append({
                    "name": p.get("name", "Unknown"),
                    "x": int(p["x_percent"] * self.screen_w),
                    "y": int(p["y_percent"] * self.screen_h)
                })
        
        # 调试画图
        if results:
            self._debug_draw_points(screenshot_path, results, tag="patients_fix")
            
        return results

    def extract_patient_details(self, screenshot_path: str) -> Optional[Dict]:
        """提取详情页数据"""
        prompt = """
        Extract patient details from this profile page.
        Required Fields: first_name, last_name, gender (MALE/FEMALE/OTHER), birth_date (YYYY-MM-DD), ehr_patient_id.
        
        Return JSON object only. No markdown formatting.
        Example: {"first_name": "John", ...}
        """
        return self._call_claude_json(screenshot_path, prompt)

    # --- 兼容旧接口 ---
    def find_tab_or_button(self, screenshot_path: str, target_name: str) -> Optional[Tuple[int, int]]:
        prompt = f"Find the button or tab labeled '{target_name}'. Return JSON: {{'found': true, 'x_percent': 0.5, 'y_percent': 0.5}}"
        data = self._call_claude_json(screenshot_path, prompt)
        if data and data.get("found"):
            return int(data["x_percent"] * self.screen_w), int(data["y_percent"] * self.screen_h)
        return None

    def extract_free_text(self, screenshot_path: str) -> str:
        # 这个方法返回纯文本，不需要 JSON 解析
        b64 = self._encode_image(screenshot_path)
        try:
            resp = self.client.messages.create(
                model=self.model, max_tokens=2048,
                messages=[{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}, {"type": "text", "text": "OCR this text."}]}]
            )
            return resp.content[0].text
        except:
            return ""

    # =========================================================
    # v3.0 新功能: 批量建档 & 二次截图精准定位
    # =========================================================

    def _call_claude(self, b64_image: str, prompt: str) -> Optional[Dict]:
        """发送 base64 图片并获取 JSON 响应"""
        if not self.client:
            console.print("[red]❌ AI 客户端未初始化[/red]")
            return None

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system="Output strictly valid JSON only. No text explanations.",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64_image}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            return self._extract_json_from_text(response.content[0].text)
        except Exception as e:
            console.print(f"[red]AI Error: {e}[/red]")
            return None

    def extract_patient_list_data(self, screenshot_path: str) -> List[Dict]:
        """
        [批量建档模式] 直接从列表页 OCR 提取所有病人的结构化数据
        不再返回坐标，而是返回 {first_name, last_name, dob, gender...}
        """
        img = Image.open(screenshot_path)
        b64 = self._encode_pil_image(img)

        prompt = """
        Analyze this EMR patient list table.
        Extract data for **EVERY** visible patient row into a structured JSON list.

        **Columns to Map:**
        - Name -> split into `first_name`, `last_name`
        - Date of birth -> `birth_date` (Format: YYYY-MM-DD)
        - Gender -> `gender` (MALE/FEMALE)
        - Email/Phone -> put in `additional_context` string
        - Patient ID -> if hidden, leave null.

        **Output Format:**
        {
            "patients": [
                {
                    "first_name": "Diana",
                    "last_name": "Rossi",
                    "birth_date": "1998-04-03",
                    "gender": "FEMALE",
                    "additional_context": "Phone: (415)... Email: ..."
                },
                ...
            ]
        }
        """

        console.print("[cyan]🔍 AI 正在读取列表数据...[/cyan]")
        data = self._call_claude(b64, prompt)

        if data and "patients" in data:
            return data["patients"]
        return []

    def locate_patient_precise(self, screenshot_path: str, target_desc: str = "first patient row") -> Optional[Tuple[int, int]]:
        """
        [精准点击模式] 二次截图技术
        Step 1: 找大区域 (Table)
        Step 2: 裁剪
        Step 3: 找精确点
        """
        img = Image.open(screenshot_path)
        scale = self._get_pixel_scale(img)  # 计算缩放比例

        # --- Step 1: 粗定位区域 ---
        console.print("[dim]Phase 1: 识别表格区域...[/dim]")
        global_prompt = """
        Identify the bounding box of the **Main Patient Data Table** (excluding the left sidebar and top navigation).
        Focus on the area containing the list of names.

        Return JSON: { "bbox": [ymin, xmin, ymax, xmax] }  (0.0-1.0 relative coords)
        """
        b64_global = self._encode_pil_image(img)
        res_global = self._call_claude(b64_global, global_prompt)

        if not res_global or "bbox" not in res_global:
            console.print("[red]❌ 无法识别表格区域[/red]")
            return None

        # 计算裁剪坐标 (物理像素)
        ymin, xmin, ymax, xmax = res_global["bbox"]
        width, height = img.size

        crop_box = (
            int(xmin * width),
            int(ymin * height),
            int(xmax * width),
            int(ymax * height)
        )

        # --- Step 2: 裁剪 ---
        cropped_img = img.crop(crop_box)
        # 调试：保存裁剪图
        if DEBUG_MODE:
            crop_path = SCREENSHOT_OUTPUT_DIR / "debug_crop.png"
            cropped_img.save(crop_path)
            console.print(f"[dim]裁剪区域已保存: {crop_path}[/dim]")

        # --- Step 3: 精定位 ---
        console.print(f"[dim]Phase 2: 在局部区域精确查找 '{target_desc}'...[/dim]")
        local_prompt = f"""
        This is a cropped view of the patient list.
        Locate the **{target_desc}** (e.g. the Name text itself).

        Return the center coordinates relative to THIS cropped image (0.0-1.0).
        JSON: {{ "found": true, "x": 0.5, "y": 0.1 }}
        """
        b64_local = self._encode_pil_image(cropped_img)
        res_local = self._call_claude(b64_local, local_prompt)

        if res_local and res_local.get("found"):
            # 坐标还原逻辑
            # 1. 小图相对 -> 小图绝对
            local_x = res_local["x"] * (crop_box[2] - crop_box[0])
            local_y = res_local["y"] * (crop_box[3] - crop_box[1])

            # 2. 小图绝对 -> 大图绝对 (物理像素)
            global_x_px = crop_box[0] + local_x
            global_y_px = crop_box[1] + local_y

            # 3. 物理像素 -> 逻辑像素 (除以 scale)
            final_x = int(global_x_px / scale)
            final_y = int(global_y_px / scale)

            console.print(f"[green]🎯 坐标校准: 物理({int(global_x_px)},{int(global_y_px)}) -> 逻辑({final_x},{final_y}) (Scale: {scale:.1f})[/green]")
            return final_x, final_y

        console.print("[red]❌ 精确定位失败[/red]")
        return None

    # =========================================================
    # 兼容旧接口
    # =========================================================

    def locate_with_layout_analysis(self, screenshot_path: str, user_target_desc: str) -> Optional[Tuple[int, int]]:
        """兼容旧接口 - 使用精准定位"""
        return self.locate_patient_precise(screenshot_path, user_target_desc)

    def extract_page_data(self, screenshot_path: str, context_data: Optional[Dict] = None) -> Dict:
        """兼容旧接口"""
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

    def locate_patient_row_universal(self, screenshot_path: str) -> Optional[Tuple[int, int]]:
        """兼容旧接口 - 使用精准定位"""
        return self.locate_patient_precise(screenshot_path, "First patient Name text")

    def extract_profile_details(self, screenshot_path: str) -> Optional[Dict]:
        """从详情页提取完整病人信息"""
        img = Image.open(screenshot_path)
        prompt = """
        Extract full patient details from this profile page.
        Include: first_name, last_name, birth_date (YYYY-MM-DD), gender (MALE/FEMALE/OTHER),
        ehr_patient_id, and any additional information like history, notes, phone, email.

        Return JSON: {
            "first_name": "...",
            "last_name": "...",
            "birth_date": "YYYY-MM-DD",
            "gender": "MALE/FEMALE/OTHER",
            "ehr_patient_id": "...",
            "additional_context": "any extra info..."
        }
        """
        return self._call_claude(self._encode_pil_image(img), prompt)