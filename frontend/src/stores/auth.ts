import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { UserPayload } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')

  const payload = computed<UserPayload | null>(() => {
    if (!token.value) return null
    try {
      const base64 = token.value.split('.')[1]
      return JSON.parse(atob(base64))
    } catch {
      return null
    }
  })

  const isLoggedIn = computed(() => {
    if (!payload.value) return false
    return payload.value.exp * 1000 > Date.now()
  })

  const role = computed(() => payload.value?.role || null)
  const username = computed(() => payload.value?.sub || '')

  async function login(user: string, pass: string) {
    const { data } = await authApi.login({ username: user, password: pass })
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
  }

  function logout() {
    token.value = ''
    localStorage.removeItem('token')
  }

  return { token, payload, isLoggedIn, role, username, login, logout }
})
