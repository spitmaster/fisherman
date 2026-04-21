#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
屏幕区域选择器

提供一个全屏半透明覆盖层，用户拖拽矩形框选出屏幕区域。
选择完成后通过 area_selected(x, y, width, height) 信号返回结果。
"""

from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QGuiApplication
from PyQt5.QtWidgets import QWidget


class ScreenAreaSelector(QWidget):
    """全屏区域选择覆盖层"""

    area_selected = pyqtSignal(int, int, int, int)  # x, y, width, height
    cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

        # 覆盖所有屏幕：遍历所有 QScreen 求并集，避免某些驱动下 virtualGeometry 不完整
        geo = QRect()
        for scr in QGuiApplication.screens():
            geo = geo.united(scr.geometry())
        if geo.isEmpty():
            geo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geo)
        self._origin = geo.topLeft()

        self._start = None
        self._end = None
        self._dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # 半透明遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        # 当前选择区域：挖空 + 描边
        if self._start and self._end:
            rect = QRect(self._start, self._end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            pen = QPen(QColor(33, 150, 243), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            # 显示尺寸文本
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            text = f"{rect.width()} x {rect.height()}    ({rect.x() + self._origin.x()}, {rect.y() + self._origin.y()})"
            painter.drawText(rect.x(), max(rect.y() - 8, 20), text)

        # 顶部提示文字
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        hint = "拖拽选择识别区域  |  Esc 取消  |  Enter 确认"
        painter.drawText(20, 36, hint)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start = event.pos()
            self._end = event.pos()
            self._dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._end = event.pos()
            self.update()
            # 鼠标松开即确认
            self._emit_result()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._emit_result()

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

        # 转换为屏幕绝对坐标
        x = rect.x() + self._origin.x()
        y = rect.y() + self._origin.y()
        self.area_selected.emit(x, y, rect.width(), rect.height())
        self.close()
