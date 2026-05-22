"""
标签页模块

包含各个功能标签页的实现
"""

from .training_tab import TrainingTab
from .training_result_tab import TrainingResultTab
from .recognition_tab import RecognitionTab
from .recognition_test_tab import RecognitionTestTab
from .recognition_action_tab import RecognitionActionTab
from .displacement_test_tab import DisplacementTestTab
from .displacement_action_tab import DisplacementActionTab
from .settings_tab import SettingsTab

__all__ = [
    'TrainingTab',
    'TrainingResultTab',
    'RecognitionTab',
    'RecognitionTestTab',
    'RecognitionActionTab',
    'DisplacementTestTab',
    'DisplacementActionTab',
    'SettingsTab',
]
