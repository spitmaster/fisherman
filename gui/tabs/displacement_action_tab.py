#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
位移操作标签页

识别到目标后，只有当目标中心点在时间窗口内发生明显位移时，才执行用户自定义 Python 脚本。
脚本中的 detections 变量只包含触发了位移条件的目标列表。
"""

import logging
import threading
from datetime import datetime

from PyQt5.QtCore import Q_ARG, Qt, QMetaObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QSlider, QTextEdit,
    QVBoxLayout, QWidget,
)

from global_support.device_resolver import device_display_name, get_available_devices
from gui.screen_area_selector import ScreenAreaSelector
from recognition.displacement_tracker import DisplacementTracker
from recognition.screen_recognition import ScreenRecognition
from training_result.model_manager import model_manager

logger = logging.getLogger(__name__)


class DisplacementActionTab(QWidget):
    """位移操作标签页"""

    triggered_received = pyqtSignal(list)
    error_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recognition = None
        self.monitor_area = None
        self._selector = None
        self._tracker: DisplacementTracker = None
        self._trigger_count = 0
        self._script_count = 0
        self._init_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- 识别参数 ---
        params_group = QGroupBox("识别参数")
        params_layout = QVBoxLayout(params_group)

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self._load_models()
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        params_layout.addLayout(model_layout)

        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("置信度阈值:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setMinimum(10)
        self.conf_slider.setMaximum(95)
        self.conf_slider.setValue(70)
        self.conf_slider.valueChanged.connect(
            lambda v: self.conf_label.setText(f"{v / 100:.2f}")
        )
        conf_layout.addWidget(self.conf_slider)
        self.conf_label = QLabel("0.70")
        self.conf_label.setFixedWidth(50)
        conf_layout.addWidget(self.conf_label)
        params_layout.addLayout(conf_layout)

        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("计算设备:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(260)
        for info in get_available_devices():
            self.device_combo.addItem(device_display_name(info), info.spec)
        device_layout.addWidget(self.device_combo)
        device_layout.addStretch()
        params_layout.addLayout(device_layout)

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

        # --- 位移检测参数 ---
        disp_group = QGroupBox("位移检测参数")
        disp_layout = QVBoxLayout(disp_group)

        # 灵敏度:实际触发阈值 = bbox 对角线 × ratio,远近自适应
        sens_layout = QHBoxLayout()
        sens_lbl = QLabel("灵敏度:")
        sens_lbl.setToolTip("以目标自身大小为基准:位移超过 bbox 对角线的此百分比即触发")
        sens_layout.addWidget(sens_lbl)
        self.disp_slider = QSlider(Qt.Horizontal)
        self.disp_slider.setMinimum(5)
        self.disp_slider.setMaximum(50)
        self.disp_slider.setValue(9)
        self.disp_slider.valueChanged.connect(
            lambda v: self.disp_label.setText(f"{v} %")
        )
        sens_layout.addWidget(self.disp_slider)
        self.disp_label = QLabel("9 %")
        self.disp_label.setFixedWidth(60)
        sens_layout.addWidget(self.disp_label)
        disp_layout.addLayout(sens_layout)

        # 最小绝对阈值:防止远处目标 bbox 太小导致 YOLO 抖动假阳
        floor_layout = QHBoxLayout()
        floor_lbl = QLabel("最小阈值:")
        floor_lbl.setToolTip("无论目标多小,触发都需要至少这么多像素的位移;默认 5 px 兜底")
        floor_layout.addWidget(floor_lbl)
        self.floor_slider = QSlider(Qt.Horizontal)
        self.floor_slider.setMinimum(1)
        self.floor_slider.setMaximum(30)
        self.floor_slider.setValue(5)
        self.floor_slider.valueChanged.connect(
            lambda v: self.floor_label.setText(f"{v} px")
        )
        floor_layout.addWidget(self.floor_slider)
        self.floor_label = QLabel("5 px")
        self.floor_label.setFixedWidth(60)
        floor_layout.addWidget(self.floor_label)
        disp_layout.addLayout(floor_layout)

        win_layout = QHBoxLayout()
        win_layout.addWidget(QLabel("时间窗口:"))
        self.window_slider = QSlider(Qt.Horizontal)
        self.window_slider.setMinimum(5)
        self.window_slider.setMaximum(100)
        self.window_slider.setValue(5)
        self.window_slider.valueChanged.connect(
            lambda v: self.window_label.setText(f"{v / 10:.1f} s")
        )
        win_layout.addWidget(self.window_slider)
        self.window_label = QLabel("0.5 s")
        self.window_label.setFixedWidth(60)
        win_layout.addWidget(self.window_label)
        disp_layout.addLayout(win_layout)

        cool_layout = QHBoxLayout()
        cool_layout.addWidget(QLabel("触发冷却:"))
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
        disp_layout.addLayout(cool_layout)

        layout.addWidget(disp_group)

        # --- Python 脚本 ---
        script_group = QGroupBox("Python 脚本配置")
        script_layout = QVBoxLayout(script_group)
        script_layout.addWidget(QLabel("位移触发后执行的 Python 代码（pyautogui / time 已预置）:"))
        self.script_text = QTextEdit()
        self.script_text.setPlaceholderText(
            "# 可用变量 / 模块:\n"
            "#   detections  — 触发位移的目标列表\n"
            "#     .class_name           类别名称\n"
            "#     .center               (cx, cy)  屏幕绝对坐标\n"
            "#     .confidence           置信度 float\n"
            "#     .displacement_px      本次位移距离(px)\n"
            "#     .threshold_px         触发该次的阈值(px)\n"
            "#     .displacement_ratio   位移占 bbox 对角线的比例(0~1)\n"
            "#     .bbox_diag_px         bbox 对角线长度(px)\n"
            "#     .bbox                 (x1, y1, x2, y2)\n"
            "#   pyautogui   — 鼠标/键盘控制\n"
            "#   time        — 时间工具\n"
            "\n"
            "# 示例：点击位移最大的目标\n"
            "if detections:\n"
            "    target = max(detections, key=lambda d: d['displacement_px'])\n"
            "    cx, cy = target['center']\n"
            "    pyautogui.click(cx, cy)\n"
            "    print(f\"点击 {target['class_name']} 位移 {target['displacement_px']} px\")"
        )
        self.script_text.setMaximumHeight(180)
        script_layout.addWidget(self.script_text)
        layout.addWidget(script_group)

        # --- 控制按钮 ---
        control_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始识别")
        self.btn_start.clicked.connect(self._start_recognition)
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #FAFAFA; }"
        )
        control_layout.addWidget(self.btn_start)
        self.btn_stop = QPushButton("停止识别")
        self.btn_stop.clicked.connect(self._stop_recognition)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #FAFAFA; }"
        )
        control_layout.addWidget(self.btn_stop)
        layout.addLayout(control_layout)

        # --- 执行结果 ---
        result_group = QGroupBox("执行结果")
        result_layout = QVBoxLayout(result_group)

        self.stats_label = QLabel("识别次数: 0 | 位移触发: 0 | 脚本执行: 0 | FPS: 0")
        result_layout.addWidget(self.stats_label)

        result_layout.addWidget(QLabel("脚本执行日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        result_layout.addWidget(self.log_text)

        layout.addWidget(result_group)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(500)

    def _connect_signals(self):
        self.triggered_received.connect(self._on_triggered_main_thread)
        self.error_received.connect(
            lambda e: self.log_text.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] [错误] {e}"
            )
        )

    # ------------------------------------------------------------------
    # 模型加载
    # ------------------------------------------------------------------

    def _load_models(self):
        try:
            models = model_manager.get_model_list()
            self.model_combo.clear()
            for m in models:
                self.model_combo.addItem(m["filename"], m["path"])
        except Exception as e:
            logger.error(f"加载模型列表失败: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        self._load_models()

    # ------------------------------------------------------------------
    # 区域选择
    # ------------------------------------------------------------------

    def _select_screen_area(self):
        try:
            self._selector = ScreenAreaSelector()
            self._selector.area_selected.connect(self._on_area_selected)
            self._selector.cancelled.connect(lambda: None)
            self._selector.show()
            self._selector.activateWindow()
            self._selector.raise_()
        except Exception as e:
            logger.error(f"选择区域失败: {e}")
            QMessageBox.critical(self, "错误", f"选择区域失败: {e}")

    def _on_area_selected(self, x: int, y: int, width: int, height: int):
        self.monitor_area = (x, y, width, height)
        self.area_label.setText(f"({x}, {y})  {width}×{height}")
        if self.recognition and self.recognition.is_running:
            self.recognition.set_monitor_area(x, y, width, height)

    def _reset_area(self):
        self.monitor_area = None
        self.area_label.setText("全屏")
        if self.recognition and self.recognition.is_running:
            self.recognition.use_full_screen_monitor()

    # ------------------------------------------------------------------
    # 识别控制
    # ------------------------------------------------------------------

    def _start_recognition(self):
        logger.info("开始位移操作识别")
        try:
            model_index = self.model_combo.currentIndex()
            if model_index < 0:
                QMessageBox.warning(self, "警告", "请先选择模型")
                return

            model_path = self.model_combo.itemData(model_index)
            confidence_threshold = self.conf_slider.value() / 100.0
            device = self.device_combo.currentData() or "cpu"
            displacement_ratio = self.disp_slider.value() / 100.0
            min_displacement_px = float(self.floor_slider.value())
            window_s = self.window_slider.value() / 10.0
            cooldown_s = self.cooldown_slider.value() / 10.0

            self._tracker = DisplacementTracker(
                displacement_ratio=displacement_ratio,
                min_displacement_px=min_displacement_px,
                window_seconds=window_s,
                trigger_cooldown_s=cooldown_s,
            )
            self._trigger_count = 0
            self._script_count = 0

            # 位移操作 Tab 只执行用户脚本，不做自动点击
            self.recognition = ScreenRecognition(
                model_path=model_path,
                confidence_threshold=confidence_threshold,
                click_enabled=False,
                device=device,
            )

            if self.monitor_area:
                self.recognition.set_monitor_area(*self.monitor_area)
            else:
                self.recognition.use_full_screen_monitor()

            self.recognition.on_recognition_result = self._on_raw_detections
            self.recognition.on_error = lambda e: self.error_received.emit(str(e))

            if self.recognition.start_recognition():
                self.btn_start.setEnabled(False)
                self.btn_stop.setEnabled(True)
                self.btn_select_area.setEnabled(False)
                self.btn_reset_area.setEnabled(False)
                self.model_combo.setEnabled(False)
                self.device_combo.setEnabled(False)
                self.script_text.setEnabled(False)

                self.log_text.clear()
                ts = datetime.now().strftime("%H:%M:%S")
                self.log_text.append(f"[{ts}] 位移操作已启动")
                self.log_text.append(f"模型: {model_path}  |  设备: {device}")
                self.log_text.append(
                    f"灵敏度: {displacement_ratio:.0%}  |  最小阈值: {min_displacement_px:.0f} px  |  窗口: {window_s:.1f} s  |  冷却: {cooldown_s:.1f} s"
                )
                self.log_text.append("-" * 80)
            else:
                QMessageBox.warning(self, "警告", "启动识别失败")
                self.recognition = None

        except Exception as e:
            logger.error(f"启动位移操作出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"启动位移操作出错: {e}")
            self.recognition = None

    def _stop_recognition(self):
        logger.info("停止位移操作识别")
        try:
            if self.recognition:
                self.recognition.stop_recognition()
                self.recognition = None
            if self._tracker:
                self._tracker.reset()

            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_select_area.setEnabled(True)
            self.btn_reset_area.setEnabled(True)
            self.model_combo.setEnabled(True)
            self.device_combo.setEnabled(True)
            self.script_text.setEnabled(True)

            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"\n[{ts}] 识别已停止")
            self.log_text.append(
                f"位移触发: {self._trigger_count}  |  脚本执行: {self._script_count}"
            )

        except Exception as e:
            logger.error(f"停止位移操作出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"停止位移操作出错: {e}")

    # ------------------------------------------------------------------
    # 后台线程回调
    # ------------------------------------------------------------------

    def _on_raw_detections(self, detections: list):
        if self._tracker is None:
            return
        triggered = self._tracker.update(detections)
        if triggered:
            self.triggered_received.emit(triggered)

    # ------------------------------------------------------------------
    # 主线程 slots
    # ------------------------------------------------------------------

    def _on_triggered_main_thread(self, triggered: list):
        self._trigger_count += len(triggered)
        script_code = self.script_text.toPlainText().strip()
        if not script_code:
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{ts}] 位移触发（未配置脚本）")
            return
        threading.Thread(
            target=self._execute_script,
            args=(triggered, script_code),
            daemon=True,
        ).start()

    def _execute_script(self, detections: list, script_code: str):
        try:
            import pyautogui as _pyautogui
            import time as _time
            exec_globals = {
                "__name__": "__main__",
                "detections": detections,
                "print": self._safe_print,
                "pyautogui": _pyautogui,
                "time": _time,
            }
            exec(script_code, exec_globals)
            self._script_count += 1
        except Exception as e:
            logger.error(f"执行脚本出错: {e}")
            self._safe_print(f"脚本执行出错: {e}")

    def _safe_print(self, *args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "")
        output = sep.join(str(a) for a in args)
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        QMetaObject.invokeMethod(
            self.log_text,
            "append",
            Qt.QueuedConnection,
            Q_ARG(str, f"[{ts}] {output}{end}"),
        )

    def _update_stats(self):
        if self.recognition and self.recognition.is_running:
            stats = self.recognition.get_statistics()
            self.stats_label.setText(
                f"识别次数: {stats['recognitions_count']}  |  "
                f"位移触发: {self._trigger_count}  |  "
                f"脚本执行: {self._script_count}  |  "
                f"FPS: {stats['fps']:.1f}"
            )
        else:
            self.stats_label.setText("识别未运行")

    def close(self):
        if self.recognition and self.recognition.is_running:
            self.recognition.stop_recognition()
            self.recognition = None
        if self.timer.isActive():
            self.timer.stop()
        return super().close()

    def closeEvent(self, event):
        if self.recognition and self.recognition.is_running:
            self.recognition.stop_recognition()
            self.recognition = None
        event.accept()
