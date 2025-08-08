#!/usr/bin/env python3
"""
测试任务状态更新
"""

import requests
import json
import time

def test_status_update():
    """测试任务状态更新"""
    print("测试任务状态更新...")
    
    test_data = {
        "name": "状态更新测试",
        "task_type": "immediate",
        "function_code": """
import time

def test():
    # 模拟一些处理时间
    time.sleep(2)
    return {"result": "success", "message": "状态更新测试完成"}
""",
        "function_name": "test",
        "requirements": []
    }
    
    try:
        print("发送任务请求...")
        response = requests.post(
            "http://localhost:5000/api/tasks/isolated",
            json=test_data,
            timeout=60
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 201:
            result = response.json()
            if result.get('success'):
                task_id = result.get('task_id')
                print(f"✅ 任务创建成功: {task_id}")
                
                # 监控任务状态变化
                return monitor_status_progression(task_id)
            else:
                print(f"❌ 任务创建失败: {result.get('error')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器，请确保服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def monitor_status_progression(task_id):
    """监控任务状态变化"""
    print(f"监控任务状态变化: {task_id}")
    
    max_wait_time = 30  # 最大等待时间30秒
    check_interval = 1   # 每1秒检查一次
    elapsed_time = 0
    
    status_history = []
    last_status = None
    
    while elapsed_time < max_wait_time:
        try:
            status_response = requests.get(f"http://localhost:5000/api/tasks/{task_id}")
            
            if status_response.status_code == 200:
                task_info = status_response.json()
                status = task_info.get('status', 'unknown')
                
                # 记录状态变化
                if status != last_status:
                    status_history.append((elapsed_time, status))
                    print(f"状态变化: {status} (时间: {elapsed_time}s)")
                    last_status = status
                
                if status == 'completed':
                    print(f"✅ 任务完成")
                    print(f"结果: {task_info.get('result', 'N/A')}")
                    print(f"状态历史: {status_history}")
                    return True
                elif status == 'failed':
                    print(f"❌ 任务失败")
                    print(f"错误: {task_info.get('result', 'N/A')}")
                    print(f"状态历史: {status_history}")
                    return False
                elif status == 'running':
                    print(f"🔄 任务运行中... (时间: {elapsed_time}s)")
                elif status == 'pending':
                    print(f"⏳ 任务等待中... (时间: {elapsed_time}s)")
                else:
                    print(f"❓ 未知状态: {status}")
            else:
                print(f"❌ 获取任务状态失败: {status_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 监控任务状态失败: {e}")
            return False
        
        time.sleep(check_interval)
        elapsed_time += check_interval
    
    print(f"⏰ 任务超时")
    print(f"状态历史: {status_history}")
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("任务状态更新测试")
    print("=" * 50)
    
    success = test_status_update()
    
    if success:
        print("\n🎉 任务状态更新正常！")
        print("期望的状态流程:")
        print("1. pending -> running -> completed")
    else:
        print("\n❌ 任务状态更新有问题，需要进一步检查。")
        print("可能的问题:")
        print("1. 状态更新方法没有正确工作")
        print("2. 任务管理器有问题")
        print("3. Redis连接有问题")
