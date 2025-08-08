"""
API路由
定义所有的HTTP接口
"""

import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from config.settings import config
from utils.logger import SystemLogger
api_logger = SystemLogger("api")

def create_app(celery_app, redis_client, task_manager):
    """创建Flask应用"""
    app = Flask(__name__)
    CORS(app)
    
    # 存储应用组件
    app.celery_app = celery_app
    app.redis_client = redis_client
    app.task_manager = task_manager
    app.start_time = time.time()
    
    # 注册路由
    register_routes(app)
    
    return app

def register_routes(app):
    """注册路由"""
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """健康检查"""
        try:
            # 检查Redis连接
            app.redis_client.ping()
            redis_status = "connected"
        except Exception as e:
            redis_status = f"error: {str(e)}"
        
        # 检查Celery状态
        try:
            inspect = app.celery_app.control.inspect()
            active_tasks = inspect.active()
            celery_status = "running"
            active_task_count = len(active_tasks) if active_tasks else 0
        except Exception as e:
            celery_status = f"error: {str(e)}"
            active_task_count = 0
        
        response = {
            "status": "healthy" if redis_status == "connected" and celery_status == "running" else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "version": config.APP_VERSION,
            "uptime": time.time() - app.start_time,
            "redis_status": redis_status,
            "celery_status": celery_status,
            "active_tasks": active_task_count
        }
        
        return jsonify(response), 200
    
    @app.route('/api/tasks', methods=['POST'])
    def create_task():
        """创建任务"""
        try:
            request_data = request.get_json()
            if not request_data:
                return jsonify({
                    "success": False,
                    "error": "请求数据不能为空"
                }), 400
            
            # 创建任务
            result = app.task_manager.create_task(request_data)
            
            return jsonify(result), 201 if result['success'] else 400
                
        except Exception as e:
            api_logger.error("创建任务失败", error=e)
            return jsonify({
                "success": False,
                "error": f"服务器内部错误: {str(e)}"
            }), 500
    
    @app.route('/api/tasks', methods=['GET'])
    def get_tasks():
        """获取任务列表"""
        try:
            limit = request.args.get('limit', 100, type=int)
            task_type = request.args.get('type')  # 新增：按类型过滤
            
            if task_type:
                # 按类型获取任务
                tasks = app.task_manager.get_tasks_by_type(task_type, limit=limit)
            else:
                # 获取所有任务
                tasks = app.task_manager.get_all_tasks(limit=limit)
            
            return jsonify({
                "success": True,
                "tasks": tasks,
                "total": len(tasks),
                "type": task_type if task_type else "all"
            }), 200
            
        except Exception as e:
            api_logger.error("获取任务列表失败", error=e)
            return jsonify({
                "success": False,
                "error": f"服务器内部错误: {str(e)}"
            }), 500
    
    @app.route('/api/tasks/<task_id>', methods=['GET'])
    def get_task(task_id):
        """获取任务详情"""
        try:
            task = app.task_manager.get_task(task_id)
            
            if not task:
                return jsonify({
                    "success": False,
                    "error": f"任务不存在: {task_id}"
                }), 404
            
            return jsonify({
                "success": True,
                "task": task
            }), 200
            
        except Exception as e:
            api_logger.error("获取任务详情失败", error=e)
            return jsonify({
                "success": False,
                "error": f"服务器内部错误: {str(e)}"
            }), 500
    
    @app.route('/api/tasks/<task_id>', methods=['DELETE'])
    def delete_task(task_id):
        """删除任务"""
        try:
            result = app.task_manager.delete_task(task_id)
            return jsonify(result), 200 if result['success'] else 400
                
        except Exception as e:
            api_logger.error("删除任务失败", error=e)
            return jsonify({
                "success": False,
                "error": f"服务器内部错误: {str(e)}"
            }), 500
    
    @app.route('/api/tasks/<task_id>/stop', methods=['POST'])
    def stop_task(task_id):
        """停止任务"""
        try:
            result = app.task_manager.stop_task(task_id)
            return jsonify(result), 200 if result['success'] else 400
                
        except Exception as e:
            api_logger.error("停止任务失败", error=e)
            return jsonify({
                "success": False,
                "error": f"服务器内部错误: {str(e)}"
            }), 500
    
    @app.route('/api/scheduled-tasks', methods=['POST'])
    def create_scheduled_task():
        """创建定时任务"""
        try:
            request_data = request.get_json()
            if not request_data:
                return jsonify({
                    "success": False,
                    "error": "请求数据不能为空"
                }), 400
            
            # 确保任务类型为scheduled
            request_data['task_type'] = 'scheduled'
            
            # 验证cron表达式
            if 'cron_expression' not in request_data:
                return jsonify({
                    "success": False,
                    "error": "定时任务必须指定cron_expression"
                }), 400
            
            # 创建定时任务
            result = app.task_manager.create_task(request_data)
            
            # 如果创建成功，格式化下次执行时间
            if result.get('success') and result.get('next_execution'):
                from datetime import datetime
                next_execution_time = datetime.fromtimestamp(result['next_execution'])
                result['next_execution_formatted'] = next_execution_time.strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify(result), 201 if result['success'] else 400
                
        except Exception as e:
            api_logger.error("创建定时任务失败", error=e)
            return jsonify({
                "success": False,
                "error": f"服务器内部错误: {str(e)}"
            }), 500
    
    @app.route('/api/scheduled-tasks', methods=['GET'])
    def get_scheduled_tasks():
        """获取定时任务列表"""
        try:
            # 获取所有定时任务
            periodic_tasks = app.task_manager.get_periodic_tasks()
            
            # 格式化下次执行时间
            from datetime import datetime
            for task in periodic_tasks:
                if task.get('next_execution'):
                    next_execution_time = datetime.fromtimestamp(task['next_execution'])
                    task['next_execution_formatted'] = next_execution_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    task['next_execution_formatted'] = None
            
            return jsonify({
                "success": True,
                "scheduled_tasks": periodic_tasks,
                "total": len(periodic_tasks)
            }), 200
            
        except Exception as e:
            api_logger.error("获取定时任务列表失败", error=e)
            return jsonify({
                "success": False,
                "error": f"服务器内部错误: {str(e)}"
            }), 500
    
    @app.route('/api/tasks/stats', methods=['GET'])
    def get_task_stats():
        """获取任务统计信息"""
        try:
            # 获取所有任务
            all_tasks = app.task_manager.get_all_tasks(limit=1000)
            
            # 统计各状态的任务数量
            stats = {
                'total': len(all_tasks),
                'pending': 0,
                'running': 0,
                'completed': 0,
                'failed': 0,
                'stopped': 0,
                'by_type': {
                    'immediate': 0,
                    'delayed': 0,
                    'scheduled': 0
                }
            }
            
            for task in all_tasks:
                status = task.get('status', 'unknown')
                task_type = task.get('type', 'unknown')
                
                if status in stats:
                    stats[status] += 1
                
                if task_type in stats['by_type']:
                    stats['by_type'][task_type] += 1
            
            return jsonify({
                "success": True,
                "stats": stats
            }), 200
            
        except Exception as e:
            api_logger.error("获取任务统计失败", error=e)
            return jsonify({
                "success": False,
                "error": f"服务器内部错误: {str(e)}"
            }), 500 