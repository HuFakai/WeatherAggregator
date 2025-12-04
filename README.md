# WeatherAggregator - 天气数据聚合服务

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个高性能的天气数据聚合服务，支持多渠道数据源聚合、智能缓存、速率限制和定时更新。

## ✨ 核心特性

- 🌤️ **多渠道聚合**: 集成易客天气(yiketianqi)和和风天气(hefeng)两大数据源
- ⚡ **智能缓存**: Redis 缓存机制，支持数据过期检测和自动刷新
- 🔐 **Key 轮转**: 自动管理多个 API Key，支持失效检测和重试机制
- 📊 **速率限制**: IP 白名单、QPM 限制、访问统计
- 🕐 **定时更新**: Celery 定时任务批量更新城市天气数据
- 🎨 **管理后台**: Web 界面管理城市、渠道、Key 配置
- 📈 **监控日志**: 完整的操作日志和错误追踪

## 🚀 快速开始

### 前提条件

- Docker & Docker Compose
- 或者: Python 3.8+, MongoDB, Redis

### Docker 部署（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/HuFakai/WeatherAggregator.git
cd WeatherAggregator

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要配置

# 3. 启动服务
docker-compose up -d

# 4. 访问服务
# API: http://localhost:18050
# 管理后台: http://localhost:18050/admin
```

### 本地开发

详见 [LOCAL_RUN_GUIDE.md](LOCAL_RUN_GUIDE.md)

## 📖 API 文档

### 获取天气数据

```bash
GET /api/v1/weather/{city}
```

**参数说明:**
- `city`: 城市名称或 ID (如: 北京, 101010100, 110100)
- `key`: (必填) API 访问密钥
- `channel`: (可选) 指定渠道(yiketianqi/hefeng),默认聚合所有渠道

**示例:**

```bash
# 使用城市代码获取天气(聚合所有渠道)
curl "http://localhost:18050/api/v1/weather/110100?key=your_api_key"

# 使用城市名称获取天气
curl "http://localhost:18050/api/v1/weather/北京?key=your_api_key"

# 指定易客天气渠道
curl "http://localhost:18050/api/v1/weather/110100?key=your_api_key&channel=yiketianqi"
```

**响应示例:**

```json
{
  "_id": "110100",
  "city_name": "北京",
  "last_updated_at": "2025-12-04T09:42:02.123456+08:00",
  "sources": {
    "hefeng": [
      {
        "date": "2025-12-04",
        "temp_high": 10,
        "temp_low": -2,
        "weather_day": "晴",
        "weather_night": "晴",
        "humidity": 30,
        "wind_direction": "北风",
        "wind_scale": "3-4级",
        "aqi": null,
        "aqi_level": null,
        "lifestyle": []
      }
    ],
    "yiketianqi": [
      {
        "date": "2025-12-04",
        "temp_high": 10,
        "temp_low": -2,
        "weather_day": "晴",
        "weather_night": "晴",
        "humidity": 30,
        "wind_direction": "无持续风向",
        "wind_scale": "<3级",
        "aqi": 85,
        "aqi_level": "良",
        "lifestyle": [
          {
            "title": "紫外线指数",
            "level": "中等",
            "desc": "涂擦SPF大于15、PA+防晒护肤品。"
          }
        ]
      }
    ]
  }
}
```

### 完整 API 文档

服务启动后访问: `http://localhost:18050/docs`

## 🛠️ 技术栈

- **Web 框架**: FastAPI
- **异步任务**: Celery + Redis
- **数据库**: MongoDB
- **缓存**: Redis
- **日志**: Loguru
- **容器化**: Docker + Docker Compose

## 📂 项目结构

```
WeatherAggregator/
├── app/
│   ├── api/              # API 路由
│   ├── core/             # 核心配置
│   ├── models/           # 数据模型
│   ├── worker/           # Celery 任务
│   │   └── fetchers/     # 数据抓取器
│   ├── static/           # 静态文件
│   └── templates/        # HTML 模板
├── tests/                # 测试文件
├── logs/                 # 日志文件
├── .env                  # 环境变量
├── docker-compose.yml    # Docker 编排
├── Dockerfile            # Docker 镜像
└── requirements.txt      # Python 依赖
```

## ⚙️ 配置说明

### 环境变量

在 `.env` 文件中配置以下变量:

```bash
# MongoDB
MONGO_URI=mongodb://localhost:27017/weather_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Admin
ADMIN_LOGIN_KEY=your_admin_key

# 服务配置
WEB_PORT=18050
```

### 管理后台

#### 登录

访问 `http://localhost:18050/admin`，使用 `ADMIN_LOGIN_KEY` 登录。

#### 功能

- **城市管理**: 添加/编辑城市信息、启用/禁用
- **渠道管理**: 配置渠道、设置定时任务、触发手动更新
- **Key 管理**: 添加 API Key、查看配额使用情况
- **访问控制**: IP 白名单、QPM 限制设置

## 📊 定时任务

系统支持自动定时更新天气数据:

```python
# 配置示例（在后台管理界面设置）
{
  "yiketianqi": "0 */6 * * *",   # 每6小时
  "hefeng": "30 */6 * * *"       # 每6小时（错峰）
}
```

## 🔧 开发指南

### 添加新的数据源

1. 在 `app/worker/fetchers/` 创建新的 fetcher 类
2. 继承 `BaseFetcher` 并实现 `fetch()` 和 `normalize()` 方法
3. 在 `app/worker/tasks.py` 中注册新渠道

示例:

```python
class NewFetcher(BaseFetcher):
    def fetch(self, city: dict, key: dict) -> Optional[dict]:
        # 实现数据获取逻辑
        pass
    
    def normalize(self, raw_data: dict) -> dict:
        # 标准化数据格式
        pass
```

### 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行测试
pytest tests/
```

## 📝 日志

日志文件位于 `logs/` 目录:

- `weather.log`: 主日志文件（每日轮转）

日志级别可在 `app/core/logger.py` 中配置。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👨‍💻 作者

HuFakai - [@HuFakai](https://github.com/HuFakai)

## 🔗 相关链接

- [易客天气 API](https://www.yiketianqi.com/)
- [和风天气 API](https://dev.qweather.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Celery 文档](https://docs.celeryproject.org/)

---

⭐ 如果这个项目对你有帮助，请给它一个星标！
