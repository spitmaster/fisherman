"""
训练模块 - 标注功能

提供可视化标注、标注验证、标注导出、YOLO格式转换等功能。

模块结构：
- tool: 标注工具核心
- manager: 标注管理器
- validator: 标注验证器
- exporter: 标注导出器
- yolo_formatter: YOLO格式转换
- visualizer: 标注可视化
"""

from .tool import AnnotationTool, AnnotationManager, annotation_manager
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
from .exporter import AnnotationExporter, create_exporter

__all__ = [
    # 标注工具
    'AnnotationTool',
    'AnnotationManager',
    'annotation_manager',
    
    # 验证器
    'validate_single_annotation_file',
    'validate_dataset_annotations',
    'get_annotation_statistics',
    
    # 格式转换
    'convert_bbox_to_yolo',
    'convert_yolo_to_bbox',
    'validate_yolo_annotation',
    
    # 可视化
    'draw_annotations',
    'show_status_info',
    
    # 导出器
    'AnnotationExporter',
    'create_exporter',
]
