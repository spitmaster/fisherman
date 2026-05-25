# 钓鱼独立 exe 构建与分发

> M6 实现的 standalone 钓鱼包,对应 [SPEC §2.15](./SPEC.md#215-钓鱼独立-exe-打包standalonefishing--已完成m6)。
> 本文档分两部分:**开发者构建** + **最终用户使用**。

---

## 一、开发者:构建 exe

### 前置

- Windows 10/11 64 位
- 已安装 [uv](https://docs.astral.sh/uv/) 并跑过 `uv sync`
- 项目根存在 `good_models/wow_fish.pt`(随 git 仓库分发)

### 一键构建

双击 [build_standalone.bat](../build_standalone.bat),或在项目根:

```bat
build_standalone.bat
```

脚本会依次:

1. `uv sync` 同步依赖
2. 清理 `build/` 和 `dist/fisherman_fishing/`
3. `uv run pyinstaller fishing_standalone.spec --noconfirm`(1-3 分钟)
4. 检查产物 `dist/fisherman_fishing/fisherman_fishing.exe` 和 `good_models/wow_fish.pt`

### 产物布局

```text
dist/fisherman_fishing/
├── fisherman_fishing.exe       # 启动入口
├── good_models/
│   └── wow_fish.pt             # 内置 YOLO 模型
├── _internal/                  # PyInstaller 内部依赖(几百个 dll/pyd)
│   ├── torch/
│   ├── ultralytics/
│   ├── PyQt5/
│   ├── cv2/
│   └── ...
└── logs/                       # 运行时自动生成
    └── fisherman_fishing.log
```

整体大小通常 **600-900 MB**(PyTorch CPU + Ultralytics + Qt + OpenCV 各占大头)。

### 分发流程

1. 把整个 `dist/fisherman_fishing/` 文件夹用 zip / 7z 压缩(压缩后 ~300-500 MB)
2. 发给最终用户(网盘 / U 盘 / 群文件等)
3. 用户解压到任意目录 → 双击 `fisherman_fishing.exe`

### 排错

| 现象 | 排查 |
|---|---|
| `uv sync` 失败 | 检查 [uv.lock](../uv.lock) 完整;有时需要 `uv lock --upgrade-package torch` |
| PyInstaller 报「无法 import torch」 | 检查 `fishing_standalone.spec` 的 `hiddenimports` 是否包含 `torch` 子模块 |
| dist 启动后报「找不到 wow_fish.pt」 | 检查 spec 的 `datas` 是否含 `good_models/wow_fish.pt`;`fishing/constants.py:resolve_bundled_model_path` 会同时搜索 `_internal/good_models/` 和 exe 同目录 `good_models/` |
| dist 体积过大 (> 1.5 GB) | 检查 `excludes` 是否漏排某些包(常见:`matplotlib` / `pandas` / `tkinter`);torch 仓库的 `.lib` 静态库(`dnnl.lib` ~606 MB)也要在 `_torch_datas_raw` 里过滤掉 |
| 启动崩溃无日志 | 临时把 spec 里 `console=True`(默认已开),双击启动看黑窗口报错;同时看 `logs/faulthandler.log` 有没有 fatal 异常 traceback |

### M6 构建期踩过的关键坑(2026-05-25 实录)

构建期遇到 4 类坑,合计耗了 5-6 次重构建。新人重做时可避雷。

#### 坑 1 — `gui` 模块找不到(ModuleNotFoundError)

- 现象:dist 秒退,日志 `No module named 'gui'`
- 根因:`fishing_standalone.spec` 的 `pathex=[]` 为空,PyInstaller 不知道项目根
- 修复:`pathex=[SPECPATH]` 让 PyInstaller 把项目根加进搜索

#### 坑 2 — `gui/tabs/__init__.py` 链式 ImportError

- 现象:PyInstaller excludes 了大多数 tab,但 `gui/tabs/__init__.py` 还在顶部
  `from .training_tab import TrainingTab` → 整个 `gui.tabs` 包被剔除
- 修复:`__init__.py` 改用 `_try_import("name", "Class")` 容错;完整 app 模式
  不会触发(没 ImportError),standalone 模式跳过缺失的 tab,只留 FishingTab

#### 坑 3 — `torch._C` 加载 0xc06d007e Windows fatal exception(最致命)

- 现象:Python `except` 抓不到,日志只到 `import torch` 这一步,
  `faulthandler.log` 显示 `Windows fatal exception: code 0xc06d007e`
  在 `torch/__init__.py line 237 from torch._C import *` 触发
- 误判路径(浪费 3 次构建):
  - 以为是 `os.add_dll_directory` 没设 → 加上 → 还是不行
  - 以为是 ctypes 没预加载 `torch/lib/*.dll` → 加上 → 还是不行
  - 以为是 _C.pyd delay-load → 用 PE 解析 _C.pyd 发现**没有** delay-load 表
- 真根因:**Conda 装的 PyTorch 用 Intel MKL**(`mkl_rt.1.dll` 等),这些 DLL
  在 `.venv/Library/bin/`(不在 `site-packages/torch/lib/`),而 PyInstaller
  的 `hook-torch.py` 试图收集 MKL DLL 时调用 `from PyInstaller.utils.hooks
  import conda_support` —— 新版 PyInstaller 已经移除了 `conda_support`,
  hook 内部 ImportError 但只 WARNING 不阻塞 → **所有 MKL DLL 一个都没打入**
- 修复:spec 里手动从 `.venv/Library/bin/` 收集 mkl 白名单 DLL 放到 `torch/lib/`
- 诊断窍门:用 `venv 的 Python + dist 的 torch 路径`跑 `import torch` 能否
  成功,如果能成功(等于 dist 文件齐全)而 PyInstaller bootloader 跑失败,
  那就一定是**进程 DLL 搜索环境**差异 / **DLL 缺失**问题

#### 坑 4 — MKL 全收却引入新错误(WinError 126 ModuleNotFound)

- 现象:把 `venv/Library/bin/mkl_*.dll` 全部打入后,torch `__init__` 报
  `Error loading mkl_blacs_intelmpi_ilp64.1.dll or one of its dependencies`
- 根因:`mkl_blacs_*.dll`(MPI 通信)和 `mkl_pgi_thread.1.dll`(PGI 编译器
  线程)自己依赖 MPI / PGI runtime,dist 里没有这些 runtime;
  `torch/__init__.py` line 122-141 遍历 `torch/lib/*.dll` 一个一个 LoadLibrary,
  遇到这些就连锁失败
- 修复:**MKL 白名单**只收 PyTorch CPU 推理实际用的几个:
  `mkl_rt / mkl_core / mkl_intel_thread / mkl_sequential / mkl_avx2 /
  mkl_avx512 / mkl_def / mkl_vml_avx2 / mkl_vml_avx512 / mkl_vml_def /
  libiomp5md / libiompstubs5md`,不带 `mkl_blacs_*` / `mkl_pgi_thread` /
  `mkl_tbb_thread` / `mkl_scalapack_*`

---

## 二、最终用户:使用钓鱼

### 第一次启动

1. 把发来的 `fisherman_fishing.zip` 解压到一个**没有中文 / 空格**的英文目录,例如:
   - ✅ `D:\game\fishing\`
   - ❌ `D:\游戏\钓鱼工具\`(可能有部分库读路径出问题)
2. 双击 `fisherman_fishing.exe`
3. **Windows Defender / 杀软**可能弹窗提示「不安全」—— 这是 PyInstaller 打的 exe 常见误报:
   - Defender:点「更多信息」→「仍要运行」
   - 360 / 火绒:把整个 `fisherman_fishing` 文件夹加入白名单
4. 看到 GUI:识别参数 + 钓鱼循环参数 + 实时预览 三块

### 单屏使用流程

1. 进入 WoW,走到钓鱼水域,把鼠标定位好
2. 在程序里直接按 **F11** → 程序进入「第 1 轮 — 预备等待」状态
3. 等程序自动跑流程:抛竿 → 等浮漂 → 检测下沉 → 右键拾取
4. 想停的时候按 **F12**,程序会在当前步骤结束后干净退出

### 双屏使用(游戏在副屏)

⚠ **必须**先点「选择区域」按钮,框选游戏窗口的可见区域(浮漂能露出来的范围),
然后再按 F11。**默认「全屏」只截主显示器**,副屏游戏抓不到画面。

### 参数调整建议

默认值是 [SPEC §2.14](./SPEC.md#214-钓鱼标签页fishingtab--已完成m5) 用户实测最优:

| 步骤 | 默认 | 何时调 |
|---|---|---|
| 0 预备等待 | 5.0 s | 节奏太快或想留时间手动干预 → 加大 |
| 2 抛竿键 | `-` | 改成你绑定的「钓鱼」动作技能位键 |
| 3a 抛竿后等浮漂 | 3.0 s | 浮漂飞得远(高纬度水域)→ 加大 |
| 3b 位移检测超时 | 17.0 s | 出现连续超时(进度条跑满) → 适当加大 |
| 4a 触发后等待 | 1.0 s | 鱼咬钩后等待时长,通常不动 |

### 热键冲突

- **F11 / F12** 默认占用整个系统,只要程序在跑就拦截。WoW 内若把 F11/F12 绑定了其他动作,
  钓鱼期间会被本程序优先响应。可在 UI 上改成其他单键(如 `f6` / `f7` / `numpad1`)。
- **不能与 F8 / F9 相同** —— 这是图库 Tab 的保留键(虽然 standalone 不带图库,
  但保留校验避免迁回完整版时冲突)。
- **不支持组合键**(如 `ctrl+f11`),只接受单键。

### 常见问题

| 现象 | 解决 |
|---|---|
| 启动黑窗口闪一下就消失 | 在终端里跑 `fisherman_fishing.exe`,看报错 / 看 `logs/fisherman_fishing.log` |
| 启动后 GUI 是英文 / 乱码 | 确认解压目录路径无中文 / 空格 |
| 钓鱼时鼠标跑去屏幕角落 | 双屏没选区域,默认全屏只截主屏;点「选择区域」框选游戏窗口 |
| 浮漂检测不到 | 在 UI 上调低「置信度阈值」(默认 0.70 → 0.50) |
| 一直超时不触发 | (1) 调低置信度 (2) 在「位移测试 Tab」(完整版)实测浮漂位移参数 |
| 杀软删了 exe | 加白名单后重新解压;不建议关闭杀软全局保护 |

### 日志

挂机异常时,日志在 `<exe同目录>\logs\fisherman_fishing.log`,可压缩发给开发者排错。

---

## 三、设计参考

- **为什么 onedir 不是 onefile**:onefile 启动时把内部 dll/pyd 解压到 `%TEMP%\_MEIxxxx\`
  再 fork 进程加载,带 PyTorch + Qt + OpenCV 的程序冷启动 **10-15 秒**,临时目录还
  占 ~600 MB 空间;onedir 直接 dlopen,~2-3 秒搞定。onefile 的自解压行为也长得太像
  恶意软件,杀软误报率更高。详见 [SPEC §2.15 S3](./SPEC.md#215-钓鱼独立-exe-打包standalonefishing--已完成m6)。

- **为什么模型固定不可外挂**:M6 scope 简化,目标是把钓鱼功能"封死"给非技术朋友用。
  允许外挂模型需要文件选择对话框 + 自定义路径校验 + 模型兼容性提示,徒增复杂度。
  开发者可改 `fishing/constants.py` 的 `BUNDLED_MODEL_FILENAME` 自定义打包模型。

- **为什么 STANDALONE_ENV_FLAG 走环境变量**:让同一份 `gui/tabs/fishing_tab.py` 代码
  在完整 app 和 standalone 包内都能用,不复制代码。`fishing_main.py` 启动时先设 env,
  FishingTab `_load_models` 自动走极简路径。
