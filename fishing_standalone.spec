# -*- mode: python ; coding: utf-8 -*-
"""
Fisherman 钓鱼独立 exe 打包配置(M6 — SPEC §2.15)。

入口:fishing_main.py(极简 MainWindow,仅挂 FishingTab,
环境变量 FISHING_STANDALONE=1 锁死模型为 good_models/wow_fish.pt)。

模式:onedir(冷启动 ~2-3s,杀软误报少;详见 docs/standalone-build.md)
产物:dist/fisherman_fishing/  整个文件夹给最终用户(zip 分发)
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None


# ----------------------------------------------------------------------------
# 依赖收集
# ----------------------------------------------------------------------------

# PyTorch CPU 运行时(.dll / .so 等),不带 .py 源(走 hidden imports)。
# 注意:`collect_data_files` 会把 lib 下所有非 .py 文件都抓进来,包括 .lib 静态
# 链接库(dnnl.lib 一个就 606 MB,libproto*.lib 共 ~80 MB)。.lib 仅编译时
# 需要,运行时无用,必须过滤掉,否则 dist 体积爆炸 ~700 MB。
_torch_datas_raw = collect_data_files("torch", include_py_files=False, subdir="lib")
torch_datas = [
    (src, dest) for src, dest in _torch_datas_raw
    if not src.lower().endswith((".lib", ".a"))
]

import os as _os_for_spec

# 关键修复 2:Conda 装的 PyTorch 把 MKL DLL 放在 venv/Library/bin/,
# hook-torch.py 的 _collect_mkl_dlls 在新版 PyInstaller 上因 conda_support
# 缺失而失败(只 WARNING 不阻塞),导致 mkl_*.dll 一个都没打进 dist。
# 运行时 torch_cpu.dll delay-load 找不到 mkl_rt.1.dll → 0xc06d007e。
#
# 注意:**只带 PyTorch CPU 推理实际用到的 MKL DLL**,不要全收!
# 全收会把 mkl_blacs_*.dll(MPI 通信)和 mkl_pgi_thread.1.dll(PGI 编译器)
# 等带进来,这些 DLL 自己依赖 MPI runtime / PGI runtime,dist 里没有,
# torch/__init__.py line 122-141 遍历 torch/lib/*.dll 预加载时连锁失败 →
# WinError 126.
import sys as _sys_for_spec

# MKL 文件名前缀白名单(精确到运行时必须的):
# - mkl_rt:主入口(single dynamic library 模式)
# - mkl_core:核心
# - mkl_intel_thread:Intel OpenMP 线程后端(默认)
# - mkl_sequential:单线程 fallback
# - mkl_avx2 / mkl_avx512:现代 CPU BLAS(2013+ 的 CPU 都有 AVX2)
# - mkl_def:fallback 通用版本(老 CPU 兜底)
# - mkl_vml_avx2 / vml_avx512 / vml_def:矢量数学库对应版本
# - libiomp5md / libiompstubs5md:Intel OpenMP runtime
# 不带:mkl_blacs_*(MPI)/ mkl_pgi_thread / mkl_tbb_thread / mkl_scalapack_*
# 不带老 CPU:mkl_avx(老 AVX1) / mkl_mc / mkl_mc3(SSE 系列)/ mkl_vml_mc*
_MKL_ALLOWED_PREFIXES = (
    "mkl_rt.", "mkl_core.", "mkl_intel_thread.", "mkl_sequential.",
    "mkl_avx2.", "mkl_avx512.", "mkl_def.",
    "mkl_vml_avx2.", "mkl_vml_avx512.", "mkl_vml_def.",
    "libiomp5md.", "libiompstubs5md.",
)

_venv_libbin = _os_for_spec.path.join(
    _os_for_spec.path.dirname(_os_for_spec.path.dirname(_sys_for_spec.executable)),
    "Library", "bin"
)
_mkl_dlls = []
if _os_for_spec.path.isdir(_venv_libbin):
    for _f in _os_for_spec.listdir(_venv_libbin):
        if not _f.lower().endswith(".dll"):
            continue
        _flow = _f.lower()
        if not any(_flow.startswith(_p) for _p in _MKL_ALLOWED_PREFIXES):
            continue
        _src = _os_for_spec.path.join(_venv_libbin, _f)
        # 放到 torch/lib/(与 torch_cpu.dll 同目录,delay-load 直接命中)
        _mkl_dlls.append((_src, "torch/lib"))

# PyTorch 全部子模块。Ultralytics 通过反射调 torch.nn / torch.cuda,
# 不全收集会运行时 ImportError
torch_imports = collect_submodules("torch")

# Ultralytics 用 torchvision 的 NMS / ops
torchvision_imports = collect_submodules("torchvision")

# ----------------------------------------------------------------------------
# datas:把内置精选模型打进 dist
# ----------------------------------------------------------------------------

datas = [
    *torch_datas,
    *_mkl_dlls,                   # MKL DLLs(hook-torch 漏收集,手动补)
    # SPEC §2.15 F2.15.5:wow_fish.pt → <dist>/good_models/wow_fish.pt
    ("good_models/wow_fish.pt", "good_models"),
]

# ----------------------------------------------------------------------------
# hidden imports:PyInstaller 静态分析抓不到的反射 / 动态导入
# ----------------------------------------------------------------------------

hiddenimports = [
    *torch_imports,
    *torchvision_imports,
    "ultralytics",
    "ultralytics.models",
    "ultralytics.models.yolo",
    "ultralytics.models.yolo.detect",
    "ultralytics.models.yolo.classify",
    "ultralytics.models.yolo.segment",
    "ultralytics.models.yolo.pose",
    "ultralytics.utils",
    "ultralytics.utils.plotting",
    "ultralytics.utils.callbacks",
    "ultralytics.utils.ops",
    "cv2",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt5.sip",
    "mss",
    "pyautogui",
    "keyboard",
    # M7 后台钓鱼(SPEC §2.15 F2.15.9):窗口捕获后端 + 窗口内框选对话框。
    # 二者经 FishingTab / screen_recognition 顶层 import 本会被静态分析带入,
    # 这里显式声明做保险,并确保不被上方 excludes 的 recognition/gui 通配误伤。
    "recognition.window_io",
    "gui.window_region_selector",
]

# ----------------------------------------------------------------------------
# excludes:不进 standalone 的模块,显著减小体积
# ----------------------------------------------------------------------------

excludes = [
    # 训练管线 - standalone 钓鱼不训练
    "training",
    "training.annotation",
    "training.task",
    "training.training",
    "training.training_manager",
    "training.annotation_tool",
    "training_result",
    "training_result.model_manager",
    # 图库 - standalone 不需要采集图片
    "image_library",
    "image_library.library_manager",
    # DB / 调度器 - standalone 纯内存,无后台任务
    "global_support.database",
    "global_support.task_scheduler",
    # 其他无关 Tab(FishingTab 不 import 它们,这里显式排除避免 PyInstaller
    # 通过 gui.tabs.__init__ 顺手把它们拖入)
    "gui.tabs.training_tab",
    "gui.tabs.training_result_tab",
    "gui.tabs.recognition_tab",
    "gui.tabs.recognition_test_tab",
    "gui.tabs.recognition_action_tab",
    "gui.tabs.displacement_test_tab",
    "gui.tabs.displacement_action_tab",
    "gui.tabs.image_library_tab",
    "gui.tabs.settings_tab",
    "gui.main_window",
    "gui.annotation_window",
    "gui.dataset_detail_dialog",
    "gui.log_viewer_dialog",
    "gui.detail_tabs",
    # SQLAlchemy - 不连 DB
    "sqlalchemy",
    "sqlalchemy.orm",
    "sqlalchemy.ext",
    # 测试 / 文档相关
    "pytest",
    "matplotlib",
    "pandas",
    "tkinter",
    # Polars:ultralytics 某些数据处理路径会拖入,钓鱼推理用不到,
    # 单独占 ~174 MB(_polars_runtime_*)
    "polars",
]

# ----------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------

a = Analysis(
    ["fishing_main.py"],
    # SPECPATH 是 PyInstaller 注入的 spec 所在目录变量,即项目根。
    # 必须显式加进来,否则 fishing_main.py 内 `from gui.tabs.fishing_tab import FishingTab`
    # 这类本地包导入(且是函数内"delayed"导入)PyInstaller 找不到 `gui` 包根,
    # 整个项目 Python 代码都不会被打入,运行时秒退 ModuleNotFoundError。
    pathex=[SPECPATH],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="fisherman_fishing",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    # console=True 保留:钓鱼后台运行时多看一个黑窗口虽不优雅,但便于早期
    # 用户反馈崩溃日志。后续稳定后可改 False。
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 图标(暂未提供 .ico,PyInstaller 用默认蓝图标;M6 SPEC §2.15 S5)
    # icon="assets/fisherman.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="fisherman_fishing",
)
