#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别测试标签页

用于测试识别功能是否正常，识别到目标后显示详细信息：
位置(x,y)、置信度、长、宽、高等信息
"""

import logging
import threading
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QTextEdit, QComboBox,
    QSlider, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt

from training_result.model_manager import model_manager
from recognition.screen_recognition import ScreenRecognition

logger = logging.getLogger(__name__)


class RecognitionTestTab(QWidget):
    """识别测试标签页"""

    def __init__(self, parent=None):
        """初始化识别测试标签页"""
        super().__init__(parent)
        self.recognition = None
        self.monitor_area = None
        self.selecting_area = False
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 识别参数设置区域
        params_group = QGroupBox("识别参数")
        params_layout = QVBoxLayout(params_group)

        # 模型选择
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self._load_models()
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        params_layout.addLayout(model_layout)

        # 置信度阈值
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("置信度阈值:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setMinimum(10)
        self.conf_slider.setMaximum(95)
        self.conf_slider.setValue(70)
        self.conf_slider.valueChanged.connect(self._update_conf_label)
        conf_layout.addWidget(self.conf_slider)
        self.conf_label = QLabel("0.70")
        self.conf_label.setFixedWidth(50)
        conf_layout.addWidget(self.conf_label)
        params_layout.addLayout(conf_layout)

        # 识别区域选择
        area_layout = QHBoxLayout()
        area_layout.addWidget(QLabel("识别区域:"))
        self.btn_select_area = QPushButton("选择区域")
        self.btn_select_area.clicked.connect(self._select_screen_area)
        area_layout.addWidget(self.btn_select_area)
        self.area_label = QLabel("全屏")
        area_layout.addWidget(self.area_label)
        area_layout.addStretch()
        params_layout.addLayout(area_layout)

        layout.addWidget(params_group)

        # 控制按钮
        control_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始测试")
        self.btn_start.clicked.connect(self._start_test)
        self.btn_start.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        control_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止测试")
        self.btn_stop.clicked.connect(self._stop_test)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")
        control_layout.addWidget(self.btn_stop)

        layout.addLayout(control_layout)

        # 识别结果显示区域
        result_group = QGroupBox("识别结果")
        result_layout = QVBoxLayout(result_group)

        # 统计信息
        self.stats_label = QLabel("识别次数: 0 | 目标数: 0 | FPS: 0")
        result_layout.addWidget(self.stats_label)

        # 详细结果
        result_layout.addWidget(QLabel("详细识别信息:"))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(300)
        result_layout.addWidget(self.result_text)

        layout.addWidget(result_group)

        # 初始化定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(500)  # 每500ms更新一次

    def _load_models(self):
        """加载可用模型"""
        try:
            models = model_manager.get_model_list()
            self.model_combo.clear()
            for model in models:
                self.model_combo.addItem(model["filename"], model["path"])
        except Exception as e:
            logger.error(f"加载模型列表失败: {str(e)}")

    def _update_conf_label(self):
        """更新置信度标签"""
        value = self.conf_slider.value() / 100.0
        self.conf_label.setText(f"{value:.2f}")

    def _select_screen_area(self):
        """选择屏幕识别区域"""
        try:
            # TODO: 实现屏幕区域选择功能
            # 这里需要实现一个全屏透明窗口，让用户拖拽选择区域
            # 暂时使用全屏识别
            self.monitor_area = None
            self.area_label.setText("全屏")
            QMessageBox.information(self, "提示", "区域选择功能开发中，当前使用全屏识别")
        except Exception as e:
            logger.error(f"选择区域失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"选择区域失败: {str(e)}")

    def _start_test(self):
        """开始识别测试"""
        logger.info("开始识别测试")

        try:
            # 获取模型路径
            model_index = self.model_combo.currentIndex()
            if model_index < 0:
                QMessageBox.warning(self, "警告", "请先选择模型")
                return

            model_path = self.model_combo.itemData(model_index)
            confidence_threshold = self.conf_slider.value() / 100.0

            # 创建识别实例
            self.recognition = ScreenRecognition(
                model_path=model_path,
                confidence_threshold=confidence_threshold,
                click_cooldown=0  # 测试模式下不需要点击冷却
            )

            # 设置监控区域
            if self.monitor_area:
                x, y, width, height = self.monitor_area
                self.recognition.set_monitor_area(x, y, width, height)
            else:
                self.recognition.use_full_screen_monitor()

            # 设置识别结果回调
            self.recognition.on_recognition_result = self._on_recognition_result

            # 启动识别
            if self.recognition.start_recognition():
                self.btn_start.setEnabled(False)
                self.btn_stop.setEnabled(True)
                self.btn_select_area.setEnabled(False)
                self.model_combo.setEnabled(False)
                self.result_text.clear()
                self.result_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 识别测试已启动")
                self.result_text.append(f"模型: {model_path}")
                self.result_text.append(f"置信度阈值: {confidence_threshold:.2f}")
                self.result_text.append(f"识别区域: {self.area_label.text()}")
                self.result_text.append("-" * 80)
            else:
                QMessageBox.warning(self, "警告", "启动识别测试失败")

        except Exception as e:
            logger.error(f"启动识别测试出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动识别测试出错: {str(e)}")

    def _stop_test(self):
        """停止识别测试"""
        logger.info("停止识别测试")

        try:
            if self.recognition:
                self.recognition.stop_recognition()
                self.recognition = None

            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_select_area.setEnabled(True)
            self.model_combo.setEnabled(True)

            self.result_text.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] 识别测试已停止")

        except Exception as e:
            logger.error(f"停止识别测试出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"停止识别测试出错: {str(e)}")

    def _on_recognition_result(self, detections):
        """识别结果回调"""
        if not detections:
            return

        try:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            self.result_text.append(f"\n[{timestamp}] 检测到 {len(detections)} 个目标:")

            for idx, detection in enumerate(detections, 1):
                bbox = detection["bbox"]
                x1, y1, x2, y2 = bbox
                width = x2 - x1
                height = y2 - y1
                center_x, center_y = detection["center"]
                confidence = detection["confidence"]
                class_name = detection["class_name"]

                result_line = (
                    f"  [{idx}] {class_name}\n"
                    f"      位置: ({x1:.0f}, {y1:.0f}) -> ({x2:.0f}, {y2:.0f})\n"
                    f"      中心: ({center_x:.0f}, {center_y:.0f})\n"
                    f"      尺寸: {width:.0f} x {height:.0f}\n"
                    f"      置信度: {confidence:.2%}"
                )
                self.result_text.append(result_line)

            # 自动滚动到底部
            scrollbar = self.result_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            logger.error(f"处理识别结果出错: {str(e)}")

    def _update_stats(self):
        """更新统计信息"""
        if self.recognition and self.recognition.is_running:
            stats = self.recognition.get_statistics()
            self.stats_label.setText(
                f"识别次数: {stats['recognitions_count']} | "
                f"FPS: {stats['fps']:.1f}"
            )
        else:
            self.stats_label.setText("识别测试未运行")

    def closeEvent(self, event):
        """关闭事件处理"""
        if self.recognition and self.recognition.is_running:
            self.recognition.stop_recognition()
        event.accept()
