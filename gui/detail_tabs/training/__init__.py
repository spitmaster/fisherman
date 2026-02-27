#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练子模块

提供训练相关的UI组件和控制器。
"""

from .training_controller import TrainingController
from .training_params_widget import TrainingParamsWidget
from .training_control_panel import TrainingControlPanel
from .training_log_widget import TrainingLogWidget

__all__ = [
    'TrainingController',
    'TrainingParamsWidget',
    'TrainingControlPanel',
    'TrainingLogWidget'
]
