import http from './http'
import type { TaskListResponse } from '@/types'

export const tasksApi = {
  list: () => http.get<TaskListResponse>('/tasks/'),
  create: (data: Record<string, any>) => http.post('/tasks/', data),
  update: (id: string, data: Record<string, any>) => http.put(`/tasks/${id}`, data),
  start: (id: string) => http.post(`/tasks/${id}/start`),
  stop: (id: string) => http.post(`/tasks/${id}/stop`),
  delete: (id: string) => http.delete(`/tasks/${id}`),
}
