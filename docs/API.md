# API 文档

## 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token
- **Content-Type**: `application/json`

## 认证

### 登录

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 使用 Token

```http
GET /api/v1/tasks
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 任务管理

### 创建任务

```http
POST /api/v1/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "spider_name": "my_spider",
  "schedule_type": "cron",
  "schedule_expr": "0 */6 * * *",
  "spider_args": ["-a", "url=https://example.com"]
}
```

**参数说明**:
- `spider_name`: 爬虫名称（必需）
- `schedule_type`: 调度类型，`cron` 或 `interval`
- `schedule_expr`: Cron 表达式或间隔秒数
- `spider_args`: 爬虫参数列表

**响应**:
```json
{
  "task_id": "task_a1b2c3d4",
  "spider_name": "my_spider",
  "schedule_type": "cron",
  "schedule_expr": "0 */6 * * *",
  "enabled": true
}
```

### 查询任务列表

```http
GET /api/v1/tasks
Authorization: Bearer <token>
```

**响应**:
```json
[
  {
    "task_id": "task_a1b2c3d4",
    "spider_name": "my_spider",
    "schedule_type": "cron",
    "schedule_expr": "0 */6 * * *",
    "enabled": true
  }
]
```

### 启动任务

```http
POST /api/v1/tasks/{task_id}/start
Authorization: Bearer <token>
```

**响应**:
```json
{
  "command_id": "cmd_x1y2z3",
  "status": "queued"
}
```

### 停止任务

```http
POST /api/v1/tasks/{task_id}/stop
Authorization: Bearer <token>
```

### 删除任务

```http
DELETE /api/v1/tasks/{task_id}
Authorization: Bearer <token>
```

---

## 种子管理

### 批量添加种子

```http
POST /api/v1/seeds/batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "spider_name": "my_spider",
  "urls": [
    "https://example.com/page/1",
    "https://example.com/page/2"
  ],
  "priority": 5.0
}
```

**响应**:
```json
{
  "added": 2,
  "duplicated": 0
}
```

### 查询队列状态

```http
GET /api/v1/seeds/{spider_name}/queue
Authorization: Bearer <token>
```

**响应**:
```json
{
  "spider_name": "my_spider",
  "queue_size": 1234,
  "top_seeds": [
    {"url": "https://example.com/page/1", "priority": 5.0}
  ]
}
```

---

## 代理管理

### 查询代理池状态

```http
GET /api/v1/proxies/status
Authorization: Bearer <token>
```

**响应**:
```json
{
  "total": 150,
  "available": 142,
  "providers": {
    "pandas": 150
  }
}
```

### 手动刷新代理池

```http
POST /api/v1/proxies/refresh
Authorization: Bearer <token>
```

---

## 监控

### 查询运行状态

```http
GET /api/v1/monitor/status
Authorization: Bearer <token>
```

**响应**:
```json
{
  "updated_at": 1709712345.678,
  "processes": [
    {
      "spider_name": "my_spider",
      "spider_id": "task_a1b2c3d4",
      "status": "running",
      "pid": 12345
    }
  ]
}
```

### Prometheus 指标

```http
GET /metrics
```

**响应**: Prometheus 格式的指标数据

---

## WebSocket

### 实时日志

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/logs');
ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(log);
};
```

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 完整 API 文档

访问 http://localhost:8000/docs 查看 Swagger UI 交互式文档
