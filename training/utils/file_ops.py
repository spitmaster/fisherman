#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件操作工具模块

提供文件系统相关的工具函数，如目录创建、文件复制、配置文件生成等。
"""

import os
import shutil
import yaml
import logging

# 日志配置
logger = logging.getLogger(__name__)


def create_task_directory(task_name: str) -> str:
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
        
    logger.info(f"任务目录创建成功: {task_dir}")
    return task_dir


def copy_dataset(source_path: str, target_dir: str) -> bool:
    """复制数据集到任务目录
    
    Args:
        source_path: 源数据集路径
        target_dir: 目标目录
        
    Returns:
        复制是否成功
    """
    try:
        # 复制数据集到任务目录
        shutil.copytree(source_path, os.path.join(target_dir, "dataset"), dirs_exist_ok=True)
        logger.info(f"数据集复制成功: {source_path} -> {target_dir}")
        return True
        
    except Exception as e:
        logger.error(f"复制数据集失败: {str(e)}", exc_info=True)
        return False


def create_default_dataset_structure(task_dir: str) -> None:
    """创建默认的数据集目录结构
    
    Args:
        task_dir: 任务目录
    """
    # 确保必要的目录存在
    subdirs = [
        "dataset/images/train",
        "dataset/images/val",
        "dataset/labels/train",
        "dataset/labels/val"
    ]
    
    for subdir in subdirs:
        dir_path = os.path.join(task_dir, subdir)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            
    logger.info(f"默认数据集结构创建成功: {task_dir}")


def create_data_yaml(task_dir: str, task_name: str) -> str:
    """创建data.yaml配置文件
    
    Args:
        task_dir: 任务目录
        task_name: 任务名称
        
    Returns:
        YAML文件路径
    """
    yaml_path = os.path.join(task_dir, "dataset", "data.yaml")
    
    yaml_content = {
        "path": "../..",  # 相对于YAML文件的路径
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 1,  # 类别数量，默认为1
        "names": ["object"]  # 类别名称
    }
    
    try:
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_content, f, default_flow_style=False, allow_unicode=True)
            
        logger.info(f"data.yaml配置文件创建成功: {yaml_path}")
        return yaml_path
        
    except Exception as e:
        logger.error(f"创建data.yaml配置文件失败: {str(e)}", exc_info=True)
        raise


def copy_image_to_dataset(source_path: str, task_dir: str, filename: str = None) -> str:
    """复制单张图片到数据集
    
    Args:
        source_path: 源图片路径
        task_dir: 任务目录
        filename: 目标文件名，如果为None则使用源文件名
        
    Returns:
        目标文件路径
    """
    if not os.path.exists(source_path):
        logger.error(f"源图片文件不存在: {source_path}")
        return None
        
    if filename is None:
        filename = os.path.basename(source_path)
        
    target_dir = os.path.join(task_dir, "dataset/images/train")
    os.makedirs(target_dir, exist_ok=True)
    
    target_path = os.path.join(target_dir, filename)
    
    try:
        shutil.copy2(source_path, target_path)
        logger.debug(f"图片复制成功: {source_path} -> {target_path}")
        return target_path
        
    except Exception as e:
        logger.error(f"复制图片失败: {str(e)}", exc_info=True)
        return None


def ensure_directory_exists(directory_path: str) -> bool:
    """确保目录存在，如果不存在则创建
    
    Args:
        directory_path: 目录路径
        
    Returns:
        目录是否存在（创建成功或已存在）
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            logger.debug(f"目录创建成功: {directory_path}")
        return True
        
    except Exception as e:
        logger.error(f"创建目录失败: {directory_path} - {str(e)}", exc_info=True)
        return False


def get_image_files(directory_path: str) -> list:
    """获取目录中的所有图片文件
    
    Args:
        directory_path: 目录路径
        
    Returns:
        图片文件列表
    """
    if not os.path.exists(directory_path):
        return []
        
    supported_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp')
    image_files = []
    
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(supported_extensions):
            image_files.append(filename)
            
    return sorted(image_files)


def get_label_files(directory_path: str) -> list:
    """获取目录中的所有标注文件
    
    Args:
        directory_path: 目录路径
        
    Returns:
        标注文件列表
    """
    if not os.path.exists(directory_path):
        return []
        
    label_files = []
    
    for filename in os.listdir(directory_path):
        if filename.lower().endswith('.txt'):
            label_files.append(filename)
            
    return sorted(label_files)