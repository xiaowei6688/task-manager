"""
任务管理器
提供任务的增删改查和状态管理功能
"""

import uuid
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from config.settings import config
from utils.logger import SystemLogger
from utils.security import code_checker

system_logger = SystemLogger("task_manager")

class TaskManager:
    """任务管理器"""
    
    def __init__(self, celery_app, redis_client):
        self.celery_app = celery_app
        self.redis_client = redis_client
    
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task_name = task_data.get('name', f'task_{task_id[:8]}')
        task_type = task_data.get('task_type', 'immediate')
        
        # 验证任务数据
        if not self._validate_task_data(task_data):
            return {
                'success': False,
                'error': '任务数据验证失败',
                'task_id': task_id
            }
        
        # 创建任务记录
        task_record = {
            'id': task_id,
            'name': task_name,
            'type': task_type,
            'status': 'pending',
            'created_at': time.time(),
            'data': task_data
        }
        
        # 保存任务记录
        self._save_task_record(task_record)
        
        # 立即执行任务
        if task_type == 'immediate':
            result = self._execute_task(task_record)
            return {
                'success': True,
                'task_id': task_id,
                'task_name': task_name,
                'result': result
            }
        
        # 延时任务
        elif task_type == 'delayed':
            delay_seconds = task_data.get('delay_seconds', 0)
            self._schedule_delayed_task(task_record, delay_seconds)
            return {
                'success': True,
                'task_id': task_id,
                'task_name': task_name,
                'next_execution': time.time() + delay_seconds
            }
        
        return {
            'success': False,
            'error': f'不支持的任务类型: {task_type}',
            'task_id': task_id
        }
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self._get_task_record(task_id)
    
    def get_all_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有任务"""
        tasks = []
        pattern = "task:*"
        
        for key in self.redis_client.scan_iter(match=pattern, count=100):
            task_data = self.redis_client.get(key)
            if task_data:
                task = json.loads(task_data)
                tasks.append(task)
        
        tasks.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        return tasks[:limit]
    
    def get_tasks_by_type(self, task_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """根据类型获取任务"""
        tasks = []
        pattern = "task:*"
        
        for key in self.redis_client.scan_iter(match=pattern, count=100):
            task_data = self.redis_client.get(key)
            if task_data:
                task = json.loads(task_data)
                if task.get('type') == task_type:
                    tasks.append(task)
        
        tasks.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        return tasks[:limit]
    
    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """删除任务"""
        task_record = self._get_task_record(task_id)
        if not task_record:
            return {
                'success': False,
                'error': f'任务不存在: {task_id}'
            }
        
        # 删除任务记录
        self.redis_client.delete(f"task:{task_id}")
        
        return {
            'success': True,
            'task_id': task_id,
            'message': '任务已删除'
        }
    
    def stop_task(self, task_id: str) -> Dict[str, Any]:
        """停止任务"""
        task_record = self._get_task_record(task_id)
        if not task_record:
            return {
                'success': False,
                'error': f'任务不存在: {task_id}'
            }
        
        task_record['status'] = 'stopped'
        self._save_task_record(task_record)
        
        return {
            'success': True,
            'task_id': task_id,
            'message': '任务已停止'
        }
    
    def update_task_status(self, task_id: str, status: str, result: Dict[str, Any] = None) -> None:
        """更新任务状态和结果"""
        task_record = self._get_task_record(task_id)
        if task_record:
            task_record['status'] = status
            task_record['updated_at'] = time.time()
            
            # 直接将结果合并到任务信息中
            if result:
                task_record['result'] = result
            
            self._save_task_record(task_record)
    
    def _validate_task_data(self, task_data: Dict[str, Any]) -> bool:
        """验证任务数据"""
        if 'name' not in task_data or 'task_type' not in task_data:
            return False
        
        task_type = task_data['task_type']
        if task_type not in ['immediate', 'delayed', 'scheduled']:
            return False
        
        # 验证代码任务
        if 'function_code' in task_data:
            safety_check = code_checker.check_code_safety(task_data['function_code'])
            if not safety_check['safe']:
                return False
        
        return True
    
    def _save_task_record(self, task_record: Dict[str, Any]) -> None:
        """保存任务记录"""
        key = f"task:{task_record['id']}"
        self.redis_client.set(key, json.dumps(task_record))
    
    def _get_task_record(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务记录"""
        key = f"task:{task_id}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None
    
    def _execute_task(self, task_record: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        task_data = task_record['data']
        
        try:
            if 'function_code' in task_data:
                return self._execute_dynamic_code_task(task_record)
            elif 'api_url' in task_data:
                return self._execute_api_task(task_record)
            else:
                return {
                    'success': False,
                    'error': '未知的任务类型'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_dynamic_code_task(self, task_record: Dict[str, Any]) -> Dict[str, Any]:
        """执行动态代码任务"""
        task_data = task_record['data']
        
        # 使用已注册的任务名称
        result = self.celery_app.send_task(
            'dynamic.execute_code',
            kwargs={
                'code': task_data['function_code'],
                'function_name': task_data['function_name'],
                'args': task_data.get('args', []),
                'kwargs': task_data.get('kwargs', {}),
                'task_id': task_record['id'],
                'task_name': task_record['name']
            }
        )
        
        # 不要阻塞等待结果，直接返回任务ID
        return {
            'success': True,
            'task_id': result.id,
            'status': 'sent'
        }
    
    def _execute_api_task(self, task_record: Dict[str, Any]) -> Dict[str, Any]:
        """执行API任务"""
        task_data = task_record['data']
        
        # 使用已注册的任务名称
        result = self.celery_app.send_task(
            'api.execute_request',
            kwargs={
                'url': task_data['api_url'],
                'method': task_data.get('method', 'GET'),
                'headers': task_data.get('headers', {}),
                'data': task_data.get('data', {}),
                'timeout': task_data.get('timeout', 30),
                'task_id': task_record['id'],
                'task_name': task_record['name']
            }
        )
        
        # 不要阻塞等待结果，直接返回任务ID
        return {
            'success': True,
            'task_id': result.id,
            'status': 'sent'
        }
    
    def _schedule_delayed_task(self, task_record: Dict[str, Any], delay_seconds: int) -> None:
        """调度延时任务"""
        task_data = task_record['data']
        
        if 'function_code' in task_data:
            task_name = 'dynamic.execute_code'
            kwargs = {
                'code': task_data['function_code'],
                'function_name': task_data['function_name'],
                'args': task_data.get('args', []),
                'kwargs': task_data.get('kwargs', {}),
                'task_id': task_record['id'],
                'task_name': task_record['name']
            }
        elif 'api_url' in task_data:
            task_name = 'api.execute_request'
            kwargs = {
                'url': task_data['api_url'],
                'method': task_data.get('method', 'GET'),
                'headers': task_data.get('headers', {}),
                'data': task_data.get('data', {}),
                'timeout': task_data.get('timeout', 30),
                'task_id': task_record['id'],
                'task_name': task_record['name']
            }
        else:
            raise ValueError("未知的任务类型")
        
        self.celery_app.send_task(
            task_name,
            kwargs=kwargs,
            countdown=delay_seconds
        ) 