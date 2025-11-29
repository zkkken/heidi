# Heidi EMR Automation v8.1

## 项目简介

一个 macOS 端 RPA 自动化工具，用于：
1. 从 CareFlow EMR 系统自动提取病人信息
2. 使用 Claude AI 视觉识别 + 硬坐标双重定位
3. 通过 Chrome AppleScript 注入数据到 Heidi Web 界面
4. 调用 Heidi Health API 创建/更新 patient profile

**当前版本：** v8.1 (Ultra-Robust Click + React-Compatible Injection)

---

## 核心特性

### AI + 硬坐标双重定位
- **Claude Vision** 智能识别 UI 元素位置
- **硬坐标保底** 当 AI 偏差过大时自动纠正
- **Retina 支持** 自动处理 macOS 高分屏缩放

### Chrome 直接注入 (React 兼容)
- **AppleScript → JS** 直接操控 Chrome DOM
- **Native Value Setter** 绕过 React 状态管理
- **0.1s 注入速度** 比传统鼠标点击快 30 倍

### 鲁棒点击机制 v2
- **Press & Hold** 模拟真人长按点击
- **物理晃动** 确保触发 Hover 状态
- **双保险机制** 可选补刀点击

---

## 快速开始

### 1. 环境要求

- **Python：** 3.10+
- **操作系统：** macOS (需要 AppleScript 权限)
- **浏览器：** Google Chrome
- **API Key：** Anthropic Claude API + Heidi Health API

### 2. 安装依赖

```bash
cd heidi
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Claude API (AI 视觉识别)
ANTHROPIC_API_KEY=sk-ant-...

# Heidi Health API
HEIDI_API_KEY=your_heidi_api_key
HEIDI_BASE_URL=https://registrar.api.heidihealth.com/api/v2/ml-scribe/open-api
```

### 4. 获取硬坐标

```bash
python tools/get_mouse_pos.py
```

将获取的坐标更新到 `core/rpa_automation.py`：

```python
HARD_COORDS_FIRST_PATIENT = (1322, 412)   # 第一个病人名字
HARD_COORDS_CONSULTATIONS = (1317, 250)   # Consultations 标签
```

### 5. 运行

```bash
python main.py
```

---

## 功能菜单

```
🏥 Heidi EMR Automation v8.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] 📋 批量日程 (Batch -> Web)
    EMR 列表读取 -> 生成 JSON -> Chrome 注入

[2] 🎯 精准 Consultations [推荐]
    AI/硬坐标双重定位 -> 病人 -> Consultations -> 提取 -> 注入 Web

[3] 💉 单人 Context 注入
    EMR 点击 -> AI 提取病历 -> Chrome 注入

[4] ⚡ 智能点击 (Auto-Correct)
    AI定位 + 硬坐标纠偏 -> Heidi API 上传

[5] 🔧 更多选项
    批量建档 / 极速模式 / 旧版菜单

[q] 退出
```

---

## 项目结构

```
heidi/
├── main.py                    # 主入口 v8.1
├── heidi_menu.py              # 备用菜单
│
├── core/                      # 核心模块
│   ├── config.py              # 配置管理
│   ├── capture.py             # 屏幕截图
│   ├── ai_locator.py          # Claude AI 视觉定位
│   ├── web_bridge.py          # Chrome JS 注入 (React 兼容)
│   ├── rpa_automation.py      # RPA 流程编排
│   ├── heidi_client.py        # Heidi API 客户端
│   └── ocr_parser.py          # OCR 解析 (备用)
│
├── tools/                     # 工具脚本
│   ├── get_mouse_pos.py       # 坐标获取工具
│   ├── force_link.py          # 账号绑定工具
│   └── voice_commander.py     # 语音控制 (实验)
│
├── integrations/              # 集成层
│   ├── standalone/            # 独立命令行
│   └── ootb/                  # OOTB 集成
│
├── tmp/                       # 临时文件
│   └── screenshots/           # 截图保存
│
├── .env                       # 环境变量
└── requirements.txt           # 依赖
```

---

## 核心模块说明

### `core/ai_locator.py` - AI 视觉引擎

```python
navigator = AINavigator()

# 精准定位病人
coords = navigator.locate_patient_precise(screenshot, "First Patient")

# 查找文本坐标
coords = navigator.find_text_coordinates(screenshot, "Consultations")

# 提取咨询内容
content = navigator.extract_consultation_content(screenshot)

# 批量提取日程
json_data = navigator.extract_patient_list_for_schedule(screenshot)
```

### `core/web_bridge.py` - Chrome 注入器

```python
web = WebBridge()

# 批量日程注入
web.inject_batch_schedule(json_data)

# 单人 Context 注入
web.inject_single_context(context_text)
```

### `core/rpa_automation.py` - 流程编排

```python
workflow = RPAWorkflow()

# 精准 Consultations 流程 (推荐)
workflow.run_precise_consultations_pipeline()

# 批量日程流程
workflow.run_batch_pipeline()

# 智能点击 + API 上传
workflow.run_smart_click_auto()
```

---

## 配置说明

### 硬坐标配置

在 `core/rpa_automation.py` 中：

```python
# 列表页：第一个病人名字位置
HARD_COORDS_FIRST_PATIENT = (1322, 412)

# 详情页：Consultations 标签位置
HARD_COORDS_CONSULTATIONS = (1317, 250)

# 偏差阈值 (像素) - AI 与硬坐标差距超过此值则纠偏
DEVIATION_THRESHOLD = 50
SAFE_THRESHOLD = 150
```

### 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | Claude API Key | 是 |
| `HEIDI_API_KEY` | Heidi API Key | 是 |
| `HEIDI_BASE_URL` | Heidi API URL | 否 |
| `DEBUG_MODE` | 调试模式 | 否 |

---

## 常见问题

### 1. 点击无效？

**解决方案：**
1. 运行 `python tools/get_mouse_pos.py` 重新获取硬坐标
2. 确保 EMR 窗口位置固定
3. 如果仍无效，取消 `_robust_click()` 中双击注释：
   ```python
   pyautogui.click(x, y)  # 取消这行注释
   ```

### 2. Chrome 注入无反应？

**解决方案：**
1. 确保 Chrome 已授予 AppleScript 权限
2. 打开 Chrome DevTools (F12) 查看 Console 日志
3. 确认目标页面有 `<textarea>` 元素

### 3. AI 定位偏差大？

**解决方案：**
- 系统会自动使用硬坐标保底
- 调整 `DEVIATION_THRESHOLD` 值
- 确保屏幕分辨率与获取坐标时一致

### 4. Retina 屏幕坐标偏移？

**解决方案：**
- `ai_locator.py` 已内置 `_get_pixel_scale()` 自动处理
- 确保使用最新版本代码

---

## 版本历史

| 版本 | 更新内容 |
|------|----------|
| v8.1 | Ultra-Robust Click (Press & Hold) + React 兼容注入 |
| v8.0 | Chrome AppleScript 注入 + 双重纠偏 |
| v5.1 | Anchor-based Deviation Check |
| v5.0 | 账号绑定检测 + 批量建档 |
| v4.0 | 深度挖掘 + 交互菜单 |
| v3.0 | Retina 支持 + Crop & Refine |

---

## 注意事项

1. **仅供演示使用**，不适用于真实医疗生产环境
2. 请勿在代码中硬编码 API Key
3. 遵守 HIPAA 等医疗数据隐私法规
4. macOS 需要授予终端/IDE 辅助功能权限

---

## 技术栈

- **AI Vision:** Claude claude-sonnet-4-20250514
- **RPA:** PyAutoGUI + AppleScript
- **Web Injection:** Chrome JavaScript
- **OCR (备用):** PaddleOCR
- **UI:** Rich Terminal

---

**最后更新：** 2025-11-29
