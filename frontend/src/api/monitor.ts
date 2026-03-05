import http from './http'
import type { DashboardData, HealthReport } from '@/types'

export const monitorApi = {
  dashboard: () => http.get<DashboardData>('/monitor/dashboard'),
  health: () => http.get<HealthReport>('/monitor/health'),
}
