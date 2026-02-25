"""
训练模块 - 基础管理器类

提供训练模块中所有管理器的基类，包含通用的数据库操作、日志记录和资源管理功能。
支持回调接口和增强的错误处理机制。
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Union
from abc import ABC, abstractmethod
from global_support.database import db_manager


class IBaseManager(ABC):
    """基础管理器接口
    
    定义所有管理器必须实现的基本接口。
    """
    
    @abstractmethod
    def log_operation(self, operation: str, details: str = "", level: str = "INFO") -> None:
        """记录操作日志"""
        pass
    
    @abstractmethod
    def validate_parameters(self, params: Dict[str, Any], required_params: list) -> bool:
        """验证参数是否完整"""
        pass
    
    @abstractmethod
    def format_response(self, success: bool, data: Any = None, message: str = "") -> Dict[str, Any]:
        """格式化响应数据"""
        pass


class BaseManager(IBaseManager):
    """基础管理器类
    
    所有训练模块管理器的基类，提供以下功能：
    1. 数据库会话管理
    2. 统一的日志记录
    3. 增强的错误处理和资源清理
    4. 基础CRUD操作模板
    5. 回调接口机制
    6. 事件通知系统
    """
    
    def __init__(self, module_name: str = None):
        """初始化基础管理器
        
        Args:
            module_name: 模块名称，用于日志记录
        """
        if module_name:
            self.logger = logging.getLogger(f"training.{module_name}")
        else:
            self.logger = logging.getLogger(self.__class__.__module__)
        
        self._initialized = False
        self._callbacks: Dict[str, List[Callable]] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        
    def _ensure_initialized(self) -> None:
        """确保管理器已初始化"""
        if not self._initialized:
            self._initialize()
            self._initialized = True
    
    def _initialize(self) -> None:
        """初始化管理器，子类可重写此方法"""
        pass
    
    def _get_db_session(self):
        """获取数据库会话
        
        Returns:
            数据库会话对象
        """
        return db_manager.get_session()
    
    def _execute_db_operation(self, operation_func, *args, **kwargs) -> Any:
        """执行数据库操作，自动处理会话和异常
        
        Args:
            operation_func: 数据库操作函数，接收session作为第一个参数
            *args: 传递给操作函数的参数
            **kwargs: 传递给操作函数的关键字参数
            
        Returns:
            操作函数的返回值，操作失败时返回None
        """
        session = self._get_db_session()
        try:
            result = operation_func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            self.logger.error(f"数据库操作失败: {str(e)}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()
    
    def _safe_execute(self, func, *args, **kwargs) -> Any:
        """安全执行函数，捕获并记录异常
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数返回值，异常时返回None
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"执行函数 {func.__name__} 失败: {str(e)}", exc_info=True)
            self._notify_event("operation_failed", {
                "function": func.__name__,
                "error": str(e),
                "args": args,
                "kwargs": kwargs
            })
            return None
    
    def _safe_execute_with_retry(self, func, max_retries: int = 3, 
                                delay: float = 1.0, *args, **kwargs) -> Any:
        """带重试机制的安全执行函数
        
        Args:
            func: 要执行的函数
            max_retries: 最大重试次数
            delay: 重试间隔（秒）
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数返回值，异常时返回None
        """
        import time
        
        for attempt in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"函数 {func.__name__} 在第 {attempt + 1} 次尝试后成功执行")
                return result
            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(f"函数 {func.__name__} 执行失败，第 {attempt + 1} 次重试: {str(e)}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"函数 {func.__name__} 在 {max_retries} 次重试后仍然失败: {str(e)}", exc_info=True)
                    self._notify_event("operation_failed_after_retry", {
                        "function": func.__name__,
                        "error": str(e),
                        "attempts": attempt + 1,
                        "args": args,
                        "kwargs": kwargs
                    })
                    return None
    
    def log_operation(self, operation: str, details: str = "", level: str = "INFO") -> None:
        """记录操作日志
        
        Args:
            operation: 操作名称
            details: 操作详情
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
        """
        log_message = f"{operation}"
        if details:
            log_message += f": {details}"
        
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(log_message)
    
    def validate_parameters(self, params: Dict[str, Any], required_params: list) -> bool:
        """验证参数是否完整
        
        Args:
            params: 参数字典
            required_params: 必需参数列表
            
        Returns:
            参数是否有效
        """
        missing_params = []
        for param in required_params:
            if param not in params:
                missing_params.append(param)
            elif params[param] is None:
                missing_params.append(f"{param} (值为None)")
        
        if missing_params:
            self.logger.error(f"参数验证失败，缺少参数: {', '.join(missing_params)}")
            return False
        
        return True
    
    def format_response(self, success: bool, data: Any = None, message: str = "", 
                       error_code: str = None, error_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """格式化响应数据
        
        Args:
            success: 操作是否成功
            data: 响应数据
            message: 响应消息
            error_code: 错误代码
            error_details: 错误详细信息
            
        Returns:
            格式化的响应字典
        """
        response = {
            "success": success,
            "message": message,
            "data": data
        }
        
        if not message:
            response["message"] = "操作成功" if success else "操作失败"
        
        if not success:
            response["error_code"] = error_code or "UNKNOWN_ERROR"
            if error_details:
                response["error_details"] = error_details
        
        return response
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """注册回调函数
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        
        if callback not in self._callbacks[event_type]:
            self._callbacks[event_type].append(callback)
            self.logger.debug(f"已注册回调函数到事件: {event_type}")
    
    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """注销回调函数
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)
            self.logger.debug(f"已注销回调函数从事件: {event_type}")
    
    def _notify_callbacks(self, event_type: str, data: Any = None) -> None:
        """通知所有注册的回调函数
        
        Args:
            event_type: 事件类型
            data: 传递给回调函数的数据
        """
        if event_type in self._callbacks:
            for callback in self._callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"回调函数执行失败: {callback.__name__} - {str(e)}")
    
    def register_event_handler(self, event_name: str, handler: Callable) -> None:
        """注册事件处理器
        
        Args:
            event_name: 事件名称
            handler: 事件处理函数
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        
        if handler not in self._event_handlers[event_name]:
            self._event_handlers[event_name].append(handler)
            self.logger.debug(f"已注册事件处理器: {event_name}")
    
    def _notify_event(self, event_name: str, event_data: Dict[str, Any] = None) -> None:
        """通知事件处理器
        
        Args:
            event_name: 事件名称
            event_data: 事件数据
        """
        if event_data is None:
            event_data = {}
        
        if event_name in self._event_handlers:
            for handler in self._event_handlers[event_name]:
                try:
                    handler(event_data)
                except Exception as e:
                    self.logger.error(f"事件处理器执行失败: {handler.__name__} - {str(e)}")
    
    def create_operation_context(self, operation_name: str, **kwargs) -> Dict[str, Any]:
        """创建操作上下文
        
        Args:
            operation_name: 操作名称
            **kwargs: 上下文参数
            
        Returns:
            操作上下文字典
        """
        import time
        context = {
            "operation_name": operation_name,
            "start_time": time.time(),
            "operation_id": f"{operation_name}_{int(time.time() * 1000)}",
            "parameters": kwargs
        }
        return context
    
    def complete_operation_context(self, context: Dict[str, Any], success: bool, 
                                 result: Any = None, error: str = None) -> Dict[str, Any]:
        """完成操作上下文
        
        Args:
            context: 操作上下文
            success: 是否成功
            result: 操作结果
            error: 错误信息
            
        Returns:
            完成的上下文信息
        """
        import time
        context["end_time"] = time.time()
        context["duration"] = context["end_time"] - context["start_time"]
        context["success"] = success
        context["result"] = result
        
        if error:
            context["error"] = error
        
        return context
    
    def _handle_database_error(self, error: Exception, operation: str, 
                             task_id: int = None) -> Dict[str, Any]:
        """处理数据库错误
        
        Args:
            error: 错误对象
            operation: 操作名称
            task_id: 任务ID（可选）
            
        Returns:
            错误响应
        """
        error_details = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        
        if task_id is not None:
            error_details["task_id"] = task_id
        
        self.log_operation("error", f"数据库操作失败: {operation}", "ERROR")
        self._notify_event("database_error", error_details)
        
        return self.format_response(
            success=False,
            message=f"数据库操作失败: {str(error)}",
            error_code="DATABASE_ERROR",
            error_details=error_details
        )
    
    def _handle_file_operation_error(self, error: Exception, operation: str, 
                                   file_path: str = None) -> Dict[str, Any]:
        """处理文件操作错误
        
        Args:
            error: 错误对象
            operation: 操作名称
            file_path: 文件路径（可选）
            
        Returns:
            错误响应
        """
        error_details = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        
        if file_path is not None:
            error_details["file_path"] = file_path
        
        self.log_operation("error", f"文件操作失败: {operation}", "ERROR")
        self._notify_event("file_operation_error", error_details)
        
        return self.format_response(
            success=False,
            message=f"文件操作失败: {str(error)}",
            error_code="FILE_OPERATION_ERROR",
            error_details=error_details
        )
    
    def validate_file_path(self, file_path: str, check_exists: bool = True, 
                          check_readable: bool = False, check_writable: bool = False) -> Dict[str, Any]:
        """验证文件路径
        
        Args:
            file_path: 文件路径
            check_exists: 检查文件是否存在
            check_readable: 检查文件是否可读
            check_writable: 检查文件是否可写
            
        Returns:
            验证结果
        """
        import os
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if not file_path:
            validation_result["valid"] = False
            validation_result["errors"].append("文件路径不能为空")
            return validation_result
        
        if check_exists and not os.path.exists(file_path):
            validation_result["valid"] = False
            validation_result["errors"].append(f"文件不存在: {file_path}")
        
        if check_readable and os.path.exists(file_path) and not os.access(file_path, os.R_OK):
            validation_result["valid"] = False
            validation_result["errors"].append(f"文件不可读: {file_path}")
        
        if check_writable and os.path.exists(file_path) and not os.access(file_path, os.W_OK):
            validation_result["valid"] = False
            validation_result["errors"].append(f"文件不可写: {file_path}")
        
        return validation_result