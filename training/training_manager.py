#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 训练管理器（Facade）

负责管理训练任务的整个生命周期。
采用Facade模式，委托给各个子模块处理具体逻辑。

主要功能：
- 训练任务创建和管理（委托给TaskCreator）
- 数据集导入和管理（委托给DatasetManager）
- 标注功能（委托给AnnotationTool）
- 训练过程管理（委托给TrainingExecutor）
- 训练结果处理（委托给ResultSaver）
- 验证功能（委托给TrainingValidator）
- 备份恢复（委托给TrainingBackupManager）
- 统计功能（委托给TrainingStatistics）
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from global_support.database import db_manager, TrainingTask, TrainingLog, ModelVersion
from global_support.task_scheduler import task_scheduler, TrainingTask as SchedulerTrainingTask

# 导入子模块
from .task.creator import TaskCreator
from .task.dataset_manager import DatasetManager
from .task.status_tracker import TaskStatusTracker
from .training.executor import TrainingExecutor
from .validator import training_validator, dataset_validator
from .statistics import training_statistics
from .backup import training_backup_manager

# 日志配置
logger = logging.getLogger(__name__)


class TrainingManager:
    """训练管理器（Facade）
    
    采用Facade模式，统一管理训练任务的各个方面，
    具体逻辑委托给各个子模块处理。
    """
    
    def __init__(self):
        """初始化训练管理器"""
        # 初始化子模块
        self.task_creator = TaskCreator()
        self.dataset_manager = DatasetManager()
        self.status_tracker = TaskStatusTracker()
        self.training_executor = TrainingExecutor()
        
        # 缓存任务信息
        self.training_tasks: Dict[int, Dict[str, Any]] = {}
        
        # 加载所有训练任务
        self._load_all_training_tasks()
    
    def _load_all_training_tasks(self):
        """加载所有训练任务"""
        session = db_manager.get_session()
        try:
            tasks = session.query(TrainingTask).all()
            for task in tasks:
                task_info = {
                    "task_dir": os.path.join("training_data", task.task_name),
                    "status": task.status,
                    "annotated_images": 0,
                    "total_images": 0
                }
                
                # 获取数据集信息
                if task.dataset_path and os.path.exists(task.dataset_path):
                    image_dir = os.path.join(os.path.dirname(task.dataset_path), "images", "train")
                    label_dir = os.path.join(os.path.dirname(task.dataset_path), "labels", "train")
                    
                    if os.path.exists(image_dir):
                        image_files = [f for f in os.listdir(image_dir) 
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                        task_info["total_images"] = len(image_files)
                        
                        if os.path.exists(label_dir):
                            annotated_count = 0
                            for img_file in image_files:
                                txt_file = os.path.splitext(img_file)[0] + ".txt"
                                if os.path.exists(os.path.join(label_dir, txt_file)):
                                    annotated_count += 1
                            task_info["annotated_images"] = annotated_count
                
                self.training_tasks[task.id] = task_info
                
            logger.info(f"加载训练任务成功: 共 {len(tasks)} 个任务")
            
        except Exception as e:
            logger.error(f"加载训练任务出错: {str(e)}", exc_info=True)
            
        finally:
            session.close()
    
    # ==================== 任务CRUD ====================
    
    def create_training_task(self, task_name: str, task_description: str, 
                           dataset_path: Optional[str] = None, 
                           epochs: int = 50, batch_size: int = 8) -> Optional[int]:
        """创建新的训练任务
        
        Args:
            task_name: 任务名称
            task_description: 任务描述
            dataset_path: 数据集路径
            epochs: 训练轮数
            batch_size: 批次大小
            
        Returns:
            训练任务ID
        """
        # 验证配置
        is_valid, msg = training_validator.validate_training_config({
            "epochs": epochs,
            "batch_size": batch_size
        })
        if not is_valid:
            logger.error(f"训练配置验证失败: {msg}")
            return None
        
        return self.task_creator.create_training_task(
            task_name, task_description, dataset_path, epochs, batch_size
        )
    
    def get_all_training_tasks(self) -> List[Dict[str, Any]]:
        """获取所有训练任务
        
        Returns:
            训练任务列表
        """
        session = db_manager.get_session()
        try:
            tasks = session.query(TrainingTask).all()
            
            task_list = []
            for task in tasks:
                task_info = self.training_tasks.get(task.id)
                if not task_info:
                    task_info = {
                        "task_dir": os.path.join("training_data", task.task_name),
                        "status": task.status,
                        "annotated_images": 0,
                        "total_images": 0
                    }
                
                task_list.append({
                    "id": task.id,
                    "task_name": task.task_name,
                    "task_description": task.task_description,
                    "status": task.status,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at,
                    "dataset_path": task.dataset_path,
                    "model_path": task.model_path,
                    "epochs": task.epochs,
                    "batch_size": task.batch_size,
                    "annotated_images": task_info["annotated_images"],
                    "total_images": task_info["total_images"]
                })
            
            return task_list
            
        except Exception as e:
            logger.error(f"获取训练任务列表出错: {str(e)}", exc_info=True)
            return []
            
        finally:
            session.close()
    
    def get_training_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            训练任务详情
        """
        session = db_manager.get_session()
        try:
            task = session.get(TrainingTask, task_id)
            
            if not task:
                logger.error(f"训练任务不存在: {task_id}")
                return None
            
            task_info = self.training_tasks.get(task_id)
            if not task_info:
                task_info = {
                    "task_dir": os.path.join("training_data", task.task_name),
                    "status": task.status,
                    "annotated_images": 0,
                    "total_images": 0
                }
            
            return {
                "id": task.id,
                "task_name": task.task_name,
                "task_description": task.task_description,
                "status": task.status,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "dataset_path": task.dataset_path,
                "model_path": task.model_path,
                "epochs": task.epochs,
                "batch_size": task.batch_size,
                "annotated_images": task_info["annotated_images"],
                "total_images": task_info["total_images"]
            }
            
        except Exception as e:
            logger.error(f"获取训练任务详情出错: {str(e)}", exc_info=True)
            return None
            
        finally:
            session.close()
    
    def update_training_task(self, task_id: int, **kwargs) -> bool:
        """更新训练任务信息
        
        Args:
            task_id: 任务ID
            **kwargs: 要更新的字段
            
        Returns:
            更新是否成功
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            
            if not task:
                logger.error(f"训练任务不存在: {task_id}")
                return False
            
            # 更新允许的字段
            allowed_fields = ["task_name", "task_description", "epochs", "batch_size", "status"]
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(task, field):
                    setattr(task, field, value)
            
            # 处理任务名称变更
            if "task_name" in kwargs and kwargs["task_name"] != task.task_name:
                old_dir = os.path.join("training_data", task.task_name)
                new_dir = os.path.join("training_data", kwargs["task_name"])
                
                if os.path.exists(old_dir) and old_dir != new_dir:
                    os.rename(old_dir, new_dir)
            
            session.commit()
            
            # 更新缓存
            if task_id in self.training_tasks:
                self.training_tasks[task_id]["task_dir"] = os.path.join("training_data", task.task_name)
            
            logger.info(f"训练任务更新成功: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新训练任务出错: {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()
    
    def delete_training_task(self, task_id: int) -> bool:
        """删除训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            删除是否成功
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            
            if not task:
                logger.error(f"训练任务不存在: {task_id}")
                return False
            
            # 删除任务目录
            task_dir = os.path.join("training_data", task.task_name)
            if os.path.exists(task_dir):
                import shutil
                try:
                    shutil.rmtree(task_dir)
                    logger.info(f"任务目录删除成功: {task_dir}")
                except Exception as e:
                    logger.error(f"删除任务目录失败: {str(e)}")
            
            # 删除数据库记录
            session.delete(task)
            session.commit()
            
            # 从训练任务字典中移除
            if task_id in self.training_tasks:
                del self.training_tasks[task_id]
            
            logger.info(f"训练任务删除成功: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除训练任务出错: {str(e)}", exc_info=True)
            session.rollback()
            return False
        
        finally:
            session.close()
    
    # ==================== 数据集管理 ====================
    
    def import_images(self, task_id: int, image_paths: List[str]) -> int:
        """导入图片到训练任务
        
        Args:
            task_id: 任务ID
            image_paths: 图片路径列表
            
        Returns:
            导入的图片数量
        """
        return self.dataset_manager.import_images(task_id, image_paths)
    
    def get_dataset_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取数据集信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            数据集信息
        """
        return self.dataset_manager.get_dataset_info(task_id)
    
    def get_image_list(self, task_id: int) -> List[str]:
        """获取任务的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            图片文件列表
        """
        return self.dataset_manager.get_image_list(task_id)
    
    def get_unannotated_images(self, task_id: int) -> List[str]:
        """获取未标注的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            未标注的图片文件列表
        """
        return self.dataset_manager.get_unannotated_images(task_id)
    
    # ==================== 标注功能 ====================
    
    def start_annotation(self, task_id: int) -> Optional[Dict[str, Any]]:
        """开始标注任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            标注任务信息
        """
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task_id)
            
            if not training_task:
                logger.error(f"训练任务不存在: {task_id}")
                return None
            
            # 更新任务状态为标注中
            if training_task.status == 'pending':
                training_task.status = 'annotating'
                session.commit()
                logger.info(f"任务状态更新为标注中: {task_id}")
            
            # 获取任务信息
            task_info = self.training_tasks.get(task_id)
            if not task_info:
                task_info = {
                    "task_dir": os.path.join("training_data", training_task.task_name),
                    "status": training_task.status,
                    "annotated_images": 0,
                    "total_images": 0
                }
                self.training_tasks[task_id] = task_info
            
            # 获取图片列表
            image_dir = os.path.join(task_info["task_dir"], "dataset/images/train")
            label_dir = os.path.join(task_info["task_dir"], "dataset/labels/train")
            
            if not os.path.exists(image_dir):
                return None
            
            image_files = [f for f in os.listdir(image_dir) 
                          if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            
            annotated_count = 0
            for img_file in image_files:
                txt_file = os.path.splitext(img_file)[0] + ".txt"
                if os.path.exists(os.path.join(label_dir, txt_file)):
                    annotated_count += 1
            
            task_info["annotated_images"] = annotated_count
            task_info["total_images"] = len(image_files)
            
            logger.info(f"标注任务启动: 任务ID={task_id}, 已标注={annotated_count}, 总数={len(image_files)}")
            
            return {
                "task_info": task_info,
                "image_files": image_files,
                "annotated_count": annotated_count
            }
            
        except Exception as e:
            logger.error(f"启动标注任务出错: {str(e)}", exc_info=True)
            session.rollback()
            return None
            
        finally:
            session.close()
    
    def save_annotation(self, task_id: int, image_filename: str, annotations: List) -> bool:
        """保存标注数据
        
        Args:
            task_id: 任务ID
            image_filename: 图片文件名
            annotations: 标注数据
            
        Returns:
            保存结果
        """
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task_id)
            
            if not training_task:
                logger.error(f"训练任务不存在: {task_id}")
                return False
            
            task_info = self.training_tasks.get(task_id)
            if not task_info:
                task_info = {
                    "task_dir": os.path.join("training_data", training_task.task_name),
                    "status": training_task.status,
                    "annotated_images": 0,
                    "total_images": 0
                }
                self.training_tasks[task_id] = task_info
            
            # 保存标注到YOLO格式的txt文件
            label_dir = os.path.join(task_info["task_dir"], "dataset/labels/train")
            txt_filename = os.path.splitext(image_filename)[0] + ".txt"
            txt_path = os.path.join(label_dir, txt_filename)
            
            with open(txt_path, "w", encoding="utf-8") as f:
                for annotation in annotations:
                    class_id, x_center, y_center, width, height = annotation
                    f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
            
            # 更新任务信息
            task_info["annotated_images"] += 1
            
            logger.info(f"标注保存成功: 任务ID={task_id}, 图片={image_filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"保存标注出错: {str(e)}", exc_info=True)
            return False
            
        finally:
            session.close()
    
    # ==================== 训练执行 ====================
    
    def start_training(self, task_id: int) -> bool:
        """开始训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            训练任务是否成功启动
        """
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task_id)
            
            if not training_task:
                logger.error(f"训练任务不存在: {task_id}")
                return False
            
            task_info = self.training_tasks.get(task_id)
            if not task_info:
                task_info = {
                    "task_dir": os.path.join("training_data", training_task.task_name),
                    "status": training_task.status,
                    "annotated_images": 0,
                    "total_images": 0
                }
                self.training_tasks[task_id] = task_info
            
            # 验证任务是否可以训练
            dataset_info = self.get_dataset_info(task_id)
            is_valid, msg = training_validator.validate_task_for_training(
                self.get_training_task_by_id(task_id) or {},
                dataset_info or {}
            )
            if not is_valid:
                logger.error(f"任务验证失败: {msg}")
                return False
            
            # 更新任务状态为训练中
            training_task.status = "training"
            session.commit()
            
            # 创建训练任务并添加到调度器
            scheduler_task = SchedulerTrainingTask(
                task_id=task_id,
                task_name=training_task.task_name,
                dataset_path=training_task.dataset_path,
                model_path=os.path.join(task_info["task_dir"], "models"),
                epochs=training_task.epochs,
                batch_size=training_task.batch_size
            )
            
            scheduler_task.on_completed = self._on_training_completed
            scheduler_task.on_error = self._on_training_error
            scheduler_task.on_progress = self._on_training_progress
            
            # 实现训练任务的run方法
            scheduler_task.run = lambda: self._run_training(scheduler_task, task_info)
            
            # 添加到调度器
            task_scheduler.add_task(scheduler_task)
            logger.info(f"训练任务启动成功: {training_task.task_name} (ID: {task_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"启动训练任务出错: {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()
    
    def _run_training(self, scheduler_task, task_info: Dict[str, Any]):
        """运行训练任务
        
        Args:
            scheduler_task: 调度器任务对象
            task_info: 任务信息
        """
        try:
            # 配置训练参数
            data_config = os.path.join(task_info["task_dir"], "data.yaml")
            training_config = {
                "data": data_config,
                "epochs": scheduler_task.epochs,
                "batch": scheduler_task.batch_size,
                "imgsz": 640,
                "project": task_info["task_dir"],
                "name": "yolo_training",
                "exist_ok": True,
                "verbose": True,
                "device": getattr(scheduler_task, "device", "cpu"),
                "workers": 1,
                "patience": min(50, scheduler_task.epochs // 3),
                "lr0": 0.01,
                "lrf": 0.01
            }
            
            # 注册进度回调
            def progress_callback(progress: float, message: str = ""):
                scheduler_task.update_progress(progress, message)
            
            # 执行训练
            logger.info(f"开始执行训练任务: {scheduler_task.task_name}")
            result = self.training_executor.train(training_config, progress_callback)
            
            if result["success"]:
                self._save_training_result(scheduler_task.task_id, result["results"])
                scheduler_task.complete(result["results"])
            else:
                scheduler_task.fail(result["error"])
            
        except Exception as e:
            logger.error(f"训练任务执行错误: {str(e)}", exc_info=True)
            scheduler_task.fail(e)
    
    def _save_training_result(self, task_id: int, results):
        """保存训练结果
        
        Args:
            task_id: 任务ID
            results: 训练结果对象
        """
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task_id)
            
            if not training_task:
                logger.error(f"训练任务不存在: {task_id}")
                return
            
            task_info = self.training_tasks.get(task_id)
            
            # 确定训练后的模型文件路径
            model_path = None
            if hasattr(results, 'weights') and results.weights:
                model_path = results.weights
            else:
                runs_dir = os.path.join("runs", "detect")
                if os.path.exists(runs_dir):
                    try:
                        train_dirs = [d for d in os.listdir(runs_dir) if d.startswith('train')]
                        if train_dirs:
                            latest_train = sorted(train_dirs)[-1]
                            model_path = os.path.join(runs_dir, latest_train, "weights", "best.pt")
                    except Exception as e:
                        logger.warning(f"查找训练目录失败: {e}")
            
            if not model_path or not os.path.exists(model_path):
                logger.error(f"找不到训练后的模型文件: {model_path}")
                return
            
            # 复制模型到任务目录
            import shutil
            dest_dir = os.path.join(task_info["task_dir"], "models")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, "best.pt")
            shutil.copy2(model_path, dest_path)
            
            # 提取训练指标
            mAP = None
            loss = None
            
            try:
                if hasattr(results, 'metrics'):
                    metrics = results.metrics
                    if hasattr(metrics, 'map50'):
                        mAP = float(metrics.map50)
                    elif isinstance(metrics, dict) and 'metrics/mAP50' in metrics:
                        mAP = float(metrics['metrics/mAP50'])
                    
                    if hasattr(metrics, 'box_loss'):
                        loss = float(metrics.box_loss)
                    elif isinstance(metrics, dict) and 'metrics/box_loss' in metrics:
                        loss = float(metrics['metrics/box_loss'])
            except Exception as e:
                logger.warning(f"提取训练指标失败: {e}")
            
            # 更新任务信息
            training_task.status = "completed"
            training_task.model_path = dest_path
            if mAP is not None:
                training_task.mAP = mAP
            if loss is not None:
                training_task.loss = loss
            
            # 保存模型版本信息
            model_version = ModelVersion(
                training_task_id=task_id,
                model_path=dest_path,
                version="v1.0",
                is_default=True,
                file_size=os.path.getsize(dest_path)
            )
            
            session.add(model_version)
            session.commit()
            
            logger.info(f"训练结果保存成功: 任务ID={task_id}, 模型路径={dest_path}, mAP={mAP}, loss={loss}")
            
        except Exception as e:
            logger.error(f"保存训练结果出错: {str(e)}", exc_info=True)
            session.rollback()
            raise
            
        finally:
            session.close()
    
    def _on_training_completed(self, task, result):
        """训练完成回调"""
        logger.info(f"训练任务完成: {task.task_name}")
    
    def _on_training_error(self, task, error):
        """训练错误回调"""
        logger.error(f"训练任务失败: {task.task_name} - {str(error)}")
        
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task.task_id)
            if training_task:
                training_task.status = "failed"
                session.commit()
        except Exception as e:
            logger.error(f"更新任务状态出错: {str(e)}")
        finally:
            session.close()
    
    def _on_training_progress(self, task, progress, message):
        """训练进度回调"""
        logger.info(f"训练进度: {task.task_name} - {progress*100:.1f}% - {message}")
    
    # ==================== 任务状态 ====================
    
    def get_training_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取训练任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        return self.status_tracker.get_full_status(task_id)
    
    def update_task_status(self, task_id: int, status: str) -> bool:
        """更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            
        Returns:
            更新结果
        """
        # 验证状态
        is_valid, msg = training_validator.validate_status(status)
        if not is_valid:
            logger.error(f"无效的任务状态: {status}")
            return False
        
        return self.status_tracker.update_task_status(task_id, status)
    
    def get_task_progress(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务进度
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务进度信息
        """
        return self.status_tracker.get_task_progress(task_id)
    
    # ==================== 验证功能 ====================
    
    def validate_training_task(self, task_id: int) -> tuple[bool, str]:
        """验证训练任务是否可以进行训练
        
        Args:
            task_id: 任务ID
            
        Returns:
            验证结果和错误信息
        """
        task_info = self.get_training_task_by_id(task_id)
        if not task_info:
            return False, f"训练任务不存在: {task_id}"
        
        dataset_info = self.get_dataset_info(task_id)
        
        return training_validator.validate_task_for_training(task_info, dataset_info or {})
    
    def batch_validate_tasks(self) -> Dict[str, Any]:
        """批量验证所有训练任务
        
        Returns:
            验证结果字典
        """
        validation_result = {
            "total_tasks": 0,
            "valid_tasks": 0,
            "invalid_tasks": 0,
            "errors": {}
        }
        
        try:
            all_tasks = self.get_all_training_tasks()
            validation_result["total_tasks"] = len(all_tasks)
            
            for task in all_tasks:
                task_id = task["id"]
                is_valid, error_msg = self.validate_training_task(task_id)
                
                if is_valid:
                    validation_result["valid_tasks"] += 1
                else:
                    validation_result["invalid_tasks"] += 1
                    validation_result["errors"][task_id] = error_msg
            
            logger.info(f"批量验证完成: 共{validation_result['total_tasks']}个任务，"
                       f"有效{validation_result['valid_tasks']}个，"
                       f"无效{validation_result['invalid_tasks']}个")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"批量验证任务失败: {str(e)}", exc_info=True)
            return {"total_tasks": 0, "valid_tasks": 0, "invalid_tasks": 0, "errors": {}}
    
    # ==================== 备份恢复 ====================
    
    def create_backup(self, task_id: int) -> str:
        """为训练任务创建备份
        
        Args:
            task_id: 任务ID
            
        Returns:
            备份路径
        """
        task_info = self.get_training_task_by_id(task_id)
        if not task_info:
            logger.error(f"训练任务不存在: {task_id}")
            return ""
        
        return training_backup_manager.create_task_backup(task_id, task_info)
    
    def restore_backup(self, task_id: int, backup_path: str) -> bool:
        """从备份恢复训练任务
        
        Args:
            task_id: 任务ID
            backup_path: 备份路径
            
        Returns:
            恢复是否成功
        """
        task_info = self.get_training_task_by_id(task_id)
        if not task_info:
            logger.error(f"训练任务不存在: {task_id}")
            return False
        
        return training_backup_manager.restore_task_backup(task_id, task_info, backup_path)
    
    # ==================== 统计功能 ====================
    
    def get_training_statistics(self, task_id: int) -> Dict[str, Any]:
        """获取训练任务的统计信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            统计信息字典
        """
        task_info = self.get_training_task_by_id(task_id)
        if not task_info:
            return {}
        
        dataset_info = self.get_dataset_info(task_id)
        
        return training_statistics.get_task_statistics(task_id, task_info, dataset_info)


# 全局训练管理器实例
training_manager = TrainingManager()
