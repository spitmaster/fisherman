#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练配置生成器

负责生成YOLO训练所需的data.yaml配置文件和训练参数。
"""

from typing import Dict, Any
from pathlib import Path
from datetime import datetime

from ..dataset_path_manager import DatasetPathManager


class TrainingConfigBuilder:
    """训练配置生成器"""

    @staticmethod
    def create_data_yaml(dataset_name: str) -> Path:
        """创建YOLO训练所需的data.yaml文件

        Args:
            dataset_name: 训练集名称

        Returns:
            data.yaml文件路径
        """
        dataset_path = DatasetPathManager.get_dataset_path(dataset_name)

        data_yaml_content = f"""path: {dataset_path.absolute()}
train: {DatasetPathManager.DATASET_DIR}/{DatasetPathManager.IMAGES_DIR}
val: {DatasetPathManager.DATASET_DIR}/{DatasetPathManager.IMAGES_DIR}

names:
  0: fish
"""

        data_yaml_path = dataset_path / "data.yaml"
        with open(data_yaml_path, 'w', encoding='utf-8') as f:
            f.write(data_yaml_content)

        return data_yaml_path

    @staticmethod
    def build_yolo_params(
        data_yaml_path: Path,
        weights_dir: Path,
        training_params: Dict[str, Any],
        verbose: bool = True
    ) -> Dict[str, Any]:
        """构建YOLO训练参数

        Args:
            data_yaml_path: data.yaml文件路径
            weights_dir: 权重保存目录
            training_params: 训练参数
            verbose: 是否输出详细日志

        Returns:
            YOLO训练参数字典
        """
        # 生成唯一的训练名称，使用时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        train_name = f"train_{timestamp}"

        return {
            "data": str(data_yaml_path),
            "epochs": training_params.get("epochs", 100),
            "batch": training_params.get("batch_size", 16),
            "imgsz": training_params.get("image_size", 640),
            "project": str(weights_dir),
            "name": train_name,
            "exist_ok": True,
            "verbose": verbose,
            "device": training_params.get("device", "cpu"),
        }
