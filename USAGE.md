# 任务管理系统使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动Redis

```bash
# 使用Docker启动Redis
docker run -d -p 6379:6379 redis:7-alpine

# 或者使用Docker Compose启动所有服务
docker-compose up -d redis
```

### 3. 启动系统

```bash
# 方式1: 使用启动脚本
python start.py

# 方式2: 分别启动各个组件
# 启动Celery Worker
celery -A celery_app worker --loglevel=info

# 启动Celery Beat (定时任务)
celery -A celery_app beat --loglevel=info

# 启动API服务
python celery_app.py
```

### 4. 测试系统

```bash
python test_system.py
```

## API接口使用

### 健康检查

```bash
curl http://localhost:5000/api/health
```

### 创建立即执行任务

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试任务",
    "task_type": "immediate",
    "function_code": "def hello():\n    return \"Hello World!\"",
    "function_name": "hello",
    "args": [],
    "kwargs": {}
  }'
```

### 创建延时任务

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "延时任务",
    "task_type": "delayed",
    "delay_seconds": 60,
    "function_code": "def delayed_task():\n    return \"延时任务执行完成\"",
    "function_name": "delayed_task",
    "args": [],
    "kwargs": {}
  }'
```

### 创建API任务

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API任务",
    "task_type": "immediate",
    "api_url": "https://httpbin.org/get",
    "method": "GET",
    "headers": {
      "User-Agent": "TaskManagementSystem/1.0"
    },
    "timeout": 30
  }'
```

### 获取任务列表

```bash
curl http://localhost:5000/api/tasks
```

### 获取任务详情

```bash
curl http://localhost:5000/api/tasks/{task_id}
```

### 停止任务

```bash
curl -X POST http://localhost:5000/api/tasks/{task_id}/stop
```

### 删除任务

```bash
curl -X DELETE http://localhost:5000/api/tasks/{task_id}
```

## 任务类型说明

### 1. 立即执行任务 (immediate)

任务创建后立即执行，适用于需要快速响应的场景。

```json
{
  "name": "立即任务",
  "task_type": "immediate",
  "function_code": "def task():\n    return \"立即执行\"",
  "function_name": "task"
}
```

### 2. 延时执行任务 (delayed)

任务在指定时间后执行，适用于需要延迟处理的场景。

```json
{
  "name": "延时任务",
  "task_type": "delayed",
  "delay_seconds": 300,
  "function_code": "def task():\n    return \"延时执行\"",
  "function_name": "task"
}
```

### 3. 定时执行任务 (scheduled)

任务按照Cron表达式定时执行，适用于定期任务。

```json
{
  "name": "定时任务",
  "task_type": "scheduled",
  "cron_expression": "0 0 * * *",
  "function_code": "def task():\n    return \"定时执行\"",
  "function_name": "task"
}
```

## 代码执行安全

系统对动态代码执行进行了安全检查，禁止以下操作：

- 危险模块导入 (os, sys, subprocess等)
- 危险函数调用 (eval, exec, open等)
- 文件系统操作
- 网络操作
- 系统命令执行

允许使用的模块：
- math, datetime, json, re, random
- collections, itertools, functools, operator

## 监控和管理

### Flower监控界面

访问 http://localhost:5555 查看Celery任务监控界面。

### 日志查看

```bash
# 查看应用日志
tail -f logs/task_manage.log

# 查看Celery Worker日志
celery -A celery_app worker --loglevel=info
```

### 系统状态检查

```bash
# 检查Redis连接
redis-cli ping

# 检查Celery状态
celery -A celery_app inspect active
```

## 生产环境部署

### 使用Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 环境变量配置

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export FLASK_ENV=production
export DEBUG=false
export SECRET_KEY=your-secret-key
export JWT_SECRET_KEY=your-jwt-secret-key
```

### 性能优化

1. 调整Celery Worker数量
2. 配置Redis连接池
3. 设置任务超时时间
4. 启用任务结果存储
5. 配置日志轮转

## 故障排除

### 常见问题

1. **Redis连接失败**
   - 检查Redis服务是否启动
   - 验证连接参数是否正确

2. **Celery Worker无法启动**
   - 检查Redis连接
   - 验证任务模块导入

3. **任务执行失败**
   - 检查代码语法
   - 验证函数名称
   - 查看错误日志

4. **API接口无响应**
   - 检查Flask服务是否启动
   - 验证端口是否被占用

### 日志分析

```bash
# 查看错误日志
grep "ERROR" logs/task_manage.log

# 查看任务执行日志
grep "task" logs/task_manage.log
```

## 扩展开发

### 添加新的任务类型

1. 在 `tasks/base_tasks.py` 中定义新的任务类
2. 在 `celery_app.py` 中注册任务
3. 在 `tasks/task_manager.py` 中添加处理逻辑
4. 在API中添加相应的接口

### 自定义配置

修改 `config/settings.py` 中的配置项：

```python
# 调整任务超时时间
TASK_TIMEOUT = 1800  # 30分钟

# 调整并发任务数
MAX_CONCURRENT_TASKS = 200

# 调整日志级别
LOG_LEVEL = "DEBUG"
```

### 添加监控指标

1. 集成Prometheus监控
2. 添加自定义指标收集
3. 配置告警规则 