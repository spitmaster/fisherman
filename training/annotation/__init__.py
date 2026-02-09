"""
训练模块 - 标注功能

提供可视化标注、标注验证、YOLO格式转换等功能。
"""

from .tool import AnnotationTool
from .manager import AnnotationManager
from .validator import (
    validate_single_annotation_file,
    validate_dataset_annotations,
    get_annotation_statistics
)
from .yolo_formatter import (
    convert_bbox_to_yolo,
    convert_yolo_to_bbox,
    validate_yolo_annotation
)
from .visualizer import (
    draw_annotations,
    show_status_info
)

# 创建全局管理器实例
annotation_manager = AnnotationManager()

__all__ = [
    'AnnotationTool',
    'AnnotationManager',
    'annotation_manager',
    'validate_single_annotation_file',
    'validate_dataset_annotations',
    'get_annotation_statistics',
    'convert_bbox_to_yolo',
    'convert_yolo_to_bbox',
    'validate_yolo_annotation',
    'draw_annotations',
    'show_status_info'
]