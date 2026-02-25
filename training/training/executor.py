#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练执行器

实现ITrainer接口，负责训练任务的执行和管理。
"""

import os
import logging
import shutil
from typing import Dict, Any, Optional
from datetime import datetime

from ultralytics import YOLO
from global_support.database import db_manager, TrainingTask, TrainingLog, ModelVersion
from global_support.task_scheduler import task_scheduler, TrainingTask as SchedulerTrainingTask

from ..core.interfaces import ITrainer
from ..core.base_manager import BaseManager
from ..dataset_path_manager import DatasetPathManager

# 日志配置
logger = logging.getLogger(__name__)


class TrainingExecutor(ITrainer, BaseManager):
    """训练执行器"""
    
    def __init__(self):
        """初始化训练执行器"""
        super().__init__()
        # 确保基础目录存在
        DatasetPathManager.ensure_directories()
        
    def train(self, task_id: int, dataset_config: Dict[str, Any],
              training_params: Dict[str, Any]) -> Dict[str, Any]:
        """执行训练任务

        Args:
            task_id: 任务ID
            dataset_config: 数据集配置
            training_params: 训练参数

        Returns:
            训练结果字典
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                return {"success": False, "error": f"任务不存在: {task_id}"}

            # 更新任务状态为训练中
            task.status = "training"
            session.commit()

            # 记录训练开始日志
            training_log = TrainingLog(
                task_id=task_id,
                log_type="training_start",
                message=f"开始训练任务: {task.task_name}"
            )
            session.add(training_log)
            session.commit()

            # 使用新的路径管理器
            dataset_name = task.task_name
            dataset_path = DatasetPathManager.get_dataset_path(dataset_name)

            # 生成data.yaml配置文件
            data_yaml_path = self._create_data_yaml(dataset_name)

            # 权重保存目录
            weights_dir = DatasetPathManager.get_weights_path(dataset_name)

            # 构建YOLO训练参数
            yolo_params = {
                "data": str(data_yaml_path),
                "epochs": training_params.get("epochs", task.epochs or 100),
                "batch": training_params.get("batch_size", task.batch_size or 16),
                "imgsz": training_params.get("image_size", 640),
                "project": str(weights_dir),
                "name": "train_run",
                "exist_ok": True,
                "verbose": False
            }

            # 使用YOLOv8进行训练
            self.log_operation("info", f"开始YOLOv8训练: {task.task_name}")

            try:
                # 加载YOLO模型
                model_type = training_params.get("model_type", "yolov8n.pt")
                model = YOLO(model_type)

                # 执行训练
                results = model.train(**yolo_params)

                # 保存训练结果
                result_info = self._save_training_result(task_id, results, dataset_name)

                # 更新任务状态为已完成
                task.status = "completed"
                task.completed_at = datetime.now()
                session.commit()

                # 记录训练完成日志
                training_log = TrainingLog(
                    task_id=task_id,
                    log_type="training_completed",
                    message=f"训练任务完成: {task.task_name}"
                )
                session.add(training_log)
                session.commit()

                self.log_operation("info", f"训练任务完成: {task.task_name}")

                return {
                    "success": True,
                    "task_id": task_id,
                    "task_name": task.task_name,
                    "result": result_info
                }

            except Exception as e:
                error_msg = f"训练过程中出错: {str(e)}"
                self.log_operation("error", error_msg, exc_info=True)

                # 更新任务状态为失败
                task.status = "failed"
                session.commit()

                # 记录错误日志
                training_log = TrainingLog(
                    task_id=task_id,
                    log_type="training_error",
                    message=error_msg
                )
                session.add(training_log)
                session.commit()

                return {"success": False, "error": error_msg}

        except Exception as e:
            self.log_operation("error", f"训练任务执行失败: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

        finally:
            session.close()

    def train_by_name(self, dataset_name: str, training_params: Dict[str, Any]) -> Dict[str, Any]:
        """根据训练集名称直接训练（不通过数据库）

        Args:
            dataset_name: 训练集名称
            training_params: 训练参数

        Returns:
            训练结果字典
        """
        try:
            self.log_operation("info", f"开始训练训练集: {dataset_name}")

            # 生成data.yaml配置文件
            data_yaml_path = self._create_data_yaml(dataset_name)

            # 权重保存目录
            weights_dir = DatasetPathManager.get_weights_path(dataset_name)

            # 构建YOLO训练参数
            yolo_params = {
                "data": str(data_yaml_path),
                "epochs": training_params.get("epochs", 100),
                "batch": training_params.get("batch_size", 16),
                "imgsz": training_params.get("image_size", 640),
                "project": str(weights_dir),
                "name": "train_run",
                "exist_ok": True,
                "verbose": True
            }

            # 加载YOLO模型
            model_type = training_params.get("model_type", "yolov8n.pt")
            model = YOLO(model_type)

            # 执行训练
            results = model.train(**yolo_params)

            # 保存训练结果
            result_info = self._save_training_result_by_name(dataset_name, results)

            self.log_operation("info", f"训练完成: {dataset_name}")

            return {
                "success": True,
                "dataset_name": dataset_name,
                "result": result_info
            }

        except Exception as e:
            error_msg = f"训练失败: {str(e)}"
            self.log_operation("error", error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    def _create_data_yaml(self, dataset_name: str):
        """创建YOLO训练所需的data.yaml文件

        Args:
            dataset_name: 训练集名称

        Returns:
            data.yaml文件路径
        """
        from pathlib import Path

        dataset_path = DatasetPathManager.get_dataset_path(dataset_name)
        images_dir = DatasetPathManager.get_images_path(dataset_name)
        labels_dir = DatasetPathManager.get_labels_path(dataset_name)

        data_yaml_content = f"""path: {dataset_path.absolute()}
train: {DatasetPathManager.IMAGES_DIR}
val: {DatasetPathManager.IMAGES_DIR}

names:
  0: fish
"""

        data_yaml_path = dataset_path / "data.yaml"
        with open(data_yaml_path, 'w', encoding='utf-8') as f:
            f.write(data_yaml_content)

        return data_yaml_path
            
    def _save_training_result(self, task_id: int, results: Any, dataset_name: str) -> Dict[str, Any]:
        """保存训练结果

        Args:
            task_id: 任务ID
            results: 训练结果对象
            dataset_name: 训练集名称

        Returns:
            结果信息字典
        """
        try:
            # 获取最佳模型路径
            weights_dir = DatasetPathManager.get_weights_path(dataset_name)
            best_model_path = weights_dir / "train_run" / "weights" / "best.pt"

            if not best_model_path.exists():
                self.log_operation("warning", f"最佳模型文件不存在: {best_model_path}")
                return {"model_path": None, "metrics": {}}

            # 同步到训练结果管理目录
            model_name = f"{dataset_name}_model"
            result_dir = DatasetPathManager.create_model_result_dir(model_name)
            shutil.copy2(str(best_model_path), str(result_dir / "best.pt"))
            self.log_operation("info", f"模型已同步到结果管理: {result_dir}")

            # 创建模型版本记录
            session = db_manager.get_session()
            try:
                metrics = self._extract_metrics(results)

                model_version = ModelVersion(
                    task_id=task_id,
                    model_path=str(best_model_path),
                    version="1.0",
                    metrics=metrics
                )

                session.add(model_version)
                session.commit()

                result_info = {
                    "model_path": str(best_model_path),
                    "model_result_path": str(result_dir / "best.pt"),
                    "model_version_id": model_version.id,
                    "metrics": metrics
                }

                self.log_operation("info", f"训练结果保存成功: 模型版本 {model_version.id}")
                return result_info

            except Exception as e:
                self.log_operation("error", f"保存模型版本失败: {str(e)}", exc_info=True)
                session.rollback()
                return {"model_path": str(best_model_path), "metrics": self._extract_metrics(results)}

            finally:
                session.close()

        except Exception as e:
            self.log_operation("error", f"保存训练结果失败: {str(e)}", exc_info=True)
            return {"model_path": None, "metrics": {}}

    def _save_training_result_by_name(self, dataset_name: str, results: Any) -> Dict[str, Any]:
        """根据训练集名称保存训练结果

        Args:
            dataset_name: 训练集名称
            results: 训练结果对象

        Returns:
            结果信息字典
        """
        try:
            # 获取最佳模型路径
            weights_dir = DatasetPathManager.get_weights_path(dataset_name)
            best_model_path = weights_dir / "train_run" / "weights" / "best.pt"

            if not best_model_path.exists():
                self.log_operation("warning", f"最佳模型文件不存在: {best_model_path}")
                return {"model_path": None, "metrics": {}}

            # 同步到训练结果管理目录
            model_name = f"{dataset_name}_model"
            result_dir = DatasetPathManager.create_model_result_dir(model_name)
            shutil.copy2(str(best_model_path), str(result_dir / "best.pt"))
            self.log_operation("info", f"模型已同步到结果管理: {result_dir}")

            metrics = self._extract_metrics(results)

            return {
                "model_path": str(best_model_path),
                "model_result_path": str(result_dir / "best.pt"),
                "model_name": model_name,
                "metrics": metrics
            }

        except Exception as e:
            self.log_operation("error", f"保存训练结果失败: {str(e)}", exc_info=True)
            return {"model_path": None, "metrics": {}}

    def _extract_metrics(self, results: Any) -> Dict[str, float]:
        """提取训练指标

        Args:
            results: 训练结果对象

        Returns:
            指标字典
        """
        try:
            # 尝试从results中获取指标
            if hasattr(results, 'results_dict'):
                return {
                    "precision": results.results_dict.get('metrics/precision(B)', 0),
                    "recall": results.results_dict.get('metrics/recall(B)', 0),
                    "mAP50": results.results_dict.get('metrics/mAP50(B)', 0),
                    "mAP50-95": results.results_dict.get('metrics/mAP50-95(B)', 0)
                }
            elif hasattr(results, 'metrics'):
                return results.metrics
            else:
                return {"precision": 0, "recall": 0, "mAP50": 0, "mAP50-95": 0}
        except:
            return {"precision": 0, "recall": 0, "mAP50": 0, "mAP50-95": 0}