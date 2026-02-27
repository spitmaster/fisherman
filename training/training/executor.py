#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练执行器

实现ITrainer接口,负责训练任务的执行和管理。
"""

import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ultralytics import YOLO
from global_support.database import db_manager, TrainingTask, TrainingLog

from ..core.interfaces import ITrainer
from ..core.base_manager import BaseManager
from ..dataset_path_manager import DatasetPathManager
from .log_manager import TrainingLogManager
from .config_builder import TrainingConfigBuilder
from .result_saver import TrainingResultSaver
from .training_callbacks import TrainingCallbacks

# 日志配置
logger = logging.getLogger(__name__)


class TrainingExecutor(ITrainer, BaseManager):
    """训练执行器"""

    @classmethod
    def set_log_callback(cls, callback):
        """设置日志回调函数

        Args:
            callback: 日志回调函数
        """
        TrainingLogManager.set_log_callback(callback)

    @classmethod
    def stop_training(cls):
        """停止训练"""
        TrainingCallbacks.stop_training()

    @classmethod
    def reset_stop_flag(cls):
        """重置停止标志"""
        TrainingCallbacks.reset_stop_flag()

    def __init__(self):
        """初始化训练执行器"""
        super().__init__()
        # 确保基础目录存在
        DatasetPathManager.ensure_directories()
        # 初始化子模块
        self.log_manager: Optional[TrainingLogManager] = None
        self.config_builder = TrainingConfigBuilder()
        self.result_saver: Optional[TrainingResultSaver] = None
        self.training_callbacks: Optional[TrainingCallbacks] = None

    def log_operation(self, operation: str, details: str = "", level: str = "INFO", exc_info: bool = False) -> None:
        """重写基类的log_operation,同时输出到logger和GUI回调

        Args:
            operation: 操作名称
            details: 操作详情
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
            exc_info: 是否包含异常堆栈信息
        """
        log_message = f"{operation}"
        if details:
            log_message += f": {details}"

        # 输出到logger
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(log_message, exc_info=exc_info)

        # 发送到GUI回调(去除level前缀)
        gui_message = log_message.replace(f"{level.lower()}:", "").strip()
        if self.log_manager:
            self.log_manager.emit_log(gui_message)

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

            # 使用路径管理器
            dataset_name = task.task_name
            dataset_path = DatasetPathManager.get_dataset_path(dataset_name)

            # 初始化日志管理器
            self.log_manager = TrainingLogManager(dataset_name)

            # 生成data.yaml配置文件
            data_yaml_path = self.config_builder.create_data_yaml(dataset_name)

            # 权重保存目录
            weights_dir = DatasetPathManager.get_weights_path(dataset_name)

            # 构建YOLO训练参数
            yolo_params = self.config_builder.build_yolo_params(
                data_yaml_path,
                weights_dir,
                {
                    "epochs": training_params.get("epochs", task.epochs or 100),
                    "batch_size": training_params.get("batch_size", task.batch_size or 16),
                    "image_size": training_params.get("image_size", 640)
                },
                verbose=False
            )

            # 使用YOLOv8进行训练
            self.log_operation("info", f"开始YOLOv8训练: {task.task_name}")

            try:
                # 初始化结果保存器和回调处理器
                self.result_saver = TrainingResultSaver(self.log_manager)

                # 加载YOLO模型
                model_type = training_params.get("model_type", "yolov8n.pt")
                model = YOLO(model_type)

                # 执行训练
                results = model.train(**yolo_params)

                # 保存训练结果
                result_info = self.result_saver.save_training_result(task_id, results, dataset_name)

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
        """根据训练集名称直接训练(不通过数据库)

        Args:
            dataset_name: 训练集名称
            training_params: 训练参数

        Returns:
            训练结果字典
        """
        # 初始化日志管理器
        self.log_manager = TrainingLogManager(dataset_name)

        self.log_operation("info", f"开始训练训练集: {dataset_name}")

        # 生成data.yaml配置文件
        data_yaml_path = self.config_builder.create_data_yaml(dataset_name)

        # 权重保存目录
        weights_dir = DatasetPathManager.get_weights_path(dataset_name)

        # 重定向stdout以捕获YOLO的verbose输出(在加载模型之前)
        original_stdout = sys.stdout

        def write_and_emit(text):
            original_stdout.write(text)
            # 发送到回调
            if text.strip():  # 只处理非空行
                clean_text = self.log_manager.remove_ansi_codes(text)
                if clean_text:  # 只处理清理后有内容的行
                    self.log_manager.emit_log(clean_text)

        class StdoutRedirect:
            def __init__(self, emitter):
                self.emitter = emitter
            def write(self, text):
                write_and_emit(text)
            def flush(self):
                pass

        sys.stdout = StdoutRedirect(write_and_emit)

        try:
            # 重置停止标志
            self.reset_stop_flag()

            # 初始化结果保存器和回调处理器
            self.result_saver = TrainingResultSaver(self.log_manager)
            self.training_callbacks = TrainingCallbacks(self.log_manager)

            # 构建YOLO训练参数
            yolo_params = self.config_builder.build_yolo_params(
                data_yaml_path,
                weights_dir,
                training_params,
                verbose=True
            )

            # 加载YOLO模型(现在可以捕获初始化输出)
            model_type = training_params.get("model_type", "yolov8n.pt")
            model = YOLO(model_type)

            # 添加自定义回调
            self.training_callbacks.register_to_model(model)

            # 执行训练
            results = model.train(**yolo_params)

            # 保存训练结果
            result_info = self.result_saver.save_training_result_by_name(dataset_name, results)

            self.log_operation("info", f"训练完成: {dataset_name}")

            # 写入训练完成信息到日志文件
            self.log_manager.write_completion_log(success=True)

            return {
                "success": True,
                "dataset_name": dataset_name,
                "result": result_info
            }

        except KeyboardInterrupt:
            # 训练被用户停止
            self.log_operation("info", "训练已被用户停止")
            # 写入停止信息到日志文件
            self.log_manager.write_completion_log(success=False, error_msg="用户手动停止")

            return {"success": False, "error": "训练已被用户停止"}

        except Exception as e:
            error_msg = f"训练失败: {str(e)}"
            self.log_operation("error", error_msg, exc_info=True)

            # 写入错误信息到日志文件
            self.log_manager.write_completion_log(success=False, error_msg=error_msg)

            return {"success": False, "error": error_msg}

        finally:
            # 恢复原始stdout
            sys.stdout = original_stdout

    def save_training_result(self, task_id: int, result: Dict[str, Any]) -> bool:
        """保存训练结果

        Args:
            task_id: 任务ID
            result: 训练结果字典

        Returns:
            保存是否成功
        """
        if not self.log_manager:
            self.log_manager = TrainingLogManager()
        self.result_saver = TrainingResultSaver(self.log_manager)

        return self.result_saver.save_training_result_direct(task_id, result)
