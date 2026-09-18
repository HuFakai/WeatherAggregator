# Weather Aggregator - 本地运行指南 (Local Run Guide)

本文档介绍了如何在本地环境 (Mac/Linux/Windows) 启动 Weather Aggregator 项目，包括 Web 服务、Celery Worker 和 Celery Beat。

## 1. 环境准备 (Prerequisites)

确保已安装 Python 3.9+。

### 安装依赖
在项目根目录下运行：
```bash
pip install -r requirements.txt
```

## 2. 启动服务 (Start Services)

你需要打开 **3 个独立的终端窗口** (Terminal) 来分别启动以下服务。

### 终端 1: 启动 Web 服务 (FastAPI)
Web 服务负责处理 API 请求和管理后台。
```bash
# 默认端口 8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
-   **API 文档**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
-   **管理后台**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

### 终端 2: 启动 Celery Worker
Worker 负责执行异步任务（如天气抓取）。
```bash
# -A 指定应用实例, -l 指定日志级别
celery -A app.celery_app worker -l info
```

### 终端 3: 启动 Celery Beat
Beat 负责定时触发任务（如每 3 小时更新一次）。
```bash
celery -A app.celery_app beat -l info
```

## 3. PyCharm 启动配置 (PyCharm Configuration)

如果你使用 PyCharm，可以创建 3 个 "Python" 或 "Shell Script" 运行配置：

1.  **Web Server**:
    -   **Module name**: `uvicorn`
    -   **Parameters**: `app.main:app --reload --port 8000`
    -   **Working directory**: 项目根目录

2.  **Celery Worker**:
    -   **Module name**: `celery`
    -   **Parameters**: `-A app.celery_app worker -l info`
    -   **Working directory**: 项目根目录

3.  **Celery Beat**:
    -   **Module name**: `celery`
    -   **Parameters**: `-A app.celery_app beat -l info`
    -   **Working directory**: 项目根目录

## 4. 测试与验证 (Testing)

### 4.1 自动化单元测试 (无需启动本地 Web 服务)
项目配备了高覆盖率的单元测试套件，直接在项目根目录下运行：

```bash
# 运行全部核心业务、数据模型与生命周期治理测试
python3 -m unittest tests/test_optimizations.py

# 运行定时任务调度规则解析测试
python3 tests/test_cron_schedule.py
```

### 4.2 端到端集成测试 (需先启动 Web 服务)
当本地 Web 服务在 `http://127.0.0.1:18050` 启动后，运行集成验证脚本：

```bash
python3 tests/verify_core_features.py
```

该脚本会自动验证：
1. **Admin 登录鉴权**: 校验超级管理员 Key 是否有效。
2. **客户端 Key 生命周期**: 自动化创建、配置 QPM 限制、配置 IP 白名单。
3. **Weather API**: 测试 Path/Query 传参方式及实时聚合返回。
4. **限流防刷拦截**: 模拟高频突发流量，验证 429 拦截。
5. **数据清理**: 自动化回收测试生成的测试 Key。

