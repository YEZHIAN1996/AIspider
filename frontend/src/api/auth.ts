import http from './http'
import type { LoginRequest, LoginResponse } from '@/types'

export const authApi = {
  login: (data: LoginRequest) =>
    http.post<LoginResponse>('/auth/login', data),
}
