"""
任务管理器
提供任务的增删改查和状态管理功能
"""
from datetime import timedelta
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
        
        # 定时任务
        elif task_type == 'scheduled':
            cron_expression = task_data.get('cron_expression')
            if not cron_expression:
                return {
                    'success': False,
                    'error': '定时任务必须指定cron_expression',
                    'task_id': task_id
                }
            
            result = self._schedule_periodic_task(task_record, cron_expression)
            return {
                'success': True,
                'task_id': task_id,
                'task_name': task_name,
                'cron_expression': cron_expression,
                'next_execution': result.get('next_execution')
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
        
        # 如果是定时任务，需要从Celery Beat中删除
        if task_record.get('type') == 'scheduled':
            self._remove_periodic_task(task_id)
        
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
        
        # 如果是定时任务，需要从Celery Beat中删除
        if task_record.get('type') == 'scheduled':
            self._remove_periodic_task(task_id)
        
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
    
    def _schedule_periodic_task(self, task_record: Dict[str, Any], cron_expression: str) -> Dict[str, Any]:
        """调度定时任务"""
        task_data = task_record['data']
        task_id = task_record['id']
        
        # 确定任务类型和参数
        if 'function_code' in task_data:
            task_name = 'dynamic.execute_code'
            kwargs = {
                'code': task_data['function_code'],
                'function_name': task_data['function_name'],
                'args': task_data.get('args', []),
                'kwargs': task_data.get('kwargs', {}),
                'task_id': task_id,
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
                'task_id': task_id,
                'task_name': task_record['name']
            }
        else:
            raise ValueError("未知的任务类型")
        
        # 解析Cron表达式并添加到Celery Beat调度
        try:
            from celery.schedules import crontab
            from datetime import datetime, timedelta
            
            system_logger.info(f"开始创建定时任务: {task_id}, cron: {cron_expression}")
            
            # 解析cron表达式 (格式: 分 时 日 月 周)
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError("Cron表达式格式错误，应为5个字段：分 时 日 月 周")
            
            minute, hour, day_of_month, month_of_year, day_of_week = parts
            
            system_logger.info(f"Cron解析结果: 分={minute}, 时={hour}, 日={day_of_month}, 月={month_of_year}, 周={day_of_week}")
            
            # 创建crontab对象
            schedule = crontab(
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
                day_of_week=day_of_week
            )
            
            system_logger.info(f"Crontab对象创建成功")
            
            # 计算下次执行时间 - 使用croniter
            now = datetime.now()
            system_logger.info(f"当前时间: {now}")
            
            try:
                from croniter import croniter
                cron = croniter(cron_expression, now)
                next_execution = cron.get_next(datetime)
                next_execution_timestamp = next_execution.timestamp()
                system_logger.info(f"使用croniter计算下次执行时间: {next_execution}, 时间戳: {next_execution_timestamp}")
            except ImportError:
                # 如果没有croniter，使用简单的计算方法
                system_logger.info("croniter未安装，使用简单计算方法")
                next_execution = self._calculate_next_execution(cron_expression, now)
                next_execution_timestamp = next_execution.timestamp()
                system_logger.info(f"简单计算下次执行时间: {next_execution}, 时间戳: {next_execution_timestamp}")
            
            # 添加定时任务到Celery Beat
            schedule_key = f'periodic_task_{task_id}'
            self.celery_app.conf.beat_schedule[schedule_key] = {
                'task': task_name,
                'schedule': schedule,
                'kwargs': kwargs,
                'args': []
            }
            
            system_logger.info(f"定时任务已添加到Celery Beat: {schedule_key}")
            
            # 保存定时任务信息到Redis
            periodic_task_info = {
                'task_id': task_id,
                'task_name': task_record['name'],
                'cron_expression': cron_expression,
                'celery_task_name': task_name,
                'created_at': time.time(),
                'next_execution': next_execution_timestamp
            }
            
            redis_key = f"periodic_task:{task_id}"
            self.redis_client.set(redis_key, json.dumps(periodic_task_info))
            
            system_logger.info(f"定时任务信息已保存到Redis: {redis_key}")
            system_logger.info(f"定时任务已创建: {task_id}, cron: {cron_expression}, 下次执行: {next_execution}")
            
            return {
                'success': True,
                'task_id': task_id,
                'cron_expression': cron_expression,
                'next_execution': next_execution_timestamp
            }
            
        except Exception as e:
            system_logger.error(f"创建定时任务失败: {str(e)}")
            import traceback
            system_logger.error(f"详细错误信息: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'创建定时任务失败: {str(e)}'
            }
    
    def _calculate_next_execution(self, cron_expression: str, now: datetime) -> datetime:
        """简单计算下次执行时间"""
        try:
            from croniter import croniter
            cron = croniter(cron_expression, now)
            return cron.get_next(datetime)
        except ImportError:
            # 如果没有croniter，使用简单的逻辑
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError("Cron表达式格式错误")
            
            minute, hour, day_of_month, month_of_year, day_of_week = parts
            
            # 简单的计算逻辑 - 对于 */2 * * * * 这样的表达式
            if minute.startswith('*/'):
                interval = int(minute[2:])
                current_minute = now.minute
                next_minute = ((current_minute // interval) + 1) * interval
                if next_minute >= 60:
                    next_minute = 0
                    next_hour = now.hour + 1
                    if next_hour >= 24:
                        next_hour = 0
                        next_day = now.day + 1
                    else:
                        next_day = now.day
                else:
                    next_hour = now.hour
                    next_day = now.day
                
                next_execution = now.replace(
                    minute=next_minute,
                    hour=next_hour,
                    day=next_day,
                    second=0,
                    microsecond=0
                )
                
                # 如果计算出的时间已经过去，加一个间隔
                if next_execution <= now:
                    next_execution += timedelta(minutes=interval)
                
                return next_execution
            else:
                # 默认返回当前时间加2分钟
                return now + timedelta(minutes=2)
    
    def _remove_periodic_task(self, task_id: str) -> None:
        """删除定时任务"""
        try:
            # 从Celery Beat调度中删除
            schedule_key = f'periodic_task_{task_id}'
            if schedule_key in self.celery_app.conf.beat_schedule:
                del self.celery_app.conf.beat_schedule[schedule_key]
            
            # 从Redis中删除定时任务信息
            self.redis_client.delete(f"periodic_task:{task_id}")
            
            system_logger.info(f"定时任务已删除: {task_id}")
            
        except Exception as e:
            system_logger.error(f"删除定时任务失败: {str(e)}")
    
    def get_periodic_tasks(self) -> List[Dict[str, Any]]:
        """获取所有定时任务"""
        periodic_tasks = []
        pattern = "periodic_task:*"
        
        for key in self.redis_client.scan_iter(match=pattern, count=100):
            task_data = self.redis_client.get(key)
            if task_data:
                task_info = json.loads(task_data)
                
                # 如果缺少下次执行时间，重新计算
                if 'next_execution' not in task_info or task_info['next_execution'] is None:
                    try:
                        from croniter import croniter
                        from datetime import datetime
                        
                        # 解析cron表达式
                        cron_expression = task_info['cron_expression']
                        now = datetime.now()
                        
                        # 使用croniter计算下次执行时间
                        cron = croniter(cron_expression, now)
                        next_execution = cron.get_next(datetime)
                        task_info['next_execution'] = next_execution.timestamp()
                        
                        # 更新Redis中的信息
                        self.redis_client.set(key, json.dumps(task_info))
                        
                        system_logger.info(f"重新计算下次执行时间: {task_info['task_id']}, 下次执行: {next_execution}")
                        
                    except Exception as e:
                        system_logger.error(f"计算下次执行时间失败: {str(e)}")
                        task_info['next_execution'] = None
                
                periodic_tasks.append(task_info)
        
        return periodic_tasks 