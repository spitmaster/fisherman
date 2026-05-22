#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图库标签页

截图采集 + 图片导入 + 一键导入训练集
"""

import os
import threading
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QFileDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap, QImage, QColor

from image_library.library_manager import library_manager

logger = logging.getLogger(__name__)


class ImageLibraryTab(QWidget):
    """图库标签页"""

    _thumbnail_ready = pyqtSignal(str, object)  # (image_id, QImage | None)
    _screenshot_taken = pyqtSignal(str)          # image_id，截图完成后通知主线程

    DEFAULT_HOTKEY = 'f9'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._load_stop = threading.Event()
        self._hotkey_registered = False
        self._placeholder = self._make_placeholder()
        self._init_ui()
        self._thumbnail_ready.connect(self._on_thumbnail_ready)
        self._screenshot_taken.connect(self._on_screenshot_taken)
        self._start_hotkey()
        self.refresh_library()

    # ------------------------------------------------------------------ UI --

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 顶部控件行
        top = QHBoxLayout()
        self.btn_import_files = QPushButton("导入图片")
        self.btn_import_files.clicked.connect(self._import_files)
        top.addWidget(self.btn_import_files)

        self.btn_import_folder = QPushButton("导入文件夹")
        self.btn_import_folder.clicked.connect(self._import_folder)
        top.addWidget(self.btn_import_folder)

        top.addStretch()

        self.hotkey_label = QLabel("截图热键: F9 [未启用]")
        top.addWidget(self.hotkey_label)

        self.stats_label = QLabel("共 0 张 | 今日截图 0 张")
        top.addWidget(self.stats_label)

        layout.addLayout(top)

        # 缩略图网格
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(120, 120))
        self.list_widget.setSpacing(8)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.itemSelectionChanged.connect(self._update_selection_label)
        layout.addWidget(self.list_widget)

        # 底部操作行
        bottom = QHBoxLayout()
        btn_select_all = QPushButton("全选")
        btn_select_all.clicked.connect(self.list_widget.selectAll)
        bottom.addWidget(btn_select_all)

        btn_deselect = QPushButton("取消选择")
        btn_deselect.clicked.connect(self.list_widget.clearSelection)
        bottom.addWidget(btn_deselect)

        self.selection_label = QLabel("已选 0 张")
        bottom.addWidget(self.selection_label)

        bottom.addStretch()

        self.btn_delete = QPushButton("删除选中")
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_delete.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 6px 14px; }"
        )
        bottom.addWidget(self.btn_delete)

        self.btn_to_dataset = QPushButton("导入到训练集")
        self.btn_to_dataset.clicked.connect(self._import_to_training_set)
        self.btn_to_dataset.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 6px 14px; }"
        )
        bottom.addWidget(self.btn_to_dataset)

        layout.addLayout(bottom)

    # --------------------------------------------------------- 加载图库 ------

    def refresh_library(self):
        """从 DB 刷新图库，后台异步加载缩略图。"""
        self._load_stop.set()
        self.list_widget.clear()

        items = library_manager.get_all()
        for item in items:
            lw_item = QListWidgetItem(self._placeholder, os.path.basename(item['file_path']))
            lw_item.setData(Qt.UserRole, item['id'])
            lw_item.setData(Qt.UserRole + 1, item['file_path'])
            ts = item['created_at'].strftime('%Y-%m-%d %H:%M:%S') if item['created_at'] else ''
            lw_item.setToolTip(f"{item['file_path']}\n{item['source']} · {ts}")
            self.list_widget.addItem(lw_item)

        self._update_stats(len(items))

        self._load_stop = threading.Event()
        threading.Thread(
            target=self._load_thumbnails_bg,
            args=([(i['id'], i['file_path']) for i in items],),
            daemon=True,
        ).start()

    def _load_thumbnails_bg(self, pairs):
        """后台线程：逐张加载缩略图并通知主线程。"""
        for image_id, file_path in pairs:
            if self._load_stop.is_set():
                break
            if not os.path.exists(file_path):
                self._thumbnail_ready.emit(image_id, None)
                continue
            try:
                qimg = QImage(file_path)
                if not qimg.isNull():
                    scaled = qimg.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self._thumbnail_ready.emit(image_id, scaled)
            except Exception as e:
                logger.warning(f"缩略图加载失败 {file_path}: {e}")
                self._thumbnail_ready.emit(image_id, None)

    def _on_thumbnail_ready(self, image_id, qimg):
        """主线程槽：将加载好的 QImage 设置为对应条目的图标。"""
        if qimg is None:
            return
        icon = QIcon(QPixmap.fromImage(qimg))
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.UserRole) == image_id:
                item.setIcon(icon)
                break

    # ---------------------------------------------------------- 统计 / 选择 -

    def _update_stats(self, total=None):
        if total is None:
            total = self.list_widget.count()
        today = library_manager.get_today_screenshot_count()
        self.stats_label.setText(f"共 {total} 张 | 今日截图 {today} 张")

    def _update_selection_label(self):
        count = len(self.list_widget.selectedItems())
        self.selection_label.setText(f"已选 {count} 张")

    # ---------------------------------------------------------- 操作 ---------

    def _delete_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要删除的图片")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除选中的 {len(selected)} 张图片？磁盘文件也将同步删除，不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for item in selected:
            library_manager.delete(item.data(Qt.UserRole))
        self.refresh_library()

    def _import_files(self):
        """选择单张或多张图片文件导入图库。"""
        exts = "图片文件 (*.jpg *.jpeg *.png *.bmp *.webp *.gif)"
        paths, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", exts)
        if not paths:
            return
        self._run_import(paths)

    def _import_folder(self):
        """选择文件夹，递归扫描所有图片后导入图库。"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder:
            return
        paths = library_manager.scan_folder(folder)
        if not paths:
            QMessageBox.information(self, "提示", "所选文件夹内没有支持的图片文件")
            return
        reply = QMessageBox.question(
            self, "确认导入",
            f"找到 {len(paths)} 张图片，确认导入到图库？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return
        self._run_import(paths)

    def _run_import(self, paths: list):
        """在后台线程执行批量导入，完成后刷新界面。"""
        self.btn_import_files.setEnabled(False)
        self.btn_import_folder.setEnabled(False)
        self.stats_label.setText(f"导入中… 0 / {len(paths)}")

        def _progress(done, total):
            from PyQt5.QtCore import QMetaObject, Q_ARG
            QMetaObject.invokeMethod(
                self.stats_label, "setText",
                Qt.QueuedConnection,
                Q_ARG(str, f"导入中… {done} / {total}"),
            )

        def _worker():
            count = library_manager.import_files(paths, progress_cb=_progress)
            from PyQt5.QtCore import QMetaObject
            QMetaObject.invokeMethod(self, "_on_import_done",
                                     Qt.QueuedConnection,
                                     Q_ARG(int, count))

        threading.Thread(target=_worker, daemon=True).start()

    @pyqtSlot(int)
    def _on_import_done(self, count: int):
        """主线程槽：导入完成后恢复按钮并刷新。"""
        self.btn_import_files.setEnabled(True)
        self.btn_import_folder.setEnabled(True)
        self.refresh_library()
        if count:
            QMessageBox.information(self, "完成", f"成功导入 {count} 张图片")

    def _import_to_training_set(self):
        """将选中图片复制到目标训练集的 images/ 目录。"""
        selected = self.list_widget.selectedItems()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要导入的图片")
            return

        # 查询所有训练集供用户选择
        task_id = self._pick_training_task()
        if not task_id:
            return

        file_paths = [item.data(Qt.UserRole + 1) for item in selected]

        count = library_manager.import_to_dataset(file_paths, task_id)
        if count:
            QMessageBox.information(self, "完成", f"已将 {count} 张图片导入训练集")
        else:
            QMessageBox.warning(self, "失败", "没有图片被成功导入，请检查文件是否存在")

    def _pick_training_task(self) -> str:
        """弹出对话框让用户选择目标训练集，返回 task_id 或空字符串。"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QComboBox, QFormLayout
        from global_support.database import db_manager, TrainingTask

        session = db_manager.get_session()
        tasks = session.query(TrainingTask).order_by(TrainingTask.created_at.desc()).all()
        task_list = [{'id': t.id, 'name': t.task_name} for t in tasks]
        session.close()

        if not task_list:
            QMessageBox.warning(self, "提示", "尚未创建任何训练集，请先在「训练」页新建训练集")
            return ''

        dlg = QDialog(self)
        dlg.setWindowTitle("选择目标训练集")
        dlg.setMinimumWidth(320)
        form = QFormLayout(dlg)

        combo = QComboBox()
        for t in task_list:
            combo.addItem(t['name'], t['id'])
        form.addRow("训练集:", combo)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec_() != QDialog.Accepted:
            return ''
        return combo.currentData()

    # ---------------------------------------------------------- 热键截图 ------

    def _start_hotkey(self):
        """注册全局快捷键（F9），应用在后台时亦可触发。"""
        try:
            import keyboard
            keyboard.add_hotkey(self.DEFAULT_HOTKEY, self._on_hotkey_pressed)
            self._hotkey_registered = True
            self.hotkey_label.setText(f"截图热键: {self.DEFAULT_HOTKEY.upper()} [已启用]")
            logger.info(f"全局截图热键已注册: {self.DEFAULT_HOTKEY}")
        except Exception as e:
            logger.error(f"注册截图热键失败: {e}")
            self.hotkey_label.setText(f"截图热键: {self.DEFAULT_HOTKEY.upper()} [注册失败]")

    def _stop_hotkey(self):
        """注销全局快捷键。"""
        if not self._hotkey_registered:
            return
        try:
            import keyboard
            keyboard.remove_hotkey(self.DEFAULT_HOTKEY)
            self._hotkey_registered = False
            logger.info("全局截图热键已注销")
        except Exception as e:
            logger.warning(f"注销截图热键失败: {e}")

    def _on_hotkey_pressed(self):
        """在 keyboard 后台线程中触发：截图并通知主线程。"""
        image_id = library_manager.take_screenshot()
        if image_id:
            self._screenshot_taken.emit(image_id)

    @pyqtSlot(str)
    def _on_screenshot_taken(self, image_id: str):
        """主线程槽：截图完成，把新条目插入列表顶部并加载缩略图。"""
        items = library_manager.get_all()
        # 找到刚截的那条
        new_item_data = next((i for i in items if i['id'] == image_id), None)
        if not new_item_data:
            return

        lw_item = QListWidgetItem(
            self._placeholder,
            os.path.basename(new_item_data['file_path']),
        )
        lw_item.setData(Qt.UserRole, image_id)
        lw_item.setData(Qt.UserRole + 1, new_item_data['file_path'])
        ts = new_item_data['created_at'].strftime('%Y-%m-%d %H:%M:%S') if new_item_data['created_at'] else ''
        lw_item.setToolTip(f"{new_item_data['file_path']}\nscreenshot · {ts}")
        self.list_widget.insertItem(0, lw_item)  # 插入顶部

        self._update_stats(self.list_widget.count())

        # 异步加载这张图的缩略图
        fp = new_item_data['file_path']
        threading.Thread(
            target=self._load_one_thumbnail,
            args=(image_id, fp),
            daemon=True,
        ).start()

    def _load_one_thumbnail(self, image_id: str, file_path: str):
        """后台线程：加载单张缩略图。"""
        if not os.path.exists(file_path):
            return
        try:
            qimg = QImage(file_path)
            if not qimg.isNull():
                scaled = qimg.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._thumbnail_ready.emit(image_id, scaled)
        except Exception as e:
            logger.warning(f"缩略图加载失败 {file_path}: {e}")

    # ---------------------------------------------------------- 工具 ---------

    @staticmethod
    def _make_placeholder() -> QIcon:
        pixmap = QPixmap(120, 120)
        pixmap.fill(QColor(210, 210, 210))
        return QIcon(pixmap)

    def closeEvent(self, event):
        self._load_stop.set()
        self._stop_hotkey()
        event.accept()
