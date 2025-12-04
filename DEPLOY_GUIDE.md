# 部署指南 (Deployment Guide)

本指南介绍如何在 1Panel 服务器上部署 WeatherAggregator 项目。

## 1. 环境准备

确保服务器已安装：
- **Docker & Docker Compose** (1Panel 默认已安装)
- **MongoDB** (运行在宿主机或 1Panel 容器中，端口 27017)
- **Redis** (运行在宿主机或 1Panel 容器中，端口 6379)

## 2. 部署步骤

### 2.1 上传代码
将项目代码上传到服务器目录，例如 `/opt/1panel/apps/weather-aggregator`。

### 2.2 配置环境变量
在项目根目录下创建或修改 `.env` 文件。
**注意**：由于我们使用 Docker 部署，且数据库在宿主机上，请确保 `.env` 中的配置如下（或者直接依赖 `docker-compose.yml` 中的默认覆盖）：

```ini
APP_ENV=production

# MongoDB (宿主机)
MONGO_HOST=host.docker.internal
MONGO_PORT=27017
MONGO_USER=root
MONGO_PASS=your_mongo_password
MONGO_DB=weather_aggregator
AUTH_DB=admin

# Redis (宿主机)
REDIS_HOST=host.docker.internal
REDIS_PORT=6379
REDIS_PASS=your_redis_password

# Admin Security
ADMIN_LOGIN_KEY=your_secure_admin_key
```

> **关于 `host.docker.internal`**:
> 在 `docker-compose.yml` 中，我们配置了 `extra_hosts: - "host.docker.internal:host-gateway"`。
> 这使得容器可以通过 `host.docker.internal` 域名访问宿主机的网络服务。
> 请确保您的 MongoDB 和 Redis 允许来自 `172.x.x.x` (Docker 网段) 的连接，或者绑定到 `0.0.0.0`。

### 2.3 启动服务
在项目根目录下执行：

```bash
# 构建并后台启动
docker compose up -d --build
```

### 2.4 验证部署
1.  查看容器状态：
    ```bash
    docker compose ps
    ```
    应该看到 `weather_app`, `weather_worker`, `weather_beat` 三个容器均为 `Up` 状态。

2.  查看日志：
    ```bash
    docker compose logs -f app
    ```

3.  访问管理后台：
    打开浏览器访问 `http://<服务器IP>:18050/admin`。

## 3. 常见问题

### 3.1 无法连接数据库
如果报错 `Connection refused`，请检查：
1.  MongoDB/Redis 是否在运行。
2.  MongoDB/Redis 的配置文件 (`mongod.conf`, `redis.conf`) 中 `bind` 是否为 `0.0.0.0` (如果绑定 `127.0.0.1`，容器无法访问)。
3.  服务器防火墙是否放行了相关端口（虽然 Docker 走内部网络，但有时防火墙规则会影响）。

### 3.2 1Panel 特殊配置
如果您使用的是 1Panel 的应用商店安装的 MongoDB/Redis，它们通常运行在 Docker 容器中。
- **方法 A (推荐)**: 使用 `host.docker.internal` (如上所述)，前提是数据库容器映射了端口到宿主机。
- **方法 B**: 将本项目加入到 1Panel 的 Docker 网络中 (`1panel-network`)，然后直接使用容器名连接。
    - 修改 `docker-compose.yml`:
      ```yaml
      networks:
        default:
          external:
            name: 1panel-network
      ```
    - 修改 `.env`: `MONGO_HOST=mongo` (假设 1Panel 中 Mongo 容器名为 mongo)。

### 3.3 "docker-compose: command not found" 错误
现在的 Docker 版本通常使用 `docker compose` (中间有空格) 而不是 `docker-compose` (中间有连字符)。
如果遇到此错误，请尝试使用 `docker compose up -d --build`。

## 4. 更新部署
代码更新后，执行：
```bash
docker compose down
docker compose up -d --build
```
## 5. 定时时间更新
定时时间更新后，执行：
重启 beat 服务以重新加载调度
```bash
docker compose restart beat
```