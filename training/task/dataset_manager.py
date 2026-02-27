#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集管理器

实现IDatasetManager接口，负责数据集的导入、管理和查询。
"""

import os
import shutil
import logging
from typing import List, Dict, Any, Optional

from global_support.database import db_manager, TrainingTask

from ..core.interfaces import IDatasetManager
from ..core.base_manager import BaseManager
from ..dataset_path_manager import DatasetPathManager

# 日志配置
logger = logging.getLogger(__name__)


class DatasetManager(IDatasetManager, BaseManager):
    """数据集管理器"""
    
    def __init__(self):
        """初始化数据集管理器"""
        super().__init__()
        # 确保基础目录存在
        DatasetPathManager.ensure_directories()
        
    def import_images(self, task_id: int, image_paths: List[str]) -> int:
        """导入图片到训练任务（复制方式）

        Args:
            task_id: 任务ID
            image_paths: 图片路径列表

        Returns:
            成功导入的图片数量
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                self.log_operation("error", f"任务不存在: {task_id}")
                return 0

            # 创建训练集目录结构（使用任务ID）
            dataset_path = DatasetPathManager.create_dataset_dirs(str(task.id))
            images_dir = DatasetPathManager.get_images_path(str(task.id))

            imported_count = 0
            for image_path in image_paths:
                if os.path.exists(image_path):
                    # 获取文件名
                    filename = os.path.basename(image_path)
                    target_path = images_dir / filename

                    # 复制文件到训练集目录
                    shutil.copy2(image_path, str(target_path))
                    imported_count += 1

                    self.log_operation("debug", f"图片导入成功: {filename}")
                else:
                    self.log_operation("error", f"图片文件不存在: {image_path}")

            # 更新任务状态
            if imported_count > 0:
                if task.status == "pending":
                    task.status = "ready"
                    session.commit()

                self.log_operation("info", f"图片导入完成: 成功导入 {imported_count} 张图片到 {dataset_path}")

            return imported_count

        except Exception as e:
            self.log_operation("error", f"导入图片失败: {str(e)}", exc_info=True)
            return 0

        finally:
            session.close()

    def import_images_to_dataset(self, dataset_id: str, image_paths: List[str]) -> int:
        """直接导入图片到指定训练集（不通过数据库）

        Args:
            dataset_id: 训练集ID (UUID)
            image_paths: 图片路径列表

        Returns:
            成功导入的图片数量
        """
        try:
            # 创建训练集目录结构
            dataset_path = DatasetPathManager.create_dataset_dirs(dataset_id)
            images_dir = DatasetPathManager.get_images_path(dataset_id)

            imported_count = 0
            for image_path in image_paths:
                if os.path.exists(image_path):
                    # 获取文件名
                    filename = os.path.basename(image_path)
                    target_path = images_dir / filename

                    # 复制文件
                    shutil.copy2(image_path, str(target_path))
                    imported_count += 1

                    self.log_operation("debug", f"图片导入成功: {filename}")
                else:
                    self.log_operation("error", f"图片文件不存在: {image_path}")

            self.log_operation("info", f"图片导入完成: 成功导入 {imported_count} 张图片到 {dataset_path}")
            return imported_count

        except Exception as e:
            self.log_operation("error", f"导入图片失败: {str(e)}", exc_info=True)
            return 0
            
    def get_dataset_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取数据集信息

        Args:
            task_id: 任务ID

        Returns:
            数据集信息字典，包含以下字段：
            - total_images: 总图片数
            - annotated_images: 已标注图片数
            - annotation_progress: 标注进度百分比
            - dataset_path: 数据集路径
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                return None

            # 使用新的路径管理器（使用任务ID）
            dataset_info = DatasetPathManager.get_dataset_info(str(task.id))

            if not dataset_info:
                return {
                    "total_images": 0,
                    "annotated_images": 0,
                    "annotation_progress": 0,
                    "dataset_path": str(DatasetPathManager.get_dataset_path(str(task.id)))
                }

            # 计算标注进度
            total_images = dataset_info["image_count"]
            label_count = dataset_info["label_count"]
            annotation_progress = (label_count / total_images * 100) if total_images > 0 else 0

            return {
                "total_images": total_images,
                "annotated_images": label_count,
                "annotation_progress": annotation_progress,
                "dataset_path": dataset_info["path"]
            }

        except Exception as e:
            self.log_operation("error", f"获取数据集信息失败: {str(e)}", exc_info=True)
            return None

        finally:
            session.close()

    def get_dataset_info_by_name(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """根据训练集ID获取数据集信息

        Args:
            dataset_id: 训练集ID (UUID)

        Returns:
            数据集信息字典
        """
        try:
            dataset_info = DatasetPathManager.get_dataset_info(dataset_id)

            if not dataset_info:
                return None

            # 计算标注进度
            total_images = dataset_info["image_count"]
            label_count = dataset_info["label_count"]
            annotation_progress = (label_count / total_images * 100) if total_images > 0 else 0

            return {
                "total_images": total_images,
                "annotated_images": label_count,
                "annotation_progress": annotation_progress,
                "dataset_path": dataset_info["path"],
                "has_weights": dataset_info["has_weights"]
            }

        except Exception as e:
            self.log_operation("error", f"获取数据集信息失败: {str(e)}", exc_info=True)
            return None

    def list_all_datasets(self) -> List[Dict[str, Any]]:
        """列出所有训练集信息

        Returns:
            训练集信息列表
        """
        try:
            datasets = DatasetPathManager.list_datasets()
            result = []
            for name in datasets:
                info = self.get_dataset_info_by_name(name)
                if info:
                    result.append(info)
            return result
        except Exception as e:
            self.log_operation("error", f"列出训练集失败: {str(e)}", exc_info=True)
            return []
            
    def get_image_list(self, task_id: int) -> List[str]:
        """获取任务的图片列表

        Args:
            task_id: 任务ID

        Returns:
            图片文件名列表
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                return []

            return self.get_image_list_by_name(str(task.id))

        except Exception as e:
            self.log_operation("error", f"获取图片列表失败: {str(e)}", exc_info=True)
            return []

        finally:
            session.close()

    def get_image_list_by_name(self, dataset_id: str) -> List[str]:
        """根据训练集ID获取图片列表

        Args:
            dataset_id: 训练集ID (UUID)

        Returns:
            图片文件名列表
        """
        try:
            images_dir = DatasetPathManager.get_images_path(dataset_id)

            if not images_dir.exists():
                return []

            image_files = [f.name for f in images_dir.iterdir()
                          if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp')]

            return sorted(image_files)

        except Exception as e:
            self.log_operation("error", f"获取图片列表失败: {str(e)}", exc_info=True)
            return []

    def get_unannotated_images(self, task_id: int) -> List[str]:
        """获取未标注的图片列表

        Args:
            task_id: 任务ID

        Returns:
            未标注图片文件名列表
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                return []

            return self.get_unannotated_images_by_name(str(task.id))

        except Exception as e:
            self.log_operation("error", f"获取未标注图片列表失败: {str(e)}", exc_info=True)
            return []

        finally:
            session.close()

    def get_unannotated_images_by_name(self, dataset_id: str) -> List[str]:
        """根据训练集ID获取未标注的图片列表

        Args:
            dataset_id: 训练集ID (UUID)

        Returns:
            未标注图片文件名列表
        """
        try:
            images_dir = DatasetPathManager.get_images_path(dataset_id)
            labels_dir = DatasetPathManager.get_labels_path(dataset_id)

            if not images_dir.exists():
                return []

            image_files = [f for f in images_dir.iterdir()
                          if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp')]

            unannotated_images = []
            for img_file in image_files:
                txt_file = img_file.stem + ".txt"
                label_path = labels_dir / txt_file

                if not label_path.exists() or label_path.stat().st_size == 0:
                    unannotated_images.append(img_file.name)

            return sorted(unannotated_images)

        except Exception as e:
            self.log_operation("error", f"获取未标注图片列表失败: {str(e)}", exc_info=True)
            return []