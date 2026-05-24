#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
位移测试标签页

识别到目标后，只有当目标中心点在时间窗口内发生明显位移时才提示。
测试模式：不触发点击。预览画面显示所有检测框，日志只记录触发位移的目标。
"""

import logging
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QSlider, QSplitter, QTextEdit,
    QVBoxLayout, QWidget,
)

from global_support.device_resolver import device_display_name, get_available_devices
from gui.screen_area_selector import ScreenAreaSelector
from recognition.displacement_tracker import DisplacementTracker
from recognition.screen_recognition import ScreenRecognition
from recognition.visualizer import draw_detections
from training_result.model_manager import model_manager

logger = logging.getLogger(__name__)


class DisplacementTestTab(QWidget):
    """位移测试标签页"""

    # 后台线程 → 主线程信号
    detections_received = pyqtSignal(list)  # 触发位移的目标子集
    # 图像处理在截图后台线程完成，仅传已渲染好的 QImage 给主线程
    frame_ready = pyqtSignal(QImage)
    error_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recognition = None
        self.monitor_area = None
        self._selector = None
        self._tracker: DisplacementTracker = None
        self._trigger_count = 0
        self._preview_logged = False
        # 供后台线程读取预览区域尺寸（Python int 赋值 GIL 原子）
        self._preview_w = 640
        self._preview_h = 480
        self._init_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _init_ui(self):
        # 左右分栏:左侧窄列放所有参数,右侧主区放识别结果(预览 + 日志),
        # 这样预览可以拿到 ~整个 tab 高度,不再被参数区往下挤
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)

        main_splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        layout = QVBoxLayout(left_panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- 识别参数 ---
        params_group = QGroupBox("识别参数")
        params_layout = QVBoxLayout(params_group)

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(360)
        model_layout.addWidget(self.model_combo)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self._load_models)
        model_layout.addWidget(self.btn_refresh)
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
        self.window_slider.setMinimum(5)    # 0.5 s（单位 0.1 s）
        self.window_slider.setMaximum(100)  # 10.0 s
        self.window_slider.setValue(5)      # 0.5 s 默认
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
        self.cooldown_slider.setMaximum(100)  # 10.0 s
        self.cooldown_slider.setValue(10)     # 1.0 s 默认
        self.cooldown_slider.valueChanged.connect(
            lambda v: self.cooldown_label.setText(f"{v / 10:.1f} s")
        )
        cool_layout.addWidget(self.cooldown_slider)
        self.cooldown_label = QLabel("1.0 s")
        self.cooldown_label.setFixedWidth(60)
        cool_layout.addWidget(self.cooldown_label)
        disp_layout.addLayout(cool_layout)

        layout.addWidget(disp_group)

        # --- 控制按钮 ---
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

        tip = QLabel("提示：仅当目标位移超过阈值时才记录日志；预览画面仍显示所有检测框。")
        tip.setStyleSheet("color: #666; font-style: italic;")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        # --- 识别日志(填充左侧剩余空间) ---
        result_group = QGroupBox("识别日志")
        result_layout = QVBoxLayout(result_group)

        toolbar = QHBoxLayout()
        self.chk_preview = QCheckBox("实时预览画面")
        self.chk_preview.setChecked(True)
        self.chk_preview.toggled.connect(self._on_preview_toggled)
        toolbar.addWidget(self.chk_preview)
        self.btn_clear = QPushButton("清空日志")
        self.btn_clear.clicked.connect(lambda: self.result_text.clear())
        toolbar.addWidget(self.btn_clear)
        toolbar.addStretch()
        result_layout.addLayout(toolbar)

        self.stats_label = QLabel("位移测试未运行")
        self.stats_label.setStyleSheet("font-weight: bold; padding: 4px;")
        result_layout.addWidget(self.stats_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setLineWrapMode(QTextEdit.NoWrap)
        result_layout.addWidget(self.result_text, 1)

        # 日志区拿走左侧底部所有剩余空间(stretch=1)
        layout.addWidget(result_group, 1)
        main_splitter.addWidget(left_panel)

        # --- 预览(独占右侧) ---
        self.preview_label = QLabel("预览（开始测试后显示画面）")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(320, 240)
        self.preview_label.setStyleSheet(
            "QLabel { background-color: #1e1e1e; color: #888; border: 1px solid #444; }"
        )
        # 监听 preview_label 自己的 resize(分隔条拖动也算),保证缓存随时跟实际尺寸一致
        self.preview_label.installEventFilter(self)
        main_splitter.addWidget(self.preview_label)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setSizes([400, 1200])
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)

        root_layout.addWidget(main_splitter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(500)

        self._load_models()
        self._update_start_btn()

    def _connect_signals(self):
        self.detections_received.connect(self._on_triggered_main_thread)
        self.frame_ready.connect(self._on_frame_ready_main_thread)
        self.error_received.connect(lambda e: self._append_log(f"[错误] {e}"))

    # ------------------------------------------------------------------
    # 模型加载
    # ------------------------------------------------------------------

    def _load_models(self):
        try:
            model_manager.load_models()
            models = model_manager.get_model_list()
            self.model_combo.clear()
            for m in models:
                display_text = f"{m['filename']}  —  {m.get('dataset_name', '未知')}"
                self.model_combo.addItem(display_text, m["path"])
            logger.info(f"位移测试页加载模型: 共 {len(models)} 个")
        except Exception as e:
            logger.error(f"加载模型列表失败: {e}")
        self._update_start_btn()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_models()

    def _update_start_btn(self):
        has_model = self.model_combo.count() > 0
        running = self.recognition is not None and self.recognition.is_running
        self.btn_start.setEnabled(has_model and not running)

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

    def _start_test(self):
        logger.info("开始位移测试")
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
            self._preview_logged = False

            self.recognition = ScreenRecognition(
                model_path=model_path,
                confidence_threshold=confidence_threshold,
                click_enabled=False,
                device=device,
            )

            if self.recognition.model is None:
                QMessageBox.critical(self, "错误", f"模型加载失败: {model_path}")
                self.recognition = None
                return

            if self.monitor_area:
                self.recognition.set_monitor_area(*self.monitor_area)
            else:
                self.recognition.use_full_screen_monitor()

            self.recognition.on_recognition_result = self._on_raw_detections
            self.recognition.on_error = lambda e: self.error_received.emit(str(e))
            if self.chk_preview.isChecked():
                self.recognition.on_frame_result = self._on_raw_frame

            if self.recognition.start_recognition():
                self.btn_start.setEnabled(False)
                self.btn_stop.setEnabled(True)
                self.model_combo.setEnabled(False)
                self.device_combo.setEnabled(False)

                self.result_text.clear()
                self._append_log("位移测试已启动")
                self._append_log(f"模型: {model_path}")
                self._append_log(
                    f"置信度: {confidence_threshold:.2f}  |  设备: {device}"
                )
                self._append_log(
                    f"灵敏度: {displacement_ratio:.0%}  |  最小阈值: {min_displacement_px:.0f} px  |  窗口: {window_s:.1f} s  |  冷却: {cooldown_s:.1f} s"
                )
                self._append_log(f"识别区域: {self.area_label.text()}")
                self._append_log("-" * 80)
            else:
                QMessageBox.warning(self, "警告", "启动识别失败")
                self.recognition = None

        except Exception as e:
            logger.error(f"启动位移测试出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"启动位移测试出错: {e}")
            self.recognition = None

        self._update_start_btn()

    def _stop_test(self):
        logger.info("停止位移测试")
        try:
            if self.recognition:
                self.recognition.stop_recognition()
                self.recognition = None
            if self._tracker:
                self._tracker.reset()

            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.model_combo.setEnabled(True)
            self.device_combo.setEnabled(True)

            self._append_log("")
            self._append_log("位移测试已停止")
            self.preview_label.clear()
            self.preview_label.setText("预览（开始测试后显示画面）")
        except Exception as e:
            logger.error(f"停止位移测试出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"停止位移测试出错: {e}")

        self._update_start_btn()

    # ------------------------------------------------------------------
    # 后台线程回调（recognition 线程 → 发信号切到主线程）
    # ------------------------------------------------------------------

    def _on_raw_detections(self, detections: list):
        if self._tracker is None:
            return
        triggered = self._tracker.update(detections)
        if triggered:
            self.detections_received.emit(triggered)

    def _on_raw_frame(self, frame, detections: list):
        """截图后台线程回调：在此完成所有图像处理，主线程只做 setPixmap。"""
        if not self.chk_preview.isChecked():
            return
        try:
            import cv2
            import numpy as np

            annotated = draw_detections(frame, detections)
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            rgb = np.ascontiguousarray(rgb)
            h, w = rgb.shape[:2]
            # QImage 是可重入类，可在任意线程创建；scaled() 也是
            qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888)
            scaled = qimg.scaled(
                self._preview_w, self._preview_h,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
            if not self._preview_logged:
                logger.info(f"位移测试预览首帧: {w}x{h}")
                self._preview_logged = True
            self.frame_ready.emit(scaled)
        except Exception as e:
            logger.error(f"帧处理出错: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # 主线程 slots
    # ------------------------------------------------------------------

    def _on_triggered_main_thread(self, triggered: list):
        self._trigger_count += len(triggered)
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._append_log(f"[{ts}] 位移触发 {len(triggered)} 个目标:")
        for det in triggered:
            cx, cy = det.get("center", (0, 0))
            dist = det.get("displacement_px", "?")
            thr = det.get("threshold_px", "?")
            ratio = det.get("displacement_ratio", 0)
            diag = det.get("bbox_diag_px", 0)
            cls = det.get("class_name", "unknown")
            conf = float(det.get("confidence", 0))
            self.result_text.append(
                f"  {cls}  中心({cx:.0f}, {cy:.0f})  "
                f"位移 {dist}/{thr} px ({ratio:.0%} of bbox diag {diag} px)  "
                f"置信度 {conf:.2%}"
            )
        sb = self.result_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_frame_ready_main_thread(self, qimg: QImage):
        """主线程：仅做 QPixmap 转换 + setPixmap，< 1ms。"""
        self.preview_label.setPixmap(QPixmap.fromImage(qimg))

    def resizeEvent(self, event):
        """更新供后台线程使用的预览尺寸缓存(主窗口缩放走这里)。"""
        super().resizeEvent(event)
        self._refresh_preview_size_cache()

    def eventFilter(self, obj, event):
        """监听 preview_label 自己的 resize:覆盖分隔条拖动、子布局变化等
        tab.resizeEvent 不会触发的场景。
        """
        if obj is self.preview_label and event.type() == QEvent.Resize:
            self._refresh_preview_size_cache()
        return super().eventFilter(obj, event)

    def _refresh_preview_size_cache(self):
        if hasattr(self, "preview_label") and self.preview_label is not None:
            sz = self.preview_label.size()
            if sz.width() > 0 and sz.height() > 0:
                self._preview_w = sz.width()
                self._preview_h = sz.height()

    def _on_preview_toggled(self, checked: bool):
        if self.recognition and self.recognition.is_running:
            self.recognition.on_frame_result = self._on_raw_frame if checked else None
        if not checked:
            self.preview_label.clear()
            self.preview_label.setText("预览已关闭")

    def _append_log(self, text: str):
        if text == "":
            self.result_text.append("")
            return
        ts = datetime.now().strftime("%H:%M:%S")
        if text.startswith("[") or text.startswith("  ") or text.startswith("-"):
            self.result_text.append(text)
        else:
            self.result_text.append(f"[{ts}] {text}")

    def _update_stats(self):
        if self.recognition and self.recognition.is_running:
            stats = self.recognition.get_statistics()
            self.stats_label.setText(
                f"状态: 运行中  |  推理帧: {stats['recognitions_count']}  |  "
                f"位移触发: {self._trigger_count}  |  FPS: {stats['fps']:.1f}"
            )
            self.stats_label.setStyleSheet("color: #2E7D32; font-weight: bold; padding: 4px;")
        else:
            self.stats_label.setText("状态: 未运行")
            self.stats_label.setStyleSheet("color: #666; font-weight: bold; padding: 4px;")

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
