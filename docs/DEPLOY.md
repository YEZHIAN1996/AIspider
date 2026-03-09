# 部署指南

## 环境准备

### 系统要求

- **操作系统**: Linux (Ubuntu 20.04+ / CentOS 7+) 或 macOS
- **Python**: 3.9+
- **内存**: 最低 4GB，推荐 8GB+
- **磁盘**: 最低 20GB 可用空间

### 依赖服务

| 服务 | 版本 | 用途 |
|------|------|------|
| Redis | 6.0+ | 队列、去重、分布式锁 |
| PostgreSQL | 13+ | 数据存储 |
| Kafka | 2.8+ | 实时数据流 |
| MinIO | RELEASE.2023+ | 媒体文件存储 |

---

## 快速部署（Docker Compose）

### 1. 克隆项目

```bash
git clone https://github.com/YEZHIAN1996/AIspider.git
cd AIspider
```

### 2. 配置环境变量

```bash
cp .env.example .env
vim .env
```

**必需配置**:
```bash
# JWT 密钥（必需，最少16字符）
AISPIDER_JWT_SECRET=<生成一个强密码>

# 环境标识
AISPIDER_ENV=prod

# 初始管理员账户（首次部署必需）
AISPIDER_BOOTSTRAP_ADMIN_USERNAME=admin
AISPIDER_BOOTSTRAP_ADMIN_PASSWORD=<设置管理员密码>
```

**生成强密码**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. 启动服务

```bash
docker compose up -d
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker exec aispider-api-1 alembic upgrade head
```

### 5. 验证部署

```bash
# 健康检查
./deploy/health_check.sh

# 测试登录（使用步骤2配置的管理员账户）
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'
```

**预期输出**:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "admin"
}
```

---

## 手动部署

### 1. 安装 Python 依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
# PostgreSQL
psql -U postgres -c "CREATE DATABASE aispider;"
psql -U postgres -d aispider -f deploy/schema.sql
```

### 3. 启动服务

```bash
# 方式1: 统一入口
python main.py all

# 方式2: 分别启动
python main.py api &
python main.py scheduler &
python main.py worker &
```

---

## 生产环境配置

### 安全配置

```bash
# .env
AISPIDER_ENV=prod
AISPIDER_JWT_SECRET=<强密码>
AISPIDER_CORS_ORIGINS=https://your-domain.com
AISPIDER_LOG_LEVEL=WARNING
```

### 性能调优

```bash
# PostgreSQL 连接池
AISPIDER_PG_POOL_MIN=10
AISPIDER_PG_POOL_MAX=50

# 并发控制
CONCURRENT_REQUESTS=64
CONCURRENT_REQUESTS_PER_DOMAIN=16
```

### 监控配置

```bash
# Prometheus
docker run -d -p 9090:9090 \
  -v $(pwd)/deploy/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Grafana
docker run -d -p 3000:3000 grafana/grafana
# 导入 deploy/grafana-dashboard.json
```

---

## 扩展部署

### 水平扩展 Worker

```bash
# 本地扩展
./deploy/scale_workers.sh 8

# 远程节点
./deploy/add_remote_worker.sh ubuntu@192.168.1.101
./deploy/add_remote_worker.sh ubuntu@192.168.1.102
```

### 高可用部署

```bash
# Redis 哨兵模式
AISPIDER_REDIS_URL=redis-sentinel://sentinel1:26379,sentinel2:26379/mymaster

# PostgreSQL 主从复制
AISPIDER_PG_DSN=postgresql://user:pass@pgpool:5432/aispider
```

---

## 故障排查

### 常见问题

**1. 数据库表不存在**
```
spider_users table not found, run `alembic upgrade head`
```
解决: 运行数据库迁移
```bash
docker exec aispider-api-1 alembic upgrade head
```

**2. JWT Secret 错误**
```
ValidationError: AISPIDER_JWT_SECRET is required
```
解决: 在 .env 中设置 `AISPIDER_JWT_SECRET`

**3. 登录失败 - 无用户**
```
Invalid credentials
```
解决: 确保 .env 中配置了 `AISPIDER_BOOTSTRAP_ADMIN_USERNAME` 和 `AISPIDER_BOOTSTRAP_ADMIN_PASSWORD`，然后重启 API 服务
```bash
docker restart aispider-api-1
```

**4. Redis 连接失败**
```
ConnectionError: Error connecting to Redis
```
解决: 检查 Redis 是否启动，端口是否正确

**5. Worker 无法获取任务**
```
No tasks in queue
```
解决: 检查种子是否已注入，调度器是否运行

### 日志查看

```bash
# API 日志
tail -f /var/log/aispider/api.log

# Scheduler 日志
tail -f /var/log/aispider/scheduler.log

# Worker 日志
tail -f /var/log/aispider/worker.log
```

---

## 备份与恢复

### 数据库备份

```bash
pg_dump -U postgres aispider > backup.sql
```

### Redis 备份

```bash
redis-cli SAVE
cp /var/lib/redis/dump.rdb backup/
```

---

## 升级指南

```bash
# 1. 备份数据
./deploy/backup.sh

# 2. 拉取最新代码
git pull origin main

# 3. 更新依赖
pip install -r requirements.txt

# 4. 重启服务
docker-compose restart
```
