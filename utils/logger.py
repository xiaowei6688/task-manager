"""
日志工具模块
提供结构化的日志记录功能，支持不同级别的日志输出
"""

import os
import sys
import logging
import structlog
from datetime import datetime
from typing import Any, Dict, Optional
from config.settings import config

def setup_logging() -> None:
    """设置日志配置"""
    
    # 创建日志目录
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 使用简单的日志格式，避免复杂的structlog配置
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, config.LOG_LEVEL.upper()),
        handlers=[
            logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 配置structlog使用简单格式
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=False)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """获取日志记录器"""
    return structlog.get_logger(name)

class TaskLogger:
    """任务专用日志记录器"""
    
    def __init__(self, task_id: str, task_name: str):
        self.task_id = task_id
        self.task_name = task_name
        self.logger = get_logger(f"task.{task_name}")
    
    def info(self, message: str, **kwargs) -> None:
        """记录信息日志"""
        self.logger.info(
            message,
            task_id=self.task_id,
            task_name=self.task_name,
            **kwargs
        )
    
    def warning(self, message: str, **kwargs) -> None:
        """记录警告日志"""
        self.logger.warning(
            message,
            task_id=self.task_id,
            task_name=self.task_name,
            **kwargs
        )
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """记录错误日志"""
        extra_data = {
            "task_id": self.task_id,
            "task_name": self.task_name,
            **kwargs
        }
        
        if error:
            extra_data["error_type"] = type(error).__name__
            extra_data["error_message"] = str(error)
        
        self.logger.error(message, **extra_data)
    
    def debug(self, message: str, **kwargs) -> None:
        """记录调试日志"""
        self.logger.debug(
            message,
            task_id=self.task_id,
            task_name=self.task_name,
            **kwargs
        )

class SystemLogger:
    """系统日志记录器"""
    
    def __init__(self, component: str):
        self.component = component
        self.logger = get_logger(f"system.{component}")
    
    def info(self, message: str, **kwargs) -> None:
        """记录系统信息"""
        self.logger.info(message, component=self.component, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """记录系统警告"""
        self.logger.warning(message, component=self.component, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """记录系统错误"""
        extra_data = {"component": self.component, **kwargs}
        
        if error:
            extra_data["error_type"] = type(error).__name__
            extra_data["error_message"] = str(error)
        
        self.logger.error(message, **extra_data)
    
    def debug(self, message: str, **kwargs) -> None:
        """记录系统调试信息"""
        self.logger.debug(message, component=self.component, **kwargs)

# 初始化日志系统
setup_logging()

# 创建默认日志记录器
default_logger = get_logger("task_manage")
system_logger = SystemLogger("main") 