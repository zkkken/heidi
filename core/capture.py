"""
屏幕截图模块
负责捕获 EMR 界面的指定区域
支持 Phase 1 独立实现和 Phase 2 OOTB 能力复用
"""

import pyautogui
import time
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
from PIL import Image

from .config import SCREENSHOT_OUTPUT_DIR, DEFAULT_SCREENSHOT_REGION


def capture_emr_region(
    region: Optional[Tuple[int, int, int, int]] = None,
    save_path: Optional[str] = None,
    add_timestamp: bool = True
) -> str:
    """
    使用 pyautogui 对指定 region 截图，并保存到 save_path

    参数:
        region: 截图区域 (left, top, width, height)
                如果为 None，使用 config.py 中的 DEFAULT_SCREENSHOT_REGION
        save_path: 保存路径。如果为 None，自动生成带时间戳的文件名
        add_timestamp: 是否在文件名中添加时间戳

    返回:
        str: 实际保存的图片路径

    异常:
        ValueError: region 参数无效
        RuntimeError: 截图失败

    示例:
        >>> # 使用默认配置截图
        >>> path = capture_emr_region()

        >>> # 自定义区域截图
        >>> path = capture_emr_region(region=(100, 200, 800, 600))

        >>> # 指定保存路径
        >>> path = capture_emr_region(save_path="./my_screenshot.png")
    """
    # 使用默认区域
    if region is None:
        region = DEFAULT_SCREENSHOT_REGION

    # 验证区域参数
    if len(region) != 4:
        raise ValueError(f"region 必须包含 4 个元素 (left, top, width, height)，当前: {region}")

    left, top, width, height = region

    if width <= 0 or height <= 0:
        raise ValueError(f"width 和 height 必须大于 0，当前: width={width}, height={height}")

    # 生成保存路径
    if save_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if add_timestamp else ""
        filename = f"emr_screenshot_{timestamp}.png" if timestamp else "emr_screenshot.png"
        save_path = str(SCREENSHOT_OUTPUT_DIR / filename)

    # 确保保存目录存在
    save_dir = Path(save_path).parent
    save_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 截图（pyautogui.screenshot 返回 PIL Image 对象）
        screenshot = pyautogui.screenshot(region=(left, top, width, height))

        # 保存截图
        screenshot.save(save_path)

        # 验证文件是否成功保存
        if not Path(save_path).exists():
            raise RuntimeError(f"截图保存失败：{save_path} 文件不存在")

        return save_path

    except Exception as e:
        raise RuntimeError(f"截图过程中发生错误: {str(e)}") from e


def capture_full_screen(save_path: Optional[str] = None) -> str:
    """
    截取整个屏幕

    参数:
        save_path: 保存路径。如果为 None，自动生成文件名

    返回:
        str: 实际保存的图片路径
    """
    if save_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = str(SCREENSHOT_OUTPUT_DIR / f"fullscreen_{timestamp}.png")

    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(save_path)
        return save_path
    except Exception as e:
        raise RuntimeError(f"全屏截图失败: {str(e)}") from e


def get_screen_coordinates_helper(duration: int = 10, interval: float = 0.5) -> None:
    """
    帮助用户获取屏幕坐标的工具函数
    运行后，移动鼠标到感兴趣的区域，程序会实时打印鼠标坐标

    参数:
        duration: 监控持续时间（秒），默认 10 秒
        interval: 打印间隔（秒），默认 0.5 秒

    使用方法:
        1. 运行此函数
        2. 打开 EMR 系统，切到病人详情页面
        3. 移动鼠标到病人信息区域的左上角，记录坐标 (left, top)
        4. 移动鼠标到右下角，记录坐标 (right, bottom)
        5. 计算: width = right - left, height = bottom - top
        6. 在 config.py 中设置 SCREENSHOT_REGION = (left, top, width, height)

    示例:
        >>> get_screen_coordinates_helper(duration=15)
        开始监控鼠标坐标... (持续 15 秒)
        按 Ctrl+C 提前结束

        X:  100, Y:  200
        X:  150, Y:  250
        ...
    """
    print(f"\n📍 开始监控鼠标坐标... (持续 {duration} 秒)")
    print("💡 提示：")
    print("   1. 移动鼠标到病人信息区域的 **左上角**，记录坐标")
    print("   2. 移动鼠标到病人信息区域的 **右下角**，记录坐标")
    print("   3. 计算: width = right - left, height = bottom - top")
    print("   4. 在 config.py 或 .env 中设置截图区域")
    print("\n按 Ctrl+C 提前结束\n")

    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            x, y = pyautogui.position()
            print(f"\rX: {x:4d}, Y: {y:4d}", end="", flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n⏹️  已停止监控")

    print("\n\n✅ 监控结束")
    print("\n示例配置：")
    print("假设你记录的坐标为:")
    print("  左上角: (100, 200)")
    print("  右下角: (900, 600)")
    print("\n则在 config.py 中设置:")
    print("  SCREENSHOT_REGION = (100, 200, 800, 400)")
    print("  其中: width = 900 - 100 = 800, height = 600 - 200 = 400")
    print("\n或在 .env 中设置:")
    print("  SCREENSHOT_LEFT=100")
    print("  SCREENSHOT_TOP=200")
    print("  SCREENSHOT_WIDTH=800")
    print("  SCREENSHOT_HEIGHT=400")


def preview_screenshot_region(
    region: Optional[Tuple[int, int, int, int]] = None,
    display_duration: int = 3
) -> None:
    """
    预览截图区域（用于验证配置是否正确）
    截图后会自动打开图片预览

    参数:
        region: 截图区域，如果为 None 则使用默认配置
        display_duration: 提示显示时间（秒）

    示例:
        >>> preview_screenshot_region()  # 使用默认配置预览
    """
    if region is None:
        region = DEFAULT_SCREENSHOT_REGION

    left, top, width, height = region

    print(f"\n📸 准备预览截图区域...")
    print(f"   区域: (left={left}, top={top}, width={width}, height={height})")
    print(f"\n⏰ {display_duration} 秒后开始截图，请切换到 EMR 界面...")

    for i in range(display_duration, 0, -1):
        print(f"\r   {i}...", end="", flush=True)
        time.sleep(1)

    print("\r   📷 截图中...")

    # 执行截图
    save_path = capture_emr_region(region=region)

    print(f"\n✅ 截图已保存: {save_path}")
    print(f"\n正在打开预览...")

    # 打开图片预览
    try:
        img = Image.open(save_path)
        img.show()
        print("✅ 预览已打开")
        print("\n💡 检查截图是否包含完整的病人信息区域")
        print("   如果不正确，请调整 config.py 中的 SCREENSHOT_REGION")
    except Exception as e:
        print(f"⚠️  无法打开预览: {str(e)}")
        print(f"   请手动打开文件: {save_path}")


# ============================================
# Phase 2 准备：OOTB 集成接口
# ============================================

class CaptureInterface:
    """
    截图接口类（为 Phase 2 OOTB 集成准备）
    可以轻松替换为 OOTB 的 screen_capture 模块
    """

    @staticmethod
    def capture(region: Optional[Tuple[int, int, int, int]] = None,
                save_path: Optional[str] = None) -> str:
        """统一的截图接口"""
        return capture_emr_region(region=region, save_path=save_path)

    @staticmethod
    def capture_full() -> str:
        """全屏截图接口"""
        return capture_full_screen()


# 方便导入
__all__ = [
    "capture_emr_region",
    "capture_full_screen",
    "get_screen_coordinates_helper",
    "preview_screenshot_region",
    "CaptureInterface",
]


if __name__ == "__main__":
    # 测试模块
    import sys

    print("=== 截图模块测试 ===\n")

    if len(sys.argv) > 1:
        if sys.argv[1] == "coords":
            # 获取坐标
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            get_screen_coordinates_helper(duration=duration)

        elif sys.argv[1] == "preview":
            # 预览截图
            preview_screenshot_region()

        elif sys.argv[1] == "test":
            # 测试截图
            print("测试截图功能...")
            path = capture_emr_region()
            print(f"✅ 截图成功: {path}")
    else:
        print("使用方法:")
        print("  python -m core.capture coords [duration]  - 获取屏幕坐标")
        print("  python -m core.capture preview            - 预览截图区域")
        print("  python -m core.capture test               - 测试截图功能")
