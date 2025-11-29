"""
RPA 自动化模块 - 端到端自动化流程
自动打开应用 → 识别窗口 → 点击操作 → 截图 → 数据传输
"""

import time
import subprocess
import pyautogui
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re

from .config import DEBUG_MODE, HEIDI_WEB_URL
from .capture import capture_full_screen
from .ocr_parser import run_ocr
from .smart_capture import smart_capture_and_extract
from .ai_locator import AINavigator


class WindowDetector:
    """窗口检测器 - 识别桌面上的应用窗口"""

    @staticmethod
    def find_window_by_title(title_pattern: str) -> Optional[Dict]:
        """
        通过窗口标题查找窗口

        参数:
            title_pattern: 窗口标题关键词或正则表达式

        返回:
            Dict: {
                "title": str,
                "position": (x, y),
                "size": (width, height)
            } 或 None
        """
        try:
            # macOS: 使用 AppleScript 获取窗口信息
            script = f'''
            tell application "System Events"
                set windowList to {{}}
                repeat with proc in (every process whose visible is true)
                    try
                        repeat with win in (every window of proc)
                            set windowInfo to {{name of proc, name of win, position of win, size of win}}
                            set end of windowList to windowInfo
                        end repeat
                    end try
                end repeat
                return windowList
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # 解析 AppleScript 返回的窗口列表
                output = result.stdout.strip()

                if DEBUG_MODE:
                    print(f"窗口搜索原始结果: {output}")

                if not output:
                    return None

                # AppleScript 返回格式: "App Name, Window Title, {x, y}, {width, height}, App2, Win2, {x2, y2}, {w2, h2}, ..."
                # 尝试解析窗口列表
                try:
                    # 使用正则表达式提取窗口信息
                    # 匹配模式: "应用名, 窗口标题, {x, y}, {width, height}"
                    import re

                    # 分割成独立的窗口条目（每4个元素为一组）
                    # AppleScript 返回的是逗号分隔的列表
                    parts = output.split(',')

                    # 每4个元素构成一个窗口信息：app_name, window_title, position, size
                    i = 0
                    while i + 3 < len(parts):
                        app_name = parts[i].strip()
                        window_title = parts[i + 1].strip()
                        position_str = parts[i + 2].strip()
                        size_str = parts[i + 3].strip()

                        if DEBUG_MODE:
                            print(f"解析窗口: {app_name} / {window_title}")

                        # 检查是否匹配 title_pattern
                        if (title_pattern.lower() in app_name.lower() or
                            title_pattern.lower() in window_title.lower()):

                            # 解析位置 "{x, y}"
                            pos_match = re.search(r'\{?\s*(-?\d+)\s*,\s*(-?\d+)\s*\}?', position_str)
                            # 解析尺寸 "{width, height}"
                            size_match = re.search(r'\{?\s*(\d+)\s*,\s*(\d+)\s*\}?', size_str)

                            if pos_match and size_match:
                                x, y = int(pos_match.group(1)), int(pos_match.group(2))
                                width, height = int(size_match.group(1)), int(size_match.group(2))

                                if DEBUG_MODE:
                                    print(f"✅ 找到匹配窗口: {window_title}")
                                    print(f"   位置: ({x}, {y}), 尺寸: {width}x{height}")

                                return {
                                    "title": window_title,
                                    "app_name": app_name,
                                    "position": (x, y),
                                    "size": (width, height)
                                }

                        i += 4

                    # 没有找到匹配的窗口
                    if DEBUG_MODE:
                        print(f"未找到包含关键词 '{title_pattern}' 的窗口")
                    return None

                except Exception as parse_error:
                    if DEBUG_MODE:
                        print(f"窗口信息解析失败: {parse_error}")
                        import traceback
                        traceback.print_exc()
                    return None

        except Exception as e:
            if DEBUG_MODE:
                print(f"窗口检测失败: {e}")
            return None

    @staticmethod
    def detect_emr_window() -> Optional[Dict]:
        """
        自动检测 EMR 窗口

        尝试查找包含以下关键词的窗口：
        - EMR, HIS, 电子病历, Electronic Medical Record
        - Epic, Cerner, 等常见 EMR 系统名称
        """
        keywords = [
            "EMR", "HIS", "电子病历", "病历系统",
            "Electronic Medical", "Epic", "Cerner",
            "患者", "Patient"
        ]

        for keyword in keywords:
            window = WindowDetector.find_window_by_title(keyword)
            if window:
                if DEBUG_MODE:
                    print(f"找到 EMR 窗口: {keyword}")
                return window

        return None


class MouseController:
    """鼠标控制器 - 自动化鼠标操作"""

    @staticmethod
    def move_to_window(window_info: Dict):
        """将鼠标移动到窗口中心"""
        x, y = window_info["position"]
        width, height = window_info["size"]
        center_x = x + width // 2
        center_y = y + height // 2

        pyautogui.moveTo(center_x, center_y, duration=0.5)

        if DEBUG_MODE:
            print(f"鼠标移动到窗口中心: ({center_x}, {center_y})")

    @staticmethod
    def find_and_click_patient(search_region: Optional[Tuple] = None) -> bool:
        """
        在指定区域查找并点击第一个病人（使用OCR位置信息）

        参数:
            search_region: 搜索区域 (left, top, width, height)

        返回:
            bool: 是否成功找到并点击
        """
        from paddleocr import PaddleOCR
        from core.config import OCR_LANGUAGE, OCR_USE_ANGLE_CLS

        # 截图当前屏幕
        screenshot_path = capture_full_screen()

        if DEBUG_MODE:
            print(f"使用截图: {screenshot_path}")

        try:
            # 初始化 OCR（带位置信息）
            if DEBUG_MODE:
                print("正在初始化 PaddleOCR 引擎...")

            ocr = PaddleOCR(use_angle_cls=OCR_USE_ANGLE_CLS, lang=OCR_LANGUAGE)

            if DEBUG_MODE:
                print("正在执行 OCR 识别...")

            result = ocr.ocr(screenshot_path, cls=OCR_USE_ANGLE_CLS)

            if DEBUG_MODE:
                print("OCR 识别完成")

            if not result or not result[0]:
                if DEBUG_MODE:
                    print("OCR 未识别到任何文字")
                return False

            # 查找病人名字相关的关键词（带位置信息）
            patient_patterns = [
                r"([\u4e00-\u9fff]{2,4})\s*[男女]",  # 中文姓名 + 性别
                r"姓名[:：]\s*([\u4e00-\u9fff]{2,4})",  # 姓名: XXX
                r"患者[:：]\s*([\u4e00-\u9fff]{2,4})",  # 患者: XXX
                r"([\u4e00-\u9fff]{2,4})\s+\d{1,3}岁",  # 姓名 + 年龄
                r"([\u4e00-\u9fff]{2,4})\s+[0-9]{4}-[0-9]{2}-[0-9]{2}",  # 姓名 + 日期
                r"([A-Z][a-z]+\s+[A-Z][a-z]+)",  # 英文姓名 (First Last)
                r"([A-Z][a-z]+,\s*[A-Z][a-z]+)",  # 英文姓名 (Last, First)
            ]

            # 收集所有OCR结果
            ocr_results = []
            for line in result[0]:
                if line and len(line) >= 2:
                    try:
                        # line格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]], (text, confidence)
                        box = line[0]  # 四个角的坐标
                        text_info = line[1]

                        # 确保 text_info 是元组或列表且有足够的元素
                        if isinstance(text_info, (tuple, list)) and len(text_info) >= 2:
                            text = text_info[0]  # 识别的文本
                            confidence = text_info[1]  # 置信度
                        else:
                            if DEBUG_MODE:
                                print(f"跳过格式异常的OCR结果: {line}")
                            continue

                        # 计算文本中心点
                        x_coords = [pt[0] for pt in box]
                        y_coords = [pt[1] for pt in box]
                        center_x = sum(x_coords) / len(x_coords)
                        center_y = sum(y_coords) / len(y_coords)

                        ocr_results.append({
                            'text': text,
                            'confidence': confidence,
                            'center': (int(center_x), int(center_y)),
                            'box': box
                        })
                    except (IndexError, TypeError, ValueError) as e:
                        if DEBUG_MODE:
                            print(f"解析OCR结果时出错: {e}, line: {line}")
                        continue

            if DEBUG_MODE:
                print(f"OCR识别到 {len(ocr_results)} 个文本块")
                for item in ocr_results[:5]:  # 显示前5个
                    print(f"  - {item['text']} at {item['center']}")

            # 查找所有匹配病人姓名的文本块
            matched_patients = []
            for item in ocr_results:
                text = item['text']
                for pattern in patient_patterns:
                    match = re.search(pattern, text)
                    if match:
                        patient_name = match.group(1) if match.lastindex >= 1 else text
                        matched_patients.append({
                            'name': patient_name,
                            'text': text,
                            'center': item['center'],
                            'confidence': item['confidence']
                        })
                        break  # 找到匹配就跳出内层循环

            if not matched_patients:
                if DEBUG_MODE:
                    print("未找到匹配的病人信息")
                return False

            # 按 Y 坐标排序，找到最上方的病人（通常是列表第一个）
            matched_patients.sort(key=lambda p: p['center'][1])

            # 点击第一个病人
            first_patient = matched_patients[0]
            click_x, click_y = first_patient['center']

            if DEBUG_MODE:
                print(f"找到 {len(matched_patients)} 个病人，选择最上方的:")
                print(f"  姓名: {first_patient['name']}")
                print(f"  文本: {first_patient['text']}")
                print(f"  点击坐标: ({click_x}, {click_y})")
                print(f"  置信度: {first_patient['confidence']:.2f}")

            # 使用OCR识别的位置进行精确点击
            pyautogui.click(click_x, click_y)
            time.sleep(1.5)  # 等待页面加载

            return True

        except Exception as e:
            if DEBUG_MODE:
                print(f"查找并点击病人失败: {e}")
                import traceback
                traceback.print_exc()
            return False

    @staticmethod
    def smart_click_patient() -> bool:
        """
        智能查找并点击病人（基于屏幕截图和 OCR）

        返回:
            bool: 是否成功
        """
        # 方法 1: 尝试查找"病人列表"区域的第一条记录
        # 方法 2: 查找包含姓名、性别、年龄等信息的区域
        # 方法 3: 使用计算机视觉找到类似"行"的区域并点击第一行

        return MouseController.find_and_click_patient()


class BrowserAutomation:
    """浏览器自动化 - 控制 Heidi 浏览器"""

    @staticmethod
    def open_heidi_browser(url: str = "https://www.heidihealth.com") -> bool:
        """
        打开 Heidi 浏览器

        参数:
            url: Heidi 网址

        返回:
            bool: 是否成功打开
        """
        try:
            if DEBUG_MODE:
                print(f"正在打开浏览器: {url}")

            # macOS: 使用 open 命令打开浏览器
            result = subprocess.run(['open', url], check=True, capture_output=True, text=True)

            if DEBUG_MODE:
                print("浏览器命令已执行，等待启动...")

            time.sleep(3)  # 等待浏览器启动

            if DEBUG_MODE:
                print("✅ 浏览器已打开")

            return True
        except subprocess.CalledProcessError as e:
            if DEBUG_MODE:
                print(f"打开浏览器失败 (命令错误): {e}")
                if e.stderr:
                    print(f"错误输出: {e.stderr}")
            return False
        except Exception as e:
            if DEBUG_MODE:
                print(f"打开浏览器失败: {e}")
                import traceback
                traceback.print_exc()
            return False

    @staticmethod
    def input_to_heidi(patient_data: Dict) -> bool:
        """
        将病人数据输入到 Heidi 界面

        参数:
            patient_data: 病人信息字典

        返回:
            bool: 是否成功
        """
        try:
            # 方法 1: 使用 API（已经实现）
            # 方法 2: 使用浏览器自动化（selenium/playwright）

            # 简化实现：通过键盘输入（需要先定位到输入框）
            # 这里假设已经切换到 Heidi 浏览器窗口

            # 拼接文本
            text_to_input = f"""
姓名: {patient_data.get('last_name', '')}{patient_data.get('first_name', '')}
性别: {patient_data.get('gender', '')}
出生日期: {patient_data.get('birth_date', '')}
病历号: {patient_data.get('ehr_patient_id', '')}
"""

            # 复制到剪贴板
            try:
                import pyperclip
                pyperclip.copy(text_to_input.strip())

                if DEBUG_MODE:
                    print(f"已复制到剪贴板:\n{text_to_input}")

            except ImportError:
                if DEBUG_MODE:
                    print("警告: pyperclip 未安装，无法复制到剪贴板")
                    print("请运行: pip install pyperclip")
                print(f"病人数据:\n{text_to_input}")
                return False

            # 提示用户手动粘贴（或使用 Cmd+V 自动粘贴）
            # pyautogui.hotkey('command', 'v')  # macOS

            return True

        except Exception as e:
            if DEBUG_MODE:
                print(f"输入到 Heidi 失败: {e}")
            return False


class RPAWorkflow:
    """RPA 工作流程编排"""

    def __init__(self, emr_app_path: Optional[str] = None, heidi_url: Optional[str] = None):
        """
        初始化 RPA 工作流

        参数:
            emr_app_path: EMR 应用程序路径（如果需要自动启动）
            heidi_url: Heidi 网址（默认使用配置文件中的 HEIDI_WEB_URL）
        """
        self.emr_app_path = emr_app_path
        self.heidi_url = heidi_url or HEIDI_WEB_URL

        # [配置] 控制是否开启循环。设为 1 即为单次提取模式（最快）
        self.max_extraction_loops = 1

    def step1_launch_applications(self) -> bool:
        """
        步骤 1: 启动 EMR 和 Heidi 浏览器

        返回:
            bool: 是否成功
        """
        from rich.console import Console
        console = Console()

        console.print("\n[bold cyan]📱 步骤 1: 启动应用[/bold cyan]")

        # 启动 EMR（如果提供了路径）
        if self.emr_app_path and Path(self.emr_app_path).exists():
            try:
                subprocess.Popen([self.emr_app_path])
                console.print(f"[green]✅ 已启动 EMR: {self.emr_app_path}[/green]")
                time.sleep(3)
            except Exception as e:
                console.print(f"[yellow]⚠️  无法自动启动 EMR: {e}[/yellow]")
                console.print("[yellow]   请手动打开 EMR 应用[/yellow]")
        else:
            console.print("[yellow]⚠️  未配置 EMR 路径，请手动打开 EMR 应用[/yellow]")

        # 打开 Heidi 浏览器
        console.print(f"\n[cyan]正在打开 Heidi 浏览器: {self.heidi_url}[/cyan]")
        if BrowserAutomation.open_heidi_browser(self.heidi_url):
            console.print("[green]✅ Heidi 浏览器已打开[/green]")
        else:
            console.print("[red]❌ 无法打开 Heidi 浏览器[/red]")
            return False

        # 等待用户确认应用已启动
        console.print("\n[yellow]请确保 EMR 应用已打开并显示病人列表[/yellow]")
        input("按 Enter 继续...")

        return True

    def step2_find_and_click_patient(self) -> bool:
        """
        步骤 2: 识别 EMR 窗口，找到第一个病人并点击

        返回:
            bool: 是否成功
        """
        from rich.console import Console
        console = Console()

        console.print("\n[bold cyan]🖱️  步骤 2: 查找并点击病人[/bold cyan]")

        # 检测 EMR 窗口
        console.print("[cyan]正在检测 EMR 窗口...[/cyan]")
        emr_window = WindowDetector.detect_emr_window()

        if emr_window:
            console.print(f"[green]✅ 找到 EMR 窗口: {emr_window['title']}[/green]")

            # 移动鼠标到 EMR 窗口
            MouseController.move_to_window(emr_window)
        else:
            console.print("[yellow]⚠️  未能自动检测 EMR 窗口，将在整个屏幕查找[/yellow]")

        # 查找并点击第一个病人
        console.print("\n[cyan]正在查找病人列表...[/cyan]")
        if MouseController.smart_click_patient():
            console.print("[green]✅ 已点击第一个病人，等待详情页加载...[/green]")
            time.sleep(2)  # 等待页面加载
            return True
        else:
            console.print("[red]❌ 未找到病人信息[/red]")
            console.print("[yellow]提示: 请确保 EMR 界面显示病人列表[/yellow]")
            return False

    def step2_ai_find_and_click_patient(self) -> bool:
        """
        步骤 2 (AI 增强版): 截图 -> AI 分析坐标 -> 本地点击

        返回:
            bool: 是否成功
        """
        from rich.console import Console
        console = Console()

        console.print("\n[bold cyan]🧠 步骤 2: AI 视觉定位病人[/bold cyan]")

        # 1. 截取全屏
        console.print("[dim]正在截取当前屏幕...[/dim]")
        screenshot_path = capture_full_screen()

        # 2. 调用 Claude 进行定位
        try:
            navigator = AINavigator()
            console.print("[cyan]正在请求 AI 分析屏幕结构...[/cyan]")

            coords = navigator.locate_emr_patient_row(screenshot_path)

            if coords:
                target_x, target_y = coords
                console.print(f"[green]✅ AI 定位成功！目标坐标: ({target_x}, {target_y})[/green]")

                # 3. 本地执行鼠标操作
                # 移动鼠标（带平滑动画，显得更自然）
                pyautogui.moveTo(target_x, target_y, duration=0.6, tween=pyautogui.easeInOutQuad)

                # 点击
                console.print(f"[dim]正在点击坐标 ({target_x}, {target_y})...[/dim]")
                pyautogui.click()

                # 等待页面加载（这是关键，进入详情页需要时间）
                console.print("[dim]等待页面跳转 (3秒)...[/dim]")
                time.sleep(3)

                return True
            else:
                console.print("[red]❌ AI 未能在屏幕上识别到病人列表[/red]")
                return False

        except Exception as e:
            console.print(f"[red]❌ AI 定位过程出错: {e}[/red]")
            if DEBUG_MODE:
                import traceback
                console.print(traceback.format_exc())
            return False

    def step3_screenshot_and_extract(self) -> Dict:
        """
        步骤 3: 截图并提取病人信息

        返回:
            Dict: 提取的病人信息
        """
        from rich.console import Console
        console = Console()

        console.print("\n[bold cyan]📸 步骤 3: 截图并提取数据[/bold cyan]")

        # 使用智能捕获
        result = smart_capture_and_extract(
            display_prompt=False,
            countdown=0
        )

        if result["success"]:
            console.print("[green]✅ 成功提取病人信息[/green]")
            return result
        else:
            console.print(f"[red]❌ 提取失败: {result.get('error')}[/red]")
            return result

    def step3_ai_extract_smart(self) -> Dict:
        """
        [Step 3] 智能提取 (支持单次或循环)

        返回:
            Dict: {
                "success": bool,
                "patient_info": Dict,
                "screenshot_path": str
            }
        """
        from rich.console import Console
        console = Console()

        navigator = AINavigator()
        collected_data = {}
        loop_count = 0
        screenshot_path = None

        mode_text = "单次" if self.max_extraction_loops == 1 else f"循环(最多{self.max_extraction_loops}次)"
        console.print(f"\n[bold cyan]📸 步骤 3: AI 智能提取数据 (模式: {mode_text})[/bold cyan]")

        while loop_count < self.max_extraction_loops:
            loop_count += 1
            if self.max_extraction_loops > 1:
                console.print(f"\n[cyan]--- 采集轮次 {loop_count}/{self.max_extraction_loops} ---[/cyan]")

            # 1. 截图
            screenshot_path = capture_full_screen()
            if DEBUG_MODE:
                console.print(f"[dim]截图路径: {screenshot_path}[/dim]")

            # 2. AI 分析
            result = navigator.extract_page_data(screenshot_path, collected_data)

            # 3. 数据合并
            new_info = result.get("patient_info", {})
            if new_info:
                # 简单的字典合并，只更新非空值
                collected_data.update({k: v for k, v in new_info.items() if v})
                console.print(f"[green]✅ 已提取字段: {list(new_info.keys())}[/green]")

            # 4. 判断下一步
            action = result.get("next_action", {})
            action_type = action.get("type", "finish")
            is_complete = result.get("is_complete", False)

            # 单次模式下的快速退出
            if self.max_extraction_loops == 1:
                console.print("[green]✅ 单次提取完成[/green]")
                break

            # 循环模式下的逻辑
            if is_complete or action_type == "finish":
                console.print("[green]✅ AI 判定数据收集完成[/green]")
                break

            # 执行 AI 指示的额外操作 (翻页/点击)
            if action_type == "click":
                cx, cy = action.get("x"), action.get("y")
                if cx and cy:
                    console.print(f"[cyan]👉 AI 导航点击: ({cx}, {cy}) - {action.get('reason', '')}[/cyan]")
                    pyautogui.moveTo(cx, cy, duration=0.3)
                    pyautogui.click()
                    time.sleep(2)
                else:
                    console.print("[yellow]⚠️  AI 返回点击操作但缺少坐标[/yellow]")
                    break
            elif action_type == "scroll":
                scroll_amount = action.get("amount", -500)
                console.print(f"[cyan]👇 AI 导航滚动: {scroll_amount} - {action.get('reason', '')}[/cyan]")
                pyautogui.scroll(scroll_amount)
                time.sleep(1)

        # 最终检查
        if collected_data:
            console.print(f"\n[green]✅ 数据提取流程结束，共收集 {len(collected_data)} 个字段[/green]")
            if DEBUG_MODE:
                console.print(f"[dim]提取数据: {collected_data}[/dim]")

            return {
                "success": True,
                "patient_info": collected_data,
                "screenshot_path": screenshot_path
            }
        else:
            console.print("[red]❌ 未提取到有效数据[/red]")
            return {
                "success": False,
                "error": "未提取到有效数据",
                "patient_info": {}
            }

    def step4_send_to_heidi(self, patient_data: Dict) -> bool:
        """
        步骤 4: 将数据发送到 Heidi

        参数:
            patient_data: 病人信息

        返回:
            bool: 是否成功
        """
        from rich.console import Console
        console = Console()

        console.print("\n[bold cyan]🚀 步骤 4: 发送到 Heidi[/bold cyan]")

        # 方法 1: 使用 Heidi API（优先使用轻量的 /patients，避免需要 linked account 的 profile 接口）
        from core.heidi_client import HeidiClient, PatientProfile

        try:
            console.print("[cyan]正在准备病人数据...[/cyan]")
            patient_profile = PatientProfile(
                first_name=patient_data.get("first_name", ""),
                last_name=patient_data.get("last_name", ""),
                birth_date=patient_data.get("birth_date", ""),
                gender=patient_data.get("gender", ""),
                ehr_patient_id=patient_data.get("ehr_patient_id", "")
            )

            if DEBUG_MODE:
                console.print(f"[dim]Patient Profile: {patient_profile.__dict__}[/dim]")

            console.print("[cyan]正在连接 Heidi API...[/cyan]")
            with HeidiClient() as client:
                console.print("[cyan]正在进行身份验证...[/cyan]")
                client.authenticate()

                # 优先使用 create_patient（不依赖 linked account），若失败再尝试 profile 接口
                console.print("[cyan]正在发送病人数据 (patients)...[/cyan]")
                result = client.create_patient(patient_data)

                if not result:
                    console.print("[yellow]⚠️  /patients 接口返回空，尝试 profile 接口...[/yellow]")
                    result = client.create_or_update_patient_profile(patient_profile)

            console.print("[green]✅ 成功发送到 Heidi API[/green]")
            console.print(f"[dim]Response: {result}[/dim]")
            return True

        except Exception as e:
            console.print(f"[red]❌ API 发送失败: {e}[/red]")
            if DEBUG_MODE:
                import traceback
                console.print("[dim]" + traceback.format_exc() + "[/dim]")

            # 方法 2: 备用方案 - 复制到剪贴板
            console.print("\n[yellow]尝试备用方案: 复制到剪贴板[/yellow]")
            if BrowserAutomation.input_to_heidi(patient_data):
                console.print("[green]✅ 数据已复制到剪贴板，请手动粘贴到 Heidi 浏览器[/green]")
                return True
            else:
                return False

    def run_full_workflow(self) -> Dict:
        """
        运行完整的 RPA 工作流

        返回:
            Dict: 执行结果
        """
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        console.print(Panel.fit(
            "[bold cyan]🤖 RPA 自动化工作流[/bold cyan]\n\n"
            "1. 启动 EMR 和 Heidi 浏览器\n"
            "2. 识别 EMR 窗口，查找并点击第一个病人\n"
            "3. 截图并提取病人信息\n"
            "4. 将数据发送到 Heidi",
            title="端到端自动化",
            border_style="cyan"
        ))

        result = {
            "success": False,
            "steps_completed": [],
            "patient_data": None,
            "error": None
        }

        try:
            # 步骤 1: 启动应用
            if not self.step1_launch_applications():
                result["error"] = "步骤 1 失败: 无法启动应用"
                return result
            result["steps_completed"].append("step1_launch")

            # 步骤 2: AI 视觉定位并点击病人 (使用 AI 增强版)
            if not self.step2_ai_find_and_click_patient():
                result["error"] = "步骤 2 失败: AI 无法定位病人"
                return result
            result["steps_completed"].append("step2_ai_click")

            # 步骤 3: AI 智能提取 (单次或循环模式)
            extraction_result = self.step3_ai_extract_smart()
            if not extraction_result["success"]:
                result["error"] = f"步骤 3 失败: {extraction_result.get('error')}"
                return result
            result["steps_completed"].append("step3_ai_extract")
            result["patient_data"] = extraction_result["patient_info"]

            # 步骤 4: 发送到 Heidi
            if not self.step4_send_to_heidi(extraction_result["patient_info"]):
                result["error"] = "步骤 4 失败: 无法发送到 Heidi"
                return result
            result["steps_completed"].append("step4_send")

            # 全部成功
            result["success"] = True
            console.print("\n[bold green]🎉 RPA 工作流执行成功！[/bold green]")

            return result

        except Exception as e:
            result["error"] = f"工作流异常: {str(e)}"
            if DEBUG_MODE:
                import traceback
                console.print(traceback.format_exc())
            return result


# 方便导入
__all__ = [
    "WindowDetector",
    "MouseController",
    "BrowserAutomation",
    "RPAWorkflow",
]


if __name__ == "__main__":
    # 测试 RPA 工作流
    print("=== RPA 自动化测试 ===\n")

    workflow = RPAWorkflow(
        emr_app_path=None,  # 设置为实际 EMR 路径，或 None 手动打开
        heidi_url="https://www.heidihealth.com"
    )

    result = workflow.run_full_workflow()

    print(f"\n执行结果: {'成功' if result['success'] else '失败'}")
    print(f"完成步骤: {', '.join(result['steps_completed'])}")
    if result['error']:
        print(f"错误: {result['error']}")
