#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 训练管理

负责管理训练任务的整个生命周期，包括任务创建、数据集管理、标注、训练执行等。

主要功能：
- 训练任务创建和管理
- 数据集导入和管理
- 标注功能
- 训练过程管理
- 训练结果处理
"""

import os
import sys
import logging
import shutil
import yaml
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO
# from ultralytics.utils.ops import non_max_suppression  # Not available in ultralytics 8.x
from ultralytics.engine.results import Results
from PIL import Image, ImageDraw, ImageFont

from fisherman.global_support.database import db_manager, TrainingTask, TrainingLog, ModelVersion
from fisherman.global_support.task_scheduler import task_scheduler, TrainingTask as SchedulerTrainingTask

# 日志配置
logger = logging.getLogger(__name__)

class TrainingManager:
    """训练管理器"""
    
    def __init__(self):
        """初始化训练管理器"""
        self.training_tasks = {}
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
                        image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
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
    
    def get_all_training_tasks(self):
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
    
    def get_training_task_by_id(self, task_id):
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
    
    def update_training_task(self, task_id, task_name=None, task_description=None, epochs=None, batch_size=None):
        """更新训练任务信息
        
        Args:
            task_id: 任务ID
            task_name: 新任务名称
            task_description: 新任务描述
            epochs: 新训练轮数
            batch_size: 新批次大小
            
        Returns:
            更新结果
        """
        session = db_manager.get_session()
        try:
            task = session.get(TrainingTask, task_id)
            
            if not task:
                logger.error(f"训练任务不存在: {task_id}")
                return False
                
            if task_name:
                # 重命名任务目录
                old_dir = os.path.join("training_data", task.task_name)
                new_dir = os.path.join("training_data", task_name)
                
                if os.path.exists(old_dir) and old_dir != new_dir:
                    os.rename(old_dir, new_dir)
                    
                task.task_name = task_name
                
            if task_description is not None:
                task.task_description = task_description
                
            if epochs is not None:
                task.epochs = epochs
                
            if batch_size is not None:
                task.batch_size = batch_size
                
            session.commit()
            
            # 更新训练任务字典
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
    
    def delete_training_task(self, task_id):
        """删除训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            删除结果
        """
        session = db_manager.get_session()
        try:
            task = session.get(TrainingTask, task_id)
            
            if not task:
                logger.error(f"训练任务不存在: {task_id}")
                return False
                
            # 删除任务目录
            task_dir = os.path.join("training_data", task.task_name)
            if os.path.exists(task_dir):
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
        
    def create_training_task(self, task_name, task_description, dataset_path=None, epochs=50, batch_size=8):
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
        # 创建任务文件夹结构
        task_dir = self._create_task_directory(task_name)
        
        # 创建数据集目录
        if dataset_path:
            # 如果提供了数据集路径，复制到任务目录
            self._copy_dataset(dataset_path, task_dir)
        else:
            # 否则创建空的数据集结构
            self._create_default_dataset_structure(task_dir)
        
        # 创建data.yaml配置文件
        self._create_data_yaml(task_dir, task_name)
        
        # 在数据库中创建任务记录
        session = db_manager.get_session()
        try:
            training_task = TrainingTask(
                task_name=task_name,
                task_description=task_description,
                dataset_path=os.path.join(task_dir, "dataset"),
                epochs=epochs,
                batch_size=batch_size
            )
            
            session.add(training_task)
            session.commit()
            
            logger.info(f"训练任务创建成功: {task_name} (ID: {training_task.id})")
            
            # 存储任务信息
            self.training_tasks[training_task.id] = {
                "task_dir": task_dir,
                "status": "pending",
                "annotated_images": 0,
                "total_images": 0
            }
            
            return training_task.id
            
        except Exception as e:
            logger.error(f"创建训练任务失败: {str(e)}", exc_info=True)
            session.rollback()
            return None
            
        finally:
            session.close()
            
    def _create_task_directory(self, task_name):
        """创建任务目录结构
        
        Args:
            task_name: 任务名称
            
        Returns:
            任务目录路径
        """
        task_dir = os.path.join("training_data", task_name)
        os.makedirs(task_dir, exist_ok=True)
        
        # 创建子目录
        subdirs = [
            "dataset/images/train",
            "dataset/images/val", 
            "dataset/images/test",
            "dataset/labels/train",
            "dataset/labels/val",
            "dataset/labels/test",
            "annotations",
            "models"
        ]
        
        for subdir in subdirs:
            os.makedirs(os.path.join(task_dir, subdir), exist_ok=True)
            
        return task_dir
        
    def _copy_dataset(self, source_path, target_dir):
        """复制数据集到任务目录
        
        Args:
            source_path: 源数据集路径
            target_dir: 目标目录
        """
        try:
            # 复制数据集到任务目录
            shutil.copytree(source_path, os.path.join(target_dir, "dataset"), dirs_exist_ok=True)
            logger.info(f"数据集复制成功: {source_path} → {target_dir}")
        except Exception as e:
            logger.error(f"数据集复制失败: {str(e)}")
            
    def _create_default_dataset_structure(self, task_dir):
        """创建默认的数据集结构
        
        Args:
            task_dir: 任务目录
        """
        default_structure = [
            "dataset/images/train",
            "dataset/images/val",
            "dataset/images/test",
            "dataset/labels/train",
            "dataset/labels/val",
            "dataset/labels/test"
        ]
        
        for directory in default_structure:
            os.makedirs(os.path.join(task_dir, directory), exist_ok=True)
            
    def _create_data_yaml(self, task_dir, task_name):
        """创建YOLO训练配置文件data.yaml
        
        Args:
            task_dir: 任务目录
            task_name: 任务名称
        """
        data_config = {
            "path": os.path.abspath(os.path.join(task_dir, "dataset")),
            "train": "images/train",
            "val": "images/val",
            "test": "images/test",
            "nc": 1,  # 默认单类检测
            "names": [task_name]
        }
        
        yaml_path = os.path.join(task_dir, "data.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data_config, f, default_flow_style=False, allow_unicode=True)
            
        logger.info(f"数据配置文件创建成功: {yaml_path}")
        
    def import_images(self, task_id, image_paths):
        """导入图片到训练任务
        
        Args:
            task_id: 任务ID
            image_paths: 图片路径列表
            
        Returns:
            导入的图片数量
        """
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task_id)
            
            if not training_task:
                logger.error(f"训练任务不存在: {task_id}")
                return 0
                
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
                
            # 确保数据集目录存在
            image_dir = os.path.join(task_info["task_dir"], "dataset/images/train")
            label_dir = os.path.join(task_info["task_dir"], "dataset/labels/train")
            os.makedirs(image_dir, exist_ok=True)
            os.makedirs(label_dir, exist_ok=True)
            
            imported_count = 0
            for image_path in image_paths:
                try:
                    # 检查文件是否为图片格式
                    if not image_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                        logger.warning(f"跳过非图片文件: {image_path}")
                        continue
                        
                    # 复制图片到任务目录
                    filename = os.path.basename(image_path)
                    dest_path = os.path.join(image_dir, filename)
                    
                    # 检查文件是否已存在
                    if os.path.exists(dest_path):
                        logger.warning(f"图片已存在，跳过: {filename}")
                        continue
                        
                    shutil.copy2(image_path, dest_path)
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"导入图片失败: {image_path} - {str(e)}")
                    
            # 更新任务信息
            task_info["total_images"] = len([f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))])
            task_info["annotated_images"] = len([f for f in os.listdir(label_dir) if f.lower().endswith('.txt')])
            
            logger.info(f"图片导入成功: 任务ID={task_id}, 导入数量={imported_count}")
            
            return imported_count
            
        except Exception as e:
            logger.error(f"导入图片出错: {str(e)}", exc_info=True)
            return 0
            
        finally:
            session.close()
    
    def get_dataset_info(self, task_id):
        """获取数据集信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            数据集信息，包括图片数量、标注数量等
        """
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task_id)
            
            if not training_task:
                logger.error(f"训练任务不存在: {task_id}")
                return None
                
            task_info = self.training_tasks.get(task_id)
            if not task_info:
                task_info = {
                    "task_dir": os.path.join("training_data", training_task.task_name),
                    "status": training_task.status,
                    "annotated_images": 0,
                    "total_images": 0
                }
                
            image_dir = os.path.join(task_info["task_dir"], "dataset/images/train")
            label_dir = os.path.join(task_info["task_dir"], "dataset/labels/train")
            
            if not os.path.exists(image_dir):
                return {
                    "total_images": 0,
                    "annotated_images": 0,
                    "unannotated_images": 0,
                    "image_files": []
                }
                
            image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            annotated_files = []
            
            if os.path.exists(label_dir):
                annotated_files = [os.path.splitext(f)[0] + ".txt" for f in os.listdir(label_dir) if f.lower().endswith('.txt')]
                
            annotated_count = 0
            unannotated_images = []
            
            for img_file in image_files:
                txt_file = os.path.splitext(img_file)[0] + ".txt"
                if txt_file in annotated_files:
                    annotated_count += 1
                else:
                    unannotated_images.append(img_file)
                    
            return {
                "total_images": len(image_files),
                "annotated_images": annotated_count,
                "unannotated_images": len(unannotated_images),
                "image_files": image_files,
                "unannotated_image_files": unannotated_images
            }
            
        except Exception as e:
            logger.error(f"获取数据集信息出错: {str(e)}", exc_info=True)
            return None
            
        finally:
            session.close()
    
    def get_image_list(self, task_id):
        """获取任务的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            图片文件列表
        """
        dataset_info = self.get_dataset_info(task_id)
        if dataset_info:
            return dataset_info["image_files"]
        return []
    
    def get_unannotated_images(self, task_id):
        """获取未标注的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            未标注的图片文件列表
        """
        dataset_info = self.get_dataset_info(task_id)
        if dataset_info:
            return dataset_info["unannotated_image_files"]
        return []
            
    def start_annotation(self, task_id):
        """开始标注任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            图片列表和标注状态
        """
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task_id)
            
            if not training_task:
                logger.error(f"训练任务不存在: {task_id}")
                return None
            
            # 更新任务状态为标注中（如果当前状态是pending）
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
                
            # 获取图片列表和标注状态
            image_dir = os.path.join(task_info["task_dir"], "dataset/images/train")
            label_dir = os.path.join(task_info["task_dir"], "dataset/labels/train")
            
            image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            annotated_files = [os.path.splitext(f)[0] + ".txt" for f in image_files]
            
            annotated_count = 0
            for txt_file in annotated_files:
                if os.path.exists(os.path.join(label_dir, txt_file)):
                    annotated_count += 1
                    
            task_info["annotated_images"] = annotated_count
            task_info["total_images"] = len(image_files)
            task_info["status"] = training_task.status
            
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
            
    def save_annotation(self, task_id, image_filename, annotations):
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
            
    def start_training(self, task_id):
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
                
            # 检查标注数据是否足够
            if task_info["annotated_images"] == 0:
                logger.error("标注数据不足，无法开始训练")
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
            
    def _run_training(self, scheduler_task, task_info):
        """运行训练任务
        
        Args:
            scheduler_task: 调度器任务对象
            task_info: 任务信息
        """
        try:
            # 加载YOLO模型
            model = YOLO("yolov8n.pt")
            
            # 训练模型
            data_config = os.path.join(task_info["task_dir"], "data.yaml")
            
            results = model.train(
                data=data_config,
                epochs=scheduler_task.epochs,
                batch=scheduler_task.batch_size,
                imgsz=640,
                device="cpu",  # 使用CPU训练，避免CUDA依赖
                workers=1,
                verbose=True
            )
            
            # 保存训练结果
            self._save_training_result(scheduler_task.task_id, results)
            
        except Exception as e:
            logger.error(f"训练任务执行错误: {str(e)}", exc_info=True)
            scheduler_task.fail(e)
            
    def _save_training_result(self, task_id, results):
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
                
            # 获取任务信息
            task_info = self.training_tasks.get(task_id)
            
            # 确定训练后的模型文件路径
            model_path = None
            if hasattr(results, 'weights') and results.weights:
                model_path = results.weights
            else:
                # 尝试从默认的YOLOv8训练输出目录查找
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
                    # 尝试获取mAP50
                    if hasattr(metrics, 'map50'):
                        mAP = float(metrics.map50)
                    elif isinstance(metrics, dict) and 'metrics/mAP50' in metrics:
                        mAP = float(metrics['metrics/mAP50'])
                    elif isinstance(metrics, dict) and 'map50' in metrics:
                        mAP = float(metrics['map50'])
                    
                    # 尝试获取box_loss
                    if hasattr(metrics, 'box_loss'):
                        loss = float(metrics.box_loss)
                    elif isinstance(metrics, dict) and 'metrics/box_loss' in metrics:
                        loss = float(metrics['metrics/box_loss'])
                    elif isinstance(metrics, dict) and 'box_loss' in metrics:
                        loss = float(metrics['box_loss'])
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
                version="v1.0",  # 简单的版本号
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
        """训练完成回调
        
        Args:
            task: 任务对象
            result: 训练结果
        """
        logger.info(f"训练任务完成: {task.task_name}")
        
    def _on_training_error(self, task, error):
        """训练错误回调
        
        Args:
            task: 任务对象
            error: 错误信息
        """
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
        """训练进度回调
        
        Args:
            task: 任务对象
            progress: 进度百分比（0-1）
            message: 进度消息
        """
        logger.info(f"训练进度: {task.task_name} - {progress*100:.1f}% - {message}")
        
    def get_training_task_status(self, task_id):
        """获取训练任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task_id)
            
            if not training_task:
                logger.error(f"训练任务不存在: {task_id}")
                return None
                
            task_info = self.training_tasks.get(task_id)
            if not task_info:
                task_info = {
                    "task_dir": os.path.join("training_data", training_task.task_name),
                    "status": training_task.status,
                    "annotated_images": 0,
                    "total_images": 0
                }
                self.training_tasks[task_id] = task_info
                
            # 获取数据集信息
            image_dir = os.path.join(task_info["task_dir"], "dataset/images/train")
            label_dir = os.path.join(task_info["task_dir"], "dataset/labels/train")
            
            image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            annotated_files = [os.path.splitext(f)[0] + ".txt" for f in image_files]
            
            annotated_count = 0
            for txt_file in annotated_files:
                if os.path.exists(os.path.join(label_dir, txt_file)):
                    annotated_count += 1
                    
            task_info["annotated_images"] = annotated_count
            task_info["total_images"] = len(image_files)
            
            # 计算标注进度
            annotation_progress = 0
            if task_info["total_images"] > 0:
                annotation_progress = (task_info["annotated_images"] / task_info["total_images"]) * 100
            
            return {
                "id": training_task.id,
                "name": training_task.task_name,
                "description": training_task.task_description,
                "status": training_task.status,
                "created_at": training_task.created_at,
                "updated_at": training_task.updated_at,
                "dataset_path": training_task.dataset_path,
                "model_path": training_task.model_path,
                "epochs": training_task.epochs,
                "batch_size": training_task.batch_size,
                "annotated_images": task_info["annotated_images"],
                "total_images": task_info["total_images"],
                "annotation_progress": round(annotation_progress, 1),
                "mAP": training_task.mAP,
                "loss": training_task.loss
            }
            
        except Exception as e:
            logger.error(f"获取任务状态出错: {str(e)}", exc_info=True)
            return None
            
        finally:
            session.close()
    
    def update_task_status(self, task_id, status):
        """更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态 (pending/annotating/training/completed/failed)
            
        Returns:
            更新结果
        """
        valid_statuses = ['pending', 'annotating', 'training', 'completed', 'failed']
        if status not in valid_statuses:
            logger.error(f"无效的任务状态: {status}")
            return False
            
        session = db_manager.get_session()
        try:
            training_task = session.get(TrainingTask, task_id)
            
            if not training_task:
                logger.error(f"训练任务不存在: {task_id}")
                return False
                
            training_task.status = status
            session.commit()
            
            if task_id in self.training_tasks:
                self.training_tasks[task_id]["status"] = status
                
            logger.info(f"任务状态更新成功: {task_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"更新任务状态出错: {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()
    
    def get_task_progress(self, task_id):
        """获取任务进度
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务进度信息
        """
        status_info = self.get_training_task_status(task_id)
        if not status_info:
            return None
            
        progress_info = {
            "annotation_progress": status_info["annotation_progress"],
            "total_images": status_info["total_images"],
            "annotated_images": status_info["annotated_images"],
            "unannotated_images": status_info["total_images"] - status_info["annotated_images"],
            "status": status_info["status"]
        }
        
        return progress_info

# 全局训练管理器实例
training_manager = TrainingManager()