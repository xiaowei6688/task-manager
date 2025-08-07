#!/usr/bin/env python3
"""
任务管理系统启动脚本
"""

import os
import sys
import time
import signal
import subprocess
from threading import Thread
from config.settings import config
from utils.logger import system_logger

class TaskManageSystem:
    """任务管理系统启动器"""
    
    def __init__(self):
        self.processes = []
        self.running = True
    
    def start_redis(self):
        """启动Redis服务"""
        try:
            # 检查Redis是否已运行
            import redis
            # 创建Redis客户端
            redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                username=config.REDIS_USERNAME,  # 添加用户名
                password=config.REDIS_PASSWORD,
                decode_responses=True
            )
            redis_client.ping()
            system_logger.info("Redis已运行")
            return True
        except:
            system_logger.warning("Redis未运行,请先启动Redis服务")
            return False
    
    def start_celery_worker(self):
        """启动Celery Worker"""
        cmd = ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
        process = subprocess.Popen(cmd)
        self.processes.append(("Celery Worker", process))
        system_logger.info("Celery Worker已启动")
    
    def start_celery_beat(self):
        """启动Celery Beat"""
        cmd = ["celery", "-A", "celery_app", "beat", "--loglevel=info"]
        process = subprocess.Popen(cmd)
        self.processes.append(("Celery Beat", process))
        system_logger.info("Celery Beat已启动")
    
    def start_api_server(self):
        """启动API服务器"""
        from celery_app import api_app
        api_app.run(
            host=config.API_HOST,
            port=config.API_PORT,
            debug=config.API_DEBUG
        )
    
    def start_all_services(self):
        """启动所有服务"""
        system_logger.info("正在启动任务管理系统...")
        
        # 检查Redis
        if not self.start_redis():
            system_logger.error("Redis服务不可用，请先启动Redis")
            return False
        
        # 启动Celery Worker
        worker_thread = Thread(target=self.start_celery_worker)
        worker_thread.daemon = True
        worker_thread.start()
        
        # 等待Worker启动
        time.sleep(2)
        
        # 启动Celery Beat
        beat_thread = Thread(target=self.start_celery_beat)
        beat_thread.daemon = True
        beat_thread.start()
        
        # 等待Beat启动
        time.sleep(2)
        
        # 启动API服务器
        system_logger.info("启动API服务器...")
        self.start_api_server()
        
        return True
    
    def stop_all_services(self):
        """停止所有服务"""
        system_logger.info("正在停止任务管理系统...")
        
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                system_logger.info(f"{name}已停止")
            except subprocess.TimeoutExpired:
                process.kill()
                system_logger.warning(f"{name}强制停止")
            except Exception as e:
                system_logger.error(f"停止{name}时出错: {e}")
        
        self.running = False
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        system_logger.info("收到停止信号，正在关闭服务...")
        self.stop_all_services()
        sys.exit(0)
    
    def run(self):
        """运行系统"""
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            if self.start_all_services():
                system_logger.info("任务管理系统启动成功")
                system_logger.info(f"API服务地址: http://{config.API_HOST}:{config.API_PORT}")
                system_logger.info("按 Ctrl+C 停止服务")
                
                # 保持运行
                while self.running:
                    time.sleep(1)
            else:
                system_logger.error("任务管理系统启动失败")
                return False
                
        except KeyboardInterrupt:
            system_logger.info("收到键盘中断信号")
        except Exception as e:
            system_logger.error(f"系统运行出错: {e}")
        finally:
            self.stop_all_services()
        
        return True

def main():
    """主函数"""
    print("=" * 50)
    print("任务管理系统 (Task Management System)")
    print("=" * 50)
    print(f"版本: {config.APP_VERSION}")
    print(f"环境: {os.getenv('FLASK_ENV', 'development')}")
    print(f"Redis: {config.REDIS_HOST}:{config.REDIS_PORT}")
    print(f"API: http://{config.API_HOST}:{config.API_PORT}")
    print("=" * 50)
    
    # 创建并运行系统
    system = TaskManageSystem()
    success = system.run()
    
    if success:
        print("系统已正常关闭")
    else:
        print("系统启动失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 