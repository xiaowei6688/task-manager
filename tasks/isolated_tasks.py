"""
隔离环境任务模块
提供Docker容器隔离的代码执行功能
"""

import docker
import tempfile
import os
import json
import traceback
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from celery import Task
from celery.utils.log import get_task_logger
from config.settings import config
from utils.logger import TaskLogger, SystemLogger
import uuid

logger = get_task_logger(__name__)
system_logger = SystemLogger("isolated_tasks")

class IsolatedCodeTask(Task):
    """隔离环境代码执行任务"""
    
    abstract = True
    
    def __init__(self):
        self.docker_client = None
        self.base_image = "swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim"
        self.fallback_images = [
            "swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.9-slim",
            "swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.10-slim", 
        ]
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
        self.task_logger.info(f"开始执行隔离任务: {self.task_name}")
        
        # 初始化Docker客户端
        try:
            self.docker_client = docker.from_env()
            self.task_logger.info("Docker客户端初始化成功")
        except Exception as e:
            self.task_logger.error(f"Docker客户端初始化失败: {str(e)}")
            raise
        
        # 更新任务状态为运行中
        self._update_task_status('running')
        
        try:
            result = super().__call__(*args, **kwargs)
            self.end_time = datetime.now()
            execution_time = (self.end_time - self.start_time).total_seconds()
            
            self.task_logger.info(
                f"隔离任务执行完成",
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
                f"隔离任务执行失败: {str(e)}",
                error=traceback.format_exc(),
                execution_time=execution_time
            )
            
            # 更新任务状态为失败
            self._update_task_status('failed', error_result)
            
            raise
    
    def run(self, code: str, function_name: str, requirements: List[str] = None, 
            args: List = None, kwargs: Dict = None, task_id: str = None, 
            task_name: str = None):
        """
        在隔离环境中执行代码
        
        Args:
            code: 要执行的代码
            function_name: 要调用的函数名
            requirements: 依赖包列表，如 ["requests==2.28.0", "pandas==1.5.0"]
            args: 函数参数
            kwargs: 函数关键字参数
            task_id: 任务ID
            task_name: 任务名称
        """
        args = args or []
        kwargs = kwargs or {}
        requirements = requirements or []
        
        # 确保task_logger被初始化
        if self.task_logger is None:
            self.task_id = task_id or str(uuid.uuid4())
            self.task_name = task_name or "isolated.execute_code"
            self.task_logger = TaskLogger(self.task_id, self.task_name)
        
        # 确保docker_client被初始化
        if self.docker_client is None:
            try:
                self.docker_client = docker.from_env()
                self.task_logger.info("Docker客户端初始化成功")
            except Exception as e:
                self.task_logger.error(f"Docker客户端初始化失败: {str(e)}")
                error_result = {
                    'success': False,
                    'error': f'Docker客户端初始化失败: {str(e)}',
                    'traceback': traceback.format_exc()
                }
                # 手动更新任务状态为失败
                self._update_task_status('failed', error_result)
                raise Exception(f'Docker客户端初始化失败: {str(e)}')
        
        self.task_logger.info(f"开始隔离执行，依赖包: {requirements}")
        
        # 确保任务状态为running
        self._update_task_status('running')
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            self.task_logger.info(f"创建临时目录: {temp_dir}")
            
            # 创建requirements.txt
            if requirements:
                # 处理依赖包版本兼容性
                processed_requirements = self._process_requirements(requirements)
                requirements_file = os.path.join(temp_dir, "requirements.txt")
                with open(requirements_file, "w") as f:
                    for req in processed_requirements:
                        f.write(f"{req}\n")
                self.task_logger.info(f"创建requirements.txt: {processed_requirements}")
            
            # 创建执行脚本
            script_content = self._create_execution_script(code, function_name, args, kwargs)
            script_file = os.path.join(temp_dir, "execute.py")
            with open(script_file, "w") as f:
                f.write(script_content)
            self.task_logger.info("创建执行脚本完成")
            
            # 构建Docker命令
            cmd = self._build_docker_command(requirements)
            self.task_logger.info(f"Docker命令: {cmd}")
            
            # 运行容器
            result = self._run_container(temp_dir, cmd)
            
            # 检查执行结果
            if not result.get('success', False):
                error_msg = result.get('error', '未知错误')
                self.task_logger.error(f"容器执行失败: {error_msg}")
                # 手动更新任务状态为失败
                self._update_task_status('failed', result)
                raise Exception(f"容器执行失败: {error_msg}")
            
            # 手动更新任务状态为完成
            self._update_task_status('completed', result)
            return result
    
    def _create_execution_script(self, code: str, function_name: str, 
                                args: list, kwargs: dict) -> str:
        """创建执行脚本"""
        # 转义参数，避免语法错误
        args_str = repr(args) if args else '[]'
        kwargs_str = repr(kwargs) if kwargs else '{}'
        
        script = f"""
import sys
import json
import traceback
from datetime import datetime

# 用户代码
{code}

# 执行函数
try:
    if '{function_name}' in locals():
        func = locals()['{function_name}']
        result = func(*{args_str}, **{kwargs_str})
        
        output = {{
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }}
    else:
        output = {{
            'success': False,
            'error': f"函数 '{{function_name}}' 未找到",
            'timestamp': datetime.now().isoformat()
        }}
except Exception as e:
    output = {{
        'success': False,
        'error': str(e),
        'traceback': traceback.format_exc(),
        'timestamp': datetime.now().isoformat()
    }}

# 输出结果
print(json.dumps(output, ensure_ascii=False))
"""
        return script
    
    def _build_docker_command(self, requirements: list) -> list:
        """构建Docker命令"""
        if requirements:
            # 使用国内镜像源加速下载，并确保版本兼容性
            pip_cmd = f"pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ --upgrade pip && pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt && python execute.py"
            return [
                "sh", "-c",
                pip_cmd
            ]
        else:
            return ["python", "execute.py"]
    
    def _run_container(self, temp_dir: str, cmd: list) -> Dict[str, Any]:
        """运行Docker容器"""
        try:
            self.task_logger.info("开始运行Docker容器")
            
            # 检查并准备镜像
            image_to_use = self._ensure_image_available()
            if not image_to_use:
                return {
                    'success': False,
                    'error': '无法获取可用的Docker镜像',
                    'traceback': '所有备选镜像都无法拉取'
                }
            
            self.task_logger.info(f"使用镜像: {image_to_use}")
            
            # 运行容器
            container = self.docker_client.containers.run(
                image=image_to_use,
                command=cmd,
                volumes={temp_dir: {'bind': '/app', 'mode': 'ro'}},
                working_dir='/app',
                detach=True,
                mem_limit='512m',  # 内存限制
                cpu_period=100000,
                cpu_quota=50000,   # CPU限制50%
                network_disabled=False,  # 启用网络以安装依赖包
                remove=True,  # 自动删除容器
                environment={
                    'PYTHONUNBUFFERED': '1',  # 禁用Python输出缓冲
                    'PYTHONDONTWRITEBYTECODE': '1'  # 不生成.pyc文件
                }
            )
            
            self.task_logger.info(f"容器启动成功，ID: {container.id}")
            
            # 等待执行完成
            logs = container.logs().decode('utf-8').strip()
            exit_code = container.wait()['StatusCode']
            
            self.task_logger.info(f"容器执行完成，退出码: {exit_code}")
            self.task_logger.info(f"容器日志: {logs}")
            
            # 解析结果
            if exit_code == 0:
                # 容器成功退出，尝试解析JSON结果
                try:
                    result = json.loads(logs)
                    result['exit_code'] = exit_code
                    result['container_id'] = container.id
                    return result
                except json.JSONDecodeError:
                    # JSON解析失败，但容器成功退出，可能是日志包含其他信息
                    # 尝试从日志中提取JSON部分
                    lines = logs.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and line.startswith('{') and line.endswith('}'):
                            try:
                                result = json.loads(line)
                                result['exit_code'] = exit_code
                                result['container_id'] = container.id
                                return result
                            except json.JSONDecodeError:
                                continue
                    
                    # 如果无法解析JSON，返回成功但包含原始日志
                    return {
                        'success': True,
                        'result': logs,
                        'exit_code': exit_code,
                        'container_id': container.id,
                        'note': '无法解析JSON,返回原始日志'
                    }
            else:
                # 容器失败退出
                return {
                    'success': False,
                    'error': f'执行失败，退出码: {exit_code}',
                    'logs': logs,
                    'exit_code': exit_code,
                    'container_id': container.id
                }
                
        except Exception as e:
            self.task_logger.error(f"容器执行失败: {str(e)}")
            return {
                'success': False,
                'error': f'容器执行失败: {str(e)}',
                'traceback': traceback.format_exc()
            }
    
    def _ensure_image_available(self) -> str:
        """确保有可用的Docker镜像"""
        import time
        
        # 首先检查基础镜像
        try:
            self.task_logger.info(f"检查基础镜像: {self.base_image}")
            
            # 检查镜像是否已存在
            try:
                self.docker_client.images.get(self.base_image)
                self.task_logger.info(f"基础镜像已存在: {self.base_image}")
                return self.base_image
            except:
                pass
            
            # 尝试拉取基础镜像
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.task_logger.info(f"尝试拉取基础镜像: {self.base_image} (第{attempt + 1}次)")
                    self.docker_client.images.pull(self.base_image, timeout=30)
                    self.task_logger.info(f"基础镜像拉取成功: {self.base_image}")
                    return self.base_image
                except Exception as e:
                    self.task_logger.warning(f"第{attempt + 1}次拉取基础镜像失败: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        self.task_logger.error(f"基础镜像 {self.base_image} 拉取失败，尝试备选镜像")
        except Exception as e:
            self.task_logger.warning(f"基础镜像 {self.base_image} 不可用: {str(e)}")
        
        # 然后检查备选镜像
        for image in self.fallback_images:
            try:
                self.task_logger.info(f"检查备选镜像: {image}")
                
                # 检查镜像是否已存在
                try:
                    self.docker_client.images.get(image)
                    self.task_logger.info(f"备选镜像已存在: {image}")
                    return image
                except:
                    pass
                
                # 尝试拉取镜像，添加重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self.task_logger.info(f"尝试拉取备选镜像: {image} (第{attempt + 1}次)")
                        
                        # 设置较短的超时时间
                        self.docker_client.images.pull(image, timeout=30)
                        self.task_logger.info(f"备选镜像拉取成功: {image}")
                        return image
                        
                    except Exception as e:
                        self.task_logger.warning(f"第{attempt + 1}次拉取备选镜像失败: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(2)  # 等待2秒后重试
                        else:
                            self.task_logger.error(f"备选镜像 {image} 拉取失败，尝试下一个镜像")
                
            except Exception as e:
                self.task_logger.warning(f"备选镜像 {image} 不可用: {str(e)}")
                continue
        
        # 如果所有镜像都失败，尝试使用系统Python
        self.task_logger.warning("所有Docker镜像都不可用，尝试使用系统Python")
        return self._create_system_python_container()
    
    def _create_system_python_container(self) -> str:
        """创建使用系统Python的容器配置"""
        try:
            # 使用配置的镜像作为备选
            for image in self.fallback_images:
                try:
                    self.docker_client.images.get(image)
                    self.task_logger.info(f"找到可用镜像: {image}")
                    return image
                except:
                    continue
            
            # 如果配置的镜像都不可用，尝试基础镜像
            try:
                self.docker_client.images.get(self.base_image)
                return self.base_image
            except:
                pass
            
            return None
            
        except Exception as e:
            self.task_logger.error(f"创建系统容器失败: {str(e)}")
            return None
    
    def _update_task_status(self, status: str, result: Dict[str, Any] = None) -> None:
        """更新任务状态"""
        try:
            self.task_logger.info(f"更新任务状态: {status}")
            
            # 导入任务管理器
            from tasks.task_manager import TaskManager
            from celery_app import redis_client
            
            # 创建任务管理器实例
            task_manager = TaskManager(self.app, redis_client)
            
            # 更新任务状态
            task_manager.update_task_status(self.task_id, status, result)
            
            self.task_logger.info(f"任务状态更新成功: {status}")
            
        except Exception as e:
            self.task_logger.error(f"更新任务状态失败: {str(e)}")
            system_logger.error(f"更新任务状态失败: {str(e)}")

    def _process_requirements(self, requirements: List[str]) -> List[str]:
        """处理依赖包版本兼容性"""
        processed_requirements = []
        
        for req in requirements:
            # 处理pandas和numpy的版本兼容性
            if req.startswith('pandas==1.5.0'):
                # 使用更新的pandas版本，避免numpy兼容性问题
                processed_requirements.append('pandas>=2.0.0')
            elif req.startswith('numpy==1.24.0'):
                # 使用更新的numpy版本
                processed_requirements.append('numpy>=1.24.0')
            elif req.startswith('pandas'):
                # 如果没有指定版本，使用最新稳定版
                if '==' not in req:
                    processed_requirements.append('pandas>=2.0.0')
                else:
                    processed_requirements.append(req)
            elif req.startswith('numpy'):
                # 如果没有指定版本，使用最新稳定版
                if '==' not in req:
                    processed_requirements.append('numpy>=1.24.0')
                else:
                    processed_requirements.append(req)
            else:
                processed_requirements.append(req)
        
        return processed_requirements

class IsolatedAPITask(IsolatedCodeTask):
    """隔离环境API请求任务"""
    
    def run(self, url: str, method: str = "GET", headers: Dict = None, 
            data: Dict = None, timeout: int = 30, requirements: List[str] = None,
            task_id: str = None, task_name: str = None):
        """
        在隔离环境中执行API请求
        
        Args:
            url: 请求URL
            method: 请求方法
            headers: 请求头
            data: 请求数据
            timeout: 超时时间
            requirements: 依赖包列表
            task_id: 任务ID
            task_name: 任务名称
        """
        headers = headers or {}
        data = data or {}
        requirements = requirements or ["requests"]
        
        # 确保task_logger被初始化
        if self.task_logger is None:
            self.task_id = task_id or str(uuid.uuid4())
            self.task_name = task_name or "isolated.execute_api"
            self.task_logger = TaskLogger(self.task_id, self.task_name)
        
        # 确保docker_client被初始化
        if self.docker_client is None:
            try:
                self.docker_client = docker.from_env()
                self.task_logger.info("Docker客户端初始化成功")
            except Exception as e:
                self.task_logger.error(f"Docker客户端初始化失败: {str(e)}")
                return {
                    'success': False,
                    'error': f'Docker客户端初始化失败: {str(e)}',
                    'traceback': traceback.format_exc()
                }
        
        # 创建API请求代码
        code = self._create_api_request_code(url, method, headers, data, timeout)
        
        # 调用父类的run方法
        return super().run(
            code=code,
            function_name="make_request",
            requirements=requirements,
            task_id=task_id,
            task_name=task_name
        )
    
    def _create_api_request_code(self, url: str, method: str, headers: dict, 
                               data: dict, timeout: int) -> str:
        """创建API请求代码"""
        code = f"""
import requests
import json

def make_request():
    url = "{url}"
    method = "{method}"
    headers = {json.dumps(headers)}
    data = {json.dumps(data)}
    timeout = {timeout}
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data if method.upper() in ['POST', 'PUT', 'PATCH'] else None,
            params=data if method.upper() == 'GET' else None,
            timeout=timeout
        )
        
        result = {{
            'success': True,
            'status_code': response.status_code,
            'url': url,
            'method': method,
            'headers': dict(response.headers),
            'response_text': response.text,
            'response_json': None
        }}
        
        # 尝试解析JSON响应
        try:
            result['response_json'] = response.json()
        except:
            pass
        
        return result
        
    except Exception as e:
        return {{
            'success': False,
            'error': str(e),
            'url': url,
            'method': method
        }}
"""
        return code

# 便捷执行函数
def execute_isolated_code(code: str, function_name: str, requirements: List[str] = None,
                         args: List = None, kwargs: Dict = None, task_id: str = None, 
                         task_name: str = None):
    """执行隔离代码"""
    task = IsolatedCodeTask()
    return task.run(code, function_name, requirements, args, kwargs, task_id, task_name)

def execute_isolated_api_request(url: str, method: str = "GET", headers: Dict = None,
                               data: Dict = None, timeout: int = 30, 
                               requirements: List[str] = None, task_id: str = None, 
                               task_name: str = None):
    """执行隔离API请求"""
    task = IsolatedAPITask()
    return task.run(url, method, headers, data, timeout, requirements, task_id, task_name)
