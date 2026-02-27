#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别标签页

提供识别任务管理功能：启动、停止识别任务，显示统计信息
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QMessageBox
)

from training_result.model_manager import model_manager
from recognition.screen_recognition import recognition_manager

logger = logging.getLogger(__name__)


class RecognitionTab(QWidget):
    """识别标签页"""

    def __init__(self, parent=None):
        """初始化识别标签页"""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 识别任务管理区域
        task_group = QGroupBox("识别任务管理")
        task_layout = QVBoxLayout(task_group)

        # 操作按钮
        self.btn_start_recognition = QPushButton("开始识别")
        self.btn_start_recognition.clicked.connect(self.start_recognition)

        self.btn_stop_recognition = QPushButton("停止识别")
        self.btn_stop_recognition.clicked.connect(self.stop_recognition)
        self.btn_stop_recognition.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_start_recognition)
        button_layout.addWidget(self.btn_stop_recognition)

        task_layout.addLayout(button_layout)

        # 识别参数设置
        params_group = QGroupBox("识别参数")
        params_layout = QVBoxLayout(params_group)

        # 置信度阈值
        self.confidence_label = QLabel("置信度阈值: 0.7")
        params_layout.addWidget(self.confidence_label)

        # 点击冷却时间
        self.cooldown_label = QLabel("点击冷却时间: 5秒")
        params_layout.addWidget(self.cooldown_label)

        task_layout.addWidget(params_group)

        # 统计信息
        stats_group = QGroupBox("识别统计")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel("识别次数: 0 | 点击次数: 0 | FPS: 0")
        stats_layout.addWidget(self.stats_label)

        task_layout.addWidget(stats_group)
        layout.addWidget(task_group)

    def start_recognition(self):
        """开始识别任务"""
        logger.info("开始识别任务")

        try:
            model_info = model_manager.get_default_model()

            if model_info:
                # 启动识别任务
                recognition_manager.start_recognition_task(
                    model_info["path"],
                    confidence_threshold=0.7,
                    click_cooldown=5
                )

                # 更新按钮状态
                self.btn_start_recognition.setEnabled(False)
                self.btn_stop_recognition.setEnabled(True)

                QMessageBox.information(self, "成功", f"识别任务已启动: {model_info['filename']}")
            else:
                QMessageBox.warning(self, "警告", "未找到可用的模型")

        except Exception as e:
            logger.error(f"启动识别任务出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动识别任务出错: {str(e)}")

    def stop_recognition(self):
        """停止识别任务"""
        logger.info("停止识别任务")

        try:
            recognition_manager.stop_recognition_task()

            # 更新按钮状态
            self.btn_start_recognition.setEnabled(True)
            self.btn_stop_recognition.setEnabled(False)

            QMessageBox.information(self, "成功", "识别任务已停止")

        except Exception as e:
            logger.error(f"停止识别任务出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"停止识别任务出错: {str(e)}")

    def update_stats(self):
        """更新识别统计信息"""
        stats = recognition_manager.get_statistics()

        if stats["is_running"]:
            self.stats_label.setText(
                f"识别次数: {stats['recognitions_count']} | "
                f"点击次数: {stats['clicks_count']} | "
                f"FPS: {stats['fps']:.1f}"
            )
        else:
            self.stats_label.setText("识别任务未运行")
