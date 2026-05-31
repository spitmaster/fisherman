#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后台 IO 测试对话框(BackgroundIoTestDialog)。

目的:在「后台钓鱼」正式动工前,用 UI 一键验证 recognition/window_io.py 三件事
在用户机器 + 其 WoW 版本上是否可行:
  1. 选窗口 + 抓帧:被遮挡也能看到真实画面?(PrintWindow)
  2. 投抛竿键:WoW 后台认 PostMessage 按键?
  3. 投右键:在预览图上点浮漂 → WoW 后台拾取?(整条路线的生死线)

线程模型:全部在主线程。PrintWindow / PostMessage 都是瞬时调用,实时预览用 QTimer
低频(默认 3 FPS)刷新,不阻塞 UI,无需后台线程(不触碰架构不变量 2)。
"""

from __future__ import annotations

import logging
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from recognition import window_io

logger = logging.getLogger(__name__)


class _ClickableImageLabel(QLabel):
    """显示抓帧并把点击映射回**窗口客户区坐标**的 QLabel。

    内部记录最近一帧的原始尺寸 (_src_w/_src_h) 与渲染到 label 上的 pixmap 矩形
    (按 KeepAspectRatio 居中),点击时反算出客户区像素坐标,emit client_clicked(x, y)。
    """

    client_clicked = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(480, 300)
        self.setStyleSheet(
            "QLabel { background-color: #1e1e1e; color: #888; border: 1px solid #444; }"
        )
        self.setText("选择窗口后点「抓帧」")
        self._src_w = 0
        self._src_h = 0
        # pixmap 在 label 内的渲染区域(left, top, draw_w, draw_h)
        self._render_rect = (0, 0, 0, 0)

    def show_frame(self, qimg: QImage) -> None:
        self._src_w = qimg.width()
        self._src_h = qimg.height()
        lbl_w = max(self.width(), 1)
        lbl_h = max(self.height(), 1)
        scaled = qimg.scaled(lbl_w, lbl_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        draw_w, draw_h = scaled.width(), scaled.height()
        left = (lbl_w - draw_w) // 2
        top = (lbl_h - draw_h) // 2
        self._render_rect = (left, top, draw_w, draw_h)
        self.setPixmap(QPixmap.fromImage(scaled))

    def mousePressEvent(self, event):  # noqa: N802 — Qt 命名约定
        if self._src_w <= 0 or self._src_h <= 0:
            return
        left, top, draw_w, draw_h = self._render_rect
        if draw_w <= 0 or draw_h <= 0:
            return
        px = event.x() - left
        py = event.y() - top
        if px < 0 or py < 0 or px >= draw_w or py >= draw_h:
            return  # 点在黑边上,忽略
        # 渲染坐标 → 原始客户区坐标
        cx = int(px * self._src_w / draw_w)
        cy = int(py * self._src_h / draw_h)
        self.client_clicked.emit(cx, cy)


class BackgroundIoTestDialog(QDialog):
    """后台 IO 可行性测试面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("后台 IO 测试 — 窗口捕获 / 投键 / 投右键")
        self.resize(820, 760)

        self._hwnd = 0
        self._picked_xy = None  # 在预览图上选中的客户区坐标 (x, y)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._grab_once)

        self._init_ui()

        if not window_io.is_supported():
            self._log("⚠ 当前平台非 Windows,window_io 不可用")
            self._set_all_enabled(False)
        else:
            self._refresh_windows()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)

        # --- 1. 选窗口 ---
        win_group = QGroupBox("① 选择目标窗口")
        wl = QHBoxLayout(win_group)
        wl.addWidget(QLabel("窗口:"))
        self.window_combo = QComboBox()
        self.window_combo.setMinimumWidth(420)
        self.window_combo.currentIndexChanged.connect(self._on_window_changed)
        wl.addWidget(self.window_combo, stretch=1)
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.clicked.connect(self._refresh_windows)
        wl.addWidget(self.btn_refresh)
        root.addWidget(win_group)

        # --- 2. 抓帧 ---
        cap_group = QGroupBox("② 抓帧测试(被遮挡也该能抓到真实画面)")
        cl = QVBoxLayout(cap_group)
        cap_row = QHBoxLayout()
        self.btn_grab = QPushButton("📷 抓一帧")
        self.btn_grab.clicked.connect(self._grab_once)
        cap_row.addWidget(self.btn_grab)
        self.live_check = QCheckBox("实时预览(3 FPS)")
        self.live_check.toggled.connect(self._on_live_toggled)
        cap_row.addWidget(self.live_check)
        cap_row.addStretch()
        self.cap_info_label = QLabel("尺寸 — / 亮度 —")
        self.cap_info_label.setStyleSheet("QLabel { color: #555; }")
        cap_row.addWidget(self.cap_info_label)
        cl.addLayout(cap_row)

        self.preview = _ClickableImageLabel()
        self.preview.client_clicked.connect(self._on_preview_clicked)
        cl.addWidget(self.preview, stretch=1)

        hint = QLabel("💡 把 WoW 切到后台 / 用别的窗口盖住它,再抓帧;打开实时预览能看到后台画面是否在动")
        hint.setStyleSheet("QLabel { color: #888; font-size: 11px; }")
        hint.setWordWrap(True)
        cl.addWidget(hint)
        root.addWidget(cap_group, stretch=1)

        # --- 3. 投键 ---
        key_group = QGroupBox("③ 投按键测试(盯着 WoW 看人物是否抛竿)")
        kl = QHBoxLayout(key_group)
        kl.addWidget(QLabel("按键:"))
        self.key_edit = QLineEdit("-")
        self.key_edit.setFixedWidth(60)
        self.key_edit.setAlignment(Qt.AlignCenter)
        self.key_edit.setToolTip("单字符,默认抛竿键 '-'")
        kl.addWidget(self.key_edit)
        self.btn_send_key = QPushButton("⌨ 发送按键到后台窗口")
        self.btn_send_key.clicked.connect(self._send_key)
        kl.addWidget(self.btn_send_key)
        kl.addStretch()
        root.addWidget(key_group)

        # --- 4. 投右键 ---
        click_group = QGroupBox("④ 投右键测试 ★路线生死线(WoW 世界交互可能无效)")
        cgl = QVBoxLayout(click_group)
        crow = QHBoxLayout()
        self.pick_label = QLabel("目标点: 未选(请在上方预览图里点一下浮漂位置)")
        self.pick_label.setStyleSheet("QLabel { color: #555; }")
        crow.addWidget(self.pick_label, stretch=1)
        self.btn_send_rclick = QPushButton("🖱 发送右键到该点")
        self.btn_send_rclick.clicked.connect(self._send_right_click)
        self.btn_send_rclick.setEnabled(False)
        crow.addWidget(self.btn_send_rclick)
        cgl.addLayout(crow)
        root.addWidget(click_group)

        # --- 日志 ---
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(120)
        self.log_view.setStyleSheet("QTextEdit { font-family: Consolas, monospace; font-size: 11px; }")
        root.addWidget(self.log_view)

    # ------------------------------------------------------------------
    # 窗口选择
    # ------------------------------------------------------------------

    def _refresh_windows(self) -> None:
        self.window_combo.blockSignals(True)
        self.window_combo.clear()
        wins = window_io.enum_windows()
        for hwnd, title in wins:
            # 标题过长截断显示,完整放进 itemData 的 tooltip
            disp = title if len(title) <= 60 else title[:57] + "…"
            self.window_combo.addItem(f"0x{hwnd:08X}  {disp}", hwnd)
        self.window_combo.blockSignals(False)
        self._log(f"刷新窗口列表:{len(wins)} 个")
        # 优先自动选中含「魔兽」/ wow 的窗口
        for i in range(self.window_combo.count()):
            title = self.window_combo.itemText(i).lower()
            if "魔兽" in title or "wow" in title or "warcraft" in title:
                self.window_combo.setCurrentIndex(i)
                break
        self._on_window_changed()

    def _on_window_changed(self) -> None:
        self._hwnd = self.window_combo.currentData() or 0
        if self._hwnd:
            w, h = window_io.get_client_size(self._hwnd)
            self._log(f"选中窗口 hwnd=0x{self._hwnd:08X}  客户区 {w}×{h}")
        # 切窗口后清掉旧的选点
        self._picked_xy = None
        self.btn_send_rclick.setEnabled(False)
        self.pick_label.setText("目标点: 未选(请在上方预览图里点一下浮漂位置)")

    # ------------------------------------------------------------------
    # 抓帧
    # ------------------------------------------------------------------

    def _on_live_toggled(self, on: bool) -> None:
        if on:
            self._timer.start(333)  # ~3 FPS
            self._log("实时预览开启")
        else:
            self._timer.stop()
            self._log("实时预览关闭")

    def _grab_once(self) -> None:
        if not self._hwnd:
            self._log("⚠ 未选窗口")
            return
        if window_io.is_minimized(self._hwnd):
            self.cap_info_label.setText("窗口已最小化")
            self._log("✗ 窗口已最小化:系统停渲抓不到。请勿最小化,用遮挡/虚拟桌面替代")
            return
        frame = window_io.capture_window(self._hwnd)
        if frame is None:
            self.cap_info_label.setText("抓帧失败")
            self._log("✗ 抓帧失败(独占全屏?需切窗口化)")
            return
        h, w = frame.shape[:2]
        mean = float(frame.mean())
        # BGR → RGB 给 Qt
        rgb = frame[:, :, ::-1].copy()
        qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888)
        self.preview.show_frame(qimg)
        verdict = "全黑,PrintWindow 抓不到" if mean < 3 else "有画面"
        self.cap_info_label.setText(f"尺寸 {w}×{h} / 亮度 {mean:.1f} / {verdict}")
        # 实时模式下不刷屏日志,只单次抓帧记一行
        if not self._timer.isActive():
            self._log(f"📷 抓帧 {w}×{h} 亮度 {mean:.1f} → {verdict}")

    # ------------------------------------------------------------------
    # 投键
    # ------------------------------------------------------------------

    def _send_key(self) -> None:
        if not self._hwnd:
            self._log("⚠ 未选窗口")
            return
        key = self.key_edit.text().strip()
        if len(key) != 1:
            self._log("⚠ 按键须为单字符")
            return
        ok = window_io.post_key(self._hwnd, key)
        self._log(f"⌨ 投按键 {key!r} → PostMessage {'已投递' if ok else '失败'};盯 WoW 看是否抛竿")

    # ------------------------------------------------------------------
    # 投右键
    # ------------------------------------------------------------------

    def _on_preview_clicked(self, cx: int, cy: int) -> None:
        self._picked_xy = (cx, cy)
        self.pick_label.setText(f"目标点: 客户区 ({cx}, {cy})")
        self.btn_send_rclick.setEnabled(True)

    def _send_right_click(self) -> None:
        if not self._hwnd or self._picked_xy is None:
            return
        x, y = self._picked_xy
        ok = window_io.post_right_click(self._hwnd, x, y)
        self._log(
            f"🖱 投右键 @客户区({x},{y}) → PostMessage {'已投递' if ok else '失败'};"
            f"看 WoW 后台有无拾取/交互"
        )

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(f"[{ts}] {msg}")

    def _set_all_enabled(self, on: bool) -> None:
        for w in self.findChildren(QWidget):
            if w is not self.log_view:
                w.setEnabled(on)

    def closeEvent(self, event):  # noqa: N802
        self._timer.stop()
        event.accept()
