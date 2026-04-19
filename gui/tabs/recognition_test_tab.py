#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别测试标签页

用于测试识别功能是否正常，识别到目标后显示详细信息：
位置(x,y)、置信度、长、宽、高等信息
测试模式下不会触发鼠标点击。
"""

import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QTextEdit, QComboBox,
    QSlider, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal

from training_result.model_manager import model_manager
from recognition.screen_recognition import ScreenRecognition
from gui.screen_area_selector import ScreenAreaSelector

logger = logging.getLogger(__name__)


class RecognitionTestTab(QWidget):
    """识别测试标签页"""

    # 跨线程信号：识别回调在后台线程执行，通过信号切回主线程更新 UI
    detections_received = pyqtSignal(list)
    error_received = pyqtSignal(str)

    def __init__(self, parent=None):
        """初始化识别测试标签页"""
        super().__init__(parent)
        self.recognition = None
        self.monitor_area = None  # (x, y, width, height)
        self._selector = None
        self._init_ui()
        self._connect_signals()

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
        self.model_combo.setMinimumWidth(360)
        model_layout.addWidget(self.model_combo)

        self.btn_refresh_models = QPushButton("刷新")
        self.btn_refresh_models.clicked.connect(self._load_models)
        model_layout.addWidget(self.btn_refresh_models)
        model_layout.addStretch()
        params_layout.addLayout(model_layout)

        # 置信度阈值
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("置信度阈值:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setMinimum(10)
        self.conf_slider.setMaximum(95)
        self.conf_slider.setValue(70)
        self.conf_slider.valueChanged.connect(self._on_conf_changed)
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

        self.btn_reset_area = QPushButton("重置为全屏")
        self.btn_reset_area.clicked.connect(self._reset_area)
        area_layout.addWidget(self.btn_reset_area)

        self.area_label = QLabel("全屏")
        area_layout.addWidget(self.area_label)
        area_layout.addStretch()
        params_layout.addLayout(area_layout)

        layout.addWidget(params_group)

        # 控制按钮
        control_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始测试")
        self.btn_start.clicked.connect(self._start_test)
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #FAFAFA; }"
        )
        control_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止测试")
        self.btn_stop.clicked.connect(self._stop_test)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #FAFAFA; }"
        )
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        # 提示：测试模式不点击
        tip = QLabel("提示：测试模式下只显示识别结果，不会触发鼠标点击。")
        tip.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(tip)

        # 识别结果显示区域
        result_group = QGroupBox("识别结果")
        result_layout = QVBoxLayout(result_group)

        # 统计信息
        self.stats_label = QLabel("识别测试未运行")
        self.stats_label.setStyleSheet("font-weight: bold; padding: 4px;")
        result_layout.addWidget(self.stats_label)

        # 清空按钮
        toolbar = QHBoxLayout()
        self.btn_clear = QPushButton("清空日志")
        self.btn_clear.clicked.connect(lambda: self.result_text.clear())
        toolbar.addWidget(self.btn_clear)
        toolbar.addStretch()
        result_layout.addLayout(toolbar)

        # 详细结果
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setLineWrapMode(QTextEdit.NoWrap)
        result_layout.addWidget(self.result_text)

        layout.addWidget(result_group, 1)

        # 初始化定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(500)

        self._load_models()
        self._update_start_button_state()

    def _connect_signals(self):
        """连接跨线程信号"""
        self.detections_received.connect(self._on_detections_main_thread)
        self.error_received.connect(self._on_error_main_thread)

    def _load_models(self):
        """加载可用模型"""
        try:
            model_manager.load_models()
            models = model_manager.get_model_list()
            self.model_combo.clear()
            for model in models:
                dataset_name = model.get("dataset_name", "未知")
                display_text = f"{model['filename']}  —  {dataset_name}"
                self.model_combo.addItem(display_text, model["path"])
            logger.info(f"识别测试页加载模型列表: 共 {len(models)} 个")
        except Exception as e:
            logger.error(f"加载模型列表失败: {str(e)}")
        self._update_start_button_state()

    def showEvent(self, event):
        """页面显示时自动刷新模型列表"""
        super().showEvent(event)
        self._load_models()

    def _update_start_button_state(self):
        """当存在模型且未在运行时才能开始测试"""
        has_model = self.model_combo.count() > 0
        is_running = self.recognition is not None and self.recognition.is_running
        self.btn_start.setEnabled(has_model and not is_running)
        if not has_model:
            self.btn_start.setToolTip("请先训练或导入一个模型")
        else:
            self.btn_start.setToolTip("")

    def _on_conf_changed(self, value: int):
        """置信度滑块变化"""
        threshold = value / 100.0
        self.conf_label.setText(f"{threshold:.2f}")
        # 测试运行中实时调整
        if self.recognition and self.recognition.is_running:
            self.recognition.set_confidence_threshold(threshold)

    def _select_screen_area(self):
        """选择屏幕识别区域"""
        try:
            self._selector = ScreenAreaSelector()
            self._selector.area_selected.connect(self._on_area_selected)
            self._selector.cancelled.connect(self._on_area_cancelled)
            # 让主窗口短暂最小化以便选择（可选）
            self._selector.showFullScreen()
        except Exception as e:
            logger.error(f"选择区域失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"选择区域失败: {str(e)}")

    def _on_area_selected(self, x: int, y: int, width: int, height: int):
        self.monitor_area = (x, y, width, height)
        self.area_label.setText(f"({x}, {y})  {width}×{height}")
        logger.info(f"识别区域选定: x={x} y={y} w={width} h={height}")
        # 运行时实时生效
        if self.recognition and self.recognition.is_running:
            self.recognition.set_monitor_area(x, y, width, height)

    def _on_area_cancelled(self):
        logger.info("区域选择已取消")

    def _reset_area(self):
        self.monitor_area = None
        self.area_label.setText("全屏")
        if self.recognition and self.recognition.is_running:
            self.recognition.use_full_screen_monitor()

    def _start_test(self):
        """开始识别测试"""
        logger.info("开始识别测试")

        try:
            model_index = self.model_combo.currentIndex()
            if model_index < 0:
                QMessageBox.warning(self, "警告", "请先选择模型")
                return

            model_path = self.model_combo.itemData(model_index)
            confidence_threshold = self.conf_slider.value() / 100.0

            # 创建识别实例（测试模式：禁用点击）
            self.recognition = ScreenRecognition(
                model_path=model_path,
                confidence_threshold=confidence_threshold,
                click_enabled=False,
            )

            if self.recognition.model is None:
                QMessageBox.critical(self, "错误", f"模型加载失败: {model_path}")
                self.recognition = None
                return

            # 设置监控区域
            if self.monitor_area:
                x, y, width, height = self.monitor_area
                self.recognition.set_monitor_area(x, y, width, height)
            else:
                self.recognition.use_full_screen_monitor()

            # 设置识别结果回调（从后台线程切回主线程）
            self.recognition.on_recognition_result = self.detections_received.emit
            self.recognition.on_error = lambda e: self.error_received.emit(str(e))

            if self.recognition.start_recognition():
                self.btn_start.setEnabled(False)
                self.btn_stop.setEnabled(True)
                self.btn_select_area.setEnabled(True)  # 区域运行时也可改
                self.btn_reset_area.setEnabled(True)
                self.model_combo.setEnabled(False)

                self.result_text.clear()
                self._append_log(f"识别测试已启动")
                self._append_log(f"模型: {model_path}")
                self._append_log(f"置信度阈值: {confidence_threshold:.2f}")
                self._append_log(f"识别区域: {self.area_label.text()}")
                self._append_log("-" * 80)
            else:
                QMessageBox.warning(self, "警告", "启动识别测试失败")
                self.recognition = None

        except Exception as e:
            logger.error(f"启动识别测试出错: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"启动识别测试出错: {str(e)}")
            self.recognition = None

        self._update_start_button_state()

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
            self.btn_reset_area.setEnabled(True)
            self.model_combo.setEnabled(True)

            self._append_log("")
            self._append_log("识别测试已停止")
        except Exception as e:
            logger.error(f"停止识别测试出错: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"停止识别测试出错: {str(e)}")

        self._update_start_button_state()

    def _on_detections_main_thread(self, detections):
        """识别结果（主线程）"""
        if not detections:
            return

        try:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            self._append_log(f"[{timestamp}] 检测到 {len(detections)} 个目标:")

            for idx, detection in enumerate(detections, 1):
                bbox = detection["bbox"]
                x1, y1, x2, y2 = bbox
                width = x2 - x1
                height = y2 - y1
                center_x, center_y = detection["center"]
                confidence = float(detection["confidence"])
                class_name = detection["class_name"]

                result_line = (
                    f"  [{idx}] {class_name}\n"
                    f"      位置: ({x1:.0f}, {y1:.0f}) -> ({x2:.0f}, {y2:.0f})\n"
                    f"      中心: ({center_x:.0f}, {center_y:.0f})\n"
                    f"      尺寸: {width:.0f} x {height:.0f}\n"
                    f"      置信度: {confidence:.2%}"
                )
                self.result_text.append(result_line)

            scrollbar = self.result_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            logger.error(f"处理识别结果出错: {str(e)}", exc_info=True)

    def _on_error_main_thread(self, err: str):
        """识别线程错误（主线程）"""
        self._append_log(f"[错误] {err}")

    def _append_log(self, text: str):
        """写入日志区域（始终在主线程调用）"""
        if text == "":
            self.result_text.append("")
            return
        timestamp = datetime.now().strftime('%H:%M:%S')
        if text.startswith("[") or text.startswith("  "):
            self.result_text.append(text)
        else:
            self.result_text.append(f"[{timestamp}] {text}")

    def _update_stats(self):
        """更新统计信息"""
        if self.recognition and self.recognition.is_running:
            stats = self.recognition.get_statistics()
            self.stats_label.setText(
                f"状态: 运行中  |  识别次数: {stats['recognitions_count']}  |  "
                f"FPS: {stats['fps']:.1f}  |  置信度: {stats['confidence_threshold']:.2f}"
            )
            self.stats_label.setStyleSheet("color: #2E7D32; font-weight: bold; padding: 4px;")
        else:
            self.stats_label.setText("状态: 未运行")
            self.stats_label.setStyleSheet("color: #666; font-weight: bold; padding: 4px;")

    def close(self):
        """关闭时停止识别"""
        if self.recognition and self.recognition.is_running:
            self.recognition.stop_recognition()
            self.recognition = None
        if self.timer.isActive():
            self.timer.stop()
        return super().close()

    def closeEvent(self, event):
        """关闭事件"""
        if self.recognition and self.recognition.is_running:
            self.recognition.stop_recognition()
            self.recognition = None
        event.accept()
