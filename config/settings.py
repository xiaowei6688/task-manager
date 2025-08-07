"""
系统配置文件
包含Redis、Celery、日志、安全等所有配置项
"""

import os
from typing import Dict, Any
from datetime import timedelta

class Config:
    """基础配置类"""
    
    # 应用基础配置
    APP_NAME = "Task Management System"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Redis配置
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_USERNAME = os.getenv("REDIS_USERNAME", "")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    
    # Redis连接池配置
    REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", 1))
    REDIS_CONNECTION_TIMEOUT = int(os.getenv("REDIS_CONNECTION_TIMEOUT", 5))
    REDIS_SOCKET_TIMEOUT = int(os.getenv("REDIS_SOCKET_TIMEOUT", 5))
    REDIS_SOCKET_CONNECT_TIMEOUT = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", 5))
    
    # 构建带认证的Redis URL
    if REDIS_USERNAME and REDIS_PASSWORD:
        REDIS_URL = f"redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    elif REDIS_PASSWORD:
        REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:
        REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    
    # Celery配置
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TIMEZONE = "UTC"
    CELERY_ENABLE_UTC = True
    
    # Celery连接池配置
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
    CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
    CELERY_BROKER_CONNECTION_RETRY = True
    CELERY_BROKER_POOL_LIMIT = REDIS_MAX_CONNECTIONS
    CELERY_BROKER_CONNECTION_TIMEOUT = REDIS_CONNECTION_TIMEOUT
    CELERY_BROKER_SOCKET_TIMEOUT = REDIS_SOCKET_TIMEOUT
    CELERY_BROKER_SOCKET_CONNECT_TIMEOUT = REDIS_SOCKET_CONNECT_TIMEOUT
    
    # Result backend连接池配置
    CELERY_RESULT_BACKEND_CONNECTION_RETRY = True
    CELERY_RESULT_BACKEND_CONNECTION_RETRY_ON_STARTUP = True
    
    # 任务配置
    CELERY_TASK_ROUTES = {
        "*": {"queue": "celery"},  # 所有任务都使用默认的celery队列
    }
    
    # 任务执行配置
    CELERY_TASK_ALWAYS_EAGER = False  # 生产环境必须为False
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_TASK_IGNORE_RESULT = False
    CELERY_TASK_STORE_EAGER_RESULT = True
    
    # Celery结果过期配置
    CELERY_RESULT_EXPIRES = 3600  # Celery结果1小时后过期
    CELERY_TASK_RESULT_EXPIRES = 3600  # 任务结果1小时后过期
    CELERY_RESULT_PERSISTENT = False  # 结果不持久化
    
    # 重试配置
    CELERY_TASK_ACKS_LATE = True
    CELERY_TASK_REJECT_ON_WORKER_LOST = True
    CELERY_TASK_RETRY_POLICY = {
        "max_retries": 3,
        "interval_start": 0,
        "interval_step": 0.2,
        "interval_max": 0.2,
    }
    
    # 定时任务配置
    CELERY_BEAT_SCHEDULE = {
        # 系统维护任务
        "system-health-check": {
            "task": "system.health_check",
            "schedule": timedelta(minutes=5),
        },
        "cleanup-expired-tasks": {
            "task": "system.cleanup_expired_tasks",
            "schedule": timedelta(hours=1),
        },
    }
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = os.getenv("LOG_FILE", "logs/task_manage.log")
    
    # API配置
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 5001))
    API_DEBUG = DEBUG
    
    # 安全配置
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_DELTA = timedelta(hours=24)
    
    # 任务存储配置
    TASK_STORAGE_REDIS_DB = 1  # 使用不同的Redis数据库存储任务信息
    TASK_RESULT_EXPIRY = 86400  # 任务结果保存24小时
    
    # 监控配置
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "True").lower() == "true"
    METRICS_PORT = int(os.getenv("METRICS_PORT", 9090))
    
    # 性能配置
    MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", 100))
    TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", 3600))  # 1小时超时
    
    # 代码执行安全配置
    ALLOWED_MODULES = [
        "math", "datetime", "json", "re", "random", 
        "collections", "itertools", "functools", "operator"
    ]
    MAX_CODE_SIZE = 1024 * 1024  # 1MB代码大小限制
    EXECUTION_TIMEOUT = 300  # 5分钟执行超时

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    CELERY_TASK_ALWAYS_EAGER = False  # 改为False，让任务通过Worker处理

    # 重写Redis配置
    REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 1))
    # REDIS_USERNAME = os.getenv("REDIS_USERNAME", "admin")
    # REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "Admin123..")
    
    # 重写Redis URL
    # REDIS_URL = f"redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    
    # 重写Celery配置
    # CELERY_BROKER_URL = REDIS_URL
    # CELERY_RESULT_BACKEND = REDIS_URL


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = "WARNING"
    
    # 生产环境安全配置
    SECRET_KEY = os.getenv("SECRET_KEY", "admin123")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "admin123")
    
    if not SECRET_KEY or SECRET_KEY == "your-secret-key-change-in-production":
        raise ValueError("SECRET_KEY must be set in production")
    
    if not JWT_SECRET_KEY or JWT_SECRET_KEY == "your-jwt-secret-key":
        raise ValueError("JWT_SECRET_KEY must be set in production")

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    CELERY_TASK_ALWAYS_EAGER = True
    REDIS_DB = 15  # 使用不同的数据库避免冲突

# 配置映射
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

def get_config(env: str = None) -> Config:
    """获取配置对象"""
    if env is None:
        env = os.getenv("FLASK_ENV", "development")
    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()

# 默认配置
config = get_config() 