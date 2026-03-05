import { defineStore } from 'pinia'
import { ref } from 'vue'
import { monitorApi } from '@/api/monitor'
import type { DashboardData, HealthReport } from '@/types'

export const useDashboardStore = defineStore('dashboard', () => {
  const data = ref<DashboardData>({ spiders: [], alerts: [], stats: {} })
  const health = ref<HealthReport | null>(null)
  const loading = ref(false)

  async function fetchDashboard() {
    loading.value = true
    try {
      const res = await monitorApi.dashboard()
      data.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchHealth() {
    const res = await monitorApi.health()
    health.value = res.data
  }

  return { data, health, loading, fetchDashboard, fetchHealth }
})
