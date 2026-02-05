#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练结果保存器

负责训练结果的保存和管理。
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fisherman.global_support.database import db_manager, ModelVersion, TrainingLog

from ..core.base_manager import BaseManager

# 日志配置
logger = logging.getLogger(__name__)


class TrainingResultSaver(BaseManager):
    """训练结果保存器"""
    
    def __init__(self):
        """初始化结果保存器"""
        super().__init__()
        
    def save_training_result(self, task_id: int, result: Dict[str, Any]) -> bool:
        """保存训练结果到数据库
        
        Args:
            task_id: 任务ID
            result: 训练结果字典
            
        Returns:
            保存是否成功
        """
        session = db_manager.get_session()
        try:
            # 创建模型版本记录
            model_version = ModelVersion(
                task_id=task_id,
                model_path=result.get("model_path"),
                version=result.get("version", "1.0"),
                metrics=result.get("metrics", {}),
                created_at=datetime.now()
            )
            
            session.add(model_version)
            session.commit()
            
            # 记录训练完成日志
            training_log = TrainingLog(
                task_id=task_id,
                log_type="training_result_saved",
                message=f"训练结果保存成功，模型版本: {model_version.id}",
                created_at=datetime.now()
            )
            
            session.add(training_log)
            session.commit()
            
            self.log_operation("info", f"训练结果保存成功: 任务 {task_id}, 模型版本 {model_version.id}")
            return True
            
        except Exception as e:
            self.log_operation("error", f"保存训练结果失败: {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()
            
    def save_result_to_file(self, task_id: int, result: Dict[str, Any], output_dir: str) -> str:
        """保存训练结果到文件
        
        Args:
            task_id: 任务ID
            result: 训练结果字典
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"training_result_{task_id}_{timestamp}.json"
            file_path = os.path.join(output_dir, filename)
            
            # 准备保存的数据
            result_data = {
                "task_id": task_id,
                "timestamp": timestamp,
                "created_at": datetime.now().isoformat(),
                "result": result
            }
            
            # 保存到JSON文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            self.log_operation("info", f"训练结果保存到文件: {file_path}")
            return file_path
            
        except Exception as e:
            self.log_operation("error", f"保存训练结果到文件失败: {str(e)}", exc_info=True)
            return None
            
    def get_training_results(self, task_id: int) -> list:
        """获取任务的所有训练结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            训练结果列表
        """
        session = db_manager.get_session()
        try:
            results = session.query(ModelVersion).filter_by(task_id=task_id).all()
            
            result_list = []
            for result in results:
                result_list.append({
                    "id": result.id,
                    "task_id": result.task_id,
                    "model_path": result.model_path,
                    "version": result.version,
                    "metrics": result.metrics,
                    "created_at": result.created_at
                })
            
            return result_list
            
        except Exception as e:
            self.log_operation("error", f"获取训练结果失败: {str(e)}", exc_info=True)
            return []
            
        finally:
            session.close()
            
    def get_latest_training_result(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务的最新训练结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            最新的训练结果字典
        """
        session = db_manager.get_session()
        try:
            result = session.query(ModelVersion).filter_by(task_id=task_id).order_by(ModelVersion.created_at.desc()).first()
            
            if result:
                return {
                    "id": result.id,
                    "task_id": result.task_id,
                    "model_path": result.model_path,
                    "version": result.version,
                    "metrics": result.metrics,
                    "created_at": result.created_at
                }
            else:
                return None
                
        except Exception as e:
            self.log_operation("error", f"获取最新训练结果失败: {str(e)}", exc_info=True)
            return None
            
        finally:
            session.close()
            
    def delete_training_result(self, result_id: int) -> bool:
        """删除训练结果
        
        Args:
            result_id: 结果ID
            
        Returns:
            删除是否成功
        """
        session = db_manager.get_session()
        try:
            result = session.query(ModelVersion).filter_by(id=result_id).first()
            if not result:
                self.log_operation("error", f"训练结果不存在: {result_id}")
                return False
                
            # 如果模型文件存在，尝试删除
            if result.model_path and os.path.exists(result.model_path):
                try:
                    os.remove(result.model_path)
                    self.log_operation("info", f"删除模型文件: {result.model_path}")
                except Exception as e:
                    self.log_operation("warning", f"删除模型文件失败: {result.model_path} - {str(e)}")
            
            # 从数据库中删除记录
            session.delete(result)
            session.commit()
            
            self.log_operation("info", f"训练结果删除成功: {result_id}")
            return True
            
        except Exception as e:
            self.log_operation("error", f"删除训练结果失败: {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()
            
    def export_results(self, task_id: int, export_format: str = "json") -> Optional[str]:
        """导出训练结果
        
        Args:
            task_id: 任务ID
            export_format: 导出格式，支持 "json" 或 "csv"
            
        Returns:
            导出的文件路径
        """
        try:
            # 获取所有训练结果
            results = self.get_training_results(task_id)
            if not results:
                self.log_operation("warning", f"没有找到训练结果: 任务 {task_id}")
                return None
                
            # 创建导出目录
            export_dir = os.path.join("training_data", f"task_{task_id}", "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if export_format.lower() == "json":
                filename = f"training_results_{task_id}_{timestamp}.json"
                file_path = os.path.join(export_dir, filename)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "task_id": task_id,
                        "export_time": timestamp,
                        "results": results
                    }, f, ensure_ascii=False, indent=2)
                    
                self.log_operation("info", f"训练结果导出为JSON: {file_path}")
                return file_path
                
            elif export_format.lower() == "csv":
                filename = f"training_results_{task_id}_{timestamp}.csv"
                file_path = os.path.join(export_dir, filename)
                
                # 简单CSV导出
                import csv
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    # 写入标题行
                    writer.writerow(["ID", "Task ID", "Model Path", "Version", "Created At"])
                    # 写入数据行
                    for result in results:
                        writer.writerow([
                            result["id"],
                            result["task_id"],
                            result["model_path"],
                            result["version"],
                            result["created_at"]
                        ])
                
                self.log_operation("info", f"训练结果导出为CSV: {file_path}")
                return file_path
                
            else:
                self.log_operation("error", f"不支持的导出格式: {export_format}")
                return None
                
        except Exception as e:
            self.log_operation("error", f"导出训练结果失败: {str(e)}", exc_info=True)
            return None