import http from './http'
import type { ProxyStatus } from '@/types'

export const proxiesApi = {
  status: () => http.get<ProxyStatus>('/proxies/'),
  refresh: () => http.post('/proxies/refresh'),
}
