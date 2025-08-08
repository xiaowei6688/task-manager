# 隔离任务使用指南

## 概述

隔离任务功能允许你在独立的Docker容器中执行Python代码，支持任意第三方包依赖。这解决了传统动态代码执行的安全性和依赖限制问题。

## 优势

1. **完全隔离**：每个任务在独立的Docker容器中执行，互不影响
2. **安全性高**：容器自动清理，不会留下垃圾文件
3. **灵活性好**：支持任意第三方包，不受主机环境限制
4. **资源控制**：可以限制内存、CPU使用量
5. **网络隔离**：可以选择禁用网络访问

## 系统要求

1. **Docker**：必须安装并运行Docker服务
2. **Python 3.9+**：推荐使用Python 3.9或更高版本
3. **Docker权限**：确保应用有权限运行Docker容器

## 安装Docker

### macOS
```bash
# 使用Homebrew安装
brew install --cask docker

# 或者从官网下载
# https://www.docker.com/products/docker-desktop
```

### Ubuntu/Debian
```bash
# 安装Docker
sudo apt-get update
sudo apt-get install docker.io

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 将用户添加到docker组
sudo usermod -aG docker $USER
```

### CentOS/RHEL
```bash
# 安装Docker
sudo yum install docker

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 将用户添加到docker组
sudo usermod -aG docker $USER
```

## 使用方法

### 1. 创建隔离代码任务

**立即执行：**
```bash
curl -X POST http://localhost:5001/api/tasks/isolated \
  -H "Content-Type: application/json" \
  -d '{
    "name": "数据分析任务",
    "task_type": "immediate",
    "function_code": "import pandas as pd\ndef analyze():\n    df = pd.DataFrame({\"A\": [1,2,3,4,5]})\n    return df.describe().to_dict()",
    "function_name": "analyze",
    "requirements": ["pandas==1.5.0", "numpy==1.24.0"]
  }'
```

**延时执行：**
```bash
curl -X POST http://localhost:5001/api/tasks/isolated \
  -H "Content-Type: application/json" \
  -d '{
    "name": "延时数据分析",
    "task_type": "delayed",
    "delay_seconds": 60,
    "function_code": "import numpy as np\ndef generate_data():\n    return np.random.rand(10).tolist()",
    "function_name": "generate_data",
    "requirements": ["numpy==1.24.0"]
  }'
```

**定时执行：**
```bash
curl -X POST http://localhost:5001/api/tasks/isolated \
  -H "Content-Type: application/json" \
  -d '{
    "name": "定时数据收集",
    "task_type": "scheduled",
    "cron_expression": "0 */6 * * *",
    "function_code": "import requests\ndef collect_data():\n    response = requests.get(\"https://api.example.com/data\")\n    return response.json()",
    "function_name": "collect_data",
    "requirements": ["requests==2.28.0"]
  }'
```

### 2. 创建隔离API任务

**GET请求：**
```bash
curl -X POST http://localhost:5001/api/tasks/isolated \
  -H "Content-Type: application/json" \
  -d '{
    "name": "隔离GET请求",
    "task_type": "immediate",
    "api_url": "https://httpbin.org/get",
    "method": "GET",
    "timeout": 30,
    "requirements": ["requests==2.28.0"]
  }'
```

**POST请求：**
```bash
curl -X POST http://localhost:5001/api/tasks/isolated \
  -H "Content-Type: application/json" \
  -d '{
    "name": "隔离POST请求",
    "task_type": "immediate",
    "api_url": "https://httpbin.org/post",
    "method": "POST",
    "data": {"message": "Hello from isolated task"},
    "timeout": 30,
    "requirements": ["requests==2.28.0"]
  }'
```

## 参数说明

### 代码任务参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 任务名称 |
| `task_type` | string | 是 | 任务类型：immediate/delayed/scheduled |
| `function_code` | string | 是 | 要执行的Python代码 |
| `function_name` | string | 是 | 要调用的函数名 |
| `requirements` | array | 否 | 依赖包列表，如 ["pandas==1.5.0"] |
| `args` | array | 否 | 函数参数列表 |
| `kwargs` | object | 否 | 函数关键字参数 |
| `delay_seconds` | integer | 否 | 延时秒数（仅延时任务） |
| `cron_expression` | string | 否 | Cron表达式（仅定时任务） |

### API任务参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 任务名称 |
| `task_type` | string | 是 | 任务类型：immediate/delayed/scheduled |
| `api_url` | string | 是 | 请求URL |
| `method` | string | 否 | 请求方法，默认GET |
| `headers` | object | 否 | 请求头 |
| `data` | object | 否 | 请求数据 |
| `timeout` | integer | 否 | 超时时间，默认30秒 |
| `requirements` | array | 否 | 依赖包列表，默认["requests"] |
| `delay_seconds` | integer | 否 | 延时秒数（仅延时任务） |
| `cron_expression` | string | 否 | Cron表达式（仅定时任务） |

## 容器配置

### 资源限制

隔离任务使用以下Docker配置：

- **内存限制**：512MB
- **CPU限制**：50%
- **网络**：默认禁用（可选）
- **自动清理**：容器执行完成后自动删除

### 基础镜像

使用 `python:3.9-slim` 作为基础镜像，包含：
- Python 3.9
- pip包管理器
- 基础系统工具

## 最佳实践

### 1. 依赖管理

- 指定具体的版本号，避免兼容性问题
- 使用最小化的依赖列表
- 避免安装不必要的包

```json
{
  "requirements": ["pandas==1.5.0", "numpy==1.24.0"]
}
```

### 2. 错误处理

在代码中添加适当的错误处理：

```python
def my_function():
    try:
        # 你的代码
        result = some_operation()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 3. 资源优化

- 避免在容器中执行长时间运行的任务
- 合理设置超时时间
- 及时清理不需要的数据

### 4. 安全性

- 不要在代码中包含敏感信息
- 避免执行危险操作
- 使用网络隔离（如需要）

## 故障排除

### 1. Docker未运行

**错误信息：** `Docker客户端初始化失败`

**解决方案：**
```bash
# 启动Docker服务
sudo systemctl start docker

# 检查Docker状态
docker --version
docker ps
```

### 2. 权限问题

**错误信息：** `权限被拒绝`

**解决方案：**
```bash
# 将用户添加到docker组
sudo usermod -aG docker $USER

# 重新登录或重启系统
newgrp docker
```

### 3. 依赖安装失败

**错误信息：** `安装依赖包失败`

**解决方案：**
- 检查包名和版本号是否正确
- 确保包在PyPI上可用
- 尝试使用不同的版本号

### 4. 容器启动失败

**错误信息：** `容器执行失败`

**解决方案：**
- 检查代码语法是否正确
- 确保函数名存在
- 查看详细错误日志

## 监控和日志

### 查看任务状态

```bash
# 获取任务列表
curl http://localhost:5001/api/tasks

# 获取特定任务详情
curl http://localhost:5001/api/tasks/{task_id}
```

### 查看日志

任务日志保存在 `logs/` 目录下：
- `task_manage.log`：系统日志
- `task_{task_id}.log`：特定任务日志

### 健康检查

```bash
curl http://localhost:5001/api/health
```

## 性能考虑

1. **容器启动时间**：每次任务需要启动新的Docker容器，大约需要2-5秒
2. **依赖安装时间**：首次安装依赖包需要额外时间
3. **资源使用**：每个容器使用512MB内存和50%CPU限制
4. **并发限制**：建议同时运行的任务数量不超过10个

## 示例代码

### 数据分析示例

```python
import pandas as pd
import numpy as np

def analyze_sales_data():
    # 创建示例销售数据
    data = {
        'date': pd.date_range('2023-01-01', periods=100),
        'sales': np.random.randint(100, 1000, 100),
        'region': np.random.choice(['North', 'South', 'East', 'West'], 100)
    }
    df = pd.DataFrame(data)
    
    # 分析数据
    analysis = {
        'total_sales': df['sales'].sum(),
        'avg_sales': df['sales'].mean(),
        'sales_by_region': df.groupby('region')['sales'].sum().to_dict(),
        'daily_sales': df.groupby(df['date'].dt.date)['sales'].sum().to_dict()
    }
    
    return analysis
```

### 机器学习示例

```python
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

def train_model():
    # 生成示例数据
    X = np.random.rand(100, 3)
    y = np.random.rand(100)
    
    # 分割数据
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    # 训练模型
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # 评估模型
    score = model.score(X_test, y_test)
    
    return {
        'model_score': score,
        'coefficients': model.coef_.tolist(),
        'intercept': model.intercept_
    }
```

### API集成示例

```python
import requests
import json

def fetch_and_process_data():
    # 获取数据
    response = requests.get('https://jsonplaceholder.typicode.com/posts')
    posts = response.json()
    
    # 处理数据
    processed_data = []
    for post in posts[:10]:  # 只处理前10个
        processed_data.append({
            'id': post['id'],
            'title': post['title'],
            'word_count': len(post['title'].split())
        })
    
    return {
        'total_posts': len(posts),
        'processed_posts': len(processed_data),
        'data': processed_data
    }
```

## 总结

隔离任务功能为你的任务管理系统提供了强大的扩展能力：

1. **安全性**：Docker容器提供完全隔离的执行环境
2. **灵活性**：支持任意第三方包，不受主机环境限制
3. **可扩展性**：可以轻松添加新的依赖包和功能
4. **可靠性**：自动资源管理和错误处理

通过合理使用隔离任务，你可以构建更加强大和灵活的任务管理系统。
