# WeatherAggregator - 高性能多源天气数据聚合服务

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Pydantic](https://img.shields.io/badge/Pydantic-V2-orange.svg)](https://docs.pydantic.dev/)
[![Celery](https://img.shields.io/badge/Celery-5.3+-red.svg)](https://docs.celeryproject.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个高可用、高性能的多渠道天气数据聚合与分发系统。支持多数据源可插拔工厂架构、智能 Key 轮询容灾、Redis 全生命周期治理、Celery Beat 动态调度热重载、双向参数兼容的 RESTful API 以及现代化暗色玻璃拟态（Midnight Glassmorphism）管理后台。

---

## ✨ 核心特性

- 🌤️ **多渠道多源聚合**: 预置集成 **和风天气 (hefeng)**、**易客天气 (yiketianqi)**、**百度地图天气 (baidu)**，支持一键并发聚合多源天气预报。
- 🧩 **工厂化插件架构**: 采用 `FetcherRegistry` 单例注册工厂，新增三方数据源仅需添加 `@FetcherRegistry.register("channel_name")` 装饰器，彻底解耦。
- ⚡ **Redis 内存与生命周期治理**:
  - 渠道每日调用统计 Key 自动配置 3 天过期（TTL 259200s），防止无用数据累积。
  - 客户端 QPM 限流滑动窗口绑定 65 秒过期，时间窗口外自动释放。
  - Celery 启用 `task_ignore_result = True`，杜绝元数据在 Redis 中堆积。
- 🔐 **智能 Key 轮询与平滑迁移**:
  - 渠道多 Key 池自动轮询、配额追踪与失效故障转移。
  - 客户端 API Key 支持自定义修改，修改后通过 Redis Pipeline 自动平滑迁移最近 7 天的历史调用统计，监控报表无缝衔接。
- 🔄 **Celery Beat 动态热重载**:
  - 基于 MongoDB 与 Redis 信号机制自定义 `DynamicMongoScheduler`。
  - 管理后台修改 Cron 表达式或启停渠道后，**5 秒内动态热生效，无需重启 Celery Beat 容器或服务**。
- 🛡️ **精细化安全与限流**:
  - 支持 Header `X-API-Key` 与 Query `key` 双向鉴权。
  - 严格的 IP 白名单拦截与针对客户端 Key 的 QPM 速率限制。
- 🌐 **双向 API 路由传参兼容**:
  - 同时支持 RESTful Path 路径传参（`/api/v1/weather/{city}`）与 Query 查询传参（`/api/v1/weather?city=...`）。
- 🎨 **Midnight Glassmorphism 管理后台**:
  - 现代深色暗黑毛玻璃美学设计，全响应式交互。
  - 提供数据渠道监控、Key 配额看板、定时调度可视化编辑（含常用频率一键预设与防限流抖动延时设置）。

---

## 🚀 快速开始

### 前提条件

- Docker & Docker Compose
- 或本地安装: Python 3.10+, MongoDB, Redis

### 方式 A: Docker 容器化部署 (生产推荐)

```bash
# 1. 克隆代码仓库
git clone https://github.com/HuFakai/WeatherAggregator.git
cd WeatherAggregator

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，按需修改直连数据库与管理员密码

# 3. 构建并启动所有服务 (FastAPI + Celery Worker + Celery Beat)
docker compose up -d --build

# 4. 访问服务
# Web API 接口文档: http://localhost:18050/docs
# 统一管理后台:     http://localhost:18050/admin
```

### 方式 B: 本地开发运行

请参考 [LOCAL_RUN_GUIDE.md](LOCAL_RUN_GUIDE.md) 启动 Web 服务、Celery Worker 和 Celery Beat。

---

## 📖 API 接口规范

天气查询接口同时支持 **Path 路径传参** 与 **Query 查询传参** 两种标准规范。

### 1. 认证方式
- **Header 方式 (推荐)**: `X-API-Key: ck_xxxxxxxx`
- **Query 方式**: `?key=ck_xxxxxxxx`

### 2. 接口端点

#### 端点 1: Path 路径传参 (RESTful)
```http
GET /api/v1/weather/{city}
```

#### 端点 2: Query 查询传参
```http
GET /api/v1/weather?city={city}
```

### 3. 调用示例

```bash
# 示例 1: 使用城市名称 (Path 方式 + Query Key)
curl "http://localhost:18050/api/v1/weather/北京?key=your_client_key"

# 示例 2: 使用城市名称 (Query 方式 + Header Key)
curl -H "X-API-Key: your_client_key" "http://localhost:18050/api/v1/weather?city=北京"

# 示例 3: 使用城市 Adcode/代码 (如 110100)
curl "http://localhost:18050/api/v1/weather/110100?key=your_client_key"
```

### 4. 响应示例

```json
{
  "_id": "110100",
  "city_name": "北京",
  "last_updated_at": "2026-09-18T22:15:00.123456+08:00",
  "sources": {
    "hefeng": [
      {
        "date": "2026-09-18",
        "temp_high": 26,
        "temp_low": 16,
        "weather_day": "晴",
        "weather_night": "多云",
        "humidity": 45,
        "wind_direction": "南风",
        "wind_scale": "1-2级",
        "aqi": 55,
        "aqi_level": "良",
        "lifestyle": [
          {
            "title": "紫外线指数",
            "level": "中等",
            "desc": "涂擦SPF大于15、PA+防晒护肤品。"
          }
        ]
      }
    ],
    "yiketianqi": [
      {
        "date": "2026-09-18",
        "temp_high": 27,
        "temp_low": 15,
        "weather_day": "晴",
        "weather_night": "晴",
        "humidity": 42,
        "wind_direction": "南风",
        "wind_scale": "2级",
        "aqi": 52,
        "aqi_level": "良",
        "lifestyle": []
      }
    ],
    "baidu": [
      {
        "date": "2026-09-18",
        "temp_high": 26,
        "temp_low": 16,
        "weather_day": "晴",
        "weather_night": "晴",
        "humidity": 48,
        "wind_direction": "南风",
        "wind_scale": "1-2级",
        "aqi": 58,
        "aqi_level": "良",
        "lifestyle": []
      }
    ]
  }
}
```

---

## 🛠️ 技术栈与架构

- **Web 核心**: [FastAPI](https://fastapi.tiangolo.com) 0.104+
- **数据序列化与校验**: [Pydantic V2](https://docs.pydantic.dev/) (`model_dump` 全量标准化)
- **分布式调度**: [Celery](https://docs.celeryproject.org/) 5.3+ (Redis Broker)
- **动态调度器**: 自定义 `DynamicMongoScheduler` (监听 Redis 热重载信号)
- **数据存储**: MongoDB 4.6+ (按渠道隔离存储城市异构天气快照)
- **高速缓存与计数**: Redis 5.0+ (生命周期治理，TTL 自动驱逐过期键)
- **结构化日志**: [Loguru](https://github.com/Delgan/loguru) (支持自动按日轮转与上下文追踪)

---

## 📂 项目结构说明

```text
WeatherAggregator/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── admin.py        # 管理后台 API (密钥管理、调度配置、数据触发)
│   │           └── weather.py      # 天气对外聚合 API (Path/Query 双向路由)
│   ├── core/
│   │   ├── config.py               # 环境变量配置 (已移除 SSH，统一直连)
│   │   ├── db.py                   # MongoDB 与 Redis 单例直连管理
│   │   ├── key_manager.py          # 三方数据源 Key 池管理 (带 TTL 生命周期)
│   │   ├── client_key_manager.py   # 客户端 Key 鉴权/限流/平滑修改迁移
│   │   └── city_manager.py         # 城市库元数据与映射管理
│   ├── models/
│   │   └── weather.py              # Pydantic V2 天气核心数据模型
│   ├── worker/
│   │   ├── fetchers/               # 数据抓取器工厂模块
│   │   │   ├── registry.py         # FetcherRegistry 工厂类
│   │   │   ├── base.py             # 抓取器抽象基类
│   │   │   ├── hefeng.py           # 和风天气抓取器
│   │   │   ├── yike.py             # 易客天气抓取器
│   │   │   └── baidu.py            # 百度地图天气抓取器
│   │   ├── scheduler.py            # DynamicMongoScheduler 动态调度器
│   │   └── tasks.py                # Celery 采集与同步任务
│   ├── static/                     # 管理后台前端静态资源 (Glassmorphism CSS / JS)
│   ├── templates/                  # 后台 HTML 视图
│   ├── celery_app.py               # Celery 应用配置与调度器挂载
│   └── main.py                     # FastAPI 应用程序入口
├── tests/
│   ├── test_optimizations.py       # 核心业务与架构优化综合测试
│   └── test_cron_schedule.py      # 调度器规则解析单元测试
├── docker-compose.yml              # 生产级多服务容器编排
├── Dockerfile                      # 服务镜像定义
└── requirements.txt                # 纯净运行依赖 (已精简无用包)
```

---

## ⚙️ 环境配置说明 (.env)

系统全面采用数据库直连机制，无需额外的 SSH 隧道代理。在项目根目录 `.env` 中配置：

```ini
# 运行环境 (development / production)
APP_ENV=production

# Web 服务绑定端口
WEB_PORT=18050

# MongoDB 直连配置
MONGO_HOST=127.0.0.1
MONGO_PORT=27017
MONGO_USER=root
MONGO_PASS=your_mongo_password
MONGO_DB=weather_aggregator
AUTH_DB=admin

# Redis 直连配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASS=your_redis_password

# 管理后台登录超级密钥
ADMIN_LOGIN_KEY=sk-snkjcx970506
```

---

## 🎛️ 管理后台功能与动态调度

访问 `http://localhost:18050/admin`，输入配置的 `ADMIN_LOGIN_KEY` 即可进入管理面板：

1. **客户端密钥管理**:
   - 生成新密钥、设置 QPM 限流（0 为不限）、配置 IP 白名单。
   - **自定义密钥值**：点击“编辑”可将随机生成的 Key 修改为业务指定的值，历史 7 天的每日调用统计自动平滑迁移至新 Key，监控报表不丢失。
2. **数据渠道监控与动态调度**:
   - 实时监控各渠道可用 Key 数量、3 日调用量以及活跃状态。
   - **定时调度配置**：点击卡片上的“定时调度”，可配置 Cron 表达式与渠道启停，提供常见频率快捷标签（每 15/30 分钟、每 1/2/6 小时、每日凌晨），支持设置防风控随机延时秒数（0~N秒抖动）。
   - **热重载生效**：保存配置后 Celery Beat 会在 **5 秒内** 自动加载新周期，无需重启服务。
   - **一键更新**：后台任务异步触发单个渠道的全量城市实时采集。

---

## 🔧 开发者扩展指南

### 如何新增一个天气数据源？

得益于 `FetcherRegistry` 工厂模式，新增数据源只需 2 步：

1. 在 `app/worker/fetchers/` 目录下新建抓取器文件（如 `caiyun.py`）。
2. 继承 `BaseFetcher` 并添加 `@FetcherRegistry.register("渠道唯一标识")` 注解：

```python
from app.worker.fetchers.base import BaseFetcher
from app.worker.fetchers.registry import FetcherRegistry
from app.models.weather import StandardDailyWeather

@FetcherRegistry.register("caiyun")
class CaiyunFetcher(BaseFetcher):
    CHANNEL_NAME = "caiyun"

    def fetch(self, city_id: str) -> dict:
        # 1. 调用第三方 API 获取原始天气数据
        ...
        return raw_json

    def normalize(self, raw_data: dict) -> list[StandardDailyWeather]:
        # 2. 将原始数据清洗为统一 StandardDailyWeather 模型列表
        ...
        return standard_weather_list
```

3. 在 `app/worker/fetchers/__init__.py` 中导入该模块即可。Celery 任务和实时聚合接口将自动识别并加载该新渠道，无需修改任何核心路由与调度代码！

### 运行测试套件

```bash
# 运行全部优化与规范单元测试 (耗时 < 1 秒)
python -m unittest tests/test_optimizations.py

# 运行定时任务调度规则测试
python tests/test_cron_schedule.py
```

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。
