"""
训练模块 - 主模块

提供训练功能的统一入口点。
"""

# 导出新模块化结构的组件
# 注意：为了避免循环导入，我们不在这里创建全局实例
# 全局实例在各自的子模块中创建

# 重新导出子模块的内容
from .task import (
    TrainingTaskManager,
    training_manager,
    TaskCreator,
    TaskStatusTracker,
    DatasetManager
)

from .annotation import (
    AnnotationTool,
    AnnotationManager,
    annotation_manager,
    validate_single_annotation_file,
    validate_dataset_annotations,
    get_annotation_statistics,
    convert_bbox_to_yolo,
    convert_yolo_to_bbox,
    validate_yolo_annotation,
    draw_annotations,
    show_status_info
)

from .training import (
    TrainingExecutor,
    YOLOTrainer,
    TrainingCallbackHandler,
    TrainingResultSaver,
    training_executor,
    yolo_trainer,
    callback_handler,
    result_saver
)

from .utils import (
    create_task_directory,
    copy_dataset,
    create_default_dataset_structure,
    create_data_yaml,
    copy_image_to_dataset,
    ensure_directory_exists,
    get_image_files,
    get_label_files
)

from .core import (
    IAnnotationTool,
    ITrainingManager,
    IDatasetManager,
    ITrainer,
    ITaskStatusTracker,
    BaseManager
)

# 导出列表
__all__ = [
    # 任务管理
    'TrainingTaskManager',
    'training_manager',
    'TaskCreator',
    'TaskStatusTracker',
    'DatasetManager',
    
    # 标注工具
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
    'show_status_info',
    
    # 训练执行
    'TrainingExecutor',
    'YOLOTrainer',
    'TrainingCallbackHandler',
    'TrainingResultSaver',
    'training_executor',
    'yolo_trainer',
    'callback_handler',
    'result_saver',
    
    # 工具函数
    'create_task_directory',
    'copy_dataset',
    'create_default_dataset_structure',
    'create_data_yaml',
    'copy_image_to_dataset',
    'ensure_directory_exists',
    'get_image_files',
    'get_label_files',
    
    # 核心接口
    'IAnnotationTool',
    'ITrainingManager',
    'IDatasetManager',
    'ITrainer',
    'ITaskStatusTracker',
    'BaseManager'
]