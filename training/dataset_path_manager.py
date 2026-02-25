"""
训练集目录结构管理模块

统一管理训练集和训练结果的目录路径及创建。
"""

import os
from pathlib import Path
from typing import Optional


class DatasetPathManager:
    """训练集路径管理器"""

    # 基础目录
    BASE_DIR = Path(__file__).parent.parent.parent  # 项目根目录
    RUNNING_DIR = BASE_DIR / "running"
    TRAINING_DIR = RUNNING_DIR / "training"
    TRAINING_RESULT_DIR = RUNNING_DIR / "training_result"

    # 子目录名称
    IMAGES_DIR = "images"
    LABELS_DIR = "labels"
    WEIGHTS_DIR = "weights"

    @classmethod
    def ensure_directories(cls) -> None:
        """确保所有基础目录存在"""
        cls.RUNNING_DIR.mkdir(exist_ok=True)
        cls.TRAINING_DIR.mkdir(exist_ok=True)
        cls.TRAINING_RESULT_DIR.mkdir(exist_ok=True)

    @classmethod
    def get_dataset_path(cls, dataset_name: str) -> Path:
        """获取指定训练集的根路径

        Args:
            dataset_name: 训练集名称

        Returns:
            训练集路径: running/training/{dataset_name}/
        """
        return cls.TRAINING_DIR / dataset_name

    @classmethod
    def create_dataset_dirs(cls, dataset_name: str) -> Path:
        """创建训练集目录结构

        Args:
            dataset_name: 训练集名称

        Returns:
            训练集根路径
        """
        dataset_path = cls.get_dataset_path(dataset_name)
        dataset_path.mkdir(exist_ok=True)
        (dataset_path / cls.IMAGES_DIR).mkdir(exist_ok=True)
        (dataset_path / cls.LABELS_DIR).mkdir(exist_ok=True)
        (dataset_path / cls.WEIGHTS_DIR).mkdir(exist_ok=True)
        return dataset_path

    @classmethod
    def get_images_path(cls, dataset_name: str) -> Path:
        """获取训练集图片目录路径"""
        return cls.get_dataset_path(dataset_name) / cls.IMAGES_DIR

    @classmethod
    def get_labels_path(cls, dataset_name: str) -> Path:
        """获取训练集标注目录路径"""
        return cls.get_dataset_path(dataset_name) / cls.LABELS_DIR

    @classmethod
    def get_weights_path(cls, dataset_name: str) -> Path:
        """获取训练集权重目录路径"""
        return cls.get_dataset_path(dataset_name) / cls.WEIGHTS_DIR

    @classmethod
    def get_model_result_path(cls, model_name: str) -> Path:
        """获取训练结果管理中的模型路径

        Args:
            model_name: 模型名称

        Returns:
            模型路径: running/training_result/{model_name}/
        """
        return cls.TRAINING_RESULT_DIR / model_name

    @classmethod
    def create_model_result_dir(cls, model_name: str) -> Path:
        """创建训练结果目录

        Args:
            model_name: 模型名称

        Returns:
            模型结果路径
        """
        model_path = cls.get_model_result_path(model_name)
        model_path.mkdir(exist_ok=True, parents=True)
        return model_path

    @classmethod
    def list_datasets(cls) -> list[str]:
        """列出所有训练集

        Returns:
            训练集名称列表
        """
        if not cls.TRAINING_DIR.exists():
            return []
        return [d.name for d in cls.TRAINING_DIR.iterdir() if d.is_dir()]

    @classmethod
    def list_model_results(cls) -> list[str]:
        """列出所有训练结果

        Returns:
            模型名称列表
        """
        if not cls.TRAINING_RESULT_DIR.exists():
            return []
        return [d.name for d in cls.TRAINING_RESULT_DIR.iterdir() if d.is_dir()]

    @classmethod
    def dataset_exists(cls, dataset_name: str) -> bool:
        """检查训练集是否存在"""
        return cls.get_dataset_path(dataset_name).exists()

    @classmethod
    def get_dataset_info(cls, dataset_name: str) -> dict:
        """获取训练集信息

        Args:
            dataset_name: 训练集名称

        Returns:
            包含训练集信息的字典
        """
        dataset_path = cls.get_dataset_path(dataset_name)
        if not dataset_path.exists():
            return {}

        images_path = cls.get_images_path(dataset_name)
        labels_path = cls.get_labels_path(dataset_name)
        weights_path = cls.get_weights_path(dataset_name)

        image_count = len(list(images_path.glob("*"))) if images_path.exists() else 0
        label_count = len(list(labels_path.glob("*.txt"))) if labels_path.exists() else 0
        weight_count = len(list(weights_path.glob("*.pt"))) if weights_path.exists() else 0

        return {
            "name": dataset_name,
            "path": str(dataset_path),
            "image_count": image_count,
            "label_count": label_count,
            "weight_count": weight_count,
            "has_weights": weight_count > 0
        }

    @classmethod
    def get_all_datasets_info(cls) -> list[dict]:
        """获取所有训练集信息"""
        return [cls.get_dataset_info(name) for name in cls.list_datasets()]
