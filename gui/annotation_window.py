#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注窗口模块

提供PyQt5标注界面，用于在软件中直接对训练集图片进行标注。
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QFileDialog, QScrollArea,
    QFrame, QSplitter, QMessageBox, QSpinBox, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont

from training.task.dataset_manager import DatasetManager
from training.dataset_path_manager import DatasetPathManager
from training.annotation.yolo_formatter import YOLOFormatter


@dataclass
class BoundingBox:
    """边界框数据类"""
    x: float  # 归一化中心点x
    y: float  # 归一化中心点y
    width: float  # 归一化宽度
    height: float  # 归一化高度
    class_id: int  # 类别ID


class ImageLabel(QLabel):
    """可显示和绘制边界框的图片标签

    设计要点(修复历史 bug):
    - 自己接管绘制,**不**依赖 QLabel 默认的 pixmap 居中:从而避免「鼠标 widget 坐标」
      与「pixmap 像素坐标」混用导致的 bbox 偏移、窗口缩放后位置漂移、画面看着像方块。
    - 所有 mouse / draw 都通过 `_display_rect()` 这个单一来源换算:它返回当前 widget
      内 pixmap 实际绘制的矩形(保持长宽比,居中),适配窗口大小。
    - 存储一律是归一化 [0, 1],与图片实际像素无关;窗口怎么缩放显示都一致。
    """

    BBOX_COLORS = [
        QColor(0, 255, 0),
        QColor(255, 0, 0),
        QColor(0, 0, 255),
        QColor(255, 255, 0),
        QColor(255, 0, 255),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
        self.bounding_boxes: List[BoundingBox] = []
        self.current_bbox: Optional[tuple] = None  # (x, y, w, h) 在 widget 坐标系
        self.drawing = False
        self.start_pos: Optional[QPoint] = None    # widget 坐标系
        self.class_names: Dict[int, str] = {}
        self._pixmap: Optional[QPixmap] = None     # 原始 pixmap,不交给 QLabel 自带绘制

    def set_class_names(self, class_names: Dict[int, str]):
        self.class_names = class_names

    def set_image(self, pixmap: QPixmap):
        """设置图片。pixmap 保持原始大小,绘制时按 widget 自适配。"""
        self._pixmap = pixmap
        self.bounding_boxes = []
        self.current_bbox = None
        self.update()

    def clear(self):
        """清空图片和所有标注。"""
        self._pixmap = None
        self.bounding_boxes = []
        self.current_bbox = None
        super().clear()
        self.update()

    # ------------------------------------------------------- 坐标换算核心 --

    def _display_rect(self) -> QRect:
        """pixmap 在当前 widget 内的实际绘制矩形(保持长宽比 + 居中)。"""
        if self._pixmap is None or self._pixmap.isNull():
            return QRect()
        pw, ph = self._pixmap.width(), self._pixmap.height()
        ww, wh = self.width(), self.height()
        if pw <= 0 or ph <= 0 or ww <= 0 or wh <= 0:
            return QRect()
        scale = min(ww / pw, wh / ph)
        dw, dh = int(pw * scale), int(ph * scale)
        dx, dy = (ww - dw) // 2, (wh - dh) // 2
        return QRect(dx, dy, dw, dh)

    def _clamp_to_display(self, pos: QPoint) -> QPoint:
        """把 widget 坐标限制到 _display_rect 内(防止把框拖出图片范围)。"""
        rect = self._display_rect()
        if rect.isEmpty():
            return pos
        x = max(rect.left(), min(pos.x(), rect.right()))
        y = max(rect.top(), min(pos.y(), rect.bottom()))
        return QPoint(x, y)

    def _widget_to_norm(self, x: int, y: int, w: int, h: int) -> Optional[tuple]:
        """把 widget 坐标系下的 (x, y, w, h) 转成归一化 (cx, cy, nw, nh)。
        若 display_rect 为空返回 None。
        """
        rect = self._display_rect()
        if rect.isEmpty():
            return None
        norm_x = (x + w / 2 - rect.x()) / rect.width()
        norm_y = (y + h / 2 - rect.y()) / rect.height()
        norm_w = w / rect.width()
        norm_h = h / rect.height()
        # 兜底 clamp 到 [0, 1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        norm_w = max(0.0, min(1.0, norm_w))
        norm_h = max(0.0, min(1.0, norm_h))
        return (norm_x, norm_y, norm_w, norm_h)

    # ---------------------------------------------------------- IO 标注 ---

    def load_annotations(self, annotation_path: Path, img_width: int = 0, img_height: int = 0):
        """加载 YOLO 格式标注(归一化值)。img_width/height 仅为兼容旧签名,内部不依赖。"""
        if not annotation_path.exists():
            return
        try:
            with open(annotation_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = int(parts[0])
                        x = float(parts[1])
                        y = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        self.bounding_boxes.append(BoundingBox(x, y, width, height, class_id))
            self.update()
        except Exception as e:
            print(f"加载标注失败: {e}")

    def save_annotations(self, annotation_path: Path):
        try:
            with open(annotation_path, 'w', encoding='utf-8') as f:
                for bbox in self.bounding_boxes:
                    f.write(f"{bbox.class_id} {bbox.x} {bbox.y} {bbox.width} {bbox.height}\n")
        except Exception as e:
            print(f"保存标注失败: {e}")

    # ---------------------------------------------------------- 鼠标事件 --

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self._pixmap is None:
            return
        rect = self._display_rect()
        if rect.isEmpty() or not rect.contains(event.pos()):
            # 点击落在图片范围之外,忽略,不开始绘制
            return
        self.drawing = True
        self.start_pos = event.pos()
        self.current_bbox = None

    def mouseMoveEvent(self, event):
        if not self.drawing or self.start_pos is None:
            return
        cur = self._clamp_to_display(event.pos())
        x = min(self.start_pos.x(), cur.x())
        y = min(self.start_pos.y(), cur.y())
        w = abs(cur.x() - self.start_pos.x())
        h = abs(cur.y() - self.start_pos.y())
        self.current_bbox = (x, y, w, h)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self.drawing:
            return
        self.drawing = False
        if self.current_bbox:
            x, y, w, h = self.current_bbox
            if w > 5 and h > 5:
                norm = self._widget_to_norm(x, y, w, h)
                if norm is not None:
                    nx, ny, nw, nh = norm
                    self.bounding_boxes.append(BoundingBox(nx, ny, nw, nh, 0))
            self.current_bbox = None
            self.update()

    # ---------------------------------------------------------- 绘制 ------

    def paintEvent(self, event):
        # 完全接管绘制 — 不调用 super().paintEvent,避免 QLabel 默认 pixmap 居中干扰坐标
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        # 背景
        painter.fillRect(self.rect(), QColor(245, 245, 245))
        if self._pixmap is None or self._pixmap.isNull():
            return
        rect = self._display_rect()
        # 等比缩放绘制 pixmap
        painter.drawPixmap(rect, self._pixmap)
        # 已保存的 bbox(从归一化反算到 widget 坐标)
        for i, bbox in enumerate(self.bounding_boxes):
            self._draw_bbox(painter, bbox, i + 1, rect)
        # 当前正在画的 bbox(widget 坐标,直接画)
        if self.current_bbox:
            x, y, w, h = self.current_bbox
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawRect(int(x), int(y), int(w), int(h))

    def _draw_bbox(self, painter: QPainter, bbox: BoundingBox, index: int, rect: QRect):
        if rect.isEmpty():
            return
        x = int(rect.x() + (bbox.x - bbox.width / 2) * rect.width())
        y = int(rect.y() + (bbox.y - bbox.height / 2) * rect.height())
        w = int(bbox.width * rect.width())
        h = int(bbox.height * rect.height())
        color = self.BBOX_COLORS[bbox.class_id % len(self.BBOX_COLORS)]
        painter.setPen(QPen(color, 2))
        painter.drawRect(x, y, w, h)
        class_name = self.class_names.get(bbox.class_id, f"Class {bbox.class_id}")
        label = f"{index}: {class_name}"
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(x + 2, max(y - 2, 12), label)

    def delete_last_bbox(self):
        if self.bounding_boxes:
            self.bounding_boxes.pop()
            self.update()

    def clear_all_bboxes(self):
        self.bounding_boxes = []
        self.update()


class ClassEditDialog(QDialog):
    """类别编辑对话框"""

    def __init__(self, parent=None, class_names: Dict[int, str] = None):
        super().__init__(parent)
        self.class_names = class_names or {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("类别管理")
        self.layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.class_inputs = {}
        for class_id, name in self.class_names.items():
            input_field = QLineEdit(name)
            form_layout.addRow(f"类别 {class_id}:", input_field)
            self.class_inputs[class_id] = input_field

        self.layout.addLayout(form_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

        self.setLayout(self.layout)

    def get_class_names(self) -> Dict[int, str]:
        """获取更新后的类别名称"""
        result = {}
        for class_id, input_field in self.class_inputs.items():
            name = input_field.text().strip()
            if name:
                result[class_id] = name
        return result


class AnnotationWindow(QMainWindow):
    """标注窗口主类"""

    annotation_saved = pyqtSignal(str)  # 信号: 图片路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataset_name = ""
        self.current_image_index = 0
        self.image_files: List[str] = []
        self.class_names = {0: "fish"}  # 默认类别
        self.dataset_manager = DatasetManager()
        self.toast_label = None  # Toast标签

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("图片标注工具")
        self.setGeometry(100, 100, 1200, 800)

        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # 创建Toast标签(用于显示提示信息)
        self._create_toast()

        # 左侧图片显示区
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)

        # 图片标签
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.image_label = ImageLabel()
        self.image_label.set_class_names(self.class_names)
        scroll_area.setWidget(self.image_label)
        left_layout.addWidget(scroll_area)

        # 图片控制按钮
        control_layout = QHBoxLayout()
        self.prev_btn = QPushButton("上一张")
        self.prev_btn.clicked.connect(self.prev_image)
        self.next_btn = QPushButton("下一张")
        self.next_btn.clicked.connect(self.next_image)
        self.delete_btn = QPushButton("撤销上一个标注")
        self.delete_btn.clicked.connect(self.image_label.delete_last_bbox)
        self.clear_btn = QPushButton("清除所有标注")
        self.clear_btn.clicked.connect(self.image_label.clear_all_bboxes)
        self.save_btn = QPushButton("保存标注")
        self.save_btn.clicked.connect(self.save_current_annotation)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white;")

        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.next_btn)
        control_layout.addWidget(self.delete_btn)
        control_layout.addWidget(self.clear_btn)
        control_layout.addWidget(self.save_btn)
        left_layout.addLayout(control_layout)

        # 右侧控制面板
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.StyledPanel)
        right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)

        # 训练集信息
        right_layout.addWidget(QLabel("<b>训练集:</b>"))
        self.dataset_label = QLabel(self.dataset_name)
        right_layout.addWidget(self.dataset_label)

        # 图片列表
        right_layout.addWidget(QLabel("<b>图片列表:</b>"))
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.on_image_selected)
        right_layout.addWidget(self.image_list)

        # 当前图片信息
        right_layout.addWidget(QLabel("<b>当前图片:</b>"))
        self.current_image_label = QLabel("-")
        right_layout.addWidget(self.current_image_label)

        # 标注数量
        self.bbox_count_label = QLabel("标注数量: 0")
        right_layout.addWidget(self.bbox_count_label)

        # 类别管理
        right_layout.addWidget(QLabel("<b>类别管理:</b>"))
        self.class_btn = QPushButton("编辑类别")
        self.class_btn.clicked.connect(self.edit_classes)
        right_layout.addWidget(self.class_btn)

        # 删除图片
        right_layout.addWidget(QLabel("<b>图片操作:</b>"))
        self.delete_image_btn = QPushButton("删除当前图片")
        self.delete_image_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.delete_image_btn.clicked.connect(self.delete_current_image)
        right_layout.addWidget(self.delete_image_btn)

        # 快捷键说明
        right_layout.addWidget(QLabel("<b>快捷键:</b>"))
        shortcuts_text = QLabel(
            "A: 上一张图片\n"
            "S: 保存标注\n"
            "D: 下一张图片\n"
            "Z: 撤销上一个标注\n"
            "Q/Backspace/Delete: 清除所有标注"
        )
        shortcuts_text.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        right_layout.addWidget(shortcuts_text)

        right_layout.addStretch()

        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        right_layout.addWidget(self.close_btn)

        main_layout.addWidget(left_panel, stretch=3)
        main_layout.addWidget(right_panel, stretch=1)

        # 设置快捷键
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """设置快捷键"""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence

        # A - 上一张图片
        self.shortcut_prev = QShortcut(QKeySequence("A"), self)
        self.shortcut_prev.activated.connect(self.prev_image)

        # D - 下一张图片
        self.shortcut_next = QShortcut(QKeySequence("D"), self)
        self.shortcut_next.activated.connect(self.next_image)

        # Z - 撤销上一个标注
        self.shortcut_undo = QShortcut(QKeySequence("Z"), self)
        self.shortcut_undo.activated.connect(self.image_label.delete_last_bbox)

        # S - 保存标注
        self.shortcut_save = QShortcut(QKeySequence("S"), self)
        self.shortcut_save.activated.connect(self.save_current_annotation)

        # Delete - 清除所有标注
        self.shortcut_delete = QShortcut(QKeySequence("Delete"), self)
        self.shortcut_delete.activated.connect(self.image_label.clear_all_bboxes)

        # Backspace - 清除所有标注
        self.shortcut_backspace = QShortcut(QKeySequence("Backspace"), self)
        self.shortcut_backspace.activated.connect(self.image_label.clear_all_bboxes)

        # Q - 清除所有标注
        self.shortcut_q = QShortcut(QKeySequence("Q"), self)
        self.shortcut_q.activated.connect(self.image_label.clear_all_bboxes)

    def load_dataset(self, dataset_name: str):
        """加载训练集"""
        self.dataset_name = dataset_name

        # 获取图片列表
        self.image_files = self.dataset_manager.get_image_list_by_name(dataset_name)

        if not self.image_files:
            QMessageBox.warning(self, "提示", "训练集中没有图片!")
            return

        # 填充图片列表
        self.image_list.clear()
        for img_file in self.image_files:
            self.image_list.addItem(img_file)

        self.dataset_label.setText(dataset_name)
        self.current_image_index = 0
        self.load_current_image()

    def load_current_image(self):
        """加载当前图片"""
        if not self.image_files:
            return

        img_file = self.image_files[self.current_image_index]
        self.current_image_label.setText(f"{self.current_image_index + 1} / {len(self.image_files)}")

        # 更新列表选中状态
        self.image_list.setCurrentRow(self.current_image_index)

        # 加载图片
        images_dir = DatasetPathManager.get_images_path(self.dataset_name)
        img_path = images_dir / img_file

        if img_path.exists():
            # 直接传原始 pixmap;ImageLabel 会按当前 widget 大小等比适配显示,
            # 标注用归一化坐标存储,与显示分辨率无关
            pixmap = QPixmap(str(img_path))
            self.image_label.set_image(pixmap)

            # 加载标注(归一化坐标,img_width/height 仅为兼容签名传入)
            labels_dir = DatasetPathManager.get_labels_path(self.dataset_name)
            label_file = labels_dir / (img_path.stem + ".txt")
            self.image_label.load_annotations(label_file, pixmap.width(), pixmap.height())

            self._update_bbox_count()
        else:
            QMessageBox.warning(self, "错误", f"图片不存在: {img_path}")

    def _update_bbox_count(self):
        """更新标注数量显示"""
        count = len(self.image_label.bounding_boxes)
        self.bbox_count_label.setText(f"标注数量: {count}")

    def on_image_selected(self, item):
        """图片列表项选中事件"""
        row = self.image_list.row(item)
        if row >= 0:
            self.current_image_index = row
            self.load_current_image()

    def prev_image(self):
        """上一张图片"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_current_image()

    def next_image(self):
        """下一张图片"""
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.load_current_image()

    def save_current_annotation(self):
        """保存当前图片的标注"""
        if not self.image_files:
            return

        img_file = self.image_files[self.current_image_index]
        labels_dir = DatasetPathManager.get_labels_path(self.dataset_name)
        label_file = labels_dir / (Path(img_file).stem + ".txt")

        self.image_label.save_annotations(label_file)
        self.annotation_saved.emit(str(label_file))
        self.show_toast("标注已保存!")

    def _create_toast(self):
        """创建Toast标签"""
        self.toast_label = QLabel("", self)
        self.toast_label.setAlignment(Qt.AlignCenter)
        self.toast_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 200, 83, 230);
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.toast_label.hide()

    def show_toast(self, message: str):
        """显示Toast提示"""
        if not self.toast_label:
            self._create_toast()

        self.toast_label.setText(message)
        self.toast_label.adjustSize()

        # 将toast居中显示
        x = (self.width() - self.toast_label.width()) // 2
        y = self.height() - 100
        self.toast_label.move(x, y)
        self.toast_label.show()

        # 1秒后自动隐藏
        QTimer.singleShot(1000, self.hide_toast)

    def hide_toast(self):
        """隐藏Toast提示"""
        if self.toast_label:
            self.toast_label.hide()

    def edit_classes(self):
        """编辑类别"""
        dialog = ClassEditDialog(self, self.class_names)
        if dialog.exec_() == QDialog.Accepted:
            self.class_names = dialog.get_class_names()
            self.image_label.set_class_names(self.class_names)
            self.image_label.update()

    def delete_current_image(self):
        """删除当前图片（含二次确认）"""
        if not self.image_files:
            QMessageBox.warning(self, "警告", "没有可删除的图片!")
            return

        current_img_file = self.image_files[self.current_image_index]

        # 二次确认
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除当前图片吗？\n\n图片名称: {current_img_file}\n\n此操作将同时删除图片和对应的标注文件，且无法恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        try:
            # 获取图片和标注文件路径
            images_dir = DatasetPathManager.get_images_path(self.dataset_name)
            labels_dir = DatasetPathManager.get_labels_path(self.dataset_name)

            img_path = images_dir / current_img_file
            label_path = labels_dir / (Path(current_img_file).stem + ".txt")

            # 删除图片
            if img_path.exists():
                img_path.unlink()
                self.show_toast(f"图片已删除: {current_img_file}")

            # 删除标注文件
            if label_path.exists():
                label_path.unlink()

            # 从列表中移除
            self.image_files.pop(self.current_image_index)
            self.image_list.takeItem(self.current_image_index)

            # 如果列表不为空，加载下一张图片
            if self.image_files:
                if self.current_image_index >= len(self.image_files):
                    self.current_image_index = len(self.image_files) - 1
                self.load_current_image()
                self.show_toast(f"已加载下一张图片")
            else:
                # 如果没有图片了，清空显示
                self.current_image_label.setText("-")
                self.image_label.clear()
                self.image_label.bounding_boxes = []
                self.bbox_count_label.setText("标注数量: 0")
                self.show_toast("训练集中已无图片")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除图片失败: {str(e)}")


def open_annotation_window(dataset_name: str, parent=None) -> Optional[AnnotationWindow]:
    """打开标注窗口

    Args:
        dataset_name: 训练集名称
        parent: 父窗口

    Returns:
        标注窗口实例
    """
    window = AnnotationWindow(parent)
    window.load_dataset(dataset_name)
    window.show()
    return window
