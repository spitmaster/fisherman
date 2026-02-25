# Fisherman 视觉自动化程序

基于计算机视觉的自动化程序，主要用于识别和操作屏幕上的特定物体。

## 快速开始

### 1. 安装Python

确保已安装 Python 3.8 或更高版本：
- 下载地址: https://www.python.org/downloads/
- **重要**: 安装时请勾选 "Add Python to PATH"

### 2. 克隆代码库

```bash
git clone <your-repository-url>
cd fisherman
```

### 3. 运行程序

**Windows用户**（推荐）：
双击运行 `启动_Fisherman.bat`

启动器会自动：
- ✅ 检查Python环境
- ✅ 检测并安装缺失的依赖（首次运行3-5分钟）
- ✅ 检查系统组件
- ✅ 启动Fisherman程序

**手动运行**：
```bash
# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 运行程序
python main.py
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

完整依赖列表见 [requirements.txt](requirements.txt)

## 故障排除

### 提示"未检测到Python"
- 安装Python 3.8+：https://www.python.org/downloads/
- 安装时务必勾选 "Add Python to PATH"
- 安装后重启命令行窗口

### 依赖安装失败
```bash
# 手动安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 提示"PyTorch库不可用"
- 安装 Visual C++ Redistributable for Visual Studio 2015-2022
- 下载地址: https://aka.ms/vs/17/release/vc_redist.x64.exe

### 其他问题
- 查看日志文件: `logs/fisherman.log`
- 确保网络连接正常（首次运行需要下载依赖）
- 尝试重新安装依赖: `pip install -r requirements.txt --force-reinstall`

## 项目结构

```
fisherman/
├── main.py                 # 程序主入口
├── 启动_Fisherman.bat       # Windows启动脚本
├── requirements.txt        # 依赖清单
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

详细项目结构说明见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

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
