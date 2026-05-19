# 08 技术栈与环境

## 1. 运行环境

| 项 | 要求 |
|----|------|
| 操作系统 | Windows 10/11 64 位（推荐）；Linux/macOS 未正式测试 |
| Python | 3.8 及以上（由 uv 自动管理，无需手动安装） |
| 包管理 | [uv](https://docs.astral.sh/uv/)（Astral 出品，替代 pip + venv + pyenv） |
| 内存 | ≥ 4 GB |
| 磁盘 | ≥ 2 GB |
| 其他 | Visual C++ Redistributable 2015-2022（PyTorch 运行时需要） |

## 2. 依赖清单

来源：`pyproject.toml`（`[project].dependencies`）；锁文件：`uv.lock`（由 uv 自动生成）。

| 依赖 | 版本约束 | 用途 |
|------|----------|------|
| torch | ==2.3.0 | 深度学习框架，CPU 版本（便于 PyInstaller 打包） |
| torchvision | ==0.18.0 | 配套 vision 工具集 |
| ultralytics | >=8.0.0 | YOLOv8 推理与训练 |
| opencv-python-headless | >=4.8.0 | 图像处理（无 GUI 版，避免与 Qt 冲突） |
| PyQt5 | >=5.15.0 | 图形界面 |
| mss | >=9.0.0 | 高性能屏幕截图 |
| pyautogui | >=0.9.50 | 模拟鼠标/键盘 |
| SQLAlchemy | >=2.0.0 | ORM |
| Pillow | >=10.0.0 | 图像 IO 辅助 |
| numpy | <2 | 张量/数组（YOLO 生态尚未全面兼容 numpy 2） |
| pandas | >=2.0.0 | 训练结果 CSV 解析 |
| scipy | >=1.10.0 | 数值计算（YOLO 依赖） |
| psutil | >=6.0.0 | 进程/资源信息 |

### 默认索引

`pyproject.toml` 中通过 `[[tool.uv.index]]` 声明了清华镜像为默认源：

```toml
[[tool.uv.index]]
name = "tuna"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
```

### 安装/同步

```bash
# 首次使用：创建 .venv 并按 pyproject.toml 安装依赖
uv sync

# 新增依赖
uv add <package-name>

# 移除依赖
uv remove <package-name>

# 升级全部依赖到允许范围内的最新版
uv sync --upgrade
```

## 3. 关键库的角色

| 层 | 使用库 |
|----|--------|
| GUI | PyQt5 |
| 训练 | ultralytics (YOLOv8) + torch |
| 推理 | ultralytics + torch（CPU）|
| 截图 | mss（比 Pillow.ImageGrab 快 3-5 倍）|
| 操作 | pyautogui |
| 图像处理 | OpenCV + Pillow |
| 数据库 | SQLAlchemy + SQLite |
| 包/环境管理 | uv（pyproject.toml + uv.lock）|

## 4. 启动方式

### 4.1 一键启动（推荐）

双击项目根目录 `启动_Fisherman.bat`。脚本会：
1. 检测 `uv` 是否可用
2. 执行 `uv sync` 创建/同步 `.venv`
3. 调用 `uv run python main.py`

### 4.2 手动启动

```bash
uv sync
uv run python main.py
```

### 4.3 在已激活的虚拟环境中运行（可选）

```bash
# 激活 .venv（Windows）
.venv\Scripts\activate

# 激活 .venv（POSIX）
source .venv/bin/activate

python main.py
```

## 5. 日志与诊断

- 运行日志：`logs/fisherman.log`（UTF-8，INFO 级起）
- PyTorch 诊断：
  - `uv run python diagnose_pytorch.py`
  - `uv run python diagnose_pytorch_advanced.py`
- 无 PyTorch 场景：`uv run python test_without_pytorch.py` 验证非依赖 PyTorch 的模块仍可运行

## 6. 常见环境问题

| 症状 | 解决方案 |
|------|----------|
| 提示"未检测到 uv" | PowerShell: `irm https://astral.sh/uv/install.ps1 \| iex`；或 `pip install uv` |
| `uv sync` 失败 | 检查网络；用 `uv sync --verbose` 看详细日志；必要时删除 `.venv` 重建 |
| 提示"PyTorch 库不可用" | 安装 VC++ Redistributable；或运行 `uv run python diagnose_pytorch_advanced.py` |
| YOLO 加载慢 / 首次长时间下载 | 首次识别/训练会下载 `yolov8n.pt` 等权重，可提前放入项目根目录 |
| 想切换 Python 版本 | `uv python install 3.11` 后在 `pyproject.toml` 调整 `requires-python` |

## 7. 打包思路（规划）

- CPU 版 PyTorch 更易被 PyInstaller 打包
- 注意排除 `opencv-python`（带 Qt，会冲突）只用 `opencv-python-headless`
- Ultralytics 的 `runs/` 缓存、`yolov8*.pt` 权重需手动 include
- uv 本身不影响打包；`.venv` 下的 Python 解释器与 site-packages 可供 PyInstaller 使用

## 8. 版本策略

- 第一个公开版本：v1.0.0（见 README 更新日志）
- 依赖锁定：`uv.lock` 应纳入版本控制，保证团队构建一致
- 后续依据 roadmap 推进，见 [09_roadmap.md](09_roadmap.md)
