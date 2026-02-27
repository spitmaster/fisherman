#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练结果保存器

负责保存训练结果、提取指标和管理模型版本。
"""

import logging
import shutil
from typing import Dict, Any, Optional
from pathlib import Path

from global_support.database import db_manager, ModelVersion
from ..dataset_path_manager import DatasetPathManager
from .log_manager import TrainingLogManager

logger = logging.getLogger(__name__)


class TrainingResultSaver:
    """训练结果保存器"""

    def __init__(self, log_manager: TrainingLogManager):
        """初始化结果保存器

        Args:
            log_manager: 日志管理器实例
        """
        self.log_manager = log_manager

    def extract_metrics(self, results: Any) -> Dict[str, float]:
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

    def get_best_model_path(self, dataset_name: str) -> Optional[Path]:
        """获取最佳模型路径（查找最新的训练结果）

        Args:
            dataset_name: 训练集名称

        Returns:
            最佳模型路径,不存在则返回None
        """
        weights_dir = DatasetPathManager.get_weights_path(dataset_name)

        # 查找所有训练目录，格式为 train_YYYYMMDD_HHMMSS
        train_dirs = sorted(
            [d for d in weights_dir.iterdir() if d.is_dir() and d.name.startswith("train_")],
            key=lambda x: x.stat().st_mtime,  # 按修改时间排序
            reverse=True
        )

        if not train_dirs:
            self.log_manager.emit_log(f"未找到训练目录: {weights_dir}")
            return None

        # 使用最新的训练目录
        latest_train_dir = train_dirs[0]
        best_model_path = latest_train_dir / "weights" / "best.pt"

        if not best_model_path.exists():
            self.log_manager.emit_log(f"最佳模型文件不存在: {best_model_path}")
            return None

        return best_model_path

    def sync_to_result_dir(self, dataset_name: str, model_path: Path) -> Path:
        """同步模型到结果管理目录

        Args:
            dataset_name: 训练集名称
            model_path: 模型文件路径

        Returns:
            结果目录路径
        """
        # 从模型路径中提取训练时间戳，生成唯一的模型名称
        # 模型路径格式: training_data/{dataset_name}/models/train_YYYYMMDD_HHMMSS/weights/best.pt
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"{dataset_name}_{timestamp}"
        result_dir = DatasetPathManager.create_model_result_dir(model_name)
        shutil.copy2(str(model_path), str(result_dir / "best.pt"))
        self.log_manager.emit_log(f"模型已同步到结果管理: {result_dir}")
        return result_dir

    def save_training_result_by_name(
        self,
        dataset_name: str,
        results: Any
    ) -> Dict[str, Any]:
        """根据训练集名称保存训练结果

        Args:
            dataset_name: 训练集名称（实际上是UUID，即TrainingTask的id）
            results: 训练结果对象

        Returns:
            结果信息字典
        """
        try:
            self.log_manager.emit_log(f"开始保存训练结果: {dataset_name}")

            # 获取最佳模型路径
            best_model_path = self.get_best_model_path(dataset_name)

            if not best_model_path:
                self.log_manager.emit_log(f"未找到最佳模型文件")
                return {"model_path": None, "metrics": {}}

            self.log_manager.emit_log(f"找到最佳模型: {best_model_path}")

            # 同步到训练结果管理目录
            result_dir = self.sync_to_result_dir(dataset_name, best_model_path)

            metrics = self.extract_metrics(results)

            # 注册到数据库的模型版本表
            # dataset_name 实际上是 TrainingTask 的 id (UUID)
            session = db_manager.get_session()
            try:
                # 查找对应的 TrainingTask
                from global_support.database import TrainingTask
                training_task = session.query(TrainingTask).filter_by(id=dataset_name).first()

                model_version = ModelVersion(
                    training_task_id=dataset_name if training_task else None,  # 关联到训练任务
                    model_path=str(best_model_path),
                    version="1.0",
                    is_default=False,
                    file_size=best_model_path.stat().st_size if best_model_path.exists() else 0
                )

                session.add(model_version)
                session.commit()

                self.log_manager.emit_log(f"模型已注册到数据库: {model_version.id}")

                return {
                    "model_path": str(best_model_path),
                    "model_result_path": str(result_dir / "best.pt"),
                    "model_name": f"{dataset_name}_model",
                    "metrics": metrics,
                    "model_version_id": model_version.id
                }

            except Exception as e:
                self.log_manager.emit_log(f"保存模型版本失败: {str(e)}")
                logger.error(f"保存模型版本失败: {str(e)}", exc_info=True)
                session.rollback()
                # 即使数据库保存失败,仍然返回基本信息
                return {
                    "model_path": str(best_model_path),
                    "model_result_path": str(result_dir / "best.pt"),
                    "model_name": f"{dataset_name}_model",
                    "metrics": metrics
                }
            finally:
                session.close()

        except Exception as e:
            self.log_manager.emit_log(f"保存训练结果失败: {str(e)}")
            logger.error(f"保存训练结果失败: {str(e)}", exc_info=True)
            return {"model_path": None, "metrics": {}}

    def save_training_result(
        self,
        task_id: int,
        results: Any,
        dataset_name: str
    ) -> Dict[str, Any]:
        """保存训练结果到数据库

        Args:
            task_id: 任务ID
            results: 训练结果对象
            dataset_name: 训练集名称

        Returns:
            结果信息字典
        """
        try:
            # 获取最佳模型路径
            best_model_path = self.get_best_model_path(dataset_name)

            if not best_model_path:
                return {"model_path": None, "metrics": {}}

            # 同步到训练结果管理目录
            result_dir = self.sync_to_result_dir(dataset_name, best_model_path)

            # 创建模型版本记录
            session = db_manager.get_session()
            try:
                model_version = ModelVersion(
                    training_task_id=task_id,
                    model_path=str(best_model_path),
                    version="1.0",
                    is_default=False,
                    file_size=best_model_path.stat().st_size if best_model_path.exists() else 0
                )

                session.add(model_version)
                session.commit()

                result_info = {
                    "model_path": str(best_model_path),
                    "model_result_path": str(result_dir / "best.pt"),
                    "model_version_id": model_version.id,
                    "metrics": metrics
                }

                self.log_manager.emit_log(f"训练结果保存成功: 模型版本 {model_version.id}")
                return result_info

            except Exception as e:
                self.log_manager.emit_log(f"保存模型版本失败: {str(e)}")
                logger.error(f"保存模型版本失败: {str(e)}", exc_info=True)
                session.rollback()
                return {"model_path": str(best_model_path), "metrics": self.extract_metrics(results)}

            finally:
                session.close()

        except Exception as e:
            self.log_manager.emit_log(f"保存训练结果失败: {str(e)}")
            logger.error(f"保存训练结果失败: {str(e)}", exc_info=True)
            return {"model_path": None, "metrics": {}}

    def save_training_result_direct(
        self,
        task_id: int,
        result: Dict[str, Any]
    ) -> bool:
        """直接保存训练结果

        Args:
            task_id: 任务ID
            result: 训练结果字典

        Returns:
            保存是否成功
        """
        session = db_manager.get_session()
        try:
            # 保存结果到数据库
            model_version = ModelVersion(
                task_id=task_id,
                model_path=result.get("model_path"),
                version="1.0",
                metrics=result.get("metrics", {})
            )

            session.add(model_version)
            session.commit()

            self.log_manager.emit_log(f"训练结果保存成功: 任务 {task_id}, 模型版本 {model_version.id}")
            return True

        except Exception as e:
            self.log_manager.emit_log(f"保存训练结果失败: {str(e)}")
            logger.error(f"保存训练结果失败: {str(e)}", exc_info=True)
            session.rollback()
            return False

        finally:
            session.close()
