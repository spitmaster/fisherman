#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练任务管理器

实现ITrainingManager接口，提供训练任务的统一管理。
支持并发控制和增强的任务状态管理。
"""

import os
import logging
import threading
import time
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, Future

from global_support.database import db_manager, TrainingTask

from ..core.interfaces import ITrainingManager, ICallbackManager, IEventManager
from ..core.base_manager import BaseManager
from .creator import TaskCreator
from .status_tracker import TaskStatusTracker
from .dataset_manager import DatasetManager
from ..training.executor import TrainingExecutor

# 日志配置
logger = logging.getLogger(__name__)


class TrainingTaskManager(ITrainingManager, ICallbackManager, IEventManager, BaseManager):
    """训练任务管理器
    
    支持并发控制、任务锁机制和增强的状态管理。
    """
    
    def __init__(self, max_concurrent_tasks: int = 3):
        """初始化训练任务管理器
        
        Args:
            max_concurrent_tasks: 最大并发任务数
        """
        super().__init__("task_manager")
        self.task_creator = TaskCreator()
        self.status_tracker = TaskStatusTracker()
        self.dataset_manager = DatasetManager()
        self.training_executor = TrainingExecutor()
        self.training_tasks = {}
        
        # 并发控制
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)
        self.active_tasks: Dict[int, Future] = {}
        
        # 任务锁机制
        self.task_locks: Dict[int, threading.Lock] = {}
        self.global_lock = threading.RLock()
        
        # 任务状态缓存
        self.task_status_cache: Dict[int, Dict[str, Any]] = {}
        self.cache_expiry_time = 5  # 缓存过期时间（秒）
        
        # 加载所有训练任务
        self._load_all_training_tasks()
        
    def _load_all_training_tasks(self):
        """加载所有训练任务"""
        with self.global_lock:
            session = db_manager.get_session()
            try:
                tasks = session.query(TrainingTask).all()
                for task in tasks:
                    task_info = {
                        "task_dir": f"training_data/{task.id}",
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

                    # 为每个任务创建锁
                    if task.id not in self.task_locks:
                        self.task_locks[task.id] = threading.Lock()

                self.log_operation("info", f"加载训练任务成功: 共 {len(tasks)} 个任务")

            except Exception as e:
                from sqlalchemy.exc import OperationalError
                # 如果表不存在，只是跳过加载，不记录为错误
                if isinstance(e, OperationalError) and "no such table" in str(e):
                    self.log_operation("info", "数据库表尚未创建，跳过训练任务加载")
                else:
                    self.log_operation("error", f"加载训练任务出错: {str(e)}", exc_info=True)

            finally:
                session.close()
            
    # ITrainingManager接口实现
    
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
        return self.task_creator.create_training_task(
            task_name, task_description, dataset_path, epochs, batch_size
        )
    
    def get_all_training_tasks(self) -> List[Dict[str, Any]]:
        """获取所有训练任务
        
        Returns:
            训练任务列表
        """
        with self.global_lock:
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
                    
                    # 检查任务是否正在执行
                    is_running = task.id in self.active_tasks
                    
                    task_list.append({
                        "id": task.id,
                        "task_name": task.task_name,
                        "task_description": task.task_description,
                        "status": task.status,
                        "is_running": is_running,
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
                self.log_operation("error", f"获取训练任务列表出错: {str(e)}", exc_info=True)
                return []
                
            finally:
                session.close()
    
    def get_training_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            训练任务信息字典
        """
        # 检查缓存
        if self._is_cache_valid(task_id):
            return self.task_status_cache[task_id]["data"]
        
        with self._get_task_lock(task_id):
            session = db_manager.get_session()
            try:
                task = session.query(TrainingTask).filter_by(id=task_id).first()
                if not task:
                    return None
                    
                task_info = self.training_tasks.get(task.id)
                if not task_info:
                    task_info = {
                        "task_dir": os.path.join("training_data", task.task_name),
                        "status": task.status,
                        "annotated_images": 0,
                        "total_images": 0
                    }
                
                # 检查任务是否正在执行
                is_running = task_id in self.active_tasks
                
                result = {
                    "id": task.id,
                    "task_name": task.task_name,
                    "task_description": task.task_description,
                    "status": task.status,
                    "is_running": is_running,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at,
                    "dataset_path": task.dataset_path,
                    "model_path": task.model_path,
                    "epochs": task.epochs,
                    "batch_size": task.batch_size,
                    "annotated_images": task_info["annotated_images"],
                    "total_images": task_info["total_images"],
                    "task_dir": task_info["task_dir"]
                }
                
                # 更新缓存
                self._update_cache(task_id, result)
                
                return result
                
            except Exception as e:
                self.log_operation("error", f"获取训练任务出错: {task_id} - {str(e)}", exc_info=True)
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
                self.log_operation("error", f"任务不存在: {task_id}")
                return False
                
            # 更新允许的字段
            allowed_fields = ["task_name", "task_description", "epochs", "batch_size", "status"]
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(task, field):
                    setattr(task, field, value)
                    
            session.commit()
            self.log_operation("info", f"训练任务更新成功: {task_id}")
            return True
            
        except Exception as e:
            self.log_operation("error", f"更新训练任务失败: {task_id} - {str(e)}", exc_info=True)
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
                self.log_operation("error", f"任务不存在: {task_id}")
                return False
                
            # 删除任务目录
            task_dir = os.path.join("training_data", task.task_name)
            if os.path.exists(task_dir):
                import shutil
                try:
                    shutil.rmtree(task_dir)
                    self.log_operation("info", f"删除任务目录: {task_dir}")
                except Exception as e:
                    self.log_operation("error", f"删除任务目录失败: {task_dir} - {str(e)}")
            
            # 从数据库中删除任务
            session.delete(task)
            session.commit()
            
            # 从内存中移除任务信息
            if task_id in self.training_tasks:
                del self.training_tasks[task_id]
                
            self.log_operation("info", f"训练任务删除成功: {task_id}")
            return True
            
        except Exception as e:
            self.log_operation("error", f"删除训练任务失败: {task_id} - {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()
    
    def start_training(self, task_id: int) -> bool:
        """开始训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            启动是否成功
        """
        # 检查任务是否正在运行
        if self._is_task_running(task_id):
            self.log_operation("warning", f"任务正在运行中，无法重复启动: {task_id}")
            return False
            
        # 检查并发限制
        if len(self.active_tasks) >= self.max_concurrent_tasks:
            self.log_operation("warning", f"已达到最大并发任务数限制: {self.max_concurrent_tasks}")
            return False
            
        # 获取任务信息
        task_info = self.get_training_task_by_id(task_id)
        if not task_info:
            self.log_operation("error", f"任务不存在: {task_id}")
            return False
            
        # 检查标注数据是否足够
        if task_info["annotated_images"] == 0:
            self.log_operation("error", f"标注数据不足，无法开始训练: {task_id}")
            return False
            
        # 更新任务状态为训练中
        if not self.status_tracker.update_task_status(task_id, "training"):
            self.log_operation("error", f"更新任务状态失败: {task_id}")
            return False
            
        # 准备训练参数
        dataset_config = {
            "data": os.path.join(task_info["task_dir"], "dataset", "data.yaml")
        }
        
        training_params = {
            "epochs": task_info["epochs"],
            "batch_size": task_info["batch_size"]
        }
        
        # 异步执行训练
        try:
            future = self.task_executor.submit(
                self._execute_training_async, 
                task_id, dataset_config, training_params
            )
            self.active_tasks[task_id] = future
            
            # 注册完成回调
            future.add_done_callback(lambda f: self._on_training_completed(task_id, f))
            
            self.log_operation("info", f"训练任务已启动: {task_id}")
            self._notify_event("training_started", {"task_id": task_id})
            
            return True
            
        except Exception as e:
            self.log_operation("error", f"启动训练任务失败: {task_id} - {str(e)}", exc_info=True)
            self._handle_training_error(task_id, e)
            return False
    
    # 委托方法到各个组件
    
    def import_images(self, task_id: int, image_paths: List[str]) -> int:
        """导入图片到训练任务
        
        Args:
            task_id: 任务ID
            image_paths: 图片路径列表
            
        Returns:
            成功导入的图片数量
        """
        return self.dataset_manager.import_images(task_id, image_paths)
    
    def get_dataset_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取数据集信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            数据集信息字典
        """
        return self.dataset_manager.get_dataset_info(task_id)
    
    def get_image_list(self, task_id: int) -> List[str]:
        """获取任务的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            图片文件名列表
        """
        return self.dataset_manager.get_image_list(task_id)
    
    def get_unannotated_images(self, task_id: int) -> List[str]:
        """获取未标注的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            未标注图片文件名列表
        """
        return self.dataset_manager.get_unannotated_images(task_id)
    
    def update_task_status(self, task_id: int, status: str) -> bool:
        """更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            
        Returns:
            更新是否成功
        """
        return self.status_tracker.update_task_status(task_id, status)
    
    def get_task_status(self, task_id: int) -> Optional[str]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字符串
        """
        return self.status_tracker.get_task_status(task_id)
    
    def get_task_progress(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务进度信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            进度信息字典
        """
        return self.status_tracker.get_task_progress(task_id)
    
    def get_training_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取训练任务状态（向后兼容方法）
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息字典
        """
        # 这个方法是为了向后兼容，返回包含状态和进度的字典
        status = self.get_task_status(task_id)
        progress = self.get_task_progress(task_id)
        
        if status is None:
            return None
            
        result = {
            "status": status,
            "progress": progress or {}
        }
        
        return result
    
    # 并发控制方法
    
    def _get_task_lock(self, task_id: int) -> threading.Lock:
        """获取任务锁
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务锁对象
        """
        if task_id not in self.task_locks:
            with self.global_lock:
                if task_id not in self.task_locks:
                    self.task_locks[task_id] = threading.Lock()
        return self.task_locks[task_id]
    
    def _is_task_running(self, task_id: int) -> bool:
        """检查任务是否正在运行
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务是否正在运行
        """
        return task_id in self.active_tasks and not self.active_tasks[task_id].done()
    
    def _is_cache_valid(self, task_id: int) -> bool:
        """检查缓存是否有效
        
        Args:
            task_id: 任务ID
            
        Returns:
            缓存是否有效
        """
        if task_id not in self.task_status_cache:
            return False
        
        cache_data = self.task_status_cache[task_id]
        current_time = time.time()
        return current_time - cache_data["timestamp"] < self.cache_expiry_time
    
    def _update_cache(self, task_id: int, data: Dict[str, Any]) -> None:
        """更新缓存
        
        Args:
            task_id: 任务ID
            data: 缓存数据
        """
        self.task_status_cache[task_id] = {
            "data": data,
            "timestamp": time.time()
        }
    
    def _execute_training_async(self, task_id: int, dataset_config: Dict[str, Any], 
                              training_params: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行训练任务
        
        Args:
            task_id: 任务ID
            dataset_config: 数据集配置
            training_params: 训练参数
            
        Returns:
            训练结果
        """
        try:
            # 执行训练
            result = self.training_executor.train(task_id, dataset_config, training_params)
            
            # 通知训练进度
            self._notify_event("training_progress", {
                "task_id": task_id,
                "progress": 100,
                "message": "训练完成"
            })
            
            return result
            
        except Exception as e:
            self.log_operation("error", f"异步训练执行失败: {task_id} - {str(e)}", exc_info=True)
            raise
    
    def _on_training_completed(self, task_id: int, future: Future) -> None:
        """训练完成回调
        
        Args:
            task_id: 任务ID
            future: 异步任务Future对象
        """
        try:
            # 获取训练结果
            result = future.result()
            
            # 更新任务状态
            if result.get("success", False):
                self.status_tracker.update_task_status(task_id, "completed")
                self.log_operation("info", f"训练任务完成: {task_id}")
                self._notify_event("training_completed", {
                    "task_id": task_id,
                    "result": result
                })
            else:
                self.status_tracker.update_task_status(task_id, "failed")
                self.log_operation("error", f"训练任务失败: {task_id}")
                self._notify_event("training_failed", {
                    "task_id": task_id,
                    "error": result.get("error", "未知错误")
                })
            
        except Exception as e:
            self.log_operation("error", f"训练完成回调处理失败: {task_id} - {str(e)}", exc_info=True)
            self.status_tracker.update_task_status(task_id, "failed")
            
        finally:
            # 清理活动任务
            with self.global_lock:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
    
    def _handle_training_error(self, task_id: int, error: Exception) -> None:
        """处理训练错误
        
        Args:
            task_id: 任务ID
            error: 错误对象
        """
        self.status_tracker.update_task_status(task_id, "failed")
        
        # 清理活动任务
        with self.global_lock:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
        
        self._notify_event("training_error", {
            "task_id": task_id,
            "error": str(error)
        })
    
    def stop_training(self, task_id: int) -> bool:
        """停止训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            停止是否成功
        """
        if not self._is_task_running(task_id):
            self.log_operation("warning", f"任务未在运行中: {task_id}")
            return False
            
        try:
            # 取消任务
            future = self.active_tasks[task_id]
            if not future.done():
                future.cancel()
                
            # 更新任务状态
            self.status_tracker.update_task_status(task_id, "stopped")
            
            # 清理活动任务
            with self.global_lock:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
            
            self.log_operation("info", f"训练任务已停止: {task_id}")
            self._notify_event("training_stopped", {"task_id": task_id})
            
            return True
            
        except Exception as e:
            self.log_operation("error", f"停止训练任务失败: {task_id} - {str(e)}", exc_info=True)
            return False
    
    def get_active_tasks_count(self) -> int:
        """获取活动任务数量
        
        Returns:
            活动任务数量
        """
        return len(self.active_tasks)
    
    def get_concurrent_limit(self) -> int:
        """获取并发限制
        
        Returns:
            最大并发任务数
        """
        return self.max_concurrent_tasks
    
    # ICallbackManager接口实现
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """注册回调函数"""
        super().register_callback(event_type, callback)
    
    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """注销回调函数"""
        super().unregister_callback(event_type, callback)
    
    def _notify_callbacks(self, event_type: str, data: Any = None) -> None:
        """通知回调函数"""
        super()._notify_callbacks(event_type, data)
    
    # IEventManager接口实现
    
    def register_event_handler(self, event_name: str, handler: Callable) -> None:
        """注册事件处理器"""
        super().register_event_handler(event_name, handler)
    
    def _notify_event(self, event_name: str, event_data: Dict[str, Any] = None) -> None:
        """通知事件处理器"""
        super()._notify_event(event_name, event_data)
        
        # 同时通知回调函数
        self._notify_callbacks(event_name, event_data)
    
    def start_annotation(self, task_id: int) -> Dict[str, Any]:
        """开始标注任务（向后兼容方法）
        
        Args:
            task_id: 任务ID
            
        Returns:
            标注任务结果字典
        """
        try:
            # 获取任务信息
            task_info = self.get_training_task_by_id(task_id)
            if not task_info:
                return {"success": False, "error": f"任务不存在: {task_id}"}
            
            # 获取未标注的图片
            unannotated_images = self.get_unannotated_images(task_id)
            
            if not unannotated_images:
                return {"success": False, "error": "没有需要标注的图片"}
            
            # 更新任务状态为标注中
            if not self.update_task_status(task_id, "annotating"):
                return {"success": False, "error": "更新任务状态失败"}
            
            # 创建标注工具
            # 注意：这里需要从annotation_manager创建工具，但为了简化先返回成功
            # 在实际实现中，这里应该启动标注界面
            result = {
                "success": True,
                "task_id": task_id,
                "message": f"标注任务已准备，共有 {len(unannotated_images)} 张图片需要标注",
                "unannotated_images": unannotated_images,
                "task_info": task_info
            }
            
            return result
            
        except Exception as e:
            self.log_operation("error", f"开始标注任务失败: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}