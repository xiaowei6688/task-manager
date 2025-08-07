"""
API数据模型
定义请求和响应的数据结构
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime

class TaskCreateRequest(BaseModel):
    """创建任务请求模型"""
    
    name: str = Field(..., description="任务名称", min_length=1, max_length=100)
    task_type: str = Field(..., description="任务类型", regex="^(immediate|delayed|scheduled)$")
    
    # 动态代码任务参数
    function_code: Optional[str] = Field(None, description="函数代码")
    function_name: Optional[str] = Field(None, description="函数名称")
    args: Optional[List] = Field(default=[], description="函数参数")
    kwargs: Optional[Dict[str, Any]] = Field(default={}, description="函数关键字参数")
    
    # API任务参数
    api_url: Optional[str] = Field(None, description="API地址")
    method: Optional[str] = Field(default="GET", description="HTTP方法")
    headers: Optional[Dict[str, str]] = Field(default={}, description="请求头")
    data: Optional[Dict[str, Any]] = Field(default={}, description="请求数据")
    timeout: Optional[int] = Field(default=30, description="超时时间（秒）")
    
    # 延时任务参数
    delay_seconds: Optional[int] = Field(None, ge=0, description="延时执行时间（秒）")
    
    # 定时任务参数
    cron_expression: Optional[str] = Field(None, description="Cron表达式")
    
    # 其他参数
    created_by: Optional[str] = Field(default="api", description="创建者")
    
    @validator('task_type')
    def validate_task_type(cls, v):
        """验证任务类型"""
        if v == 'delayed' and cls.delay_seconds is None:
            raise ValueError('延时任务必须指定delay_seconds')
        elif v == 'scheduled' and cls.cron_expression is None:
            raise ValueError('定时任务必须指定cron_expression')
        return v
    
    @validator('function_code', 'api_url')
    def validate_task_content(cls, v, values):
        """验证任务内容"""
        task_type = values.get('task_type')
        if task_type == 'immediate' or task_type == 'delayed':
            if not cls.function_code and not cls.api_url:
                raise ValueError('必须提供function_code或api_url')
        return v

class TaskResponse(BaseModel):
    """任务响应模型"""
    
    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    type: str = Field(..., description="任务类型")
    status: str = Field(..., description="任务状态")
    created_at: float = Field(..., description="创建时间")
    data: Dict[str, Any] = Field(..., description="任务数据")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    next_execution: Optional[float] = Field(None, description="下次执行时间")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "示例任务",
                "type": "immediate",
                "status": "completed",
                "created_at": 1640995200.0,
                "data": {
                    "name": "示例任务",
                    "task_type": "immediate",
                    "function_code": "def hello():\n    return 'Hello World!'",
                    "function_name": "hello"
                },
                "result": {
                    "success": True,
                    "result": "Hello World!",
                    "execution_time": 0.001
                },
                "error": None,
                "next_execution": None
            }
        }

class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    
    tasks: List[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总数量")
    page: int = Field(default=1, description="当前页码")
    limit: int = Field(default=100, description="每页数量")
    
    class Config:
        schema_extra = {
            "example": {
                "tasks": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "示例任务1",
                        "type": "immediate",
                        "status": "completed",
                        "created_at": 1640995200.0,
                        "data": {},
                        "result": {},
                        "error": None,
                        "next_execution": None
                    }
                ],
                "total": 1,
                "page": 1,
                "limit": 100
            }
        }

class TaskCreateResponse(BaseModel):
    """创建任务响应模型"""
    
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    next_execution: Optional[float] = Field(None, description="下次执行时间")
    error: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_name": "示例任务",
                "result": {
                    "success": True,
                    "result": "Hello World!",
                    "execution_time": 0.001
                },
                "next_execution": None,
                "error": None
            }
        }

class TaskDeleteResponse(BaseModel):
    """删除任务响应模型"""
    
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "任务已删除",
                "error": None
            }
        }

class TaskStopResponse(BaseModel):
    """停止任务响应模型"""
    
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "任务已停止",
                "error": None
            }
        }

class ErrorResponse(BaseModel):
    """错误响应模型"""
    
    success: bool = Field(False, description="是否成功")
    error: str = Field(..., description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "任务不存在",
                "error_code": "TASK_NOT_FOUND",
                "details": {
                    "task_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }

class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    
    status: str = Field(..., description="服务状态")
    timestamp: str = Field(..., description="检查时间")
    version: str = Field(..., description="服务版本")
    uptime: float = Field(..., description="运行时间（秒）")
    redis_status: str = Field(..., description="Redis状态")
    celery_status: str = Field(..., description="Celery状态")
    active_tasks: int = Field(..., description="活跃任务数")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z",
                "version": "1.0.0",
                "uptime": 3600.0,
                "redis_status": "connected",
                "celery_status": "running",
                "active_tasks": 5
            }
        } 