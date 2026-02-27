#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练结果标签页

提供模型管理功能：导入、删除、对比、设置默认模型
"""

import logging
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
import os
import subprocess
import platform

from training_result.model_manager import model_manager

logger = logging.getLogger(__name__)


class TrainingResultTab(QWidget):
    """训练结果标签页"""

    def __init__(self, parent=None):
        """初始化训练结果标签页"""
        super().__init__(parent)
        self.current_model_name = None
        self.current_model_path = None
        self._init_ui()
        self.refresh_model_list()

    def showEvent(self, event):
        """页面显示时自动刷新"""
        super().showEvent(event)
        self.refresh_model_list()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 模型管理区域
        model_group = QGroupBox("模型管理")
        model_layout = QVBoxLayout(model_group)

        # 模型列表
        self.model_table = QTableWidget()
        self.model_table.setColumnCount(7)
        self.model_table.setHorizontalHeaderLabels(["模型文件", "训练集名称", "训练集ID", "创建时间", "大小", "删除", "打开文件夹"])
        self.model_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.model_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.model_table.cellClicked.connect(self.on_model_selected)
        self.model_table.setAlternatingRowColors(True)
        self.model_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 禁止编辑
        model_layout.addWidget(self.model_table)

        # 模型操作按钮
        btn_refresh = QPushButton("刷新列表")
        btn_refresh.clicked.connect(self.refresh_model_list)

        btn_import_model = QPushButton("导入模型")
        btn_import_model.clicked.connect(self.import_model)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_refresh)
        button_layout.addWidget(btn_import_model)
        button_layout.addStretch()

        model_layout.addLayout(button_layout)
        layout.addWidget(model_group)

    def refresh_model_list(self):
        """刷新模型列表"""
        try:
            # 重新加载模型
            model_manager.load_models()

            # 清空表格
            self.model_table.setRowCount(0)

            # 填充模型信息
            for i, model in enumerate(model_manager.models):
                self.model_table.insertRow(i)

                # 模型文件名
                filename = model.get('filename', '')
                self.model_table.setItem(i, 0, QTableWidgetItem(filename))

                # 训练集名称
                dataset_name = model.get('dataset_name', self._extract_dataset_name(model.get('path', '')))
                self.model_table.setItem(i, 1, QTableWidgetItem(dataset_name))

                # 训练集ID
                dataset_id = model.get('dataset_id', '')
                self.model_table.setItem(i, 2, QTableWidgetItem(dataset_id))

                # 创建时间
                created_time = model.get('created_time', '')
                if created_time:
                    created_str = created_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(created_time, 'strftime') else str(created_time)
                else:
                    created_str = ''
                self.model_table.setItem(i, 3, QTableWidgetItem(created_str))

                # 文件大小
                size = model.get('size', 0)
                size_str = self._format_size(size)
                self.model_table.setItem(i, 4, QTableWidgetItem(size_str))

                # 第6列：删除按钮
                btn_delete = QPushButton("删除")
                btn_delete.setStyleSheet("padding: 4px 8px; background-color: #f44336; color: white;")
                btn_delete.clicked.connect(lambda checked, r=i: self.delete_model_by_row(r))
                self.model_table.setCellWidget(i, 5, btn_delete)

                # 第7列：打开文件夹按钮
                btn_open = QPushButton("打开文件夹")
                btn_open.setStyleSheet("padding: 4px 8px;")
                btn_open.clicked.connect(lambda checked, r=i: self.open_folder_by_row(r))
                self.model_table.setCellWidget(i, 6, btn_open)

            logger.info(f"刷新模型列表完成,共 {len(model_manager.models)} 个模型")

        except Exception as e:
            logger.error(f"刷新模型列表失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"刷新模型列表失败: {str(e)}")

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def _extract_dataset_name(self, model_path: str) -> str:
        """从模型路径中提取训练集名称"""
        try:
            # 模型路径格式: training_data/{dataset_name}/models/train_run/weights/best.pt
            # 或者 models/{dataset_name}_model/best.pt
            if 'training_data' in model_path:
                # 从 training_data/{dataset_name} 提取
                parts = model_path.replace('\\', '/').split('/')
                if 'training_data' in parts:
                    idx = parts.index('training_data')
                    if idx + 1 < len(parts):
                        return parts[idx + 1]
            elif 'models' in model_path:
                # 从 models/{dataset_name}_model 提取
                import re
                match = re.search(r'models/([^/]+)_model', model_path.replace('\\', '/'))
                if match:
                    return match.group(1)
        except:
            pass
        return '未知'

    def on_model_selected(self, row, column):
        """选择模型时的回调"""
        if row >= 0 and row < self.model_table.rowCount():
            model_name_item = self.model_table.item(row, 0)
            if model_name_item:
                self.current_model_name = model_name_item.text()
                # 查找对应的模型路径
                for model in model_manager.models:
                    if model.get('filename') == self.current_model_name:
                        self.current_model_path = model.get('path')
                        # 显示模型详细信息
                        self._show_model_details(model)
                        logger.info(f"选择模型: {self.current_model_name}")
                        break

    def _show_model_details(self, model_info: dict):
        """显示模型详细信息"""
        details = [
            f"模型文件: {model_info.get('filename', '')}",
            f"模型路径: {model_info.get('path', '')}",
            f"训练集名称: {model_info.get('dataset_name', '未知')}",
            f"训练集ID: {model_info.get('dataset_id', '')}",
            f"任务名称: {model_info.get('task_name', '未知')}",
            f"任务描述: {model_info.get('task_description', '')}",
            f"创建时间: {model_info.get('created_time', '')}",
            f"版本: {model_info.get('version', '')}",
            f"是否默认: {'是' if model_info.get('is_default', False) else '否'}",
            f"文件大小: {self._format_size(model_info.get('size', 0))}",
        ]

        # 如果有类别信息,也显示
        if 'classes' in model_info and model_info['classes']:
            details.append(f"检测类别: {', '.join(model_info['classes'])}")

        # 如果有参数数量,也显示
        if 'params' in model_info:
            details.append(f"模型参数: {model_info['params']:,}")

        # 使用状态栏显示简要信息(如果有状态栏)
        try:
            main_window = self.window()
            if hasattr(main_window, 'statusBar'):
                info = f"{model_info.get('dataset_name', '未知')} - {model_info.get('filename', '')}"
                main_window.statusBar().showMessage(info, 5000)
        except:
            pass

    def delete_model_by_row(self, row: int):
        """根据行号删除模型"""
        if row < 0 or row >= len(model_manager.models):
            return

        model = model_manager.models[row]
        model_name = model.get('filename', '')
        model_path = model.get('path', '')

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除该模型吗？\n\n模型: {model_name}\n路径: {model_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                success = model_manager.delete_model(model_name)
                if success:
                    QMessageBox.information(self, "成功", "模型删除成功")
                    self.refresh_model_list()
                else:
                    QMessageBox.warning(self, "警告", "模型删除失败")
            except Exception as e:
                logger.error(f"删除模型失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"删除模型失败: {str(e)}")

    def open_folder_by_row(self, row: int):
        """根据行号打开模型文件夹"""
        if row < 0 or row >= len(model_manager.models):
            return

        model = model_manager.models[row]
        model_path = model.get('path', '')

        if not model_path:
            QMessageBox.warning(self, "警告", "无法获取模型路径")
            return

        try:
            model_dir = os.path.dirname(model_path)

            if platform.system() == "Windows":
                subprocess.Popen(f'explorer /select,"{model_path}"')
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-R", model_path])
            else:
                subprocess.Popen(["xdg-open", model_dir])

            logger.info(f"打开模型文件夹: {model_dir}")

        except Exception as e:
            logger.error(f"打开模型文件夹失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开模型文件夹失败: {str(e)}")

    def import_model(self):
        """导入模型文件"""
        logger.info("导入模型文件")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入模型文件",
            "",
            "模型文件 (*.pt)"
        )

        if file_path:
            try:
                result = model_manager.import_model(file_path)

                if result:
                    QMessageBox.information(self, "成功", f"模型导入成功: {result['filename']}")
                    self.refresh_model_list()
                else:
                    QMessageBox.warning(self, "警告", "模型导入失败")

            except Exception as e:
                logger.error(f"导入模型文件出错: {str(e)}")
                QMessageBox.critical(self, "错误", f"导入模型文件出错: {str(e)}")
        else:
            QMessageBox.information(self, "提示", "未选择模型文件")

    def delete_model(self):
        """删除模型文件"""
        if not self.current_model_name:
            QMessageBox.warning(self, "警告", "请先选择要删除的模型")
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的模型吗？\n\n模型: {self.current_model_name}\n路径: {self.current_model_path}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 从数据库中删除
                success = model_manager.delete_model(self.current_model_name)

                if success:
                    QMessageBox.information(self, "成功", "模型删除成功")
                    self.current_model_name = None
                    self.current_model_path = None
                    self.refresh_model_list()
                else:
                    QMessageBox.warning(self, "警告", "模型删除失败")

            except Exception as e:
                logger.error(f"删除模型文件出错: {str(e)}")
                QMessageBox.critical(self, "错误", f"删除模型文件出错: {str(e)}")

    def compare_models(self):
        """对比模型"""
        logger.info("对比模型")
        QMessageBox.information(self, "提示", "模型对比功能暂未实现")

    def set_default_model(self):
        """设置默认模型"""
        if not self.current_model_name:
            QMessageBox.warning(self, "警告", "请先选择要设为默认的模型")
            return

        try:
            success = model_manager.set_default_model(self.current_model_name)

            if success:
                QMessageBox.information(self, "成功", "已设置为默认模型")
                self.refresh_model_list()
            else:
                QMessageBox.warning(self, "警告", "设置默认模型失败")

        except Exception as e:
            logger.error(f"设置默认模型出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"设置默认模型出错: {str(e)}")

    def open_model_folder(self):
        """打开模型文件所在的文件夹"""
        if not self.current_model_path:
            QMessageBox.warning(self, "警告", "请先选择一个模型")
            return

        try:
            # 获取模型文件的目录
            model_dir = os.path.dirname(self.current_model_path)

            # 根据操作系统打开文件夹
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer /select,"{self.current_model_path}"')
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", "-R", self.current_model_path])
            else:  # Linux
                subprocess.Popen(["xdg-open", model_dir])

            logger.info(f"打开模型文件夹: {model_dir}")

        except Exception as e:
            logger.error(f"打开模型文件夹失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开模型文件夹失败: {str(e)}")

