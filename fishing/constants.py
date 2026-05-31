"""钓鱼模块常量,独立 exe 与完整 app 共用。

抽离原因(M6 SPEC §2.15 F2.15.3):FishingTab 原本 import `ImageLibraryTab`
仅为拿 F8/F9 常量做热键冲突检测,但这会把 image_library 模块及 db_manager /
library_manager 等一并拖入 standalone exe 包,徒增体积且违反"只挂 FishingTab"
的极简入口设计。把这两个常量挪到本文件,FishingTab 改 import 此处,
ImageLibraryTab 也能反过来 import(常量在更底层)。

模型路径解析:standalone 模式下走 resolve_bundled_model_path 函数,定位:
  - PyInstaller 6.x onedir:`<exe同目录>/_internal/good_models/wow_fish.pt`
  - 开发环境:`<项目根>/good_models/wow_fish.pt`
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)


# 图库 Tab 占用的全局热键(M5 实现);FishingTab 不可与之冲突
# 与 gui/tabs/image_library_tab.py 中的 DEFAULT_HOTKEY / FIXED_HOTKEY 保持同步
LIBRARY_HOTKEYS = frozenset({"f9", "f8"})

# 内置精选模型文件名(SPEC §5.5b 精选模型)
BUNDLED_MODEL_FILENAME = "wow_fish.pt"
BUNDLED_MODEL_SUBDIR = "good_models"

# 环境变量名:standalone exe 启动时设为 "1" → FishingTab 切换到极简模式
# (隐藏模型下拉、直接用 BUNDLED_MODEL_PATH 加载、不连 DB)
STANDALONE_ENV_FLAG = "FISHING_STANDALONE"


def is_standalone_mode() -> bool:
    """是否运行在打包后的独立 exe 中。"""
    return os.environ.get(STANDALONE_ENV_FLAG) == "1"


def resolve_bundled_model_path() -> Optional[str]:
    """定位内置 `wow_fish.pt` 的绝对路径。

    搜索顺序:
    1. PyInstaller onedir 模式:`<exe 同目录>/good_models/wow_fish.pt`
       (`sys.executable` 指向 exe 文件本身)
    2. PyInstaller onefile 模式:`<sys._MEIPASS>/good_models/wow_fish.pt`
       (临时解压目录;onefile 才有 _MEIPASS,onedir 不会进入此分支)
    3. 开发环境:项目根 `good_models/wow_fish.pt`
       (本文件位于 `<root>/fishing/constants.py`,上两级即项目根)

    返回首个存在的路径,全部缺失则 None(由调用方决定 fail-loud / fallback)。
    """
    candidates = []

    # PyInstaller 标准:打包后 sys.frozen=True
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        # 1) PyInstaller 6.x onedir 默认把 datas 放进 `_internal/` 子目录
        candidates.append(os.path.join(exe_dir, "_internal", BUNDLED_MODEL_SUBDIR, BUNDLED_MODEL_FILENAME))
        # 2) exe 同目录(若 spec 设了 contents_directory='.' 或用户手动挪了)
        candidates.append(os.path.join(exe_dir, BUNDLED_MODEL_SUBDIR, BUNDLED_MODEL_FILENAME))
        # 3) onefile 模式额外的临时解压根
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, BUNDLED_MODEL_SUBDIR, BUNDLED_MODEL_FILENAME))

    # 开发环境:本文件在 <root>/fishing/constants.py
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(project_root, BUNDLED_MODEL_SUBDIR, BUNDLED_MODEL_FILENAME))

    for path in candidates:
        if os.path.isfile(path):
            return path

    logger.error("找不到内置模型 %s,候选路径:%s", BUNDLED_MODEL_FILENAME, candidates)
    return None
