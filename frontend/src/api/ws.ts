import { useWebSocket } from '@vueuse/core'

function getWsBaseUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

function buildWsUrl(path: string): string {
  const token = localStorage.getItem('token') || ''
  const url = new URL(`${getWsBaseUrl()}${path}`)
  if (token) {
    url.searchParams.set('token', token)
  }
  return url.toString()
}

export function useDashboardWs() {
  return useWebSocket(buildWsUrl('/ws/dashboard'), {
    autoReconnect: { retries: 5, delay: 3000 },
    heartbeat: { message: 'ping', interval: 30000 },
  })
}

export function useLogWs(spiderId: string) {
  return useWebSocket(buildWsUrl(`/ws/logs/${spiderId}`), {
    autoReconnect: { retries: 3, delay: 2000 },
  })
}

export function useAlertWs() {
  return useWebSocket(buildWsUrl('/ws/alerts'), {
    autoReconnect: { retries: 5, delay: 3000 },
  })
}
