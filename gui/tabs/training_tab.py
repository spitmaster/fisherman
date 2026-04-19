#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练标签页

提供训练集管理功能：创建、查看、删除训练集
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton, QMessageBox, QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox
)
from PyQt5.QtCore import Qt

from training.task.dataset_manager import DatasetManager
from training.dataset_path_manager import DatasetPathManager
from global_support.database import db_manager, TrainingTask
from gui.detail_tabs.training_tab import TrainingTab as TrainingDetailTab

logger = logging.getLogger(__name__)


class TrainingTab(QWidget):
    """训练标签页"""

    def __init__(self, parent=None):
        """初始化训练标签页"""
        super().__init__(parent)
        self.dataset_manager = DatasetManager()
        self.datasets_info = {}  # 保存训练集信息（UUID -> 备注）
        self._init_ui()
        self.load_datasets()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 训练集管理区域
        dataset_group = QGroupBox("训练集管理")
        dataset_layout = QVBoxLayout(dataset_group)

        # 训练集操作按钮
        dataset_button_layout = QHBoxLayout()
        self.btn_create_dataset = QPushButton("+ 新建训练集")
        self.btn_create_dataset.setMinimumHeight(40)
        self.btn_create_dataset.setMinimumWidth(160)
        self.btn_create_dataset.setCursor(Qt.PointingHandCursor)
        self.btn_create_dataset.setStyleSheet(
            "QPushButton {"
            " background-color: #4CAF50;"
            " color: white;"
            " font-size: 14px;"
            " font-weight: bold;"
            " padding: 8px 20px;"
            " border: none;"
            " border-radius: 4px;"
            "}"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:pressed { background-color: #3d8b40; }"
        )
        self.btn_create_dataset.clicked.connect(self.create_dataset)
        dataset_button_layout.addWidget(self.btn_create_dataset)
        dataset_button_layout.addStretch()
        dataset_layout.addLayout(dataset_button_layout)

        # 训练集表格
        self.dataset_table = QTableWidget()
        self.dataset_table.setColumnCount(6)
        self.dataset_table.setHorizontalHeaderLabels(["名称", "备注", "总图片数", "已标注", "标注进度", "操作"])
        # 列宽设置
        self.dataset_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dataset_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.dataset_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.dataset_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.dataset_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.dataset_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.dataset_table.setColumnWidth(5, 280)
        self.dataset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dataset_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dataset_table.verticalHeader().setVisible(False)
        self.dataset_table.cellDoubleClicked.connect(self.on_dataset_double_clicked)

        dataset_layout.addWidget(self.dataset_table)
        layout.addWidget(dataset_group)

    def load_datasets(self):
        """加载训练集列表"""
        self.dataset_table.setRowCount(0)

        session = db_manager.get_session()

        try:
            # 从数据库加载训练任务
            tasks = session.query(TrainingTask).all()

            self.datasets_info = {}  # 保存训练集信息（UUID -> 备注）

            for task in tasks:
                task_id = str(task.id)
                dataset_info = self.dataset_manager.get_dataset_info_by_name(task_id)

                total_images = dataset_info.get('total_images', 0) if dataset_info else 0
                annotated_images = dataset_info.get('annotated_images', 0) if dataset_info else 0
                progress = dataset_info.get('annotation_progress', 0) if dataset_info else 0

                row = self.dataset_table.rowCount()
                self.dataset_table.insertRow(row)

                # 名称（显示任务名称，存储UUID）
                item_name = QTableWidgetItem(task.task_name)
                item_name.setData(Qt.UserRole, task_id)
                self.dataset_table.setItem(row, 0, item_name)

                # 备注
                remark = self._load_dataset_remark(task_id)
                item_remark = QTableWidgetItem(remark)
                self.dataset_table.setItem(row, 1, item_remark)
                self.datasets_info[task_id] = remark

                # 总图片数
                item_total = QTableWidgetItem(str(total_images))
                item_total.setTextAlignment(Qt.AlignCenter)
                self.dataset_table.setItem(row, 2, item_total)

                # 已标注
                item_annotated = QTableWidgetItem(str(annotated_images))
                item_annotated.setTextAlignment(Qt.AlignCenter)
                self.dataset_table.setItem(row, 3, item_annotated)

                # 标注进度
                item_progress = QTableWidgetItem(f"{progress:.1f}%")
                item_progress.setTextAlignment(Qt.AlignCenter)
                self.dataset_table.setItem(row, 4, item_progress)

                # 操作按钮列
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(6, 2, 6, 2)
                btn_layout.setSpacing(6)

                btn_open = QPushButton("打开详情")
                btn_open.setMinimumWidth(80)
                btn_open.setStyleSheet("padding: 4px 8px;")
                btn_open.clicked.connect(lambda checked, r=row: self.open_dataset_detail(r))

                btn_train = QPushButton("训练")
                btn_train.setMinimumWidth(60)
                if annotated_images > 0:
                    btn_train.setStyleSheet("padding: 4px 8px; background-color: #2196F3; color: white;")
                    btn_train.setToolTip("开始训练该训练集")
                else:
                    btn_train.setEnabled(False)
                    btn_train.setToolTip("尚未标注任何图片，请先完成标注")
                btn_train.clicked.connect(lambda checked, r=row: self.start_training_by_row(r))

                btn_delete = QPushButton("删除")
                btn_delete.setMinimumWidth(60)
                btn_delete.setStyleSheet("padding: 4px 8px; background-color: #f44336; color: white;")
                btn_delete.clicked.connect(lambda checked, r=row: self.delete_dataset_by_row(r))

                btn_layout.addWidget(btn_open)
                btn_layout.addWidget(btn_train)
                btn_layout.addWidget(btn_delete)
                self.dataset_table.setCellWidget(row, 5, btn_widget)

            logger.info(f"加载训练集成功: 共 {len(tasks)} 个训练集")

        except Exception as e:
            logger.error(f"加载训练集失败: {str(e)}")

        finally:
            session.close()

    def _load_dataset_remark(self, dataset_id: str) -> str:
        """从文件加载训练集备注"""
        try:
            remark_file = DatasetPathManager.get_dataset_path(dataset_id) / "remark.txt"
            if remark_file.exists():
                with open(remark_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            return ""
        except:
            return ""

    def _save_dataset_remark(self, dataset_id: str, remark: str) -> bool:
        """保存训练集备注到文件"""
        try:
            remark_file = DatasetPathManager.get_dataset_path(dataset_id) / "remark.txt"
            with open(remark_file, 'w', encoding='utf-8') as f:
                f.write(remark)
            return True
        except Exception as e:
            logger.error(f"保存备注失败: {str(e)}")
            return False

    def create_dataset(self):
        """创建新训练集"""
        logger.info("创建训练集")

        dialog = QDialog(self)
        dialog.setWindowTitle("创建训练集")

        layout = QFormLayout(dialog)

        dataset_name_edit = QLineEdit()
        dataset_name_edit.setPlaceholderText("请输入训练集名称")
        layout.addRow("训练集名称:", dataset_name_edit)

        dataset_remark_edit = QTextEdit()
        dataset_remark_edit.setPlaceholderText("请输入备注信息（可选）")
        dataset_remark_edit.setMaximumHeight(80)
        layout.addRow("备注:", dataset_remark_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() == QDialog.Accepted:
            dataset_name = dataset_name_edit.text().strip()
            remark = dataset_remark_edit.toPlainText().strip()

            if dataset_name:
                try:
                    # 检查训练集是否已存在
                    session = db_manager.get_session()
                    try:
                        existing_task = session.query(TrainingTask).filter_by(task_name=dataset_name).first()
                        if existing_task:
                            QMessageBox.warning(self, "警告", f"训练集 '{dataset_name}' 已存在!")
                            return
                    finally:
                        session.close()

                    # 创建数据库记录
                    session = db_manager.get_session()
                    try:
                        training_task = TrainingTask(
                            task_name=dataset_name,
                            status="pending"
                        )
                        session.add(training_task)
                        session.commit()
                        task_id = training_task.id
                    except Exception as e:
                        session.rollback()
                        raise
                    finally:
                        session.close()

                    # 创建训练集目录结构
                    DatasetPathManager.create_dataset_dirs(str(task_id))

                    # 保存备注到文件
                    if remark:
                        self._save_dataset_remark(str(task_id), remark)

                    self.load_datasets()
                    QMessageBox.information(self, "成功", f"训练集创建成功: {dataset_name} (ID: {task_id})")

                except Exception as e:
                    logger.error(f"创建训练集出错: {str(e)}")
                    QMessageBox.critical(self, "错误", f"创建训练集出错: {str(e)}")
            else:
                QMessageBox.warning(self, "警告", "训练集名称不能为空")

    def on_dataset_double_clicked(self, row: int, column: int):
        """双击训练集打开详情"""
        self.open_dataset_detail(row)

    def open_dataset_detail(self, row: int):
        """根据行号打开训练集详情"""
        try:
            item_name = self.dataset_table.item(row, 0)
            item_remark = self.dataset_table.item(row, 1)

            if item_name:
                dataset_id = item_name.data(Qt.UserRole)
                remark = item_remark.text() if item_remark else ""
                self.open_dataset_detail_dialog(dataset_id, remark)
        except Exception as e:
            logger.error(f"打开训练集详情失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开训练集详情失败: {str(e)}")

    def open_dataset_detail_dialog(self, dataset_id: str, remark: str):
        """打开训练集详情对话框"""
        try:
            from gui.dataset_detail_dialog import DatasetDetailDialog

            dialog = DatasetDetailDialog(dataset_id, remark, self)
            dialog.annotation_completed.connect(self.load_datasets)

            dialog.exec_()
            self.load_datasets()

        except Exception as e:
            logger.error(f"打开训练集详情失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开训练集详情失败: {str(e)}")

    def start_training_by_row(self, row: int):
        """根据行号启动训练对话框"""
        try:
            item_name = self.dataset_table.item(row, 0)
            item_annotated = self.dataset_table.item(row, 3)
            if not item_name:
                return

            dataset_id = item_name.data(Qt.UserRole)
            dataset_name = item_name.text()
            annotated = int(item_annotated.text()) if item_annotated else 0

            if annotated <= 0:
                QMessageBox.warning(self, "无法训练", "该训练集尚未标注任何图片，请先完成标注。")
                return

            dialog = TrainingLauncherDialog(dataset_id, dataset_name, annotated, self)
            dialog.training_completed.connect(self.load_datasets)
            dialog.exec_()
            self.load_datasets()

        except Exception as e:
            logger.error(f"启动训练失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动训练失败: {str(e)}")

    def delete_dataset_by_row(self, row: int):
        """根据行号删除训练集"""
        try:
            item_name = self.dataset_table.item(row, 0)
            if not item_name:
                return

            dataset_id = item_name.data(Qt.UserRole)
            dataset_name = item_name.text()

            # 二次确认
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除训练集 '{dataset_name}' 吗？\n此操作将删除所有图片和标注，不可恢复。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    import shutil

                    # 删除目录
                    dataset_path = DatasetPathManager.get_dataset_path(dataset_id)
                    if dataset_path.exists():
                        shutil.rmtree(dataset_path)

                    # 删除数据库记录
                    session = db_manager.get_session()
                    try:
                        task = session.query(TrainingTask).filter_by(id=dataset_id).first()
                        if task:
                            session.delete(task)
                            session.commit()
                    except Exception as e:
                        session.rollback()
                        raise
                    finally:
                        session.close()

                    self.load_datasets()
                    QMessageBox.information(self, "成功", f"训练集 '{dataset_name}' 删除成功")

                except Exception as e:
                    logger.error(f"删除训练集出错: {str(e)}")
                    QMessageBox.critical(self, "错误", f"删除训练集出错: {str(e)}")

        except Exception as e:
            logger.error(f"删除训练集失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"删除训练集失败: {str(e)}")


class TrainingLauncherDialog(QDialog):
    """训练启动对话框 - 在训练集列表上直接触发训练"""

    from PyQt5.QtCore import pyqtSignal
    training_completed = pyqtSignal()

    def __init__(self, dataset_id: str, dataset_name: str, annotated_count: int, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle(f"训练 - {dataset_name}")
        self.setMinimumSize(800, 600)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        self.training_widget = TrainingDetailTab(dataset_id, annotated_count, self)
        self.training_widget.training_completed.connect(self.training_completed.emit)
        layout.addWidget(self.training_widget)
