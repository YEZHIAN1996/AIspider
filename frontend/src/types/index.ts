// ---- Auth ----
export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  role: 'admin' | 'operator'
}

export interface UserPayload {
  sub: string
  role: 'admin' | 'operator'
  iat: number
  exp: number
}

// ---- Tasks ----
export interface Task {
  task_id: string
  spider_name: string
  schedule_type: 'cron' | 'interval'
  schedule_expr: string
  enabled: boolean
  spider_args: string[]
  created_at: number
  last_run: number | null
  status: 'idle' | 'running' | 'paused'
}

export interface TaskListResponse {
  tasks: Task[]
  total: number
}

// ---- Seeds ----
export interface SeedQueue {
  spider_name: string
  size: number
  priority_range: [number, number]
}

export interface SeedListResponse {
  queues: SeedQueue[]
  total: number
}

// ---- Proxies ----
export interface ProxyStatus {
  pool_size: number
  bad_count: number
}

// ---- Monitor ----
export interface SpiderStatus {
  spider_id: string
  spider_name: string
  status: string
  restart_count: number
  pid: number | null
}

export interface Alert {
  id: string
  level: string
  message: string
  timestamp: number
}

export interface DashboardData {
  spiders: SpiderStatus[]
  alerts: Alert[]
  stats: Record<string, number>
}

export interface ComponentHealth {
  status: string
  latency_ms: number
  detail: string
}

export interface HealthReport {
  healthy: boolean
  checked_at: number
  components: Record<string, ComponentHealth>
}

// ---- Data Query ----
export interface DataQuery {
  table: string
  filters: Record<string, any>
  sort_by?: string
  sort_order: 'asc' | 'desc'
  page: number
  page_size: number
}

export interface DataQueryResponse {
  data: Record<string, any>[]
  total: number
  page: number
}
