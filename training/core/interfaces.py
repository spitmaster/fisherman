"""
训练模块 - 接口定义

使用抽象基类定义训练模块的核心接口，确保模块间的一致性和可扩展性。
支持扩展的回调接口和事件处理机制。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Callable, Union


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


class ICallbackManager(ABC):
    """回调管理器接口"""
    
    @abstractmethod
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """注册回调函数
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        pass
    
    @abstractmethod
    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """注销回调函数
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        pass
    
    @abstractmethod
    def _notify_callbacks(self, event_type: str, data: Any = None) -> None:
        """通知所有注册的回调函数
        
        Args:
            event_type: 事件类型
            data: 传递给回调函数的数据
        """
        pass


class IEventManager(ABC):
    """事件管理器接口"""
    
    @abstractmethod
    def register_event_handler(self, event_name: str, handler: Callable) -> None:
        """注册事件处理器
        
        Args:
            event_name: 事件名称
            handler: 事件处理函数
        """
        pass
    
    @abstractmethod
    def _notify_event(self, event_name: str, event_data: Dict[str, Any] = None) -> None:
        """通知事件处理器
        
        Args:
            event_name: 事件名称
            event_data: 事件数据
        """
        pass


class IErrorHandler(ABC):
    """错误处理接口"""
    
    @abstractmethod
    def _handle_database_error(self, error: Exception, operation: str, 
                             task_id: int = None) -> Dict[str, Any]:
        """处理数据库错误"""
        pass
    
    @abstractmethod
    def _handle_file_operation_error(self, error: Exception, operation: str, 
                                   file_path: str = None) -> Dict[str, Any]:
        """处理文件操作错误"""
        pass
    
    @abstractmethod
    def validate_file_path(self, file_path: str, check_exists: bool = True, 
                          check_readable: bool = False, check_writable: bool = False) -> Dict[str, Any]:
        """验证文件路径"""
        pass


class IOperationManager(ABC):
    """操作管理器接口"""
    
    @abstractmethod
    def create_operation_context(self, operation_name: str, **kwargs) -> Dict[str, Any]:
        """创建操作上下文"""
        pass
    
    @abstractmethod
    def complete_operation_context(self, context: Dict[str, Any], success: bool, 
                                 result: Any = None, error: str = None) -> Dict[str, Any]:
        """完成操作上下文"""
        pass
    
    @abstractmethod
    def _safe_execute_with_retry(self, func, max_retries: int = 3, 
                                delay: float = 1.0, *args, **kwargs) -> Any:
        """带重试机制的安全执行函数"""
        pass