"""
训练模块 - 接口定义

使用抽象基类定义训练模块的核心接口，确保模块间的一致性和可扩展性。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple


class IAnnotationTool(ABC):
    """标注工具接口"""
    
    @abstractmethod
    def start_annotation(self) -> None:
        """开始标注流程"""
        pass
    
    @abstractmethod
    def get_annotation_status(self) -> Dict[str, Any]:
        """获取标注状态信息"""
        pass
    
    @abstractmethod
    def validate_annotations(self) -> Dict[str, Any]:
        """验证标注数据的合法性"""
        pass


class ITrainingManager(ABC):
    """训练管理器接口"""
    
    @abstractmethod
    def create_training_task(self, task_name: str, task_description: str, 
                           dataset_path: Optional[str] = None, 
                           epochs: int = 50, batch_size: int = 8) -> Optional[int]:
        """创建新的训练任务"""
        pass
    
    @abstractmethod
    def get_all_training_tasks(self) -> List[Dict[str, Any]]:
        """获取所有训练任务"""
        pass
    
    @abstractmethod
    def get_training_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取训练任务"""
        pass
    
    @abstractmethod
    def update_training_task(self, task_id: int, **kwargs) -> bool:
        """更新训练任务信息"""
        pass
    
    @abstractmethod
    def delete_training_task(self, task_id: int) -> bool:
        """删除训练任务"""
        pass
    
    @abstractmethod
    def start_training(self, task_id: int) -> bool:
        """开始训练任务"""
        pass


class IDatasetManager(ABC):
    """数据集管理器接口"""
    
    @abstractmethod
    def import_images(self, task_id: int, image_paths: List[str]) -> int:
        """导入图片到训练任务"""
        pass
    
    @abstractmethod
    def get_dataset_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取数据集信息"""
        pass
    
    @abstractmethod
    def get_image_list(self, task_id: int) -> List[str]:
        """获取任务的图片列表"""
        pass
    
    @abstractmethod
    def get_unannotated_images(self, task_id: int) -> List[str]:
        """获取未标注的图片列表"""
        pass


class ITrainer(ABC):
    """训练器接口"""
    
    @abstractmethod
    def train(self, task_id: int, dataset_config: Dict[str, Any], 
              training_params: Dict[str, Any]) -> Dict[str, Any]:
        """执行训练任务"""
        pass
    
    @abstractmethod
    def save_training_result(self, task_id: int, result: Dict[str, Any]) -> bool:
        """保存训练结果"""
        pass


class ITaskStatusTracker(ABC):
    """任务状态跟踪器接口"""
    
    @abstractmethod
    def update_task_status(self, task_id: int, status: str) -> bool:
        """更新任务状态"""
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: int) -> Optional[str]:
        """获取任务状态"""
        pass
    
    @abstractmethod
    def get_task_progress(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务进度信息"""
        pass