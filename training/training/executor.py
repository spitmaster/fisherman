#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练执行器

实现ITrainer接口，负责训练任务的执行和管理。
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ultralytics import YOLO
from global_support.database import db_manager, TrainingTask, TrainingLog, ModelVersion
from global_support.task_scheduler import task_scheduler, TrainingTask as SchedulerTrainingTask

from ..core.interfaces import ITrainer
from ..core.base_manager import BaseManager

# 日志配置
logger = logging.getLogger(__name__)


class TrainingExecutor(ITrainer, BaseManager):
    """训练执行器"""
    
    def __init__(self):
        """初始化训练执行器"""
        super().__init__()
        
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
            
            # 获取任务目录
            task_dir = os.path.join("training_data", task.task_name)
            
            # 构建YOLO训练参数
            yolo_params = {
                "data": os.path.join(task_dir, "dataset", "data.yaml"),
                "epochs": task.epochs,
                "batch": task.batch_size,
                "imgsz": 640,
                "project": task_dir,
                "name": "train",
                "exist_ok": True,
                "verbose": False
            }
            
            # 使用YOLOv8进行训练
            self.log_operation("info", f"开始YOLOv8训练: {task.task_name}")
            
            try:
                # 加载YOLO模型
                model = YOLO("yolov8n.pt")  # 使用nano模型
                
                # 执行训练
                results = model.train(**yolo_params)
                
                # 保存训练结果
                result_info = self._save_training_result(task_id, results, task_dir)
                
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
            
    def _save_training_result(self, task_id: int, results: Any, task_dir: str) -> Dict[str, Any]:
        """保存训练结果
        
        Args:
            task_id: 任务ID
            results: 训练结果对象
            task_dir: 任务目录
            
        Returns:
            结果信息字典
        """
        try:
            # 获取最佳模型路径
            best_model_path = os.path.join(task_dir, "train", "weights", "best.pt")
            
            if not os.path.exists(best_model_path):
                self.log_operation("warning", f"最佳模型文件不存在: {best_model_path}")
                return {"model_path": None, "metrics": {}}
            
            # 创建模型版本记录
            session = db_manager.get_session()
            try:
                model_version = ModelVersion(
                    task_id=task_id,
                    model_path=best_model_path,
                    version="1.0",
                    metrics={
                        "precision": getattr(results, "metrics", {}).get("precision", 0),
                        "recall": getattr(results, "metrics", {}).get("recall", 0),
                        "mAP50": getattr(results, "metrics", {}).get("mAP50", 0),
                        "mAP50-95": getattr(results, "metrics", {}).get("mAP50-95", 0)
                    }
                )
                
                session.add(model_version)
                session.commit()
                
                result_info = {
                    "model_path": best_model_path,
                    "model_version_id": model_version.id,
                    "metrics": model_version.metrics
                }
                
                self.log_operation("info", f"训练结果保存成功: 模型版本 {model_version.id}")
                return result_info
                
            except Exception as e:
                self.log_operation("error", f"保存模型版本失败: {str(e)}", exc_info=True)
                session.rollback()
                return {"model_path": best_model_path, "metrics": {}}
                
            finally:
                session.close()
                
        except Exception as e:
            self.log_operation("error", f"保存训练结果失败: {str(e)}", exc_info=True)
            return {"model_path": None, "metrics": {}}
            
    def save_training_result(self, task_id: int, result: Dict[str, Any]) -> bool:
        """保存训练结果
        
        Args:
            task_id: 任务ID
            result: 训练结果字典
            
        Returns:
            保存是否成功
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                self.log_operation("error", f"任务不存在: {task_id}")
                return False
                
            task_dir = os.path.join("training_data", task.task_name)
            
            # 保存结果到数据库
            model_version = ModelVersion(
                task_id=task_id,
                model_path=result.get("model_path"),
                version="1.0",
                metrics=result.get("metrics", {})
            )
            
            session.add(model_version)
            session.commit()
            
            self.log_operation("info", f"训练结果保存成功: 任务 {task_id}, 模型版本 {model_version.id}")
            return True
            
        except Exception as e:
            self.log_operation("error", f"保存训练结果失败: {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()