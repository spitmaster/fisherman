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
import fnmatch
from datetime import datetime

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


def batch_copy_images(source_dir: str, target_dir: str, file_pattern: str = "*") -> tuple[int, list[str]]:
    """批量复制图片文件
    
    Args:
        source_dir: 源目录
        target_dir: 目标目录
        file_pattern: 文件匹配模式，支持通配符
        
    Returns:
        成功复制的文件数量和失败的文件列表
    """
    if not os.path.exists(source_dir):
        logger.error(f"源目录不存在: {source_dir}")
        return 0, [f"源目录不存在: {source_dir}"]
    
    # 确保目标目录存在
    ensure_directory_exists(target_dir)
    
    supported_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp')
    failed_files = []
    success_count = 0
    
    try:
        for filename in os.listdir(source_dir):
            file_path = os.path.join(source_dir, filename)
            
            # 检查是否为图片文件
            if not filename.lower().endswith(supported_extensions):
                continue
                
            # 检查文件模式匹配
            if not fnmatch.fnmatch(filename, file_pattern):
                continue
                
            try:
                target_path = os.path.join(target_dir, filename)
                shutil.copy2(file_path, target_path)
                success_count += 1
                logger.debug(f"批量复制成功: {filename}")
                
            except Exception as e:
                failed_files.append(f"{filename}: {str(e)}")
                logger.error(f"批量复制失败: {filename} - {str(e)}")
                
        logger.info(f"批量复制完成: 成功 {success_count} 个文件，失败 {len(failed_files)} 个文件")
        return success_count, failed_files
        
    except Exception as e:
        logger.error(f"批量复制操作异常: {str(e)}", exc_info=True)
        return 0, [f"批量复制操作异常: {str(e)}"]


def batch_create_directories(directory_paths: list[str]) -> tuple[int, list[str]]:
    """批量创建目录
    
    Args:
        directory_paths: 目录路径列表
        
    Returns:
        成功创建的目录数量和失败的目录列表
    """
    failed_paths = []
    success_count = 0
    
    for dir_path in directory_paths:
        try:
            os.makedirs(dir_path, exist_ok=True)
            success_count += 1
            logger.debug(f"目录创建成功: {dir_path}")
            
        except Exception as e:
            failed_paths.append(f"{dir_path}: {str(e)}")
            logger.error(f"创建目录失败: {dir_path} - {str(e)}")
            
    logger.info(f"批量目录创建完成: 成功 {success_count} 个目录，失败 {len(failed_paths)} 个目录")
    return success_count, failed_paths


def batch_delete_files(file_paths: list[str]) -> tuple[int, list[str]]:
    """批量删除文件
    
    Args:
        file_paths: 文件路径列表
        
    Returns:
        成功删除的文件数量和失败的文件列表
    """
    failed_files = []
    success_count = 0
    
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                success_count += 1
                logger.debug(f"文件删除成功: {file_path}")
            else:
                logger.warning(f"文件不存在，跳过删除: {file_path}")
                
        except Exception as e:
            failed_files.append(f"{file_path}: {str(e)}")
            logger.error(f"删除文件失败: {file_path} - {str(e)}")
            
    logger.info(f"批量文件删除完成: 成功 {success_count} 个文件，失败 {len(failed_files)} 个文件")
    return success_count, failed_files


def batch_rename_files(rename_list: list[tuple[str, str]]) -> tuple[int, list[str]]:
    """批量重命名文件
    
    Args:
        rename_list: 重命名列表，每个元素为 (原路径, 新路径) 元组
        
    Returns:
        成功重命名的文件数量和失败的文件列表
    """
    failed_renames = []
    success_count = 0
    
    for old_path, new_path in rename_list:
        try:
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                success_count += 1
                logger.debug(f"文件重命名成功: {old_path} -> {new_path}")
            else:
                failed_renames.append(f"{old_path}: 文件不存在")
                logger.error(f"文件不存在，无法重命名: {old_path}")
                
        except Exception as e:
            failed_renames.append(f"{old_path} -> {new_path}: {str(e)}")
            logger.error(f"重命名文件失败: {old_path} -> {new_path} - {str(e)}")
            
    logger.info(f"批量文件重命名完成: 成功 {success_count} 个文件，失败 {len(failed_renames)} 个文件")
    return success_count, failed_renames


def batch_copy_with_progress(source_dir: str, target_dir: str, file_pattern: str = "*") -> dict:
    """带进度监控的批量复制
    
    Args:
        source_dir: 源目录
        target_dir: 目标目录
        file_pattern: 文件匹配模式
        
    Returns:
        复制结果统计信息
    """
    if not os.path.exists(source_dir):
        return {
            "success": False,
            "message": f"源目录不存在: {source_dir}",
            "total_files": 0,
            "copied_files": 0,
            "failed_files": []
        }
    
    ensure_directory_exists(target_dir)
    
    supported_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp')
    
    # 获取符合条件的文件列表
    matching_files = []
    for filename in os.listdir(source_dir):
        if filename.lower().endswith(supported_extensions) and fnmatch.fnmatch(filename, file_pattern):
            matching_files.append(filename)
    
    total_files = len(matching_files)
    failed_files = []
    copied_files = 0
    
    logger.info(f"开始批量复制: 共 {total_files} 个文件")
    
    for i, filename in enumerate(matching_files):
        file_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)
        
        try:
            shutil.copy2(file_path, target_path)
            copied_files += 1
            
            # 记录进度（每10个文件或最后一条记录）
            if (i + 1) % 10 == 0 or (i + 1) == total_files:
                logger.info(f"批量复制进度: {i + 1}/{total_files} ({((i + 1) / total_files * 100):.1f}%)")
                
        except Exception as e:
            failed_files.append(f"{filename}: {str(e)}")
            logger.error(f"复制失败: {filename} - {str(e)}")
    
    result = {
        "success": True,
        "message": f"批量复制完成: 成功 {copied_files}/{total_files} 个文件",
        "total_files": total_files,
        "copied_files": copied_files,
        "failed_files": failed_files
    }
    
    logger.info(result["message"])
    return result


def validate_directory_structure(base_dir: str, expected_structure: list[str]) -> dict:
    """验证目录结构
    
    Args:
        base_dir: 基础目录
        expected_structure: 期望的目录结构列表
        
    Returns:
        验证结果
    """
    missing_dirs = []
    existing_dirs = []
    
    for subdir in expected_structure:
        dir_path = os.path.join(base_dir, subdir)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            existing_dirs.append(subdir)
        else:
            missing_dirs.append(subdir)
    
    return {
        "valid": len(missing_dirs) == 0,
        "base_dir": base_dir,
        "total_expected": len(expected_structure),
        "existing_dirs": existing_dirs,
        "missing_dirs": missing_dirs,
        "message": f"目录结构验证: 存在 {len(existing_dirs)} 个目录，缺失 {len(missing_dirs)} 个目录"
    }


def create_backup(source_path: str, backup_dir: str, backup_name: str = None) -> str:
    """创建文件或目录备份
    
    Args:
        source_path: 源路径
        backup_dir: 备份目录
        backup_name: 备份名称，如果为None则使用时间戳
        
    Returns:
        备份路径
    """
    ensure_directory_exists(backup_dir)
    
    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if os.path.isfile(source_path):
            base_name = os.path.basename(source_path)
            backup_name = f"{base_name}_{timestamp}"
        else:
            backup_name = f"backup_{timestamp}"
    
    backup_path = os.path.join(backup_dir, backup_name)
    
    try:
        if os.path.isfile(source_path):
            shutil.copy2(source_path, backup_path)
        else:
            shutil.copytree(source_path, backup_path)
        
        logger.info(f"备份创建成功: {source_path} -> {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"创建备份失败: {str(e)}", exc_info=True)
        raise