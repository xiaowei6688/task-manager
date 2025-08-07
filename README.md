# 任务管理系统 (Task Management System)

## 项目简介
基于Celery + Redis的分布式任务管理系统，支持多种任务类型和动态任务管理。

## 功能特性
- **任务类型支持**：
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
python api/app.py
```

## API接口

### 任务管理接口
- `POST /api/tasks` - 创建任务
- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/{task_id}` - 获取任务详情
- `DELETE /api/tasks/{task_id}` - 删除任务
- `POST /api/tasks/{task_id}/stop` - 停止任务

### 任务类型示例
```json
{
  "name": "示例任务",
  "task_type": "immediate",  // immediate, delayed, scheduled
  "function_code": "def hello_world():\n    return 'Hello World!'",
  "function_name": "hello_world",
  "args": [],
  "kwargs": {},
  "delay_seconds": 60,  // 延时执行时间（秒）
  "cron_expression": "0 0 * * *"  // Cron表达式
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