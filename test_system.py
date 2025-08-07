"""
系统测试脚本
测试任务管理系统的各项功能
"""

import requests
import time
import json
from datetime import datetime

class TaskManagementTester:
    """任务管理系统测试器"""
    
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.test_results = []
    
    def test_health_check(self):
        """测试健康检查"""
        try:
            response = requests.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 健康检查通过: {data}")
                return True
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 健康检查异常: {str(e)}")
            return False
    
    def test_create_dynamic_task(self):
        """测试创建动态代码任务"""
        task_data = {
            "name": "测试动态代码任务",
            "task_type": "immediate",
            "function_code": """
def hello_world():
    return "Hello from dynamic code!"
""",
            "function_name": "hello_world",
            "args": [],
            "kwargs": {}
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/tasks", json=task_data)
            if response.status_code == 201:
                data = response.json()
                print(f"✅ 动态代码任务创建成功: {data}")
                return data.get('task_id')
            else:
                print(f"❌ 动态代码任务创建失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ 动态代码任务创建异常: {str(e)}")
            return None
    
    def test_create_api_task(self):
        """测试创建API任务"""
        task_data = {
            "name": "测试API任务",
            "task_type": "immediate",
            "api_url": "https://httpbin.org/get",
            "method": "GET",
            "headers": {},
            "data": {}
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/tasks", json=task_data)
            if response.status_code == 201:
                data = response.json()
                print(f"✅ API任务创建成功: {data}")
                return data.get('task_id')
            else:
                print(f"❌ API任务创建失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ API任务创建异常: {str(e)}")
            return None
    
    def test_get_task(self, task_id):
        """测试获取任务详情"""
        try:
            response = requests.get(f"{self.base_url}/api/tasks/{task_id}")
            if response.status_code == 200:
                data = response.json()
                task = data.get('task', {})
                print(f"✅ 获取任务详情成功:")
                print(f"   任务ID: {task.get('id')}")
                print(f"   任务名称: {task.get('name')}")
                print(f"   任务状态: {task.get('status')}")
                print(f"   任务类型: {task.get('type')}")
                if 'result' in task:
                    print(f"   任务结果: {task['result']}")
                return True
            else:
                print(f"❌ 获取任务详情失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 获取任务详情异常: {str(e)}")
            return False
    
    def test_get_tasks_by_type(self, task_type):
        """测试按类型获取任务"""
        try:
            response = requests.get(f"{self.base_url}/api/tasks?type={task_type}")
            if response.status_code == 200:
                data = response.json()
                tasks = data.get('tasks', [])
                print(f"✅ 按类型获取任务成功 ({task_type}):")
                print(f"   任务数量: {len(tasks)}")
                for task in tasks[:3]:  # 只显示前3个
                    print(f"   - {task.get('name')} ({task.get('status')})")
                return True
            else:
                print(f"❌ 按类型获取任务失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 按类型获取任务异常: {str(e)}")
            return False
    
    def test_get_task_stats(self):
        """测试获取任务统计"""
        try:
            response = requests.get(f"{self.base_url}/api/tasks/stats")
            if response.status_code == 200:
                data = response.json()
                stats = data.get('stats', {})
                print(f"✅ 获取任务统计成功:")
                print(f"   总任务数: {stats.get('total', 0)}")
                print(f"   待处理: {stats.get('pending', 0)}")
                print(f"   运行中: {stats.get('running', 0)}")
                print(f"   已完成: {stats.get('completed', 0)}")
                print(f"   失败: {stats.get('failed', 0)}")
                print(f"   已停止: {stats.get('stopped', 0)}")
                return True
            else:
                print(f"❌ 获取任务统计失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 获取任务统计异常: {str(e)}")
            return False
    
    def test_task_status_update(self, task_id):
        """测试任务状态更新"""
        print(f"🔄 等待任务执行完成...")
        max_wait = 30  # 最多等待30秒
        wait_time = 0
        
        while wait_time < max_wait:
            try:
                response = requests.get(f"{self.base_url}/api/tasks/{task_id}")
                if response.status_code == 200:
                    data = response.json()
                    task = data.get('task', {})
                    status = task.get('status')
                    
                    print(f"   当前状态: {status}")
                    
                    if status in ['completed', 'failed']:
                        print(f"✅ 任务执行完成，最终状态: {status}")
                        if 'result' in task:
                            print(f"   执行结果: {task['result']}")
                        return True
                    elif status == 'running':
                        print(f"   任务正在运行...")
                    elif status == 'pending':
                        print(f"   任务等待中...")
                
                time.sleep(2)
                wait_time += 2
                
            except Exception as e:
                print(f"❌ 检查任务状态异常: {str(e)}")
                break
        
        print(f"❌ 任务执行超时")
        return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行任务管理系统测试...")
        print("=" * 50)
        
        # 测试健康检查
        if not self.test_health_check():
            print("❌ 健康检查失败，停止测试")
            return False
        
        print("\n" + "=" * 50)
        
        # 测试创建动态代码任务
        print("📝 测试创建动态代码任务...")
        dynamic_task_id = self.test_create_dynamic_task()
        
        if dynamic_task_id:
            # 等待任务执行完成
            self.test_task_status_update(dynamic_task_id)
            
            # 获取任务详情
            self.test_get_task(dynamic_task_id)
        
        print("\n" + "=" * 50)
        
        # 测试创建API任务
        print("🌐 测试创建API任务...")
        api_task_id = self.test_create_api_task()
        
        if api_task_id:
            # 等待任务执行完成
            self.test_task_status_update(api_task_id)
            
            # 获取任务详情
            self.test_get_task(api_task_id)
        
        print("\n" + "=" * 50)
        
        # 测试按类型获取任务
        print("📊 测试按类型获取任务...")
        self.test_get_tasks_by_type("immediate")
        
        print("\n" + "=" * 50)
        
        # 测试获取任务统计
        print("📈 测试获取任务统计...")
        self.test_get_task_stats()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成！")
        
        return True

def main():
    """主函数"""
    tester = TaskManagementTester()
    tester.test_create_dynamic_task()

if __name__ == "__main__":
    main() 