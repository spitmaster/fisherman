#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图库标签页(图集分组版)

左栏:图集列表(图集名 + 图片数 + 右键菜单)+ 新建图集按钮
右栏:当前图集缩略图网格 + 顶部状态条 + 底部操作条
"""

import os
import threading
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QFileDialog, QInputDialog, QMenu, QAction,
    QDialog, QDialogButtonBox, QComboBox, QFormLayout, QRadioButton, QButtonGroup,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap, QImage, QColor

from image_library.library_manager import library_manager

logger = logging.getLogger(__name__)


class ImageLibraryTab(QWidget):
    """图库标签页(图集版)"""

    _thumbnail_ready = pyqtSignal(str, object)  # (image_id, QImage | None)
    _screenshot_taken = pyqtSignal(str, str)    # (image_id, album_id)

    DEFAULT_HOTKEY = 'f9'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._load_stop = threading.Event()
        self._hotkey_registered = False
        self._placeholder = self._make_placeholder()
        self._current_album_id = ''
        self._init_ui()
        self._thumbnail_ready.connect(self._on_thumbnail_ready)
        self._screenshot_taken.connect(self._on_screenshot_taken)
        # 启动时确保默认图集存在
        default_id = library_manager.ensure_default_album()
        self._current_album_id = default_id
        self._start_hotkey()
        self.refresh_albums()

    # ------------------------------------------------------------------ UI --

    def _init_ui(self):
        root = QVBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        # ---------------- 左栏:图集列表 ----------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        btn_new_album = QPushButton("新建图集")
        btn_new_album.clicked.connect(self._create_album)
        left_layout.addWidget(btn_new_album)

        self.album_list = QListWidget()
        self.album_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.album_list.customContextMenuRequested.connect(self._show_album_menu)
        self.album_list.currentItemChanged.connect(self._on_album_changed)
        left_layout.addWidget(self.album_list)

        splitter.addWidget(left_panel)

        # ---------------- 右栏:图片网格 + 操作 ----------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部:导入按钮 + 当前图集名 + 热键状态
        top = QHBoxLayout()
        self.btn_import_files = QPushButton("导入图片")
        self.btn_import_files.clicked.connect(self._import_files)
        top.addWidget(self.btn_import_files)

        self.btn_import_folder = QPushButton("导入文件夹")
        self.btn_import_folder.clicked.connect(self._import_folder)
        top.addWidget(self.btn_import_folder)

        top.addStretch()

        self.current_album_label = QLabel("当前图集: —")
        self.current_album_label.setStyleSheet("QLabel { font-weight: bold; }")
        top.addWidget(self.current_album_label)

        self.hotkey_label = QLabel("截图热键: F9 [未启用]")
        top.addWidget(self.hotkey_label)

        right_layout.addLayout(top)

        # 缩略图网格
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(120, 120))
        self.list_widget.setSpacing(8)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.itemSelectionChanged.connect(self._update_selection_label)
        right_layout.addWidget(self.list_widget)

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

        self.stats_label = QLabel("共 0 张 | 今日截图 0 张")
        bottom.addWidget(self.stats_label)

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

        right_layout.addLayout(bottom)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 900])

    # --------------------------------------------------------- 图集刷新 ------

    def refresh_albums(self):
        """重新加载图集列表,默认选中第一个(默认图集)。"""
        self.album_list.blockSignals(True)
        self.album_list.clear()

        albums = library_manager.get_all_albums()
        target_row = 0
        for idx, a in enumerate(albums):
            display = f"{a['name']}  ({a['image_count']})"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, a['id'])
            item.setData(Qt.UserRole + 1, a['name'])
            item.setData(Qt.UserRole + 2, a['is_default'])
            self.album_list.addItem(item)
            if a['id'] == self._current_album_id:
                target_row = idx

        self.album_list.blockSignals(False)
        if albums:
            self.album_list.setCurrentRow(target_row)
        else:
            self._current_album_id = ''
            self.current_album_label.setText("当前图集: —")
            self.list_widget.clear()

    def _on_album_changed(self, current, _previous):
        """切换选中图集,刷新右侧图片网格。"""
        if not current:
            return
        album_id = current.data(Qt.UserRole)
        album_name = current.data(Qt.UserRole + 1)
        self._current_album_id = album_id
        self.current_album_label.setText(f"当前图集: {album_name}")
        self.refresh_library()

    # --------------------------------------------------------- 图集 CRUD ----

    def _create_album(self):
        name, ok = QInputDialog.getText(self, "新建图集", "图集名称:")
        if not ok:
            return
        name = (name or '').strip()
        if not name:
            QMessageBox.warning(self, "提示", "图集名称不能为空")
            return
        album_id = library_manager.create_album(name)
        if not album_id:
            QMessageBox.warning(self, "提示", f"创建失败:名称「{name}」已存在或为空")
            return
        self._current_album_id = album_id
        self.refresh_albums()

    def _show_album_menu(self, pos):
        item = self.album_list.itemAt(pos)
        if not item:
            return
        is_default = item.data(Qt.UserRole + 2)

        menu = QMenu(self)
        act_rename = QAction("重命名", self)
        act_delete = QAction("删除图集", self)
        if is_default:
            act_rename.setEnabled(False)
            act_delete.setEnabled(False)
        menu.addAction(act_rename)
        menu.addAction(act_delete)

        chosen = menu.exec_(self.album_list.mapToGlobal(pos))
        if chosen == act_rename:
            self._rename_album(item)
        elif chosen == act_delete:
            self._delete_album(item)

    def _rename_album(self, item: QListWidgetItem):
        album_id = item.data(Qt.UserRole)
        old_name = item.data(Qt.UserRole + 1)
        new_name, ok = QInputDialog.getText(self, "重命名图集", "新名称:", text=old_name)
        if not ok:
            return
        new_name = (new_name or '').strip()
        if not new_name or new_name == old_name:
            return
        if not library_manager.rename_album(album_id, new_name):
            QMessageBox.warning(self, "提示", "重命名失败(名称为空 / 已存在 / 默认图集不可改)")
            return
        self.refresh_albums()

    def _delete_album(self, item: QListWidgetItem):
        album_id = item.data(Qt.UserRole)
        name = item.data(Qt.UserRole + 1)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除图集「{name}」?该图集内的所有图片(磁盘文件)将同步删除,不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if not library_manager.delete_album(album_id):
            QMessageBox.warning(self, "提示", "删除失败")
            return
        if self._current_album_id == album_id:
            self._current_album_id = library_manager.ensure_default_album()
        self.refresh_albums()

    # --------------------------------------------------------- 加载图片 ------

    def refresh_library(self):
        """从 DB 刷新当前图集的图片网格,后台异步加载缩略图。"""
        self._load_stop.set()
        self.list_widget.clear()

        if not self._current_album_id:
            self._update_stats(0)
            return

        items = library_manager.get_images(self._current_album_id)
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
        """后台线程:逐张加载缩略图并通知主线程。"""
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
        """主线程槽:把加载好的 QImage 设置为对应条目的图标。"""
        if qimg is None:
            return
        icon = QIcon(QPixmap.fromImage(qimg))
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.UserRole) == image_id:
                item.setIcon(icon)
                break

    # ---------------------------------------------------------- 统计/选择 ----

    def _update_stats(self, total=None):
        if total is None:
            total = self.list_widget.count()
        today = library_manager.get_today_screenshot_count()
        self.stats_label.setText(f"共 {total} 张 | 今日截图 {today} 张")
        # 同步更新左侧图集图片数(简单做法:重新刷一次)
        # 注:为避免切换图集时递归,只更新当前行文本
        current = self.album_list.currentItem()
        if current and current.data(Qt.UserRole) == self._current_album_id:
            name = current.data(Qt.UserRole + 1)
            current.setText(f"{name}  ({total})")

    def _update_selection_label(self):
        count = len(self.list_widget.selectedItems())
        self.selection_label.setText(f"已选 {count} 张")

    # ---------------------------------------------------------- 图片操作 ----

    def _delete_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要删除的图片")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除选中的 {len(selected)} 张图片?磁盘文件也将同步删除,不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for item in selected:
            library_manager.delete(item.data(Qt.UserRole))
        self.refresh_library()

    def _import_files(self):
        if not self._current_album_id:
            QMessageBox.information(self, "提示", "请先选中一个图集")
            return
        exts = "图片文件 (*.jpg *.jpeg *.png *.bmp *.webp *.gif)"
        paths, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", exts)
        if not paths:
            return
        self._run_import(paths)

    def _import_folder(self):
        if not self._current_album_id:
            QMessageBox.information(self, "提示", "请先选中一个图集")
            return
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder:
            return
        paths = library_manager.scan_folder(folder)
        if not paths:
            QMessageBox.information(self, "提示", "所选文件夹内没有支持的图片文件")
            return
        reply = QMessageBox.question(
            self, "确认导入",
            f"找到 {len(paths)} 张图片,确认导入到当前图集?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return
        self._run_import(paths)

    def _run_import(self, paths: list):
        """后台线程批量导入,完成后刷新。"""
        target_album = self._current_album_id
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
            count = library_manager.import_files(paths, album_id=target_album, progress_cb=_progress)
            from PyQt5.QtCore import QMetaObject, Q_ARG
            QMetaObject.invokeMethod(self, "_on_import_done",
                                     Qt.QueuedConnection,
                                     Q_ARG(int, count))

        threading.Thread(target=_worker, daemon=True).start()

    @pyqtSlot(int)
    def _on_import_done(self, count: int):
        self.btn_import_files.setEnabled(True)
        self.btn_import_folder.setEnabled(True)
        self.refresh_library()
        if count:
            QMessageBox.information(self, "完成", f"成功导入 {count} 张图片")

    # ---------------------------------------------------- 导入训练集 -------

    def _import_to_training_set(self):
        """将选中图片或当前图集全部图片复制到目标训练集 images/。"""
        selected = self.list_widget.selectedItems()
        total_in_album = self.list_widget.count()

        if total_in_album == 0:
            QMessageBox.information(self, "提示", "当前图集没有图片")
            return

        # 选择范围:选中 vs 当前图集全部
        scope = self._pick_import_scope(len(selected), total_in_album)
        if scope is None:
            return

        if scope == 'selected':
            if not selected:
                QMessageBox.information(self, "提示", "请先选择要导入的图片")
                return
            file_paths = [item.data(Qt.UserRole + 1) for item in selected]
        else:  # 'all'
            file_paths = []
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item:
                    file_paths.append(item.data(Qt.UserRole + 1))

        task_id = self._pick_training_task()
        if not task_id:
            return

        count = library_manager.import_to_dataset(file_paths, task_id)
        if count:
            QMessageBox.information(self, "完成", f"已将 {count} 张图片导入训练集")
        else:
            QMessageBox.warning(self, "失败", "没有图片被成功导入,请检查文件是否存在")

    def _pick_import_scope(self, selected_count: int, total_count: int):
        """弹出对话框选择导入范围。返回 'selected' / 'all' / None(取消)。"""
        dlg = QDialog(self)
        dlg.setWindowTitle("选择导入范围")
        dlg.setMinimumWidth(320)
        layout = QVBoxLayout(dlg)

        rb_selected = QRadioButton(f"仅选中图片 ({selected_count} 张)")
        rb_all = QRadioButton(f"当前图集全部图片 ({total_count} 张)")
        if selected_count > 0:
            rb_selected.setChecked(True)
        else:
            rb_all.setChecked(True)
            rb_selected.setEnabled(False)

        group = QButtonGroup(dlg)
        group.addButton(rb_selected)
        group.addButton(rb_all)

        layout.addWidget(rb_selected)
        layout.addWidget(rb_all)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec_() != QDialog.Accepted:
            return None
        return 'selected' if rb_selected.isChecked() else 'all'

    def _pick_training_task(self) -> str:
        """弹出对话框选择目标训练集。"""
        from global_support.database import db_manager, TrainingTask

        session = db_manager.get_session()
        tasks = session.query(TrainingTask).order_by(TrainingTask.created_at.desc()).all()
        task_list = [{'id': t.id, 'name': t.task_name} for t in tasks]
        session.close()

        if not task_list:
            QMessageBox.warning(self, "提示", "尚未创建任何训练集,请先在「训练」页新建训练集")
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

    # ---------------------------------------------------------- 热键截图 ----

    def _start_hotkey(self):
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
        """keyboard 后台线程触发:截图并通知主线程。"""
        target_album = self._current_album_id
        if not target_album:
            logger.warning("无当前图集,跳过截图")
            return
        image_id = library_manager.take_screenshot(album_id=target_album)
        if image_id:
            self._screenshot_taken.emit(image_id, target_album)

    @pyqtSlot(str, str)
    def _on_screenshot_taken(self, image_id: str, album_id: str):
        """主线程槽:截图完成。仅当截图归属当前图集时插入网格。"""
        if album_id != self._current_album_id:
            # 截图归属其他图集(用户切换过),只刷新一次以更新计数
            self.refresh_albums()
            return

        items = library_manager.get_images(album_id)
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
        self.list_widget.insertItem(0, lw_item)

        self._update_stats(self.list_widget.count())

        # 异步加载这张图的缩略图
        fp = new_item_data['file_path']
        threading.Thread(
            target=self._load_one_thumbnail,
            args=(image_id, fp),
            daemon=True,
        ).start()

    def _load_one_thumbnail(self, image_id: str, file_path: str):
        if not os.path.exists(file_path):
            return
        try:
            qimg = QImage(file_path)
            if not qimg.isNull():
                scaled = qimg.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._thumbnail_ready.emit(image_id, scaled)
        except Exception as e:
            logger.warning(f"缩略图加载失败 {file_path}: {e}")

    # ---------------------------------------------------------- 工具 --------

    @staticmethod
    def _make_placeholder() -> QIcon:
        pixmap = QPixmap(120, 120)
        pixmap.fill(QColor(210, 210, 210))
        return QIcon(pixmap)

    def closeEvent(self, event):
        self._load_stop.set()
        self._stop_hotkey()
        event.accept()
