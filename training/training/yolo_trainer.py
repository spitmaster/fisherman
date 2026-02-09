#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv8训练器

提供YOLOv8模型的训练功能封装。
"""

import os
import logging
from typing import Dict, Any, Optional

from ultralytics import YOLO

from ..core.base_manager import BaseManager

# 日志配置
logger = logging.getLogger(__name__)


class YOLOTrainer(BaseManager):
    """YOLOv8训练器"""
    
    def __init__(self):
        """初始化YOLOv8训练器"""
        super().__init__()
        
    def train(self, config: Dict[str, Any]) -> Dict[str, Any]:
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
                
        Returns:
            训练结果字典
        """
        try:
            # 加载YOLO模型
            model = YOLO("yolov8n.pt")  # 使用nano模型作为默认
            
            # 执行训练
            self.log_operation("info", "开始YOLOv8训练")
            results = model.train(**config)
            
            # 提取训练结果
            result_info = self._extract_training_results(results, config)
            
            self.log_operation("info", "YOLOv8训练完成")
            return {
                "success": True,
                "results": result_info
            }
            
        except Exception as e:
            error_msg = f"YOLOv8训练失败: {str(e)}"
            self.log_operation("error", error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
            
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
                "metrics": {}
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