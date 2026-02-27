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
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QTimer
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
    """可显示和绘制边界框的图片标签"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.bounding_boxes: List[BoundingBox] = []
        self.current_bbox: Optional[tuple] = None  # (x, y, w, h) in pixels
        self.drawing = False
        self.start_pos = None
        self.scale_factor = 1.0
        self.class_names = {}

    def set_class_names(self, class_names: Dict[int, str]):
        """设置类别名称"""
        self.class_names = class_names

    def set_image(self, pixmap: QPixmap):
        """设置图片"""
        self.setPixmap(pixmap)
        self.bounding_boxes = []
        self.current_bbox = None
        self.update()

    def load_annotations(self, annotation_path: Path, img_width: int, img_height: int):
        """加载YOLO格式标注"""
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
        """保存YOLO格式标注"""
        try:
            with open(annotation_path, 'w', encoding='utf-8') as f:
                for bbox in self.bounding_boxes:
                    f.write(f"{bbox.class_id} {bbox.x} {bbox.y} {bbox.width} {bbox.height}\n")
        except Exception as e:
            print(f"保存标注失败: {e}")

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_pos = event.pos()
            self.current_bbox = None

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.drawing and self.start_pos:
            current_pos = event.pos()
            x = min(self.start_pos.x(), current_pos.x())
            y = min(self.start_pos.y(), current_pos.y())
            w = abs(current_pos.x() - self.start_pos.x())
            h = abs(current_pos.y() - self.start_pos.y())
            self.current_bbox = (x, y, w, h)
            self.update()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            if self.current_bbox:
                x, y, w, h = self.current_bbox
                # 忽略太小的框
                if w > 5 and h > 5:
                    # 转换为归一化坐标
                    pixmap = self.pixmap()
                    if pixmap:
                        img_w = pixmap.width()
                        img_h = pixmap.height()
                        norm_x = (x + w / 2) / img_w
                        norm_y = (y + h / 2) / img_h
                        norm_w = w / img_w
                        norm_h = h / img_h

                        # 默认类别为0
                        bbox = BoundingBox(norm_x, norm_y, norm_w, norm_h, 0)
                        self.bounding_boxes.append(bbox)

                self.current_bbox = None
                self.update()

    def paintEvent(self, event):
        """绘制事件"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制已保存的边界框
        for i, bbox in enumerate(self.bounding_boxes):
            self._draw_bbox(painter, bbox, i + 1)

        # 绘制当前正在画的框
        if self.current_bbox:
            x, y, w, h = self.current_bbox
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            painter.drawRect(int(x), int(y), int(w), int(h))

    def _draw_bbox(self, painter: QPainter, bbox: BoundingBox, index: int):
        """绘制单个边界框"""
        pixmap = self.pixmap()
        if not pixmap:
            return

        img_w = pixmap.width()
        img_h = pixmap.height()

        # 转换为像素坐标
        x = int((bbox.x - bbox.width / 2) * img_w)
        y = int((bbox.y - bbox.height / 2) * img_h)
        w = int(bbox.width * img_w)
        h = int(bbox.height * img_h)

        # 根据类别选择颜色
        colors = [
            QColor(0, 255, 0),
            QColor(255, 0, 0),
            QColor(0, 0, 255),
            QColor(255, 255, 0),
            QColor(255, 0, 255),
        ]
        color = colors[bbox.class_id % len(colors)]

        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.drawRect(x, y, w, h)

        # 绘制标签
        class_name = self.class_names.get(bbox.class_id, f"Class {bbox.class_id}")
        label = f"{index}: {class_name}"
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(x + 2, y - 2, label)

    def delete_last_bbox(self):
        """删除最后一个边界框"""
        if self.bounding_boxes:
            self.bounding_boxes.pop()
            self.update()

    def clear_all_bboxes(self):
        """清除所有边界框"""
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
            pixmap = QPixmap(str(img_path))
            # 缩放到合适大小
            scaled_pixmap = pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.set_image(scaled_pixmap)

            # 加载标注
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
