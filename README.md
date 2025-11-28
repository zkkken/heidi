# EMR to Heidi Health Integration

## 🎯 项目简介

一个自动化工具，用于：
1. 从本地 EMR 系统界面截图
2. 使用 OCR 识别病人基础信息
3. 调用 Heidi Health API 创建/更新 patient profile

**当前版本：** Phase 1 MVP（混合方案 - 独立命令行工具）

**项目架构：** 混合方案，支持：
- ✅ **Phase 1：** 独立命令行工具（当前版本）
- 🔜 **Phase 2：** 复用 OOTB 能力（多屏幕、日志系统）
- 🔮 **Phase 3：** 深度集成 Computer Use OOTB（AI Agent）

---

## 📋 功能特性

### ✅ 已实现（Phase 1 MVP）
- [x] 屏幕区域截图
- [x] PaddleOCR 中英文识别
- [x] 智能解析病人信息（姓名、性别、出生日期、病历号）
- [x] Heidi Health API 集成
- [x] 自动创建/更新 patient profile
- [x] 用户确认和手动修正功能
- [x] 丰富的终端输出（Rich库）
- [x] 完善的配置管理
- [x] 工具函数（坐标获取、截图预览）

### 🔜 规划中（Phase 2/3）
- [ ] 复用 OOTB 多屏幕支持
- [ ] 集成 OOTB 日志系统
- [ ] Gradio Web UI 界面
- [ ] AI Agent 自动化 EMR 导航
- [ ] 支持更多 EMR 系统格式
- [ ] 批量处理功能

---

## 🚀 快速开始

### 1. 环境要求

- **Python：** 3.10 或更高
- **操作系统：** Windows / macOS / Linux
- **可选：** CUDA（用于 GPU 加速 OCR）

### 2. 安装依赖

```bash
# 克隆项目（如果从 git）
# git clone <repository_url>
cd heidi

# 安装 Python 依赖
pip install -r requirements.txt
```

**注意：** 首次运行会自动下载 PaddleOCR 模型文件（约 200MB），请耐心等待。

### 3. 配置

#### 3.1 创建 .env 配置文件

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件
# 在编辑器中打开 .env，填写 HEIDI_API_KEY
```

#### 3.2 配置截图区域

**方法 1：使用坐标获取工具（推荐）**

```bash
# 运行坐标获取工具（默认 10 秒）
python integrations/standalone/main.py --coords

# 或指定持续时间（例如 15 秒）
python integrations/standalone/main.py --coords 15
```

然后：
1. 打开 EMR 系统，切到病人详情页面
2. 移动鼠标到病人信息区域的**左上角**，记录坐标 `(left, top)`
3. 移动鼠标到病人信息区域的**右下角**，记录坐标 `(right, bottom)`
4. 计算：`width = right - left`, `height = bottom - top`
5. 在 `.env` 文件中设置：

```env
SCREENSHOT_LEFT=100    # 左上角 X 坐标
SCREENSHOT_TOP=200     # 左上角 Y 坐标
SCREENSHOT_WIDTH=800   # 宽度
SCREENSHOT_HEIGHT=400  # 高度
```

**方法 2：预览截图验证**

```bash
# 使用当前配置预览截图
python integrations/standalone/main.py --preview

# 或使用自定义区域预览
python integrations/standalone/main.py --preview --region 100 200 800 400
```

检查截图是否完整包含病人信息区域，如果不正确，调整 `.env` 中的坐标。

#### 3.3 验证配置

```bash
# 查看当前配置
python integrations/standalone/main.py --show-config
```

---

## 💻 使用方法

### 基本用法

```bash
# 运行完整流程
python integrations/standalone/main.py
```

流程：
1. 提示用户打开 EMR 界面
2. 截图
3. OCR 识别
4. 显示识别结果，询问是否正确
5. 调用 Heidi API
6. 显示结果

### 高级用法

```bash
# 跳过确认，直接执行
python integrations/standalone/main.py --yes

# 使用自定义截图区域
python integrations/standalone/main.py --region 100 200 800 600

# 禁用手动修正功能
python integrations/standalone/main.py --no-manual

# 截图后预览
python integrations/standalone/main.py --preview-screenshot

# 启用调试模式
python integrations/standalone/main.py --debug
```

### 工具功能

```bash
# 获取屏幕坐标（配置截图区域）
python integrations/standalone/main.py --coords [duration]

# 预览截图区域（验证配置）
python integrations/standalone/main.py --preview

# 显示当前配置
python integrations/standalone/main.py --show-config

# 查看帮助
python integrations/standalone/main.py --help
```

---

## 📁 项目结构

```
heidi/
├── core/                           # 核心模块（独立于集成方式）
│   ├── __init__.py
│   ├── config.py                   # 配置管理
│   ├── capture.py                  # 屏幕截图
│   ├── ocr_parser.py               # OCR 识别和解析
│   └── heidi_client.py             # Heidi API 客户端
│
├── integrations/                   # 集成层
│   ├── standalone/                 # 独立命令行工具
│   │   ├── __init__.py
│   │   ├── pipeline.py             # 主流程编排
│   │   └── main.py                 # 程序入口
│   │
│   └── ootb/                       # OOTB 集成（Phase 2/3）
│       ├── emr_tool.py             # OOTB Tool 封装
│       └── install.py              # 插件安装脚本
│
├── config/                         # 配置文件目录
│   └── (自定义 EMR 解析规则)
│
├── tmp/                            # 临时文件
│   ├── screenshots/                # 截图保存
│   └── logs/                       # 日志文件
│
├── requirements.txt                # Python 依赖
├── .env.example                    # 环境变量示例
├── .env                            # 环境变量配置（需创建）
├── README.md                       # 本文档
└── 可行性分析报告.md                # 技术方案分析
```

---

## ⚙️ 配置说明

### 环境变量（.env 文件）

| 变量名 | 说明 | 必填 | 默认值 |
|--------|------|------|--------|
| `HEIDI_API_KEY` | Heidi API Key | ✅ 是 | - |
| `HEIDI_BASE_URL` | Heidi API 基础 URL | 否 | https://api.heidihealth.com |
| `SCREENSHOT_LEFT` | 截图区域左坐标 | 否 | 100 |
| `SCREENSHOT_TOP` | 截图区域上坐标 | 否 | 200 |
| `SCREENSHOT_WIDTH` | 截图宽度 | 否 | 800 |
| `SCREENSHOT_HEIGHT` | 截图高度 | 否 | 400 |
| `OCR_LANGUAGE` | OCR 语言 | 否 | ch |
| `OCR_USE_GPU` | 是否使用 GPU | 否 | False |
| `EMR_SYSTEM_TYPE` | EMR 系统类型 | 否 | generic_cn |
| `DEBUG_MODE` | 调试模式 | 否 | False |

完整配置项请参考 `.env.example`。

---

## 🔧 常见问题

### 1. OCR 识别准确率不高？

**原因：**
- 截图质量不佳
- EMR 字体过小或有变形
- 识别区域包含无关信息

**解决方案：**
- 调整截图区域，只包含病人基本信息
- 增加截图分辨率（调整 `SCREENSHOT_WIDTH/HEIGHT`）
- 提高 OCR 置信度阈值（`OCR_CONFIDENCE_THRESHOLD`）
- 使用手动修正功能

### 2. 无法识别特定 EMR 系统格式？

**解决方案：**
- 在 `core/ocr_parser.py` 中添加自定义解析规则
- 或创建自定义规则文件，设置 `EMR_PARSING_RULES_FILE`

### 3. Heidi API 调用失败？

**检查项：**
- 确认 `HEIDI_API_KEY` 正确
- 检查网络连接
- 查看 Heidi API 文档，确认接口路径（代码中标注了 TODO）

### 4. PaddleOCR 模型下载慢？

**解决方案：**
- 使用镜像源下载
- 手动下载模型文件并放到 `~/.paddleocr/` 目录

### 5. 运行时找不到模块？

```bash
# 确保在项目根目录运行
cd /path/to/heidi

# 或设置 PYTHONPATH
export PYTHONPATH=/path/to/heidi:$PYTHONPATH
```

---

## 🛠️ 开发指南

### 添加自定义 EMR 解析规则

编辑 `core/ocr_parser.py`，添加新的解析函数：

```python
def _parse_custom_emr(ocr_text: str) -> Dict[str, Optional[str]]:
    """自定义 EMR 系统解析"""
    patient_info = {...}

    # 添加你的正则表达式规则
    name_match = re.search(r"YOUR_PATTERN", ocr_text)

    return patient_info
```

然后在 `parse_patient_info()` 中调用。

### 调试模式

```bash
# 启用调试模式，查看详细日志
python integrations/standalone/main.py --debug
```

### 测试单个模块

```bash
# 测试配置
python -m core.config

# 测试截图
python -m core.capture test

# 测试 OCR
python -m core.ocr_parser <image_path>

# 测试 Heidi API
python -m core.heidi_client
```

---

## 📊 Phase 2/3 规划

### Phase 2: OOTB 能力复用

**目标：** 增强功能，复用 Computer Use OOTB 的优秀能力

**计划：**
- 复用 OOTB 的多屏幕支持（`screen_capture.py`）
- 集成 OOTB 的日志系统（`logger.py`）
- 保持核心模块独立

**预计时间：** 2-3 天

### Phase 3: 深度集成 OOTB

**目标：** 提供 OOTB 插件，利用 AI Agent 实现全自动化

**计划：**
- 将核心功能封装为 OOTB Tool (`OCRTool`, `HeidiAPITool`)
- 在 OOTB `app.py` 中添加 "EMR → Heidi" 标签页
- 利用 AI Agent 自动导航 EMR 系统

**预计时间：** 3-5 天

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

---

## ⚠️ 注意事项

1. **这是 demo 工具，不适用于真实医疗生产环境**
2. Heidi demo 环境中的患者数据是随机的
3. 请勿在代码中硬编码任何真实 API Key
4. OCR 识别结果建议人工复核后再使用
5. 遵守 HIPAA 等医疗数据隐私法规

---

## 📄 许可证

（请根据实际情况添加许可证信息）

---

## 📮 联系方式

（请根据实际情况添加联系信息）

---

## 🙏 致谢

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - OCR 引擎
- [Computer Use OOTB](https://github.com/showlab/computer_use_ootb) - 架构参考
- [Heidi Health](https://www.heidihealth.com) - API 服务
- [Rich](https://github.com/Textualize/rich) - 终端美化

---

**版本：** 1.0.0 (Phase 1 MVP)
**最后更新：** 2025-11-29
**方案类型：** 混合方案（方案三）⭐⭐⭐⭐⭐
