"""
训练模块 - 基础管理器类

提供训练模块中所有管理器的基类，包含通用的数据库操作、日志记录和资源管理功能。
"""

import logging
from typing import Dict, Any, Optional
from fisherman.global_support.database import db_manager


class BaseManager:
    """基础管理器类
    
    所有训练模块管理器的基类，提供以下功能：
    1. 数据库会话管理
    2. 统一的日志记录
    3. 错误处理和资源清理
    4. 基础CRUD操作模板
    """
    
    def __init__(self, module_name: str = None):
        """初始化基础管理器
        
        Args:
            module_name: 模块名称，用于日志记录
        """
        if module_name:
            self.logger = logging.getLogger(f"fisherman.training.{module_name}")
        else:
            self.logger = logging.getLogger(self.__class__.__module__)
        
        self._initialized = False
        
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
    
    def format_response(self, success: bool, data: Any = None, message: str = "") -> Dict[str, Any]:
        """格式化响应数据
        
        Args:
            success: 操作是否成功
            data: 响应数据
            message: 响应消息
            
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
        
        return response