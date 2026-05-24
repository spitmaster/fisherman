#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练结果管理模块 - 模型管理

负责管理所有训练任务产出的.pt文件，包括模型导入、版本管理、默认模型设置等功能。

主要功能：
- 模型文件导入和管理
- 模型版本对比
- 默认模型设置
- 模型信息查询
"""

import os
import sys
import glob
import logging
import shutil
import hashlib
import platform
from datetime import datetime
import torch
from sqlalchemy import and_
from global_support.database import db_manager, ModelVersion, TrainingTask

# 日志配置
logger = logging.getLogger(__name__)

# 项目根目录:model_manager.py 位于 training_result/ 下,上一级即根
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 项目根的内置预训练权重命名约定:yolov8n.pt / yolov8s.pt / yolo11n.pt / ...
# 用 glob 扫,符合 Ultralytics 命名规则的都收
_BUILTIN_MODEL_GLOBS = ("yolov[0-9]*.pt", "yolo1[0-9]*.pt")

# 精选模型目录:开发者人工挑选并入库的"开箱即用"模型,随 git 仓库分发
# 用户在识别/位移 Tab 的模型下拉框里能直接选,不需要自己训练
_CURATED_MODELS_DIR = os.path.join(_PROJECT_ROOT, "good_models")


class ModelManager:
    """模型管理器"""

    def __init__(self):
        """初始化模型管理器"""
        # 模型存储目录
        self.models_dir = "models"
        os.makedirs(self.models_dir, exist_ok=True)

        # 加载已有的模型信息
        self.load_models()
        
    def load_models(self):
        """加载所有模型信息"""
        self.models = []

        # 从数据库加载模型版本信息
        session = db_manager.get_session()
        try:
            model_versions = session.query(ModelVersion).all()
            for version in model_versions:
                model_path = version.model_path
                if os.path.exists(model_path):
                    model_info = self._get_model_info(model_path)
                    if model_info:
                        # 添加数据库中的元数据
                        model_info["version"] = version.version
                        model_info["is_default"] = version.is_default
                        model_info["created_time"] = version.created_at
                        model_info["training_task_id"] = version.training_task_id

                        # 获取关联的训练任务信息
                        if version.training_task_id:
                            training_task = session.get(TrainingTask, version.training_task_id)
                            if training_task:
                                model_info["task_name"] = training_task.task_name
                                model_info["task_description"] = training_task.task_description
                                model_info["dataset_id"] = version.training_task_id  # 训练集ID (TrainingTask的ID)
                                model_info["dataset_name"] = training_task.task_name  # 训练集名称 (TrainingTask的task_name)
                            else:
                                model_info["task_name"] = "未知任务"
                                model_info["dataset_id"] = version.training_task_id  # 仍然保留ID
                                model_info["dataset_name"] = self._extract_dataset_name_from_path(model_path)
                        else:
                            model_info["task_name"] = "直接训练"
                            model_info["dataset_id"] = ""  # 没有关联任务,没有ID
                            # 从模型路径提取训练集名称
                            model_info["dataset_name"] = self._extract_dataset_name_from_path(model_path)

                        self.models.append(model_info)
                else:
                    logger.warning(f"模型文件不存在: {model_path}")

            logger.info(f"从数据库加载 {len(model_versions)} 个模型版本")
        except Exception as e:
            from sqlalchemy.exc import OperationalError
            # 如果表不存在，只是跳过加载，不记录为错误
            if isinstance(e, OperationalError) and "no such table" in str(e):
                logger.info("数据库表尚未创建，跳过模型加载")
            else:
                logger.error(f"从数据库加载模型失败: {str(e)}")
        finally:
            session.close()

        # 同时扫描模型目录以包含手动导入的模型（未在数据库中注册的）
        if os.path.exists(self.models_dir):
            for filename in os.listdir(self.models_dir):
                if filename.endswith(".pt"):
                    model_path = os.path.join(self.models_dir, filename)
                    # 检查是否已在模型中
                    already_loaded = any(m["path"] == model_path for m in self.models)
                    if not already_loaded:
                        model_info = self._get_model_info(model_path)
                        if model_info:
                            # 手动导入的模型标记为未关联任务
                            model_info["version"] = "manual"
                            model_info["is_default"] = False
                            model_info["created_time"] = datetime.fromtimestamp(os.path.getctime(model_path))
                            model_info["training_task_id"] = None
                            model_info["task_name"] = "手动导入"
                            model_info["task_description"] = "用户手动导入的模型"
                            model_info["dataset_name"] = "手动导入"
                            self.models.append(model_info)

        # 扫项目根的内置预训练权重(yolov8n.pt / yolo11n.pt 等),让用户在识别测试页直接选用
        builtin_paths = []
        for pattern in _BUILTIN_MODEL_GLOBS:
            builtin_paths.extend(glob.glob(os.path.join(_PROJECT_ROOT, pattern)))
        for model_path in builtin_paths:
            already_loaded = any(
                os.path.abspath(m["path"]) == os.path.abspath(model_path) for m in self.models
            )
            if already_loaded:
                continue
            model_info = self._get_model_info(model_path)
            if not model_info:
                continue
            model_info["version"] = "builtin"
            model_info["is_default"] = False
            model_info["created_time"] = datetime.fromtimestamp(os.path.getctime(model_path))
            model_info["training_task_id"] = None
            model_info["task_name"] = "内置预训练"
            model_info["task_description"] = "Ultralytics 官方 COCO 预训练权重(80 类)"
            model_info["dataset_name"] = "内置预训练 (COCO 80类)"
            self.models.append(model_info)

        # 扫 good_models/ 精选模型目录(随 git 仓库分发的开箱即用模型)
        if os.path.isdir(_CURATED_MODELS_DIR):
            for filename in sorted(os.listdir(_CURATED_MODELS_DIR)):
                if not filename.endswith((".pt", ".pth")):
                    continue
                model_path = os.path.join(_CURATED_MODELS_DIR, filename)
                already_loaded = any(
                    os.path.abspath(m["path"]) == os.path.abspath(model_path) for m in self.models
                )
                if already_loaded:
                    continue
                model_info = self._get_model_info(model_path)
                if not model_info:
                    continue
                model_info["version"] = "curated"
                model_info["is_default"] = False
                model_info["created_time"] = datetime.fromtimestamp(os.path.getctime(model_path))
                model_info["training_task_id"] = None
                model_info["task_name"] = "精选模型"
                model_info["task_description"] = "随仓库分发的精选模型(good_models/),开箱即用"
                model_info["dataset_name"] = "精选模型"
                self.models.append(model_info)

        logger.info(f"成功加载 {len(self.models)} 个模型文件")

    def _extract_dataset_name_from_path(self, path: str) -> str:
        """从路径中提取训练集名称"""
        try:
            # 路径格式: training_data/{dataset_name} 或类似
            if 'training_data' in path:
                parts = path.replace('\\', '/').split('/')
                if 'training_data' in parts:
                    idx = parts.index('training_data')
                    if idx + 1 < len(parts):
                        return parts[idx + 1]
            # 如果找不到,返回路径的最后部分
            return os.path.basename(path)
        except:
            return "未知"

    def _get_model_info(self, model_path):
        """获取模型文件信息
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            模型信息字典
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(model_path):
                logger.error(f"模型文件不存在: {model_path}")
                return None
                
            # 获取文件基本信息
            file_stat = os.stat(model_path)
            file_size = file_stat.st_size
            created_time = datetime.fromtimestamp(file_stat.st_ctime)
            modified_time = datetime.fromtimestamp(file_stat.st_mtime)
            
            # 计算文件MD5哈希值
            with open(model_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
                
            # 尝试加载模型以获取更多信息
            model_info = {
                "filename": os.path.basename(model_path),
                "path": model_path,
                "size": file_size,
                "created_time": created_time,
                "modified_time": modified_time,
                "hash": file_hash,
                "is_default": False
            }
            
            try:
                # 尝试加载YOLO模型以获取更多信息
                from ultralytics import YOLO
                model = YOLO(model_path)
                
                # 获取模型配置信息
                if hasattr(model, 'names'):
                    model_info["classes"] = list(model.names.values())
                else:
                    model_info["classes"] = []
                    
                if hasattr(model, 'model'):
                    # 获取模型参数数量
                    param_count = sum(p.numel() for p in model.model.parameters())
                    model_info["params"] = param_count
                    
                    # 获取模型输入大小
                    if hasattr(model.model, 'stride'):
                        stride = model.model.stride
                        model_info["stride"] = stride
                        
            except Exception as e:
                logger.warning(f"无法加载模型信息: {model_path} - {str(e)}")
                model_info["classes"] = []
                model_info["params"] = 0
                
            return model_info
            
        except Exception as e:
            logger.error(f"获取模型信息出错: {model_path} - {str(e)}")
            return None
            
    def import_model(self, model_path, model_name=None, training_task_id=None):
        """导入外部模型文件
        
        Args:
            model_path: 源模型文件路径
            model_name: 自定义模型名称（可选）
            training_task_id: 关联的训练任务ID（可选）
            
        Returns:
            导入后的模型信息或None
        """
        try:
            # 检查源文件是否存在
            if not os.path.exists(model_path):
                logger.error(f"源模型文件不存在: {model_path}")
                return None
                
            # 验证模型文件是否有效
            if not self._validate_model_file(model_path):
                logger.error(f"模型文件无效: {model_path}")
                return None
                
            # 确定目标文件名
            if model_name:
                if not model_name.endswith(".pt"):
                    model_name += ".pt"
                dest_filename = model_name
            else:
                dest_filename = os.path.basename(model_path)
                
            dest_path = os.path.join(self.models_dir, dest_filename)
            
            # 检查目标文件是否已存在
            if os.path.exists(dest_path):
                logger.warning(f"模型文件已存在: {dest_filename}")
                # 可以选择覆盖或重命名
                # 这里我们选择重命名
                base_name, ext = os.path.splitext(dest_filename)
                counter = 1
                while os.path.exists(os.path.join(self.models_dir, f"{base_name}_{counter}{ext}")):
                    counter += 1
                dest_filename = f"{base_name}_{counter}{ext}"
                dest_path = os.path.join(self.models_dir, dest_filename)
                
            # 复制模型文件
            shutil.copy2(model_path, dest_path)
            
            # 在数据库中创建模型版本记录
            session = db_manager.get_session()
            try:
                model_version = ModelVersion(
                    training_task_id=training_task_id,
                    model_path=dest_path,
                    version="manual",
                    is_default=False,
                    file_size=os.path.getsize(dest_path)
                )
                session.add(model_version)
                session.commit()
                logger.info(f"模型版本记录创建成功: {dest_filename}")
            except Exception as e:
                logger.error(f"创建模型版本记录失败: {str(e)}")
                session.rollback()
                # 继续执行，不中断
            finally:
                session.close()
            
            # 获取模型信息并添加到列表
            model_info = self._get_model_info(dest_path)
            if model_info:
                # 添加元数据
                model_info["version"] = "manual"
                model_info["is_default"] = False
                model_info["created_time"] = datetime.fromtimestamp(os.path.getctime(dest_path))
                model_info["training_task_id"] = training_task_id
                model_info["task_name"] = "手动导入"
                model_info["task_description"] = "用户手动导入的模型"
                self.models.append(model_info)
                logger.info(f"模型导入成功: {dest_filename}")
                return model_info
                
            return None
            
        except Exception as e:
            logger.error(f"导入模型文件出错: {str(e)}")
            return None
            
    def _validate_model_file(self, model_path):
        """验证模型文件的有效性
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            模型文件是否有效的布尔值
        """
        try:
            # 检查文件是否是.pt文件
            if not model_path.endswith(".pt"):
                return False
                
            # 尝试加载模型以验证
            from ultralytics import YOLO
            model = YOLO(model_path)
            
            # 简单验证模型是否可以正常加载
            return True
            
        except Exception as e:
            logger.error(f"模型文件验证失败: {model_path} - {str(e)}")
            return False
            
    def get_model_list(self):
        """获取所有模型列表
        
        Returns:
            模型信息列表
        """
        return self.models.copy()
        
    def get_model_by_name(self, filename):
        """根据文件名获取模型信息
        
        Args:
            filename: 模型文件名
            
        Returns:
            模型信息或None
        """
        for model_info in self.models:
            if model_info["filename"] == filename:
                return model_info
        return None
        
    def get_default_model(self):
        """获取默认模型信息
        
        Returns:
            默认模型信息或None
        """
        for model_info in self.models:
            if model_info.get("is_default", False):
                return model_info
                
        # 如果没有设置默认模型，返回第一个模型
        if self.models:
            return self.models[0]
            
        return None
        
    def set_default_model(self, filename):
        """设置默认模型
        
        Args:
            filename: 模型文件名
            
        Returns:
            是否成功设置
        """
        session = db_manager.get_session()
        try:
            # 查找模型信息
            target_model_info = None
            for model_info in self.models:
                if model_info["filename"] == filename:
                    target_model_info = model_info
                    break
            
            if not target_model_info:
                logger.error(f"模型文件不存在: {filename}")
                return False
            
            # 在数据库中清除所有默认模型标志
            session.query(ModelVersion).update({"is_default": False})
            
            # 设置指定模型为默认模型（通过模型路径匹配）
            model_version = session.query(ModelVersion).filter(
                ModelVersion.model_path == target_model_info["path"]
            ).first()
            
            if model_version:
                model_version.is_default = True
                session.commit()
                
                # 更新内存中的标志
                for model_info in self.models:
                    model_info["is_default"] = (model_info["filename"] == filename)
                
                logger.info(f"默认模型设置成功: {filename}")
                return True
            else:
                logger.error(f"在数据库中找不到模型版本记录: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"设置默认模型出错: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
            
    def delete_model(self, filename):
        """删除模型文件
        
        Args:
            filename: 模型文件名
            
        Returns:
            是否成功删除
        """
        session = db_manager.get_session()
        try:
            # 查找模型
            model_info = self.get_model_by_name(filename)
            if not model_info:
                logger.error(f"模型文件不存在: {filename}")
                return False
            
            # 检查模型是否是默认模型
            if model_info.get("is_default", False):
                logger.warning("正在删除默认模型，将重新设置其他模型为默认")
                # 如果是默认模型且还有其他模型，则设置第一个模型为默认
                other_models = [m for m in self.models if m["filename"] != filename]
                if other_models:
                    # 在数据库中设置新的默认模型
                    other_model_info = other_models[0]
                    other_model_version = session.query(ModelVersion).filter(
                        ModelVersion.model_path == other_model_info["path"]
                    ).first()
                    if other_model_version:
                        session.query(ModelVersion).update({"is_default": False})
                        other_model_version.is_default = True
                        session.commit()
                        # 更新内存中的标志
                        for m in self.models:
                            m["is_default"] = (m["filename"] == other_model_info["filename"])
            
            # 删除数据库中的模型版本记录
            model_version = session.query(ModelVersion).filter(
                ModelVersion.model_path == model_info["path"]
            ).first()
            if model_version:
                session.delete(model_version)
                session.commit()
                logger.info(f"模型版本记录删除成功: {filename}")
            
            # 删除模型文件
            if os.path.exists(model_info["path"]):
                os.remove(model_info["path"])
                logger.info(f"模型文件删除成功: {filename}")
                
            # 从内存中移除
            self.models.remove(model_info)
            return True
            
        except Exception as e:
            logger.error(f"删除模型文件出错: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
            
    def compare_models(self, model_names):
        """对比多个模型的信息
        
        Args:
            model_names: 模型文件名列表
            
        Returns:
            模型对比信息
        """
        if len(model_names) < 2:
            logger.warning("需要至少对比两个模型")
            return None
            
        comparison = {
            "models": [],
            "common_classes": [],
            "differences": {}
        }
        
        model_infos = []
        for name in model_names:
            model_info = self.get_model_by_name(name)
            if model_info:
                model_infos.append(model_info)
                
        if len(model_infos) < 2:
            logger.error("无法找到指定的模型文件")
            return None
            
        # 收集所有模型的信息
        all_classes = set()
        for model_info in model_infos:
            comparison["models"].append({
                "filename": model_info["filename"],
                "size": model_info["size"],
                "classes": len(model_info["classes"]),
                "params": model_info["params"],
                "created_time": model_info["created_time"],
                "is_default": model_info.get("is_default", False)
            })
            
            # 收集所有类别的交集
            for cls in model_info["classes"]:
                all_classes.add(cls)
                
        # 计算所有模型共有的类别
        common_classes = set(model_infos[0]["classes"])
        for model_info in model_infos[1:]:
            common_classes.intersection_update(model_info["classes"])
            
        comparison["common_classes"] = list(common_classes)
        
        # 计算类别的差异
        for i, model_info in enumerate(model_infos):
            unique_classes = set(model_info["classes"]) - common_classes
            if unique_classes:
                comparison["differences"][model_info["filename"]] = list(unique_classes)
                
        logger.info(f"模型对比完成: {len(model_names)}个模型")
        
        return comparison
        
    def get_model_statistics(self):
        """获取模型统计信息
        
        Returns:
            模型统计信息字典
        """
        if not self.models:
            return {
                "total": 0,
                "size": 0,
                "avg_size": 0,
                "avg_classes": 0,
                "avg_params": 0,
                "has_default": False
            }
            
        total_size = sum(model["size"] for model in self.models)
        total_classes = sum(len(model["classes"]) for model in self.models)
        total_params = sum(model["params"] for model in self.models)
        
        default_count = sum(1 for model in self.models if model.get("is_default", False))
        
        statistics = {
            "total": len(self.models),
            "size": total_size,
            "avg_size": total_size / len(self.models),
            "avg_classes": total_classes / len(self.models),
            "avg_params": total_params / len(self.models),
            "has_default": default_count > 0
        }
        
        return statistics
        
    def export_model_list(self, export_path):
        """导出模型列表到文件
        
        Args:
            export_path: 导出文件路径
            
        Returns:
            是否成功导出
        """
        try:
            import csv
            
            with open(export_path, "w", encoding="utf-8", newline="") as csvfile:
                fieldnames = [
                    "文件名", "路径", "大小", "创建时间", "修改时间", 
                    "类别数量", "参数数量", "默认模型", "哈希值"
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for model_info in self.models:
                    writer.writerow({
                        "文件名": model_info["filename"],
                        "路径": model_info["path"],
                        "大小": model_info["size"],
                        "创建时间": model_info["created_time"].strftime("%Y-%m-%d %H:%M:%S"),
                        "修改时间": model_info["modified_time"].strftime("%Y-%m-%d %H:%M:%S"),
                        "类别数量": len(model_info["classes"]),
                        "参数数量": model_info["params"],
                        "默认模型": "是" if model_info.get("is_default", False) else "否",
                        "哈希值": model_info["hash"]
                    })
                    
            logger.info(f"模型列表导出成功: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出模型列表出错: {str(e)}")
            return False
            
    def validate_model_directory(self):
        """验证模型目录的完整性
        
        Returns:
            验证结果
        """
        validation = {
            "valid": True,
            "total_files": 0,
            "invalid_files": [],
            "errors": []
        }
        
        if not os.path.exists(self.models_dir):
            logger.warning("模型目录不存在，将创建新目录")
            os.makedirs(self.models_dir, exist_ok=True)
            validation["valid"] = True
            return validation
            
        for filename in os.listdir(self.models_dir):
            if filename.endswith(".pt"):
                validation["total_files"] += 1
                model_path = os.path.join(self.models_dir, filename)
                
                if not self._validate_model_file(model_path):
                    validation["valid"] = False
                    validation["invalid_files"].append(filename)
                    
        return validation
        
# 全局模型管理器实例
model_manager = ModelManager()