# Fisherman 视觉自动化程序

基于计算机视觉的自动化程序，主要用于识别和操作屏幕上的特定物体。

## 快速开始

### 1. 安装 uv

本项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 环境与依赖。

```powershell
# Windows PowerShell 一键安装
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

或通过 pip 安装：

```bash
pip install uv
```

uv 会自动下载和管理 Python 解释器，无需单独安装 Python。

### 2. 克隆代码库

```bash
git clone <your-repository-url>
cd fisherman
```

### 3. 运行程序

**Windows 用户**（推荐）：
双击运行 `启动_Fisherman.bat`

启动器会自动：
- ✅ 检查 uv 环境
- ✅ 通过 `uv sync` 创建虚拟环境并安装依赖（首次 3-5 分钟）
- ✅ 启动 Fisherman 程序

**手动运行**：
```bash
# 同步依赖（首次会在 .venv 目录创建虚拟环境）
uv sync

# 运行程序
uv run python main.py
```

## 功能说明

### 训练模块
- 创建训练任务
- 导入训练图像
- 图像标注工具
- 配置训练参数
- 启动训练并监控进度

### 识别模块
- 选择训练好的模型
- 配置识别参数
- 选择识别区域
- 自动识别和点击目标

### 数据管理
- 查看训练记录和日志
- 管理模型版本
- 导入/导出模型

## 系统要求

- **操作系统**: Windows 10/11 (64位)
- **Python**: 3.8 或更高版本
- **内存**: 至少 4GB
- **磁盘**: 至少 2GB 可用空间
- **其他**: Visual C++ Redistributable for Visual Studio 2015-2022

## 依赖库

主要依赖包括：
- torch==2.3.0 (PyTorch CPU版本)
- torchvision==0.18.0
- ultralytics (YOLOv8)
- opencv-python-headless
- PyQt5 (图形界面)
- mss (屏幕截图)
- pyautogui (自动点击)
- SQLAlchemy (数据库)

完整依赖列表见 [pyproject.toml](pyproject.toml)

## 故障排除

### 提示"未检测到 uv"
- 按照上文"安装 uv"小节安装
- 安装后重启命令行窗口使 PATH 生效

### 依赖同步失败
```bash
# 查看详细日志
uv sync --verbose

# 清理环境后重试
rm -rf .venv && uv sync
```

### 提示"PyTorch库不可用"
- 安装 Visual C++ Redistributable for Visual Studio 2015-2022
- 下载地址: https://aka.ms/vs/17/release/vc_redist.x64.exe

### 其他问题
- 查看日志文件: `logs/fisherman.log`
- 确保网络连接正常（首次运行需要下载依赖）
- 强制重建环境: 删除 `.venv` 目录后重新执行 `uv sync`

## 项目结构

```
fisherman/
├── main.py                 # 程序主入口
├── 启动_Fisherman.bat       # Windows启动脚本
├── pyproject.toml          # 项目元数据与依赖（uv 管理）
├── uv.lock                 # 依赖锁定文件（uv 自动生成）
├── database_migration.py   # 数据库迁移脚本
├── gui/                    # 图形界面模块
├── recognition/            # 识别模块
├── training/               # 训练模块
├── training_result/        # 训练结果管理模块
├── global_support/         # 全局支撑模块
├── models/                 # 模型目录（自动创建）
├── logs/                   # 日志目录（自动创建）
└── training_data/          # 训练数据目录（自动创建）
```

详细设计文档见 [design/](design/README.md)

## 技术栈

- **图形界面**: PyQt5
- **计算机视觉**: OpenCV、YOLOv8 (Ultralytics)
- **深度学习**: PyTorch (CPU版本)
- **数据存储**: SQLite (SQLAlchemy ORM)
- **任务调度**: 自定义任务调度器
- **屏幕操作**: mss (屏幕截图)、pyautogui (自动点击)

## 开发者

Fisherman Team

## 许可证

[您的许可证]

## 更新日志

### v1.0.0
- 初始版本发布
- 完整的训练和识别功能
- 图形用户界面
- 数据库支持
