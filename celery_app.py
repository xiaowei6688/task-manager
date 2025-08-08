"""
Celery应用主文件
配置Celery和Redis连接，提供任务执行环境
"""

import redis
from celery import Celery
from config.settings import config
from utils.logger import system_logger
from typing import List, Dict

# 创建Redis客户端
redis_client = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    username=config.REDIS_USERNAME,
    password=config.REDIS_PASSWORD,
    decode_responses=True
)

# 创建Celery应用
celery_app = Celery(
    'task_manage',
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=['tasks.base_tasks', 'celery_app']
)

# Celery配置
celery_app.conf.update(
    task_serializer=config.CELERY_TASK_SERIALIZER,
    result_serializer=config.CELERY_RESULT_SERIALIZER,
    accept_content=config.CELERY_ACCEPT_CONTENT,
    timezone=config.CELERY_TIMEZONE,
    enable_utc=config.CELERY_ENABLE_UTC,
    task_routes=config.CELERY_TASK_ROUTES,
    task_always_eager=config.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=config.CELERY_TASK_EAGER_PROPAGATES,
    task_ignore_result=config.CELERY_TASK_IGNORE_RESULT,
    task_store_eager_result=config.CELERY_TASK_STORE_EAGER_RESULT,
    task_acks_late=config.CELERY_TASK_ACKS_LATE,
    task_reject_on_worker_lost=config.CELERY_TASK_REJECT_ON_WORKER_LOST,
    task_retry_policy=config.CELERY_TASK_RETRY_POLICY,
    beat_schedule=config.CELERY_BEAT_SCHEDULE,
    # 添加结果过期配置
    result_expires=config.CELERY_RESULT_EXPIRES,
    task_result_expires=config.CELERY_TASK_RESULT_EXPIRES,
    result_persistent=config.CELERY_RESULT_PERSISTENT
)

# 注册任务
from tasks.base_tasks import DynamicCodeTask, APITask, SystemTask
from datetime import datetime

# 注册动态代码任务
@celery_app.task(name='dynamic.execute_code', bind=True)
def dynamic_task(self, code: str, function_name: str, args: list = None, kwargs: dict = None, task_id: str = None, task_name: str = None):
    """动态代码执行任务"""
    # 获取任务ID和名称
    task_id = task_id or self.request.id
    task_name = task_name or "dynamic.execute_code"
    
    # 创建任务实例并执行
    task_instance = DynamicCodeTask()
    task_instance.task_id = task_id
    task_instance.task_name = task_name
    task_instance.start_time = datetime.now()
    
    # 更新任务状态为运行中
    task_instance._update_task_status('running')
    
    try:
        result = task_instance.run(code, function_name, args, kwargs, task_id, task_name)
        # 更新任务状态为完成
        task_instance._update_task_status('completed', result)
        return result
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'execution_time': (datetime.now() - task_instance.start_time).total_seconds()
        }
        # 更新任务状态为失败
        task_instance._update_task_status('failed', error_result)
        raise

@celery_app.task(name='api.execute_request', bind=True)
def api_task(self, url: str, method: str = 'GET', headers: dict = None, data: dict = None, timeout: int = 30, task_id: str = None, task_name: str = None):
    """API请求任务"""
    # 获取任务ID和名称
    task_id = task_id or self.request.id
    task_name = task_name or "api.execute_request"
    
    # 创建任务实例并执行
    task_instance = APITask()
    task_instance.task_id = task_id
    task_instance.task_name = task_name
    task_instance.start_time = datetime.now()
    
    # 更新任务状态为运行中
    task_instance._update_task_status('running')
    
    try:
        result = task_instance.run(url, method, headers, data, 30, task_id, task_name)
        # 更新任务状态为完成
        task_instance._update_task_status('completed', result)
        return result
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'execution_time': (datetime.now() - task_instance.start_time).total_seconds()
        }
        # 更新任务状态为失败
        task_instance._update_task_status('failed', error_result)
        raise

@celery_app.task(name='system.execute', bind=True)
def system_task(self, operation: str, params: dict = None, task_id: str = None, task_name: str = None):
    """系统任务"""
    # 获取任务ID和名称
    task_id = task_id or self.request.id
    task_name = task_name or "system.execute"
    
    # 创建任务实例并执行
    task_instance = SystemTask()
    task_instance.task_id = task_id
    task_instance.task_name = task_name
    task_instance.start_time = datetime.now()
    
    # 更新任务状态为运行中
    task_instance._update_task_status('running')
    
    try:
        result = task_instance.run(operation, params, task_id, task_name)
        # 更新任务状态为完成
        task_instance._update_task_status('completed', result)
        return result
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'execution_time': (datetime.now() - task_instance.start_time).total_seconds()
        }
        # 更新任务状态为失败
        task_instance._update_task_status('failed', error_result)
        raise

# 系统健康检查任务
@celery_app.task(name='system.health_check')
def health_check():
    """系统健康检查任务"""
    try:
        # 检查Redis连接
        redis_client.ping()
        
        # 检查Celery状态
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        return {
            "success": True,
            "redis_status": "connected",
            "celery_status": "running",
            "active_tasks": len(active_tasks) if active_tasks else 0
        }
    except Exception as e:
        system_logger.error("健康检查失败", error=e)
        return {
            "success": False,
            "error": str(e)
        }

# 清理过期任务
@celery_app.task(name='system.cleanup_expired_tasks')
def cleanup_expired_tasks():
    """清理过期任务记录（Celery结果会自动过期）"""
    try:
        import json
        import time
        
        current_time = time.time()
        expired_time = current_time - config.TASK_RESULT_EXPIRY
        
        # 只清理过期的任务记录
        keys_to_delete = []
        for key in redis_client.scan_iter(match="task:*"):
            try:
                task_data = redis_client.get(key)
                if task_data:
                    task_info = json.loads(task_data)
                    if task_info.get("created_at", 0) < expired_time:
                        keys_to_delete.append(key)
            except:
                continue
        
        # 批量删除过期的任务记录
        if keys_to_delete:
            redis_client.delete(*keys_to_delete)
        
        system_logger.info(f"清理了 {len(keys_to_delete)} 个过期任务记录")
        
        return {
            "success": True,
            "deleted_task_keys": len(keys_to_delete)
        }
        
    except Exception as e:
        system_logger.error("清理过期任务失败", error=e)
        return {
            "success": False,
            "error": str(e)
        }

# 动态调度器：扫描并派发定时任务
@celery_app.task(name='system.dispatch_periodic_tasks')
def dispatch_periodic_tasks():
    """扫描 Redis 的 periodic_task:*，到点派发对应任务，并更新 next_execution"""
    try:
        import json
        import time
        from datetime import datetime
        from croniter import croniter

        dispatched = 0
        now = datetime.now()

        for key in redis_client.scan_iter(match="periodic_task:*"):
            try:
                periodic_data_raw = redis_client.get(key)
                if not periodic_data_raw:
                    continue
                periodic = json.loads(periodic_data_raw)
                task_id = periodic.get("task_id")
                cron_expr = periodic.get("cron_expression")
                celery_task_name = periodic.get("celery_task_name")
                next_exec_ts = periodic.get("next_execution")

                if not task_id or not cron_expr or not celery_task_name:
                    continue

                # 拉取原始任务数据
                task_raw = redis_client.get(f"task:{task_id}")
                if not task_raw:
                    continue
                task_record = json.loads(task_raw)
                task_data = task_record.get("data", {})

                # 计算当前应执行与否
                if next_exec_ts is None:
                    cron = croniter(cron_expr, now)
                    next_dt = cron.get_next(datetime)
                    periodic["next_execution"] = next_dt.timestamp()
                    redis_client.set(key, json.dumps(periodic))
                    continue

                # 到点派发（容忍1分钟窗口）
                if now.timestamp() + 1 >= float(next_exec_ts):
                    # 构造kwargs
                    if "function_code" in task_data:
                        kwargs = {
                            'code': task_data['function_code'],
                            'function_name': task_data['function_name'],
                            'args': task_data.get('args', []),
                            'kwargs': task_data.get('kwargs', {}),
                            'task_id': task_record['id'],
                            'task_name': task_record['name']
                        }
                    elif "api_url" in task_data:
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
                        continue

                    celery_app.send_task(celery_task_name, kwargs=kwargs)
                    dispatched += 1

                    # 回滚下一次时间
                    cron = croniter(cron_expr, now)
                    next_dt = cron.get_next(datetime)
                    periodic["last_run_at"] = now.timestamp()
                    periodic["next_execution"] = next_dt.timestamp()
                    redis_client.set(key, json.dumps(periodic))

            except Exception as inner_e:
                system_logger.error("调度单个定时任务失败", error=inner_e)
                continue

        return {"success": True, "dispatched": dispatched, "timestamp": now.isoformat()}

    except Exception as e:
        system_logger.error("调度定时任务失败", error=e)
        return {"success": False, "error": str(e)}

# 创建任务管理器实例
from tasks.task_manager import TaskManager
task_manager = TaskManager(celery_app, redis_client)

# 创建API应用
from api.routes import create_app
api_app = create_app(celery_app, redis_client, task_manager)

if __name__ == '__main__':
    # 启动API服务
    api_app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.API_DEBUG
    )
