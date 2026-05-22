#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别操作标签页

正式识别目标，识别到目标后执行用户自定义的Python脚本
"""

import logging
import threading
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QTextEdit, QComboBox,
    QSlider, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt

from training_result.model_manager import model_manager
from recognition.screen_recognition import ScreenRecognition
from global_support.device_resolver import get_available_devices, device_display_name

logger = logging.getLogger(__name__)


class RecognitionActionTab(QWidget):
    """识别操作标签页"""

    def __init__(self, parent=None):
        """初始化识别操作标签页"""
        super().__init__(parent)
        self.recognition = None
        self.monitor_area = None
        self.selecting_area = False
        self.last_detection_time = None
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

        # 计算设备选择
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("计算设备:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(260)
        for info in get_available_devices():
            self.device_combo.addItem(device_display_name(info), info.spec)
        device_layout.addWidget(self.device_combo)
        device_layout.addStretch()
        params_layout.addLayout(device_layout)

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

        # Python脚本配置区域
        script_group = QGroupBox("Python脚本配置")
        script_layout = QVBoxLayout(script_group)

        # 执行冷却滑块（0.0–10.0 s，步长 0.1）
        cool_layout = QHBoxLayout()
        cool_layout.addWidget(QLabel("执行冷却:"))
        self.cooldown_slider = QSlider(Qt.Horizontal)
        self.cooldown_slider.setMinimum(0)
        self.cooldown_slider.setMaximum(100)
        self.cooldown_slider.setValue(10)
        self.cooldown_slider.valueChanged.connect(
            lambda v: self.cooldown_label.setText(f"{v / 10:.1f} s")
        )
        cool_layout.addWidget(self.cooldown_slider)
        self.cooldown_label = QLabel("1.0 s")
        self.cooldown_label.setFixedWidth(60)
        cool_layout.addWidget(self.cooldown_label)
        script_layout.addLayout(cool_layout)

        script_layout.addWidget(QLabel("识别到目标后执行的 Python 代码（pyautogui / time 已预置）:"))
        self.script_text = QTextEdit()
        self.script_text.setPlaceholderText(
            "# 可用变量 / 模块:\n"
            "#   detections  — 本次检测结果列表\n"
            "#     .bbox       (x1, y1, x2, y2)\n"
            "#     .center     (cx, cy)  屏幕绝对坐标\n"
            "#     .confidence 置信度 float\n"
            "#     .class_name 类别名称\n"
            "#   pyautogui   — 鼠标/键盘控制\n"
            "#   time        — 时间工具\n"
            "\n"
            "# 示例：点击置信度最高的目标\n"
            "if detections:\n"
            "    best = max(detections, key=lambda d: d['confidence'])\n"
            "    cx, cy = best['center']\n"
            "    pyautogui.click(cx, cy)\n"
            "    print(f\"点击 {best['class_name']} @ ({cx}, {cy})\")"
        )
        self.script_text.setMaximumHeight(180)
        script_layout.addWidget(self.script_text)

        layout.addWidget(script_group)

        # 控制按钮
        control_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始识别")
        self.btn_start.clicked.connect(self._start_recognition)
        self.btn_start.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        control_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止识别")
        self.btn_stop.clicked.connect(self._stop_recognition)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")
        control_layout.addWidget(self.btn_stop)

        layout.addLayout(control_layout)

        # 执行结果区域
        result_group = QGroupBox("执行结果")
        result_layout = QVBoxLayout(result_group)

        # 统计信息
        self.stats_label = QLabel("识别次数: 0 | 目标数: 0 | 脚本执行: 0 | FPS: 0")
        result_layout.addWidget(self.stats_label)

        # 执行日志
        result_layout.addWidget(QLabel("脚本执行日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        result_layout.addWidget(self.log_text)

        layout.addWidget(result_group)

        # 初始化定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(500)

        # 脚本执行次数
        self.script_executions = 0

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

    def _start_recognition(self):
        """开始识别"""
        logger.info("开始识别操作")

        try:
            # 获取模型路径
            model_index = self.model_combo.currentIndex()
            if model_index < 0:
                QMessageBox.warning(self, "警告", "请先选择模型")
                return

            model_path = self.model_combo.itemData(model_index)
            confidence_threshold = self.conf_slider.value() / 100.0
            device = self.device_combo.currentData() or "cpu"

            # 识别操作 Tab 只执行用户脚本，不做自动点击
            self.recognition = ScreenRecognition(
                model_path=model_path,
                confidence_threshold=confidence_threshold,
                click_enabled=False,
                device=device,
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
                self.device_combo.setEnabled(False)
                self.script_text.setEnabled(False)
                self.log_text.clear()
                self.script_executions = 0
                self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 识别已启动")
                self.log_text.append(f"模型: {model_path}")
                self.log_text.append(f"置信度阈值: {confidence_threshold:.2f}")
                self.log_text.append(f"计算设备: {device}")
                self.log_text.append(f"识别区域: {self.area_label.text()}")
                self.log_text.append("-" * 80)
            else:
                QMessageBox.warning(self, "警告", "启动识别失败")

        except Exception as e:
            logger.error(f"启动识别出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动识别出错: {str(e)}")

    def _stop_recognition(self):
        """停止识别"""
        logger.info("停止识别操作")

        try:
            if self.recognition:
                self.recognition.stop_recognition()
                self.recognition = None

            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_select_area.setEnabled(True)
            self.model_combo.setEnabled(True)
            self.device_combo.setEnabled(True)
            self.script_text.setEnabled(True)

            self.log_text.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] 识别已停止")
            self.log_text.append(f"脚本执行次数: {self.script_executions}")

        except Exception as e:
            logger.error(f"停止识别出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"停止识别出错: {str(e)}")

    def _on_recognition_result(self, detections):
        """识别结果回调"""
        if not detections:
            return

        # 检查执行冷却
        current_time = time.time()
        cooldown = self.cooldown_slider.value() / 10.0
        if self.last_detection_time and (current_time - self.last_detection_time) < cooldown:
            return

        self.last_detection_time = current_time

        try:
            # 获取用户脚本
            script_code = self.script_text.toPlainText().strip()

            if not script_code:
                self.log_text.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] 未配置Python脚本，跳过执行")
                return

            # 在新线程中执行脚本
            threading.Thread(
                target=self._execute_script,
                args=(detections, script_code),
                daemon=True
            ).start()

        except Exception as e:
            logger.error(f"处理识别结果出错: {str(e)}")
            self.log_text.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] 错误: {str(e)}")

    def _execute_script(self, detections, script_code):
        """执行用户Python脚本"""
        try:
            import pyautogui as _pyautogui
            import time as _time
            execution_globals = {
                '__name__': '__main__',
                'detections': detections,
                'print': self._safe_print,
                'pyautogui': _pyautogui,
                'time': _time,
            }
            exec(script_code, execution_globals)

            self.script_executions += 1

        except Exception as e:
            logger.error(f"执行Python脚本出错: {str(e)}")
            self._safe_print(f"脚本执行出错: {str(e)}")

    def _safe_print(self, *args, **kwargs):
        """线程安全的打印函数"""
        try:
            # 格式化输出
            sep = kwargs.get('sep', ' ')
            end = kwargs.get('end', '\n')
            output = sep.join(str(arg) for arg in args)

            # 在主线程中更新UI
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self.log_text,
                "append",
                Qt.QueuedConnection,
                Q_ARG(str, f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {output}{end}")
            )
        except Exception as e:
            logger.error(f"打印出错: {str(e)}")

    def _update_stats(self):
        """更新统计信息"""
        if self.recognition and self.recognition.is_running:
            stats = self.recognition.get_statistics()
            self.stats_label.setText(
                f"识别次数: {stats['recognitions_count']} | "
                f"脚本执行: {self.script_executions} | "
                f"FPS: {stats['fps']:.1f}"
            )
        else:
            self.stats_label.setText("识别未运行")

    def closeEvent(self, event):
        """关闭事件处理"""
        if self.recognition and self.recognition.is_running:
            self.recognition.stop_recognition()
        event.accept()
