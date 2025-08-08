# 任务管理系统 (Task Management System)

## 项目简介
基于Celery + Redis的分布式任务管理系统，支持多种任务类型和动态任务管理。

## 功能特性
- **任务类型支持**：
  - **动态代码任务**：执行用户提供的Python代码
  - **API接口任务**：执行HTTP请求
- **执行方式支持**：
  - 立即执行任务
  - 延时执行任务
  - 定时执行任务（Cron表达式）
- **任务管理**：
  - 手动定义任务
  - 动态添加任务（传递代码与函数名）
  - API接口任务
  - 任务添加、删除、停止
- **生产环境特性**：
  - 任务状态监控
  - 错误处理和重试机制
  - 日志记录
  - 性能监控
  - 安全认证

## 任务类型详解

### 1. 动态代码任务 (Dynamic Code Tasks)
执行用户提供的Python代码，支持安全的代码执行环境。

**支持的执行方式：**
- **立即执行**：任务创建后立即执行
- **延时执行**：指定时间后执行
- **定时执行**：按Cron表达式定时执行

**示例：**
```json
{
  "name": "计算任务",
  "task_type": "immediate",
  "function_code": "def calculate():\n    return 1 + 2 * 3",
  "function_name": "calculate"
}
```

### 2. API接口任务 (API Tasks)
执行HTTP请求，支持各种HTTP方法和参数。

**支持的执行方式：**
- **立即执行**：任务创建后立即执行
- **延时执行**：指定时间后执行
- **定时执行**：按Cron表达式定时执行

**示例：**
```json
{
  "name": "获取数据",
  "task_type": "immediate",
  "api_url": "https://api.example.com/data",
  "method": "GET",
  "timeout": 30
}
```

## 系统架构
```
task_manage/
├── celery_app.py          # Celery应用配置
├── tasks/                 # 任务模块
│   ├── __init__.py
│   ├── base_tasks.py     # 基础任务类
│   └── task_manager.py   # 任务管理器
├── api/                   # API接口
│   ├── __init__.py
│   ├── routes.py         # 路由定义
│   └── models.py         # 数据模型
├── config/               # 配置文件
│   ├── __init__.py
│   └── settings.py       # 系统配置
├── utils/                # 工具模块
│   ├── __init__.py
│   ├── logger.py         # 日志工具
│   └── security.py       # 安全工具
├── requirements.txt       # 依赖包
├── docker-compose.yml    # Docker配置
└── README.md            # 项目文档
```

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动Redis
```bash
docker-compose up -d redis
```

### 3. 启动Celery Worker
```bash
celery -A celery_app worker --loglevel=info
```

### 4. 启动Celery Beat（定时任务）
```bash
celery -A celery_app beat --loglevel=info
```

### 5. 启动API服务
```bash
python start.py
```

## API接口

### 任务管理接口
- `POST /api/tasks` - 创建任务
- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/{task_id}` - 获取任务详情
- `DELETE /api/tasks/{task_id}` - 删除任务
- `POST /api/tasks/{task_id}/stop` - 停止任务

### 定时任务专用接口
- `POST /api/scheduled-tasks` - 创建定时任务
- `GET /api/scheduled-tasks` - 获取定时任务列表

### 任务类型示例

#### 动态代码任务示例

**立即执行：**
```json
{
  "name": "立即计算任务",
  "task_type": "immediate",
  "function_code": "def hello_world():\n    return 'Hello World!'",
  "function_name": "hello_world"
}
```

**延时执行：**
```json
{
  "name": "延时计算任务",
  "task_type": "delayed",
  "delay_seconds": 60,
  "function_code": "def calculate():\n    return 1 + 2 * 3",
  "function_name": "calculate"
}
```

**定时执行：**
```json
{
  "name": "定时计算任务",
  "task_type": "scheduled",
  "cron_expression": "0 0 * * *",
  "function_code": "def daily_report():\n    return '日报生成完成'",
  "function_name": "daily_report"
}
```

#### API任务示例

**立即执行：**
```json
{
  "name": "立即API请求",
  "task_type": "immediate",
  "api_url": "https://httpbin.org/get",
  "method": "GET",
  "timeout": 30
}
```

**延时执行：**
```json
{
  "name": "延时API请求",
  "task_type": "delayed",
  "delay_seconds": 300,
  "api_url": "https://httpbin.org/post",
  "method": "POST",
  "data": {"message": "延时请求"},
  "timeout": 30
}
```

**定时执行：**
```json
{
  "name": "定时API请求",
  "task_type": "scheduled",
  "cron_expression": "*/5 * * * *",
  "api_url": "https://httpbin.org/status/200",
  "method": "GET",
  "timeout": 30
}
```

## 配置说明
- Redis连接配置
- Celery配置
- 日志配置
- 安全配置

## 监控和日志
- 任务执行状态监控
- 错误日志记录
- 性能指标收集

## 测试
运行测试脚本验证所有功能：
```bash
python test_task_types.py
``` 