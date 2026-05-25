"""标签页模块

包含各个功能标签页的实现。

容错 import:standalone 钓鱼独立 exe(M6 SPEC §2.15)会通过 PyInstaller
excludes 排除大部分 tab,只保留 FishingTab。本文件 import 失败时,把对应
名字设为 None,不影响其他 tab。完整 app(main.py)模式所有 import 都会
成功,行为与未加容错前一致。
"""

import logging as _logging

_logger = _logging.getLogger(__name__)


def _try_import(module_name: str, class_name: str):
    """单个 tab import 失败时返回 None(standalone 模式排除时正常),
    并在 logger 留一行 debug。完整 app 模式所有 tab 必须成功 import。
    """
    try:
        mod = __import__(f"gui.tabs.{module_name}", fromlist=[class_name])
        return getattr(mod, class_name)
    except ImportError as e:
        _logger.debug("跳过 tab %s (standalone excluded?): %s", module_name, e)
        return None


TrainingTab = _try_import("training_tab", "TrainingTab")
TrainingResultTab = _try_import("training_result_tab", "TrainingResultTab")
RecognitionTab = _try_import("recognition_tab", "RecognitionTab")
RecognitionTestTab = _try_import("recognition_test_tab", "RecognitionTestTab")
RecognitionActionTab = _try_import("recognition_action_tab", "RecognitionActionTab")
DisplacementTestTab = _try_import("displacement_test_tab", "DisplacementTestTab")
DisplacementActionTab = _try_import("displacement_action_tab", "DisplacementActionTab")
ImageLibraryTab = _try_import("image_library_tab", "ImageLibraryTab")
FishingTab = _try_import("fishing_tab", "FishingTab")
SettingsTab = _try_import("settings_tab", "SettingsTab")

__all__ = [
    "TrainingTab",
    "TrainingResultTab",
    "RecognitionTab",
    "RecognitionTestTab",
    "RecognitionActionTab",
    "DisplacementTestTab",
    "DisplacementActionTab",
    "ImageLibraryTab",
    "FishingTab",
    "SettingsTab",
]
