#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钓鱼标签页(FishingTab)— M5。

详见 docs/SPEC.md §2.14:F11 启动 / F12 停止的死循环自动钓鱼,
串联「预备 → 钓鱼前准备 → 抛竿 → 等浮漂 → 位移检测 → 触发后等待 → 右键拾取 → 钓鱼后处理」。

UI 锁定策略:启动后,除「停止钓鱼」按钮外所有参数控件禁用,防止运行中误改。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from PyQt5.QtCore import Qt, QEvent, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSlider, QSplitter, QVBoxLayout, QWidget,
)

from fishing import (
    BUNDLED_MODEL_FILENAME,
    DEFAULT_CAST_KEY,
    DEFAULT_DETECT_TIMEOUT_S,
    DEFAULT_POST_TRIGGER_WAIT_S,
    DEFAULT_PREPARE_WAIT_S,
    DEFAULT_WAIT_LAND_S,
    FishingConfig,
    FishingLoop,
    FishingState,
    FishingStats,
    LIBRARY_HOTKEYS,
    STATE_LABEL,
    is_standalone_mode,
    resolve_bundled_model_path,
)
from global_support.device_resolver import device_display_name, get_available_devices
from gui.screen_area_selector import ScreenAreaSelector

logger = logging.getLogger(__name__)


DEFAULT_START_HOTKEY = "f11"
DEFAULT_STOP_HOTKEY = "f12"

# 默认模型优先选 wow_fish.pt(精选模型,M5 主用)
PREFERRED_DEFAULT_MODEL = BUNDLED_MODEL_FILENAME


class FishingTab(QWidget):
    """自动钓鱼标签页。"""

    # 工作线程 → 主线程 信号(架构不变量 2)
    _state_changed = pyqtSignal(object, int, float, float)  # (FishingState, round_idx, elapsed, total)
    _round_completed = pyqtSignal(object)                   # FishingStats
    _triggered = pyqtSignal(dict)
    _error_received = pyqtSignal(str)
    _frame_ready = pyqtSignal(QImage)                       # 预渲染 + 已 scaled 的 QImage
    # 全局热键 → 主线程
    _hotkey_start_requested = pyqtSignal()
    _hotkey_stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop: Optional[FishingLoop] = None
        self._monitor_area: Optional[tuple] = None  # (x, y, w, h)
        self._selector: Optional[ScreenAreaSelector] = None

        # 当前注册到 keyboard 库的实际字符串(便于 stop 时 remove)
        self._registered_start: str = ""
        self._registered_stop: str = ""

        # 预览尺寸缓存(后台线程读,主线程通过 resizeEvent/eventFilter 写,GIL 原子)
        self._preview_w = 640
        self._preview_h = 480
        self._preview_logged = False

        self._init_ui()
        self._connect_signals()
        self._register_hotkeys()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)

        # 顶部:识别参数(横贯整宽,固定高度)
        root.addWidget(self._build_recognition_group())

        # 底部:左(钓鱼循环参数,内部滚动)+ 右(控制按钮 + 运行状态/日志)
        splitter = QSplitter(Qt.Horizontal)

        splitter.addWidget(self._build_loop_params_group())

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addLayout(self._build_control_buttons())
        right_layout.addWidget(self._build_status_group(), stretch=1)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 3)   # 左侧 参数 更宽
        splitter.setStretchFactor(1, 2)   # 右侧 状态/日志
        splitter.setSizes([700, 500])
        root.addWidget(splitter, stretch=1)

    # --- 识别参数 ----------------------------------------------------------

    def _build_recognition_group(self) -> QGroupBox:
        group = QGroupBox("识别参数")
        layout = QVBoxLayout(group)

        # 模型
        row = QHBoxLayout()
        row.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(360)
        self._load_models()
        row.addWidget(self.model_combo)
        row.addStretch()
        layout.addLayout(row)

        # 置信度
        row = QHBoxLayout()
        row.addWidget(QLabel("置信度阈值:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setMinimum(10)
        self.conf_slider.setMaximum(95)
        self.conf_slider.setValue(70)
        self.conf_slider.valueChanged.connect(
            lambda v: self.conf_label.setText(f"{v / 100:.2f}")
        )
        row.addWidget(self.conf_slider)
        self.conf_label = QLabel("0.70")
        self.conf_label.setFixedWidth(50)
        row.addWidget(self.conf_label)
        layout.addLayout(row)

        # 设备(不变量 6)
        row = QHBoxLayout()
        row.addWidget(QLabel("计算设备:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(260)
        for info in get_available_devices():
            self.device_combo.addItem(device_display_name(info), info.spec)
        row.addWidget(self.device_combo)
        row.addStretch()
        layout.addLayout(row)

        # 检测区域
        row = QHBoxLayout()
        row.addWidget(QLabel("位移检测区域:"))
        self.btn_select_area = QPushButton("选择区域")
        self.btn_select_area.setToolTip(
            "多屏用户必看:游戏在副屏时务必用此按钮框选游戏窗口,「全屏」只截主显示器"
        )
        self.btn_select_area.clicked.connect(self._select_screen_area)
        row.addWidget(self.btn_select_area)
        self.btn_reset_area = QPushButton("全屏(主显示器)")
        self.btn_reset_area.setToolTip("仅截主显示器;副屏游戏请用「选择区域」")
        self.btn_reset_area.clicked.connect(self._reset_area)
        row.addWidget(self.btn_reset_area)
        self.area_label = QLabel("全屏(主显示器)")
        row.addWidget(self.area_label)
        row.addStretch()
        layout.addLayout(row)

        return group

    # --- 钓鱼循环参数 ------------------------------------------------------

    def _build_loop_params_group(self) -> QGroupBox:
        """卡片式行布局:编号徽章 + 标题 + 程序做的事 + 输入控件,行间用底边线分隔。
        热键行固定在顶部,8 个步骤行包入内部 QScrollArea — 窗口高度不够时只滚步骤区。"""
        group = QGroupBox("钓鱼循环参数")
        outer = QVBoxLayout(group)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 8, 0, 0)

        # 热键行固定在顶部
        outer.addWidget(self._build_hotkey_row())

        # 步骤行容器(可滚动)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        steps_holder = QWidget()
        layout = QVBoxLayout(steps_holder)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 0. 预备等待
        self.prepare_spin = self._make_spin(DEFAULT_PREPARE_WAIT_S, 0.0, 10.0, 0.5)
        layout.addWidget(self._build_step_row(
            "0", "预备等待",
            "每轮循环开始前,程序强制 sleep N 秒。用途:跨轮节奏控制 / 给你按 F12 退出留窗口。",
            self.prepare_spin, "秒",
        ))

        # 1. 钓鱼前准备按键
        self.pre_action_edit = self._make_key_edit("", placeholder="空=跳过")
        layout.addWidget(self._build_step_row(
            "1", "钓鱼前准备 · 按键",
            "程序按一次你指定的键。可放抛饵宏 / 切装备宏 / 召唤鱼漂等任意准备宏。空=跳过整步。",
            self.pre_action_edit,
        ))

        # 2. 抛竿键
        self.cast_edit = self._make_key_edit(DEFAULT_CAST_KEY)
        layout.addWidget(self._build_step_row(
            "2", "抛竿 · 按键(必填)",
            "程序按一次你指定的键,把鱼竿甩出去(对应游戏内「钓鱼」动作技能位)。",
            self.cast_edit,
        ))

        # 3a. 抛竿后等待
        self.wait_land_spin = self._make_spin(DEFAULT_WAIT_LAND_S, 0.1, 10.0, 0.1)
        layout.addWidget(self._build_step_row(
            "3a", "抛竿后等浮漂落水",
            "程序 sleep N 秒,等浮漂飞出去落水稳定,再开始位移检测(过早开始会被入水水花误触发)。",
            self.wait_land_spin, "秒",
        ))

        # 3b. 位移检测超时
        self.detect_timeout_spin = self._make_spin(DEFAULT_DETECT_TIMEOUT_S, 1.0, 60.0, 1.0)
        layout.addWidget(self._build_step_row(
            "3b", "位移检测(超时上限)",
            "程序实时跑 YOLO 识别浮漂位置,N 秒内出现明显下沉位移即触发。"
            "超时未触发则放弃本轮,跳过步骤 4,直接走步骤 5。",
            self.detect_timeout_spin, "秒",
        ))

        # 4a. 触发后等待
        self.post_trigger_spin = self._make_spin(DEFAULT_POST_TRIGGER_WAIT_S, 0.1, 5.0, 0.1)
        layout.addWidget(self._build_step_row(
            "4a", "触发后等待",
            "检测到位移后,程序 sleep N 秒,等鱼咬稳。",
            self.post_trigger_spin, "秒",
        ))

        # 4b. 右键拾取(程序自动,无输入)
        layout.addWidget(self._build_step_row(
            "4b", "右键拾取(程序自动)",
            "程序自动调用 pyautogui.rightClick 点击触发目标的屏幕绝对坐标,把鱼拾取。无需配置。",
            None,
        ))

        # 5. 钓鱼后处理按键
        self.post_action_edit = self._make_key_edit("", placeholder="空=跳过")
        layout.addWidget(self._build_step_row(
            "5", "钓鱼后处理 · 按键",
            "程序按一次你指定的键。可放分解装备 / 修耐久 / 清空菜单宏。"
            "即使步骤 3b 超时也会执行(让通用宏照常生效)。空=跳过整步。",
            self.post_action_edit,
        ))

        # 步骤列底部填充,避免 8 行不满时被拉伸
        layout.addStretch()

        # 把步骤容器挂到滚动区,加到 group
        scroll.setWidget(steps_holder)
        outer.addWidget(scroll, stretch=1)

        # 警告固定在 group 底部,不参与滚动
        warn = QLabel(
            "⚠ 钓鱼运行时请勿启动其他识别任务(测试 / 操作 / 位移),否则鼠标会被多源争抢"
        )
        warn.setStyleSheet(
            "QLabel { color: #b00; padding: 8px 12px; background-color: #fff0f0; "
            "border-top: 1px solid #f5c0c0; }"
        )
        warn.setWordWrap(True)
        outer.addWidget(warn)

        return group

    # ------------------------------------------------------------------
    # 行布局辅助
    # ------------------------------------------------------------------

    def _build_hotkey_row(self) -> QFrame:
        """热键行:启动 / 停止 + 注册状态。视觉上独立(浅黄底)。"""
        frame = QFrame()
        frame.setObjectName("hotkeyRow")
        frame.setMinimumHeight(44)
        frame.setStyleSheet(
            "QFrame#hotkeyRow { background-color: #fff8e1; "
            "border-bottom: 1px solid #e0d4a0; }"
        )
        h = QHBoxLayout(frame)
        h.setContentsMargins(12, 8, 12, 8)
        h.setSpacing(8)

        label = QLabel("🎮 全局热键:")
        label.setStyleSheet("QLabel { font-weight: bold; }")
        h.addWidget(label)

        h.addSpacing(8)
        h.addWidget(QLabel("启动"))
        self.start_hotkey_edit = QLineEdit(DEFAULT_START_HOTKEY)
        self.start_hotkey_edit.setFixedWidth(70)
        self.start_hotkey_edit.setToolTip(
            "仅接受单键:f1-f24 / 字母 / 数字 / numpad0-9 / space / enter / esc 等;不支持组合键"
        )
        self.start_hotkey_edit.editingFinished.connect(self._on_hotkey_edit_finished)
        h.addWidget(self.start_hotkey_edit)

        h.addSpacing(16)
        h.addWidget(QLabel("停止"))
        self.stop_hotkey_edit = QLineEdit(DEFAULT_STOP_HOTKEY)
        self.stop_hotkey_edit.setFixedWidth(70)
        self.stop_hotkey_edit.setToolTip("仅接受单键;不能与启动热键或图库 F8/F9 相同")
        self.stop_hotkey_edit.editingFinished.connect(self._on_hotkey_edit_finished)
        h.addWidget(self.stop_hotkey_edit)

        h.addStretch()
        self.hotkey_status_label = QLabel("热键: 未注册")
        self.hotkey_status_label.setStyleSheet("QLabel { color: #888; }")
        h.addWidget(self.hotkey_status_label)

        return frame

    def _build_step_row(
        self, badge_text: str, title: str, description: str,
        input_widget: Optional[QWidget] = None, input_suffix: str = "",
    ) -> QFrame:
        """单步骤行:左侧编号徽章 + 中间(标题 + 描述)+ 右侧输入控件。底边线分隔。"""
        frame = QFrame()
        frame.setObjectName("stepRow")
        # 防止外层 VBoxLayout 把行高压扁(8 行 + 热键 + 警告会超出默认空间);
        # 56 = padding(20) + 标题(18) + 间距(2) + 描述(14) + 安全余量
        frame.setMinimumHeight(56)
        frame.setStyleSheet(
            "QFrame#stepRow { background-color: #fafafa; "
            "border-bottom: 1px solid #e0e0e0; }"
        )
        h = QHBoxLayout(frame)
        h.setContentsMargins(12, 8, 12, 8)
        h.setSpacing(12)

        # 徽章(2-3 字符的胶囊形)
        badge = QLabel(badge_text)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(40, 28)
        badge.setStyleSheet(
            "QLabel { background-color: #2196F3; color: white; "
            "border-radius: 14px; font-weight: bold; font-size: 12px; }"
        )
        h.addWidget(badge, alignment=Qt.AlignTop)

        # 标题 + 描述 竖列
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("QLabel { font-weight: bold; font-size: 13px; }")
        text_box.addWidget(title_lbl)
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("QLabel { color: #555; font-size: 11px; }")
        desc_lbl.setWordWrap(True)
        text_box.addWidget(desc_lbl)
        h.addLayout(text_box, stretch=1)

        # 右侧输入区
        if input_widget is not None:
            right = QHBoxLayout()
            right.setSpacing(4)
            right.addWidget(input_widget)
            if input_suffix:
                suffix_lbl = QLabel(input_suffix)
                suffix_lbl.setStyleSheet("QLabel { color: #666; }")
                right.addWidget(suffix_lbl)
            wrap = QWidget()
            wrap.setLayout(right)
            h.addWidget(wrap, alignment=Qt.AlignVCenter)
        else:
            info_lbl = QLabel("自动")
            info_lbl.setStyleSheet(
                "QLabel { color: #888; font-style: italic; "
                "padding: 4px 10px; background-color: #eee; border-radius: 4px; }"
            )
            h.addWidget(info_lbl, alignment=Qt.AlignVCenter)

        return frame

    @staticmethod
    def _make_spin(default: float, minimum: float, maximum: float, step: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(1)
        spin.setValue(default)
        spin.setFixedWidth(80)
        return spin

    @staticmethod
    def _make_key_edit(default: str = "", placeholder: str = "") -> QLineEdit:
        edit = QLineEdit(default)
        edit.setFixedWidth(80)
        edit.setAlignment(Qt.AlignCenter)
        if placeholder:
            edit.setPlaceholderText(placeholder)
        return edit

    # --- 控制按钮 ----------------------------------------------------------

    def _build_control_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.btn_start = QPushButton("开始钓鱼 (F11)")
        self.btn_start.clicked.connect(self._on_start_clicked)
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #FAFAFA; }"
        )
        row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止钓鱼 (F12)")
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #FAFAFA; }"
        )
        row.addWidget(self.btn_stop)
        return row

    # --- 状态 / 预览 -------------------------------------------------------

    def _build_status_group(self) -> QGroupBox:
        group = QGroupBox("运行状态 / 实时预览")
        layout = QVBoxLayout(group)

        self.state_label = QLabel("状态: 等待启动(按 F11 开始)")
        self.state_label.setStyleSheet(
            "QLabel { font-weight: bold; font-size: 14px; padding: 4px; }"
        )
        layout.addWidget(self.state_label)

        self.stats_label = QLabel("轮次 0  成功 0  超时 0  连续失败 0")
        layout.addWidget(self.stats_label)

        self.last_trigger_label = QLabel("最近触发: —")
        self.last_trigger_label.setStyleSheet("QLabel { color: #555; font-size: 11px; }")
        self.last_trigger_label.setWordWrap(True)
        layout.addWidget(self.last_trigger_label)

        # 预览画面(填满剩余空间)
        self.preview_label = QLabel("预览(开始钓鱼后显示画面)")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(320, 240)
        self.preview_label.setStyleSheet(
            "QLabel { background-color: #1e1e1e; color: #888; border: 1px solid #444; }"
        )
        # 监听 preview_label 自己的 resize(splitter 拖动也算)以同步缓存尺寸
        self.preview_label.installEventFilter(self)
        layout.addWidget(self.preview_label, stretch=1)
        return group

    # ------------------------------------------------------------------
    # 模型加载
    # ------------------------------------------------------------------

    def _load_models(self) -> None:
        """加载模型列表。

        - **standalone 模式**(独立 exe):跳过 `model_manager`(不连 DB / 不扫
          `training_result/` / `models/`),只把 `good_models/wow_fish.pt`
          作为唯一选项,UI 上下拉显示但锁死
        - **完整 app 模式**:走原来的 `model_manager.get_model_list()`,扫训练 +
          手动导入 + 内置预训练 + 精选模型
        """
        self.model_combo.clear()
        if is_standalone_mode():
            bundled = resolve_bundled_model_path()
            if bundled:
                self.model_combo.addItem(BUNDLED_MODEL_FILENAME, bundled)
                self.model_combo.setCurrentIndex(0)
                self.model_combo.setEnabled(False)   # standalone 锁死,无别的可选
                logger.info("standalone 模式加载内置模型: %s", bundled)
            else:
                logger.error("standalone 模式找不到内置模型 %s", BUNDLED_MODEL_FILENAME)
            return

        try:
            # 延迟 import,避免 standalone 打包时把 training_result / db_manager 拖入
            from training_result.model_manager import model_manager
            models = model_manager.get_model_list()
            default_idx = 0
            for idx, m in enumerate(models):
                self.model_combo.addItem(m["filename"], m["path"])
                if m["filename"] == PREFERRED_DEFAULT_MODEL:
                    default_idx = idx
            if self.model_combo.count() > 0:
                self.model_combo.setCurrentIndex(default_idx)
        except Exception as e:
            logger.error("加载模型列表失败: %s", e)

    def showEvent(self, event):  # noqa: N802 — Qt 命名约定
        super().showEvent(event)
        self._load_models()

    # ------------------------------------------------------------------
    # 信号槽
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._state_changed.connect(self._on_state_changed_main)
        self._round_completed.connect(self._on_round_completed_main)
        self._triggered.connect(self._on_triggered_main)
        self._error_received.connect(self._on_error_main)
        self._frame_ready.connect(self._on_frame_ready_main)
        self._hotkey_start_requested.connect(self._on_start_clicked)
        self._hotkey_stop_requested.connect(self._on_stop_clicked)

    # ------------------------------------------------------------------
    # 区域选择
    # ------------------------------------------------------------------

    def _select_screen_area(self) -> None:
        try:
            self._selector = ScreenAreaSelector()
            self._selector.area_selected.connect(self._on_area_selected)
            self._selector.cancelled.connect(lambda: None)
            self._selector.show()
            self._selector.activateWindow()
            self._selector.raise_()
        except Exception as e:
            logger.error("选择区域失败: %s", e)
            QMessageBox.critical(self, "错误", f"选择区域失败: {e}")

    def _on_area_selected(self, x: int, y: int, width: int, height: int) -> None:
        self._monitor_area = (x, y, width, height)
        self.area_label.setText(f"({x}, {y})  {width}×{height}")

    def _reset_area(self) -> None:
        self._monitor_area = None
        self.area_label.setText("全屏(主显示器)")

    # ------------------------------------------------------------------
    # 热键
    # ------------------------------------------------------------------

    def _register_hotkeys(self) -> None:
        """根据当前 LineEdit 内容(重新)注册全局热键。失败时 UI 提示。"""
        start_key = self._normalize_hotkey(self.start_hotkey_edit.text())
        stop_key = self._normalize_hotkey(self.stop_hotkey_edit.text())
        err = self._validate_hotkeys(start_key, stop_key)
        if err:
            self.hotkey_status_label.setText(f"热键: {err}")
            self.hotkey_status_label.setStyleSheet("QLabel { color: #b00; }")
            self._unregister_hotkeys()
            return

        try:
            import keyboard
        except Exception as e:
            self.hotkey_status_label.setText(f"热键: keyboard 库不可用 ({e})")
            self.hotkey_status_label.setStyleSheet("QLabel { color: #b00; }")
            return

        # 先卸载旧的(键变了,需要重新注册)
        self._unregister_hotkeys()

        try:
            keyboard.add_hotkey(start_key, self._hotkey_start_requested.emit)
            keyboard.add_hotkey(stop_key, self._hotkey_stop_requested.emit)
            self._registered_start = start_key
            self._registered_stop = stop_key
            self.hotkey_status_label.setText(
                f"热键: 启动 [{start_key.upper()}] / 停止 [{stop_key.upper()}] 已注册"
            )
            self.hotkey_status_label.setStyleSheet("QLabel { color: #2a7; }")
            logger.info("钓鱼热键已注册: start=%s stop=%s", start_key, stop_key)
        except Exception as e:
            logger.error("注册钓鱼热键失败: %s", e)
            self.hotkey_status_label.setText(f"热键: 注册失败 ({e})")
            self.hotkey_status_label.setStyleSheet("QLabel { color: #b00; }")

    def _unregister_hotkeys(self) -> None:
        if not self._registered_start and not self._registered_stop:
            return
        try:
            import keyboard
            for key in (self._registered_start, self._registered_stop):
                if key:
                    try:
                        keyboard.remove_hotkey(key)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("卸载钓鱼热键失败: %s", e)
        self._registered_start = ""
        self._registered_stop = ""

    def _on_hotkey_edit_finished(self) -> None:
        # 钓鱼运行时不允许改键
        if self._loop is not None and self._loop.is_running:
            return
        self._register_hotkeys()

    @staticmethod
    def _normalize_hotkey(text: str) -> str:
        return (text or "").strip().lower()

    @staticmethod
    def _validate_hotkeys(start_key: str, stop_key: str) -> str:
        """返回 "" 表示通过,否则返回错误描述。"""
        for label, key in (("启动", start_key), ("停止", stop_key)):
            if not key:
                return f"{label}热键为空"
            if "+" in key or " " in key:
                return f"{label}热键不支持组合键"
            if key in LIBRARY_HOTKEYS:
                return f"{label}热键 {key.upper()} 与图库冲突"
        if start_key == stop_key:
            return "启动与停止热键不能相同"
        return ""

    # ------------------------------------------------------------------
    # 启停
    # ------------------------------------------------------------------

    def _on_start_clicked(self) -> None:
        if self._loop is not None and self._loop.is_running:
            return

        # 校验抛竿键必填
        cast_key = self.cast_edit.text().strip().lower()
        if not cast_key:
            QMessageBox.warning(self, "提示", "抛竿键必填")
            return
        # 校验前/后处理按键(若填了)不是组合键
        for label, edit in (("钓鱼前准备", self.pre_action_edit),
                            ("钓鱼后处理", self.post_action_edit),
                            ("抛竿", self.cast_edit)):
            key = edit.text().strip().lower()
            if key and ("+" in key or " " in key):
                QMessageBox.warning(self, "提示", f"{label}按键不支持组合键")
                return

        if self.model_combo.currentIndex() < 0:
            QMessageBox.warning(self, "提示", "请先选择模型")
            return

        config = FishingConfig(
            model_path=self.model_combo.currentData(),
            confidence=self.conf_slider.value() / 100.0,
            device=self.device_combo.currentData() or "cpu",
            monitor_area=self._monitor_area,
            prepare_wait_s=self.prepare_spin.value(),
            pre_action_key=self.pre_action_edit.text().strip().lower(),
            cast_key=cast_key,
            wait_land_s=self.wait_land_spin.value(),
            detect_timeout_s=self.detect_timeout_spin.value(),
            post_trigger_wait_s=self.post_trigger_spin.value(),
            post_action_key=self.post_action_edit.text().strip().lower(),
        )

        self._loop = FishingLoop(
            config=config,
            on_state_change=lambda s, r, e, t: self._state_changed.emit(s, r, e, t),
            on_round_complete=lambda stats: self._round_completed.emit(stats),
            on_trigger=lambda det: self._triggered.emit(det),
            on_error=lambda msg: self._error_received.emit(msg),
            on_frame=self._on_raw_frame,
        )

        # 重置预览首帧标志,便于日志确认预览管线工作
        self._preview_logged = False

        if not self._loop.start():
            QMessageBox.warning(self, "提示", "启动失败")
            self._loop = None
            return

        self._set_ui_locked(True)
        self.last_trigger_label.setText("最近触发: —")
        logger.info(
            "启动钓鱼:模型 %s  设备 %s  抛竿 [%s]  超时 %.1fs",
            config.model_path, config.device,
            config.cast_key.upper(), config.detect_timeout_s,
        )

    def _on_stop_clicked(self) -> None:
        if self._loop is None or not self._loop.is_running:
            return
        logger.info("收到停止信号,等待当前步骤结束")
        self._loop.stop()
        # 不在 UI 线程 join(会卡 UI),靠 STOPPING/IDLE 状态回调解锁

    # ------------------------------------------------------------------
    # 主线程 slots
    # ------------------------------------------------------------------

    def _on_state_changed_main(
        self, state: FishingState, round_idx: int,
        elapsed: float, total: float,
    ) -> None:
        label = STATE_LABEL.get(state, state.name)
        if state == FishingState.IDLE:
            # 工作线程已退出,解锁 UI + 清预览
            self.state_label.setText("状态: 等待启动(按 F11 开始)")
            self._set_ui_locked(False)
            self.preview_label.clear()
            self.preview_label.setText("预览(开始钓鱼后显示画面)")
            self._loop = None
            return

        if total > 0:
            self.state_label.setText(
                f"状态: 第 {round_idx} 轮 — {label}  {elapsed:.1f} / {total:.1f} s"
            )
        else:
            self.state_label.setText(
                f"状态: 第 {round_idx} 轮 — {label}"
            )

    def _on_round_completed_main(self, stats: FishingStats) -> None:
        warn = ""
        if stats.consecutive_fail > 5:
            warn = "  ⚠"
        self.stats_label.setText(
            f"轮次 {stats.rounds}  成功 {stats.success}  "
            f"超时 {stats.timeout}  连续失败 {stats.consecutive_fail}{warn}"
        )
        if stats.consecutive_fail > 5:
            self.stats_label.setStyleSheet("QLabel { color: #b00; font-weight: bold; }")
        else:
            self.stats_label.setStyleSheet("")

    def _on_triggered_main(self, det: dict) -> None:
        cls = det.get("class_name", "?")
        local_cx, local_cy = det.get("center", (0, 0))
        # 转屏幕绝对坐标(选区识别时 + 偏移),与 FishingLoop._do_pick_up 保持一致
        if self._monitor_area is not None:
            abs_cx = int(local_cx) + int(self._monitor_area[0])
            abs_cy = int(local_cy) + int(self._monitor_area[1])
            coord_str = f"屏幕({abs_cx},{abs_cy})"
        else:
            coord_str = f"屏幕({local_cx},{local_cy})"
        conf = float(det.get("confidence", 0.0))
        disp = det.get("displacement_px", 0)
        ratio = det.get("displacement_ratio", 0.0)
        ts = datetime.now().strftime("%H:%M:%S")
        self.last_trigger_label.setText(
            f"最近触发 [{ts}]: {cls} @ {coord_str}  conf={conf:.2f}  "
            f"位移 {disp} px ({ratio:.0%} bbox)"
        )

    def _on_error_main(self, msg: str) -> None:
        # 异常单独突出显示在「最近触发」位置,加红色
        ts = datetime.now().strftime("%H:%M:%S")
        self.last_trigger_label.setText(f"[错误 {ts}] {msg}")
        self.last_trigger_label.setStyleSheet("QLabel { color: #b00; font-size: 11px; }")
        logger.error("钓鱼运行时错误: %s", msg)

    # ------------------------------------------------------------------
    # 预览(后台线程渲染 + 主线程 setPixmap)
    # ------------------------------------------------------------------

    def _on_raw_frame(self, frame, detections: list) -> None:
        """截图后台线程回调:在此完成所有 numpy / OpenCV 图像处理,
        发已 scaled 好的 QImage 到主线程。
        """
        try:
            import cv2
            import numpy as np
            from recognition.visualizer import draw_detections

            annotated = draw_detections(frame, detections)
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            rgb = np.ascontiguousarray(rgb)
            h, w = rgb.shape[:2]
            qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888)
            scaled = qimg.scaled(
                self._preview_w, self._preview_h,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
            # 必须 copy:rgb 这个 numpy array 在本函数返回后会被释放,
            # 而 QImage 是浅持有外部内存。.copy() 自带数据所有权,跨线程安全。
            scaled = scaled.copy()
            if not self._preview_logged:
                logger.info("钓鱼预览首帧到达: %dx%d", w, h)
                self._preview_logged = True
            self._frame_ready.emit(scaled)
        except Exception as e:
            logger.error("钓鱼预览帧处理出错: %s", e, exc_info=True)

    def _on_frame_ready_main(self, qimg: QImage) -> None:
        """主线程 slot:只做 setPixmap,<1ms。"""
        self.preview_label.setPixmap(QPixmap.fromImage(qimg))

    def resizeEvent(self, event):  # noqa: N802 — Qt 命名约定
        super().resizeEvent(event)
        self._refresh_preview_size_cache()

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self.preview_label and event.type() == QEvent.Resize:
            self._refresh_preview_size_cache()
        return super().eventFilter(obj, event)

    def _refresh_preview_size_cache(self) -> None:
        if hasattr(self, "preview_label") and self.preview_label is not None:
            sz = self.preview_label.size()
            if sz.width() > 0 and sz.height() > 0:
                self._preview_w = sz.width()
                self._preview_h = sz.height()

    # ------------------------------------------------------------------
    # UI 锁定
    # ------------------------------------------------------------------

    def _set_ui_locked(self, locked: bool) -> None:
        """运行时 True=锁定,所有参数控件禁用;False=解锁。"""
        controls = [
            self.model_combo, self.conf_slider, self.device_combo,
            self.btn_select_area, self.btn_reset_area,
            self.start_hotkey_edit, self.stop_hotkey_edit,
            self.prepare_spin, self.pre_action_edit,
            self.cast_edit, self.wait_land_spin, self.detect_timeout_spin,
            self.post_trigger_spin, self.post_action_edit,
        ]
        for c in controls:
            c.setEnabled(not locked)

        self.btn_start.setEnabled(not locked)
        self.btn_stop.setEnabled(locked)

    # ------------------------------------------------------------------
    # 关闭
    # ------------------------------------------------------------------

    def close(self):
        self._shutdown()
        return super().close()

    def closeEvent(self, event):
        self._shutdown()
        event.accept()

    def _shutdown(self) -> None:
        if self._loop is not None and self._loop.is_running:
            self._loop.stop()
            self._loop.wait_until_stopped(timeout=2.0)
            self._loop = None
        self._unregister_hotkeys()
