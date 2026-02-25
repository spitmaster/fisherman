#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv8训练器

提供YOLOv8模型的训练功能封装，支持早停机制、学习率调度等高级功能。
"""

import os
import logging
import time
from typing import Dict, Any, Optional, List, Callable

from ultralytics import YOLO

from ..core.base_manager import BaseManager

# 日志配置
logger = logging.getLogger(__name__)


class YOLOTrainer(BaseManager):
    """YOLOv8训练器"""
    
    def __init__(self):
        """初始化YOLOv8训练器"""
        super().__init__()
        self.training_callbacks = {
            "on_epoch_start": [],
            "on_epoch_end": [],
            "on_training_start": [],
            "on_training_end": [],
            "on_validation_end": []
        }
        
    def register_training_callback(self, event_type: str, callback: Callable) -> bool:
        """注册训练回调函数
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            
        Returns:
            注册是否成功
        """
        if event_type not in self.training_callbacks:
            self.log_operation("error", f"未知的训练事件类型: {event_type}")
            return False
            
        self.training_callbacks[event_type].append(callback)
        return True
        
    def _trigger_callbacks(self, event_type: str, *args, **kwargs):
        """触发训练回调函数
        
        Args:
            event_type: 事件类型
            *args: 回调参数
            **kwargs: 回调关键字参数
        """
        if event_type not in self.training_callbacks:
            return
            
        for callback in self.training_callbacks[event_type]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.log_operation("error", f"训练回调执行失败: {str(e)}", exc_info=True)
        
    def train(self, config: Dict[str, Any], progress_callback: Callable = None) -> Dict[str, Any]:
        """执行YOLOv8训练
        
        Args:
            config: 训练配置字典，包含以下字段：
                - data: 数据配置文件路径
                - epochs: 训练轮数
                - batch: 批次大小
                - imgsz: 图片大小
                - project: 项目目录
                - name: 训练名称
                - exist_ok: 是否允许覆盖现有文件
                - verbose: 是否显示详细信息
                - patience: 早停耐心值（可选）
                - lr0: 初始学习率（可选）
                - lrf: 最终学习率因子（可选）
            progress_callback: 进度回调函数
                
        Returns:
            训练结果字典
        """
        try:
            # 加载YOLO模型
            model = YOLO("yolov8n.pt")  # 使用nano模型作为默认
            
            # 添加早停机制（如果配置了patience）
            patience = config.pop("patience", None)
            if patience is not None:
                config["patience"] = patience
                
            # 添加学习率调度
            lr0 = config.pop("lr0", None)
            lrf = config.pop("lrf", None)
            if lr0 is not None:
                config["lr0"] = lr0
            if lrf is not None:
                config["lrf"] = lrf
            
            # 触发训练开始回调
            self._trigger_callbacks("on_training_start", config)
            
            # 执行训练
            self.log_operation("info", "开始YOLOv8训练")
            
            # 如果配置了进度回调，添加进度监控
            if progress_callback:
                self._setup_progress_monitoring(progress_callback)
                
            results = model.train(**config)
            
            # 提取训练结果
            result_info = self._extract_training_results(results, config)
            
            # 触发训练结束回调
            self._trigger_callbacks("on_training_end", result_info)
            
            self.log_operation("info", "YOLOv8训练完成")
            return {
                "success": True,
                "results": result_info
            }
            
        except Exception as e:
            error_msg = f"YOLOv8训练失败: {str(e)}"
            self.log_operation("error", error_msg, exc_info=True)
            
            # 触发训练错误回调
            self._trigger_callbacks("on_training_error", error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
            
    def _setup_progress_monitoring(self, progress_callback: Callable):
        """设置进度监控
        
        Args:
            progress_callback: 进度回调函数
        """
        # 这里可以添加进度监控的逻辑
        # 由于YOLO训练进度监控比较复杂，暂时使用简单的轮次模拟
        pass
    
    def _validate_training_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """验证训练配置参数
        
        Args:
            config: 训练配置字典
            
        Returns:
            验证结果和错误信息
        """
        # 必需参数检查
        required_params = ["data", "epochs", "batch", "imgsz"]
        for param in required_params:
            if param not in config:
                return False, f"缺少必需参数: {param}"
        
        # 参数范围验证
        if config["epochs"] <= 0:
            return False, "epochs必须大于0"
        
        if config["batch"] <= 0:
            return False, "batch必须大于0"
        
        if config["imgsz"] <= 0:
            return False, "imgsz必须大于0"
        
        # 学习率验证
        if "lr0" in config and config["lr0"] <= 0:
            return False, "lr0必须大于0"
        
        if "lrf" in config and (config["lrf"] <= 0 or config["lrf"] > 1):
            return False, "lrf必须在(0,1]范围内"
        
        # 早停参数验证
        if "patience" in config and config["patience"] < 0:
            return False, "patience不能为负数"
        
        return True, "配置验证通过"
    
    def _create_advanced_training_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """创建高级训练配置
        
        Args:
            config: 基础训练配置
            
        Returns:
            增强的训练配置
        """
        advanced_config = config.copy()
        
        # 添加早停机制
        if "patience" not in advanced_config:
            advanced_config["patience"] = min(50, advanced_config["epochs"] // 3)  # 默认耐心值为总轮次的1/3，最大50
        
        # 学习率调度
        if "lr0" not in advanced_config:
            advanced_config["lr0"] = 0.01
        
        if "lrf" not in advanced_config:
            advanced_config["lrf"] = 0.01
        
        # 设备配置
        if "device" not in advanced_config:
            advanced_config["device"] = self._detect_available_device()
        
        # 优化器配置
        if "optimizer" not in advanced_config:
            advanced_config["optimizer"] = "auto"
        
        # 权重衰减
        if "weight_decay" not in advanced_config:
            advanced_config["weight_decay"] = 0.0005
        
        # 动量
        if "momentum" not in advanced_config:
            advanced_config["momentum"] = 0.937
        
        # 预热参数
        if "warmup_epochs" not in advanced_config:
            advanced_config["warmup_epochs"] = 3.0
        
        if "warmup_momentum" not in advanced_config:
            advanced_config["warmup_momentum"] = 0.8
        
        if "warmup_bias_lr" not in advanced_config:
            advanced_config["warmup_bias_lr"] = 0.1
        
        return advanced_config
    
    def _detect_available_device(self) -> str:
        """检测可用设备
        
        Returns:
            设备字符串（"cpu", "cuda:0", "mps"等）
        """
        try:
            import torch
            
            if torch.cuda.is_available():
                return "cuda:0"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
                
        except ImportError:
            return "cpu"
    
    def _monitor_training_progress(self, config: Dict[str, Any], progress_callback: Callable = None):
        """监控训练进度
        
        Args:
            config: 训练配置
            progress_callback: 进度回调函数
        """
        if not progress_callback:
            return
        
        try:
            # 模拟进度更新（实际实现需要更复杂的监控机制）
            project_dir = config.get("project", ".")
            train_name = config.get("name", "train")
            results_file = os.path.join(project_dir, train_name, "results.csv")
            
            # 定期检查训练进度文件
            last_check = time.time()
            check_interval = 5.0  # 每5秒检查一次
            
            while True:
                current_time = time.time()
                if current_time - last_check >= check_interval:
                    if os.path.exists(results_file):
                        # 读取并解析进度
                        progress = self._parse_training_progress(results_file, config["epochs"])
                        if progress:
                            progress_callback(progress)
                    
                    last_check = current_time
                    
                time.sleep(1.0)
                
        except Exception as e:
            self.log_operation("warning", f"进度监控异常: {str(e)}")
    
    def _parse_training_progress(self, results_file: str, total_epochs: int) -> Dict[str, Any]:
        """解析训练进度文件
        
        Args:
            results_file: 结果文件路径
            total_epochs: 总轮次
            
        Returns:
            进度信息字典
        """
        try:
            import pandas as pd
            
            if not os.path.exists(results_file):
                return None
                
            df = pd.read_csv(results_file)
            if len(df) == 0:
                return None
                
            # 获取最新一行数据
            latest_row = df.iloc[-1]
            
            progress = {
                "current_epoch": int(latest_row.get("epoch", 0)) if "epoch" in latest_row else 0,
                "total_epochs": total_epochs,
                "completion_percentage": 0,
                "training_loss": latest_row.get("train/loss", 0) if "train/loss" in latest_row else 0,
                "validation_loss": latest_row.get("val/loss", 0) if "val/loss" in latest_row else 0,
                "precision": latest_row.get("metrics/precision(B)", 0) if "metrics/precision(B)" in latest_row else 0,
                "recall": latest_row.get("metrics/recall(B)", 0) if "metrics/recall(B)" in latest_row else 0,
                "mAP50": latest_row.get("metrics/mAP50(B)", 0) if "metrics/mAP50(B)" in latest_row else 0,
                "mAP50_95": latest_row.get("metrics/mAP50-95(B)", 0) if "metrics/mAP50-95(B)" in latest_row else 0
            }
            
            if total_epochs > 0:
                progress["completion_percentage"] = min(100, (progress["current_epoch"] / total_epochs) * 100)
            
            return progress
            
        except Exception as e:
            self.log_operation("warning", f"解析训练进度失败: {str(e)}")
            return None
            
    def _extract_training_results(self, results: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """从训练结果中提取关键信息
        
        Args:
            results: YOLO训练结果对象
            config: 训练配置
            
        Returns:
            结果信息字典
        """
        try:
            # 获取最佳模型路径
            project_dir = config.get("project", ".")
            train_name = config.get("name", "train")
            best_model_path = os.path.join(project_dir, train_name, "weights", "best.pt")
            
            result_info = {
                "best_model_path": best_model_path,
                "config": config,
                "metrics": {},
                "training_time": None,
                "epochs_completed": 0
            }
            
            # 尝试提取指标
            try:
                if hasattr(results, "metrics"):
                    metrics = results.metrics
                    result_info["metrics"] = {
                        "precision": metrics.get("precision", 0),
                        "recall": metrics.get("recall", 0),
                        "mAP50": metrics.get("mAP50", 0),
                        "mAP50-95": metrics.get("mAP50-95", 0)
                    }
                    
                # 提取训练时间
                if hasattr(results, "train_time"):
                    result_info["training_time"] = results.train_time
                    
                # 提取完成的轮次
                if hasattr(results, "epoch"):
                    result_info["epochs_completed"] = results.epoch
                    
            except Exception as e:
                self.log_operation("warning", f"提取训练指标失败: {str(e)}")
                
            return result_info
            
        except Exception as e:
            self.log_operation("error", f"提取训练结果失败: {str(e)}", exc_info=True)
            return {"best_model_path": None, "config": config, "metrics": {}}
            
    def validate_model(self, model_path: str, data_config: Dict[str, Any]) -> Dict[str, Any]:
        """验证模型性能
        
        Args:
            model_path: 模型文件路径
            data_config: 数据配置
            
        Returns:
            验证结果字典
        """
        try:
            if not os.path.exists(model_path):
                return {"success": False, "error": f"模型文件不存在: {model_path}"}
                
            # 加载模型
            model = YOLO(model_path)
            
            # 执行验证
            self.log_operation("info", f"开始模型验证: {model_path}")
            results = model.val(data=data_config.get("data"), batch=data_config.get("batch", 16))
            
            # 提取验证结果
            validation_results = {
                "precision": results.results_dict.get("metrics/precision(B)", 0),
                "recall": results.results_dict.get("metrics/recall(B)", 0),
                "mAP50": results.results_dict.get("metrics/mAP50(B)", 0),
                "mAP50-95": results.results_dict.get("metrics/mAP50-95(B)", 0),
                "fitness": results.fitness
            }
            
            self.log_operation("info", "模型验证完成")
            return {
                "success": True,
                "validation_results": validation_results
            }
            
        except Exception as e:
            error_msg = f"模型验证失败: {str(e)}"
            self.log_operation("error", error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
            
    def predict(self, model_path: str, image_path: str, conf_threshold: float = 0.25) -> Dict[str, Any]:
        """使用模型进行预测
        
        Args:
            model_path: 模型文件路径
            image_path: 图片路径
            conf_threshold: 置信度阈值
            
        Returns:
            预测结果字典
        """
        try:
            if not os.path.exists(model_path):
                return {"success": False, "error": f"模型文件不存在: {model_path}"}
                
            if not os.path.exists(image_path):
                return {"success": False, "error": f"图片文件不存在: {image_path}"}
                
            # 加载模型
            model = YOLO(model_path)
            
            # 执行预测
            self.log_operation("info", f"开始模型预测: {image_path}")
            results = model.predict(source=image_path, conf=conf_threshold, save=False)
            
            # 提取预测结果
            predictions = []
            if results and len(results) > 0:
                result = results[0]
                if hasattr(result, "boxes"):
                    boxes = result.boxes
                    if boxes is not None:
                        for i in range(len(boxes)):
                            box = boxes[i]
                            prediction = {
                                "bbox": box.xyxy[0].tolist() if hasattr(box.xyxy, '__len__') and len(box.xyxy) > 0 else [],
                                "confidence": float(box.conf[0]) if hasattr(box.conf, '__len__') and len(box.conf) > 0 else 0,
                                "class_id": int(box.cls[0]) if hasattr(box.cls, '__len__') and len(box.cls) > 0 else 0,
                                "class_name": result.names[int(box.cls[0])] if hasattr(box.cls, '__len__') and len(box.cls) > 0 and int(box.cls[0]) in result.names else "unknown"
                            }
                            predictions.append(prediction)
            
            self.log_operation("info", f"模型预测完成，检测到 {len(predictions)} 个目标")
            return {
                "success": True,
                "predictions": predictions,
                "image_size": results[0].orig_shape if results and len(results) > 0 else None
            }
            
        except Exception as e:
            error_msg = f"模型预测失败: {str(e)}"
            self.log_operation("error", error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
            
    def get_training_config_template(self) -> Dict[str, Any]:
        """获取训练配置模板
        
        Returns:
            训练配置模板字典
        """
        return {
            "data": "data.yaml",  # 数据配置文件路径
            "epochs": 50,         # 训练轮数
            "batch": 8,           # 批次大小
            "imgsz": 640,         # 图片大小
            "project": ".",       # 项目目录
            "name": "train",      # 训练名称
            "exist_ok": True,     # 是否允许覆盖现有文件
            "verbose": True,      # 是否显示详细信息
            "patience": 50,       # 早停耐心值
            "lr0": 0.01,          # 初始学习率
            "lrf": 0.01,          # 最终学习率因子
            "device": "cpu",      # 训练设备
            "workers": 1,         # 工作线程数
            "optimizer": "auto",  # 优化器
            "weight_decay": 0.0005, # 权重衰减
            "momentum": 0.937,    # 动量
            "warmup_epochs": 3.0, # 预热轮次
            "warmup_momentum": 0.8, # 预热动量
            "warmup_bias_lr": 0.1, # 预热偏置学习率
        }