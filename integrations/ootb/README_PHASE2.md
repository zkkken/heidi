# Phase 2: OOTB 能力复用

## 目标

选择性复用 Computer Use OOTB 的优秀能力，增强独立版本的功能。

## 计划任务

### 1. 复用多屏幕支持

**文件：** `/path/to/computer_use_ootb-main/computer_use_demo/tools/screen_capture.py`

**集成方式：**
```python
# core/capture.py 增加 OOTB 后端选项

def capture_emr_region(..., use_ootb=False):
    if use_ootb:
        from ootb_screen_capture import get_screenshot
        return get_screenshot(selected_screen=0, ...)
    else:
        # 使用当前的 pyautogui 实现
        ...
```

### 2. 集成日志系统

**文件：** `/path/to/computer_use_ootb-main/computer_use_demo/tools/logger.py`

**集成方式：**
```python
# core/logger.py (新增)

from ootb_logger import logger

def log_info(msg):
    logger.info(msg)
```

### 3. 图像处理工具

复用 OOTB 的图像缩放、处理功能。

---

## 实施步骤

1. [ ] 提取 OOTB 的 `screen_capture.py`
2. [ ] 适配到 core 模块
3. [ ] 测试兼容性
4. [ ] 更新文档

---

**预计时间：** 2-3 天
