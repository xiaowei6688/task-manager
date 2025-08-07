"""
基础任务模块
提供任务执行的核心功能和基础任务类
"""

import uuid
import json
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from celery import Celery, Task
from celery.utils.log import get_task_logger
from config.settings import config
from utils.logger import TaskLogger, SystemLogger
from utils.security import code_checker

logger = get_task_logger(__name__)
system_logger = SystemLogger("tasks")

class BaseTask(Task):
    """基础任务类"""
    
    abstract = True
    
    def __init__(self):
        self.task_logger = None
        self.start_time = None
        self.end_time = None
        self.task_id = None
        self.task_name = None
    
    def __call__(self, *args, **kwargs):
        """任务执行入口"""
        self.start_time = datetime.now()
        self.task_id = kwargs.get('task_id', str(uuid.uuid4()))
        self.task_name = kwargs.get('task_name', self.name)
        
        # 创建任务专用日志记录器
        self.task_logger = TaskLogger(self.task_id, self.task_name)
        self.task_logger.info(f"开始执行任务: {self.task_name}")
        
        # 更新任务状态为运行中
        self._update_task_status('running')
        
        try:
            result = super().__call__(*args, **kwargs)
            self.end_time = datetime.now()
            execution_time = (self.end_time - self.start_time).total_seconds()
            
            self.task_logger.info(
                f"任务执行完成",
                execution_time=execution_time,
                result=result
            )
            
            # 更新任务状态为完成
            self._update_task_status('completed', result)
            
            return result
            
        except Exception as e:
            self.end_time = datetime.now()
            execution_time = (self.end_time - self.start_time).total_seconds()
            
            error_result = {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'execution_time': execution_time
            }
            
            self.task_logger.error(
                f"任务执行失败: {str(e)}",
                error=traceback.format_exc(),
                execution_time=execution_time
            )
            
            # 更新任务状态为失败
            self._update_task_status('failed', error_result)
            
            raise
    
    def _update_task_status(self, status: str, result: Dict[str, Any] = None) -> None:
        """更新任务状态"""
        try:
            # 导入任务管理器
            from tasks.task_manager import TaskManager
            from celery_app import redis_client
            
            # 创建任务管理器实例
            task_manager = TaskManager(self.app, redis_client)
            
            # 更新任务状态
            task_manager.update_task_status(self.task_id, status, result)
            
        except Exception as e:
            system_logger.error(f"更新任务状态失败: {str(e)}")

class DynamicCodeTask(BaseTask):
    """动态代码执行任务"""
    
    def run(self, code: str, function_name: str, args: List = None, 
            kwargs: Dict = None, task_id: str = None, task_name: str = None):
        """
        执行动态代码
        
        Args:
            code: 要执行的代码
            function_name: 要调用的函数名
            args: 函数参数列表
            kwargs: 函数关键字参数
            task_id: 任务ID
            task_name: 任务名称
        """
        args = args or []
        kwargs = kwargs or {}
        
        # 确保start_time被初始化
        if self.start_time is None:
            self.start_time = datetime.now()
        
        # 代码安全检查
        safety_check = code_checker.check_code_safety(code)
        if not safety_check["safe"]:
            raise ValueError(f"代码安全检查失败: {safety_check['error']}")
        
        # 创建安全的执行环境
        safe_globals = self._create_safe_globals()
        safe_locals = {}
        
        try:
            # 编译并执行代码
            compiled_code = compile(code, '<string>', 'exec')
            exec(compiled_code, safe_globals, safe_locals)
            
            # 获取函数
            if function_name not in safe_locals:
                raise ValueError(f"函数 '{function_name}' 未在代码中找到")
            
            function = safe_locals[function_name]
            
            # 执行函数
            result = function(*args, **kwargs)
            
            return {
                'success': True,
                'result': result,
                'function_name': function_name,
                'execution_time': (datetime.now() - self.start_time).total_seconds()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'execution_time': (datetime.now() - self.start_time).total_seconds()
            }
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """创建安全的全局变量环境"""
        safe_globals = {}
        
        # 添加允许的模块
        for module_name in config.ALLOWED_MODULES:
            try:
                module = __import__(module_name)
                safe_globals[module_name] = module
            except ImportError:
                continue
        
        # 添加基础内置函数
        safe_globals.update({
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'bool': bool,
            'type': type,
            'isinstance': isinstance,
            'hasattr': hasattr,
            'getattr': getattr,
            'setattr': setattr,
            'dir': dir,
            'help': help,
            'id': id,
            'hash': hash,
            'repr': repr,
            'format': format,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sorted': sorted,
            'reversed': reversed,
            'range': range,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'pow': pow,
            'divmod': divmod,
            'all': all,
            'any': any,
            'bin': bin,
            'hex': hex,
            'oct': oct,
            'chr': chr,
            'ord': ord,
            'ascii': ascii,
            'globals': lambda: safe_globals,
            'locals': lambda: {},
        })
        
        return safe_globals

class APITask(BaseTask):
    """API请求任务"""
    
    def run(self, url: str, method: str = "GET", headers: Dict = None, 
            data: Dict = None, timeout: int = 30, task_id: str = None, task_name: str = None):
        """
        执行API请求
        
        Args:
            url: 请求URL
            method: 请求方法
            headers: 请求头
            data: 请求数据
            timeout: 超时时间
            task_id: 任务ID
            task_name: 任务名称
        """
        import requests
        
        headers = headers or {}
        data = data or {}
        
        # 确保start_time被初始化
        if self.start_time is None:
            self.start_time = datetime.now()
        
        try:
            # 执行请求
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=data if method.upper() in ['POST', 'PUT', 'PATCH'] else None,
                params=data if method.upper() == 'GET' else None,
                timeout=timeout
            )
            
            # 构建响应结果
            result = {
                'success': True,
                'status_code': response.status_code,
                'url': url,
                'method': method.upper(),
                'headers': dict(response.headers),
                'response_text': response.text,
                'response_json': None,
                'execution_time': (datetime.now() - self.start_time).total_seconds()
            }
            
            # 尝试解析JSON响应
            try:
                result['response_json'] = response.json()
            except:
                pass
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'method': method.upper(),
                'execution_time': (datetime.now() - self.start_time).total_seconds()
            }

class SystemTask(BaseTask):
    """系统任务"""
    
    def run(self, task_type: str, **kwargs):
        """
        执行系统任务
        
        Args:
            task_type: 任务类型
            **kwargs: 其他参数
        """
        if task_type == "health_check":
            return self._health_check(**kwargs)
        elif task_type == "cleanup_expired_tasks":
            return self._cleanup_expired_tasks(**kwargs)
        else:
            raise ValueError(f"未知的系统任务类型: {task_type}")
    
    def _health_check(self, **kwargs):
        """系统健康检查"""
        try:
            # 检查Redis连接
            from celery_app import redis_client
            redis_client.ping()
            
            # 检查Celery状态
            from celery_app import celery_app
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active()
            
            return {
                "success": True,
                "redis_status": "connected",
                "celery_status": "running",
                "active_tasks": active_tasks,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _cleanup_expired_tasks(self, **kwargs):
        """清理过期任务"""
        try:
            from celery_app import redis_client
            
            # 清理超过24小时的任务结果
            current_time = time.time()
            expired_time = current_time - config.TASK_RESULT_EXPIRY
            
            # 这里需要根据实际的Redis键模式来实现清理逻辑
            # 示例实现
            keys_to_delete = []
            for key in redis_client.scan_iter(match="task_result:*"):
                try:
                    task_data = redis_client.get(key)
                    if task_data:
                        task_info = json.loads(task_data)
                        if task_info.get("created_at", 0) < expired_time:
                            keys_to_delete.append(key)
                except:
                    continue
            
            if keys_to_delete:
                redis_client.delete(*keys_to_delete)
            
            return {
                "success": True,
                "deleted_keys": len(keys_to_delete),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# 任务注册函数
def register_dynamic_task(celery_app: Celery, task_name: str) -> None:
    """注册动态任务"""
    task = celery_app.task(
        DynamicCodeTask(),
        name=f"dynamic.{task_name}",
        bind=True
    )
    return task

def register_api_task(celery_app: Celery, task_name: str) -> None:
    """注册API任务"""
    task = celery_app.task(
        APITask(),
        name=f"api.{task_name}",
        bind=True
    )
    return task

def register_system_task(celery_app: Celery, task_name: str) -> None:
    """注册系统任务"""
    task = celery_app.task(
        SystemTask(),
        name=f"system.{task_name}",
        bind=True
    )
    return task

# 便捷执行函数
def execute_dynamic_code(code: str, function_name: str, args: List = None, 
                        kwargs: Dict = None, task_id: str = None, task_name: str = None):
    """执行动态代码"""
    task = DynamicCodeTask()
    return task.run(code, function_name, args, kwargs, task_id, task_name)

def execute_api_request(url: str, method: str = "GET", headers: Dict = None, 
                       data: Dict = None, timeout: int = 30, task_id: str = None, 
                       task_name: str = None):
    """执行API请求"""
    task = APITask()
    return task.run(url, method, headers, data, timeout, task_id, task_name)

def execute_system_task(operation: str, params: dict = None, task_id: str = None, 
                       task_name: str = None):
    """执行系统任务"""
    task = SystemTask()
    return task.run(operation, params, task_id, task_name) 