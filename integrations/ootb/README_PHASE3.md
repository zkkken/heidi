# Phase 3: 深度集成 OOTB

## 目标

将 EMR → Heidi 功能作为插件集成到 Computer Use OOTB，提供 Web UI 和 AI Agent 支持。

## 计划架构

### 1. OOTB Tool 封装

**文件：** `integrations/ootb/emr_tool.py`

```python
from computer_use_demo.tools.base import BaseAnthropicTool

class EMRToHeidiTool(BaseAnthropicTool):
    """
    复合工具：一键完成 EMR → Heidi 流程
    """
    name = "emr_to_heidi"

    def __call__(self, screenshot_region: dict):
        # 1. 调用 core.capture
        # 2. 调用 core.ocr_parser
        # 3. 调用 core.heidi_client
        ...
```

### 2. Gradio UI 集成

**文件：** OOTB 的 `app.py` 修改

```python
# 添加 "EMR → Heidi" 标签页
with gr.Tab("EMR → Heidi"):
    region_input = gr.Textbox(label="截图区域 (left,top,width,height)")
    capture_btn = gr.Button("开始识别")
    result_output = gr.JSON()

    capture_btn.click(
        fn=run_emr_to_heidi,
        inputs=[region_input],
        outputs=[result_output]
    )
```

### 3. AI Agent 全自动化

利用 OOTB 的 Planner-Actor 架构：

- **Planner (GPT-4o/Claude):** 理解用户任务，制定计划
- **Actor (ShowUI):** 自动导航 EMR 系统，定位病人信息区域
- **EMRToHeidiTool:** 执行截图→OCR→Heidi API 流程

---

## 实施步骤

### 3.1 创建 OOTB Tool

1. [ ] 实现 `EMRToHeidiTool`
2. [ ] 注册到 OOTB tools 系统
3. [ ] 测试工具调用

### 3.2 UI 集成

1. [ ] 在 `app.py` 添加 EMR 标签页
2. [ ] 实现交互逻辑
3. [ ] 测试 UI 功能

### 3.3 AI Agent 集成

1. [ ] 设计 AI Agent 提示词
2. [ ] 测试自动化流程
3. [ ] 优化用户体验

### 3.4 安装脚本

**文件：** `integrations/ootb/install.py`

```python
# 自动安装脚本
# 将核心模块复制到 OOTB 目录
# 注册工具和 UI
```

---

## 技术挑战

### 1. 异步架构适配

OOTB 使用 `sampling_loop_sync`，需要适配 OCR 的同步操作。

**解决方案：**
```python
import asyncio

def __call__(self, ...):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, self._sync_ocr, ...)
```

### 2. 工具依赖顺序

Agent 需要按顺序调用：截图 → OCR → Heidi API

**解决方案：** 使用复合工具，内部自动编排。

### 3. 配置管理冲突

OOTB 使用 Gradio State，我们使用 config.py。

**解决方案：** 创建统一的配置接口。

---

## 交付物

- [ ] `emr_tool.py` - OOTB Tool 实现
- [ ] 修改后的 `app.py` - Gradio UI
- [ ] `install.py` - 安装脚本
- [ ] `README_OOTB_INTEGRATION.md` - 集成文档

---

**预计时间：** 3-5 天
**依赖：** Phase 1 + Phase 2 完成
