# 任务管理系统 - 快速启动指南

## 🚀 5分钟快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动Redis

```bash
# 使用Docker启动Redis (推荐)
docker run -d -p 6379:6379 redis:7-alpine

# 或者使用Docker Compose
docker-compose up -d redis
```

### 3. 启动系统

```bash
# 一键启动所有服务
python start.py
```

### 4. 测试系统

```bash
# 运行测试脚本
python test_system.py
```

## 📋 系统功能

✅ **立即执行任务** - 任务创建后立即执行  
✅ **延时执行任务** - 指定时间后执行  
✅ **定时执行任务** - 按Cron表达式定时执行  
✅ **动态代码执行** - 安全执行用户提供的代码  
✅ **API接口任务** - 执行HTTP请求  
✅ **任务管理** - 添加、删除、停止任务  
✅ **状态监控** - 实时查看任务状态  
✅ **日志记录** - 完整的操作日志  
✅ **安全控制** - 代码执行安全检查  

## 🔧 API接口

### 健康检查
```bash
curl http://localhost:5000/api/health
```

### 创建任务
```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试任务",
    "task_type": "immediate",
    "function_code": "def hello():\n    return \"Hello World!\"",
    "function_name": "hello"
  }'
```

### 定时任务
```bash
curl -X POST http://localhost:5001/api/scheduled-tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "daily_report",
    "task_type": "dynamic",
    "cron_expression": "30 18 * * *",
    "function_code": "def generate_report():\n    return {\"message\": \"日报生成完成\", \"timestamp\": datetime.now().isoformat()}",
    "function_name": "generate_report"
  }'
```

### 获取任务列表
```bash
curl http://localhost:5000/api/tasks
```

## 🐳 Docker部署

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 📊 监控界面

- **API服务**: http://localhost:5000
- **Flower监控**: http://localhost:5555
- **健康检查**: http://localhost:5000/api/health

## 📝 使用示例

### 立即执行任务
```json
{
  "name": "计算任务",
  "task_type": "immediate",
  "function_code": "def calculate():\n    return 1 + 2 * 3",
  "function_name": "calculate"
}
```

### 延时任务
```json
{
  "name": "延时通知",
  "task_type": "delayed",
  "delay_seconds": 60,
  "function_code": "def notify():\n    return \"延时通知已发送\"",
  "function_name": "notify"
}
```

### API任务
```json
{
  "name": "获取数据",
  "task_type": "immediate",
  "api_url": "https://api.example.com/data",
  "method": "GET",
  "timeout": 30
}
```

## 🔒 安全特性

- ✅ 代码执行安全检查
- ✅ 危险函数调用拦截
- ✅ 模块导入限制
- ✅ 执行超时控制
- ✅ 错误隔离处理

## 📈 生产环境

```bash
# 设置环境变量
export FLASK_ENV=production
export DEBUG=false
export SECRET_KEY=your-secret-key

# 启动生产服务
python start.py
```

## 🆘 故障排除

### 常见问题

1. **Redis连接失败**
   ```bash
   # 检查Redis是否运行
   redis-cli ping
   ```

2. **端口被占用**
   ```bash
   # 检查端口使用情况
   netstat -tulpn | grep :5000
   ```

3. **依赖安装失败**
   ```bash
   # 升级pip
   pip install --upgrade pip
   
   # 重新安装依赖
   pip install -r requirements.txt
   ```

## 📚 更多信息

- 📖 [详细使用指南](USAGE.md)
- 📖 [API文档](README.md)
- 🧪 [测试脚本](test_system.py)
- 🐳 [Docker配置](docker-compose.yml)

---

**🎉 恭喜！你的任务管理系统已经启动成功！**

现在你可以通过API接口来管理任务了。系统支持立即执行、延时执行和定时执行三种任务类型，并且提供了完整的任务管理功能。 