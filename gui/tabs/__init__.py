"""
标签页模块

包含各个功能标签页的实现
"""

from .training_tab import TrainingTab
from .training_result_tab import TrainingResultTab
from .recognition_tab import RecognitionTab
from .settings_tab import SettingsTab

__all__ = [
    'TrainingTab',
    'TrainingResultTab',
    'RecognitionTab',
    'SettingsTab'
]
