import axios from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// 请求拦截：附加 JWT
http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：401 跳转登录
http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default http
