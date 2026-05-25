#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钓鱼独立 exe 入口(M6)— 详见 docs/SPEC.md §2.15。

仅挂载 FishingTab 的极简 MainWindow:
- 无菜单栏 / 无日志按钮 / 无其他 Tab
- 模型固定从 `good_models/wow_fish.pt` 加载(通过 STANDALONE 模式标志)
- 启动前预设 `FISHING_STANDALONE=1` 环境变量,FishingTab 据此走极简路径

打包入口由 fishing_standalone.spec 引用本文件。
"""

from __future__ import annotations

import logging
import os
import sys


def _preload_torch_runtime(logger: logging.Logger) -> None:
    """在 import torch *之前*,把 PyTorch + MKL 的运行时 DLL 全部用 ctypes 装入进程。

    背景(M6 standalone 实测踩坑,见 docs/standalone-build.md):
    PyInstaller onedir 模式打包 Conda PyTorch 时,默认 hook-torch.py 的
    `_collect_mkl_dlls` 因 `conda_support` 模块缺失而失败(只 WARNING 不阻塞),
    导致 `mkl_*.dll` 一个都没打进 dist。`torch._C.pyd` 加载触发 delay-load 找不
    到 mkl_rt.1.dll → 抛 STATUS_DELAY_LOAD_FAILURE (0xc06d007e),OS 直接终止
    进程,Python except 抓不到。

    `os.add_dll_directory` 只对 ctypes / `LoadLibraryExW(SEARCH_USER_DIRS)` 有
    效,**不影响 PE delay-load 解析**。唯一可靠方案:在 import torch 之前用
    ctypes 把 torch/lib/*.dll 全部 LoadLibrary 进进程,这样 _C.pyd 触发 delay-
    load 时直接命中**已加载的 DLL**(Windows 同名 DLL 优先复用进程内已加载的),
    不再走磁盘搜索。
    """
    if sys.platform != "win32":
        return

    import ctypes
    import glob

    if getattr(sys, "frozen", False):
        torch_lib_dir = os.path.join(os.path.dirname(sys.executable), "_internal", "torch", "lib")
    else:
        torch_lib_dir = os.path.join(os.path.dirname(__file__), ".venv", "Lib", "site-packages", "torch", "lib")

    if not os.path.isdir(torch_lib_dir):
        logger.warning("torch/lib 目录不存在,跳过预加载: %s", torch_lib_dir)
        return

    # 三重保险:add_dll_directory(import 走) + PATH(legacy delay-load 走)+
    # 显式 LoadLibrary(让 DLL 进进程,后续解析直接命中)
    os.add_dll_directory(torch_lib_dir)
    os.environ["PATH"] = torch_lib_dir + os.pathsep + os.environ.get("PATH", "")

    # 按依赖顺序预加载:foundation DLLs(libiomp / c10)先于 torch_cpu / torch_python;
    # MKL 也在剩余扫描里被加载
    priority = ["libiomp5md.dll", "uv.dll", "asmjit.dll", "c10.dll",
                "fbgemm.dll", "torch_cpu.dll", "torch_python.dll"]
    loaded = set()
    for name in priority:
        p = os.path.join(torch_lib_dir, name)
        if os.path.isfile(p):
            try:
                ctypes.CDLL(p)
                loaded.add(name)
            except OSError as e:
                logger.warning("预加载 %s 失败: %s", name, e)
    for dll in glob.glob(os.path.join(torch_lib_dir, "*.dll")):
        name = os.path.basename(dll)
        if name in loaded:
            continue
        try:
            ctypes.CDLL(dll)
            loaded.add(name)
        except OSError as e:
            logger.warning("预加载 %s 失败: %s", name, e)
    logger.info("预加载了 %d 个 torch / MKL DLL", len(loaded))


def _setup_logging() -> None:
    """日志写入 exe 同目录的 logs/fisherman_fishing.log,与正式版分离。"""
    # 打包模式下 sys.frozen=True,以 exe 所在目录为根;否则用项目根
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    log_dir = os.path.join(base, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "fisherman_fishing.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    # 必须在 import FishingTab 之前设环境变量,
    # 因为 FishingTab._load_models 在构造时被 showEvent 触发就会读这个标志
    os.environ["FISHING_STANDALONE"] = "1"

    _setup_logging()

    # 把 fatal 错误(段错误 / DLL 加载崩溃 / Python C 层异常)的 traceback
    # 转储到日志文件,否则 OS 杀进程时 Python except 抓不到,日志无线索。
    # 用户排错时把 logs/ 整个目录发回开发者即可。
    import faulthandler
    if getattr(sys, "frozen", False):
        fault_log_dir = os.path.join(os.path.dirname(sys.executable), "logs")
    else:
        fault_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(fault_log_dir, exist_ok=True)
    fault_log = open(os.path.join(fault_log_dir, "faulthandler.log"), "w", encoding="utf-8")
    faulthandler.enable(file=fault_log, all_threads=True)
    logger = logging.getLogger("fishing_main")
    logger.info("Fisherman 钓鱼独立版启动 (standalone mode)")

    _preload_torch_runtime(logger)

    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow, QStatusBar, QVBoxLayout, QWidget
        import torch  # noqa: F401
        import ultralytics  # noqa: F401
        import cv2  # noqa: F401
        import mss  # noqa: F401
        import keyboard  # noqa: F401
        import pyautogui  # noqa: F401
        from gui.tabs.fishing_tab import FishingTab
    except Exception as e:
        logger.error("import 失败: %s", e, exc_info=True)
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("Fisherman 钓鱼")

    window = QMainWindow()
    window.setWindowTitle("Fisherman 钓鱼 — 独立版")
    window.setGeometry(100, 100, 1200, 800)
    window.setMinimumSize(900, 650)

    # 极简中央部件:只挂 FishingTab,无额外 Tab / 菜单 / 日志按钮
    central = QWidget()
    layout = QVBoxLayout(central)
    layout.setContentsMargins(0, 0, 0, 0)
    fishing_tab = FishingTab()
    layout.addWidget(fishing_tab)
    window.setCentralWidget(central)

    # 状态栏:固定一行提示,告诉用户热键
    status = QStatusBar()
    status.showMessage("准备就绪 — F11 开始 / F12 停止;副屏游戏请用「选择区域」")
    window.setStatusBar(status)

    # 关闭主窗口时优雅停 FishingTab(注销热键 + 停循环线程)
    original_close = window.closeEvent

    def _close(event):
        logger.info("主窗口关闭,清理 FishingTab")
        try:
            fishing_tab.close()
        except Exception as e:
            logger.warning("FishingTab 清理出错: %s", e)
        original_close(event)

    window.closeEvent = _close
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
