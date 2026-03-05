# 告警规则配置说明

## 配置文件位置

默认读取项目根目录的 `alert_rules.yaml`，可通过环境变量 `ALERT_RULES_FILE` 自定义路径。

## 规则类型

### 1. 关键词匹配 (keyword)
匹配日志消息中是否包含指定关键词。

```yaml
- name: error_alert
  match_type: keyword
  pattern: ["ERROR", "Exception"]
  level: critical
  enabled: true
```

### 2. 正则匹配 (regex)
使用正则表达式匹配日志消息。

```yaml
- name: timeout_alert
  match_type: regex
  pattern: "timeout.*\\d+s"
  level: warning
  enabled: true
```

### 3. 日志级别匹配 (level)
匹配日志的级别字段。

```yaml
- name: critical_level
  match_type: level
  pattern: ["CRITICAL", "FATAL"]
  level: critical
  enabled: true
```

### 4. 字段匹配 (field)
匹配日志中的特定字段值。

```yaml
- name: spider_failed
  match_type: field
  pattern: "status=failed"
  level: warning
  enabled: true
```

## 告警级别

- `info`: 信息级别
- `warning`: 警告级别
- `critical`: 严重级别

## 使用方法

1. 复制示例配置：
```bash
cp alert_rules.example.yaml alert_rules.yaml
```

2. 编辑规则配置，启动 monitor 服务会自动加载。

3. 如未配置规则文件，系统使用默认硬编码规则（ERROR、CRITICAL、Exception 等）。
