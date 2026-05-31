#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
窗口内检测区域选择器(WindowRegionSelector)— M7 后台钓鱼。

详见 docs/SPEC.md §2.16 F2.16.3。

与 `gui/screen_area_selector.py`(全屏遮罩框选屏幕绝对坐标)不同:后台模式下游戏可能被
遮挡,无法在真实屏幕上框选。本对话框先用 `window_io.capture_window(hwnd)` 抓一帧目标窗口
画面,显示在对话框里,用户在**这帧画面上**橡皮筋框选,返回**客户区相对坐标** (x, y, w, h)。

线程模型:纯主线程。抓帧是瞬时调用,框选是鼠标事件,无后台线程。
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QDialog,
)

from recognition import window_io

logger = logging.getLogger(__name__)


class _RubberBandLabel(QLabel):
    """显示窗口抓帧并支持橡皮筋框选,把选区映射回客户区坐标的 QLabel。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640, 400)
        self.setStyleSheet("QLabel { background-color: #1e1e1e; border: 1px solid #444; }")
        # 不开 mouseTracking:只在按住拖动时收 move 事件,松开即停(否则框会一直跟手)
        self._qimg: Optional[QImage] = None        # 原始帧,resize 时按当前尺寸重渲染
        self._src_w = 0
        self._src_h = 0
        self._render_rect = (0, 0, 0, 0)   # pixmap 在 label 内的渲染矩形 (left, top, w, h)
        self._selecting = False                    # 是否正在拖动中(按下到松开)
        self._sel_start: Optional[QPoint] = None  # widget 坐标
        self._sel_cur: Optional[QPoint] = None

    def show_frame(self, qimg: QImage) -> None:
        self._qimg = qimg
        self._src_w = qimg.width()
        self._src_h = qimg.height()
        # 重新抓帧后旧选区作废
        self._sel_start = None
        self._sel_cur = None
        self._render()

    def _render(self) -> None:
        """按 label **当前**尺寸把原始帧缩放居中,刷新 _render_rect。
        必须在每次 resize 后重算,否则 _render_rect 与实际显示不符,鼠标映射全错。"""
        if self._qimg is None:
            return
        lbl_w = max(self.width(), 1)
        lbl_h = max(self.height(), 1)
        scaled = self._qimg.scaled(lbl_w, lbl_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        draw_w, draw_h = scaled.width(), scaled.height()
        left = (lbl_w - draw_w) // 2
        top = (lbl_h - draw_h) // 2
        self._render_rect = (left, top, draw_w, draw_h)
        self.setPixmap(QPixmap.fromImage(scaled))
        self.update()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        # 对话框首次显示 / 拖拉改尺寸都会触发;重渲染让坐标系跟手。选区随之作废。
        self._selecting = False
        self._sel_start = None
        self._sel_cur = None
        self._render()

    def _clamp_to_render(self, pos: QPoint) -> QPoint:
        left, top, w, h = self._render_rect
        x = min(max(pos.x(), left), left + w)
        y = min(max(pos.y(), top), top + h)
        return QPoint(x, y)

    def mousePressEvent(self, event):  # noqa: N802
        if self._src_w <= 0 or event.button() != Qt.LeftButton:
            return
        self._selecting = True
        self._sel_start = self._clamp_to_render(event.pos())
        self._sel_cur = self._sel_start
        self.update()

    def mouseMoveEvent(self, event):  # noqa: N802
        # 仅拖动中更新终点;松开后 _selecting=False,框锁定不再跟手
        if self._selecting:
            self._sel_cur = self._clamp_to_render(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):  # noqa: N802
        if self._selecting and event.button() == Qt.LeftButton:
            self._sel_cur = self._clamp_to_render(event.pos())
            self._selecting = False
            self.update()

    def paintEvent(self, event):  # noqa: N802
        super().paintEvent(event)  # 先画底图 pixmap
        if self._sel_start is None or self._sel_cur is None:
            return
        rect = QRect(self._sel_start, self._sel_cur).normalized()
        painter = QPainter(self)
        painter.setPen(QPen(QColor(0, 200, 0), 2, Qt.SolidLine))
        painter.setBrush(QColor(0, 200, 0, 40))
        painter.drawRect(rect)
        painter.end()

    def client_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """把 widget 选区映射回客户区坐标 (x, y, w, h);选区过小返回 None。"""
        if self._sel_start is None or self._sel_cur is None or self._src_w <= 0:
            return None
        left, top, draw_w, draw_h = self._render_rect
        if draw_w <= 0 or draw_h <= 0:
            return None
        rect = QRect(self._sel_start, self._sel_cur).normalized()
        # widget → 渲染区相对 → 客户区
        sx = self._src_w / draw_w
        sy = self._src_h / draw_h
        x = int((rect.left() - left) * sx)
        y = int((rect.top() - top) * sy)
        w = int(rect.width() * sx)
        h = int(rect.height() * sy)
        x = max(0, min(x, self._src_w))
        y = max(0, min(y, self._src_h))
        w = max(0, min(w, self._src_w - x))
        h = max(0, min(h, self._src_h - y))
        if w < 8 or h < 8:  # 太小视为误操作
            return None
        return (x, y, w, h)


class WindowRegionSelector(QDialog):
    """在目标窗口的抓帧画面上框选检测子区域。

    用法:
        dlg = WindowRegionSelector(hwnd, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            region = dlg.result_region  # None=整窗,或 (x,y,w,h) 客户区坐标
    """

    def __init__(self, hwnd: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("窗口内检测区域 — 在画面上拖出矩形")
        self.resize(900, 640)
        self._hwnd = hwnd
        self.result_region: Optional[Tuple[int, int, int, int]] = None

        root = QVBoxLayout(self)

        tip = QLabel("在下方游戏画面上按住拖动框出检测区域;不框选直接点「整窗」用整个客户区。")
        tip.setStyleSheet("QLabel { color: #555; }")
        tip.setWordWrap(True)
        root.addWidget(tip)

        self._canvas = _RubberBandLabel()
        root.addWidget(self._canvas, stretch=1)

        btn_row = QHBoxLayout()
        self._btn_recapture = QPushButton("🔄 重新抓帧")
        self._btn_recapture.clicked.connect(self._grab)
        btn_row.addWidget(self._btn_recapture)
        self._btn_fullwin = QPushButton("整窗(不限制区域)")
        self._btn_fullwin.clicked.connect(self._use_full_window)
        btn_row.addWidget(self._btn_fullwin)
        btn_row.addStretch()

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Ok).setText("确定用此区域")
        self._buttons.accepted.connect(self._accept_region)
        self._buttons.rejected.connect(self.reject)
        btn_row.addWidget(self._buttons)
        root.addLayout(btn_row)

        self._grab()

    def _grab(self) -> None:
        if window_io.is_minimized(self._hwnd):
            self._canvas.setText(
                "窗口已最小化,无法抓帧。\n请先还原游戏窗口(可被遮挡 / 放到别的虚拟桌面,但勿最小化)再框选。"
            )
            return
        frame = window_io.capture_window(self._hwnd)
        if frame is None:
            self._canvas.setText("抓帧失败(窗口已关闭 / 独占全屏?)")
            return
        h, w = frame.shape[:2]
        rgb = frame[:, :, ::-1].copy()  # BGR → RGB
        qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888)
        self._canvas.show_frame(qimg)

    def _use_full_window(self) -> None:
        self.result_region = None
        self.accept()

    def _accept_region(self) -> None:
        from PyQt5.QtWidgets import QMessageBox
        region = self._canvas.client_rect()
        if region is None:
            QMessageBox.information(
                self, "提示", "未框选有效区域。请在画面上拖出矩形,或点「整窗」。"
            )
            return
        self.result_region = region
        self.accept()
