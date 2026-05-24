#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
屏幕区域选择器

两种模式:
- 自由框选(默认):用户拖拽矩形框选,松开鼠标确认
- 固定尺寸跟随(fixed_size=(w, h)):W×H 矩形随鼠标移动,点击鼠标确认

选择完成后通过 area_selected(x, y, width, height) 信号返回结果(绝对屏幕坐标)。
"""

from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QGuiApplication, QCursor
from PyQt5.QtWidgets import QWidget


class ScreenAreaSelector(QWidget):
    """全屏区域选择覆盖层"""

    area_selected = pyqtSignal(int, int, int, int)  # x, y, width, height
    cancelled = pyqtSignal()

    def __init__(self, fixed_size: tuple = None):
        """
        fixed_size=(w, h) 启用固定尺寸跟随鼠标模式;
        fixed_size=None  使用自由拖拽框选(默认/旧行为)。
        """
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 必须显式声明可接收焦点,否则点击穿透/Alt-Tab 后键盘事件会丢
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.CrossCursor)

        self._fixed_size = fixed_size
        # 固定模式下需要无按键的 mouseMoveEvent
        if fixed_size is not None:
            self.setMouseTracking(True)

        # 覆盖所有屏幕：遍历所有 QScreen 求并集，避免某些驱动下 virtualGeometry 不完整
        geo = QRect()
        for scr in QGuiApplication.screens():
            geo = geo.united(scr.geometry())
        if geo.isEmpty():
            geo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geo)
        self._origin = geo.topLeft()

        # 自由模式状态
        self._start = None
        self._end = None
        self._dragging = False
        # 固定模式状态:当前跟随鼠标的矩形(本地坐标)
        self._fixed_rect = None

    # ------------------------------------------------------------- 工具 ----

    def _compute_fixed_rect(self, pos: QPoint) -> QRect:
        """以鼠标位置为中心算出固定矩形,clamp 到 overlay 内,避免越界。"""
        w, h = self._fixed_size
        x = pos.x() - w // 2
        y = pos.y() - h // 2
        x = max(0, min(x, max(0, self.width() - w)))
        y = max(0, min(y, max(0, self.height() - h)))
        return QRect(x, y, w, h)

    # ------------------------------------------------------------- 事件 ----

    def showEvent(self, event):
        super().showEvent(event)
        # 显式抢焦点,保证 Esc/Enter 一定能到达本 widget(否则点击穿透时焦点会丢到桌面)
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)
        if self._fixed_size is not None:
            # 用当前光标位置初始化跟随矩形,避免首次绘制时鼠标还没动就空白
            cursor_local = self.mapFromGlobal(QCursor.pos())
            self._fixed_rect = self._compute_fixed_rect(cursor_local)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # 半透明遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        if self._fixed_size is not None:
            # ----------------- 固定尺寸跟随模式 -----------------
            rect = self._fixed_rect
            if rect is not None:
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.fillRect(rect, Qt.transparent)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                # 关键:回填 alpha=1 的色块。完全透明像素在 WA_TranslucentBackground 下
                # 会导致鼠标穿透(mouseMove/click 都收不到),alpha=1 视觉不可见但保留命中。
                painter.fillRect(rect, QColor(0, 0, 0, 1))

                pen = QPen(QColor(255, 152, 0), 2, Qt.SolidLine)  # 橙色与自由模式区分
                painter.setPen(pen)
                painter.drawRect(rect)

                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Arial", 12, QFont.Bold))
                text = (
                    f"{rect.width()} x {rect.height()}"
                    f"    ({rect.x() + self._origin.x()}, {rect.y() + self._origin.y()})"
                )
                painter.drawText(rect.x(), max(rect.y() - 8, 20), text)

            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
            w, h = self._fixed_size
            hint = f"鼠标定位 {w}×{h} 框  |  左键确认  |  Esc 取消"
            painter.drawText(20, 36, hint)
            return

        # ----------------- 自由拖拽框选模式(原行为) -----------------
        if self._start and self._end:
            rect = QRect(self._start, self._end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            # 同上:回填 alpha=1 保留鼠标命中
            painter.fillRect(rect, QColor(0, 0, 0, 1))

            pen = QPen(QColor(33, 150, 243), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            text = f"{rect.width()} x {rect.height()}    ({rect.x() + self._origin.x()}, {rect.y() + self._origin.y()})"
            painter.drawText(rect.x(), max(rect.y() - 8, 20), text)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        hint = "拖拽选择识别区域  |  Esc 取消  |  Enter 确认"
        painter.drawText(20, 36, hint)

    def mousePressEvent(self, event):
        if self._fixed_size is not None:
            if event.button() == Qt.LeftButton:
                self._fixed_rect = self._compute_fixed_rect(event.pos())
                self._emit_fixed_result()
            return
        if event.button() == Qt.LeftButton:
            self._start = event.pos()
            self._end = event.pos()
            self._dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._fixed_size is not None:
            self._fixed_rect = self._compute_fixed_rect(event.pos())
            self.update()
            return
        if self._dragging:
            self._end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self._fixed_size is not None:
            return
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._end = event.pos()
            self.update()
            self._emit_result()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self._fixed_size is not None:
                self._emit_fixed_result()
            else:
                self._emit_result()

    # ------------------------------------------------------------- 结果 ----

    def _emit_result(self):
        if not (self._start and self._end):
            self.cancelled.emit()
            self.close()
            return

        rect = QRect(self._start, self._end).normalized()
        if rect.width() < 5 or rect.height() < 5:
            self.cancelled.emit()
            self.close()
            return

        x = rect.x() + self._origin.x()
        y = rect.y() + self._origin.y()
        self.area_selected.emit(x, y, rect.width(), rect.height())
        self.close()

    def _emit_fixed_result(self):
        rect = self._fixed_rect
        if rect is None:
            self.cancelled.emit()
            self.close()
            return
        x = rect.x() + self._origin.x()
        y = rect.y() + self._origin.y()
        self.area_selected.emit(x, y, rect.width(), rect.height())
        self.close()
