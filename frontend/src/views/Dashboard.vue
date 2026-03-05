<template>
  <n-space vertical :size="24">
    <!-- 统计卡片 -->
    <n-grid :cols="4" :x-gap="16">
      <n-gi>
        <n-card>
          <n-statistic label="运行中爬虫" :value="dashStore.data.spiders.filter(s => s.status === 'running').length" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic label="总抓取量" :value="dashStore.data.stats.total_items || 0" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic label="错误数" :value="dashStore.data.stats.total_errors || 0" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic label="队列积压" :value="dashStore.data.stats.queue_size || 0" />
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 健康状态 -->
    <n-card title="组件健康状态">
      <n-space v-if="dashStore.health" vertical :size="12">
        <n-space align="center">
          <n-tag :type="dashStore.health.healthy ? 'success' : 'error'">
            {{ dashStore.health.healthy ? '整体健康' : '存在异常' }}
          </n-tag>
          <n-text depth="3">检查时间：{{ formatCheckedAt(dashStore.health.checked_at) }}</n-text>
        </n-space>

        <n-grid :cols="2" :x-gap="12" :y-gap="12">
          <n-gi v-for="item in healthRows" :key="item.name">
            <n-card size="small">
              <n-space vertical :size="6">
                <n-space justify="space-between">
                  <n-text strong>{{ item.name }}</n-text>
                  <n-tag :type="item.status === 'ok' ? 'success' : 'error'">
                    {{ item.status }}
                  </n-tag>
                </n-space>
                <n-space align="center">
                  <n-text depth="2">延迟：{{ Number(item.latency_ms).toFixed(2) }} ms</n-text>
                  <n-tag size="small" :type="latencyTagType(item.latency_ms)">
                    {{ latencyLabel(item.latency_ms) }}
                  </n-tag>
                </n-space>
                <n-text v-if="item.detail" depth="2">详情：{{ item.detail }}</n-text>
              </n-space>
            </n-card>
          </n-gi>
        </n-grid>
      </n-space>
      <n-spin v-else size="small" />
    </n-card>

    <n-grid :cols="2" :x-gap="16">
      <!-- 抓取速率图表 -->
      <n-gi>
        <n-card title="抓取速率">
          <div ref="chartRef" style="height: 300px"></div>
        </n-card>
      </n-gi>

      <!-- 告警列表 -->
      <n-gi v-if="isAdmin">
        <n-card title="最近告警">
          <n-list v-if="dashStore.data.alerts.length">
            <n-list-item v-for="alert in dashStore.data.alerts" :key="alert.id">
              <n-thing>
                <template #header>
                  <n-tag :type="alertTagType(alert.level)" size="small">{{ alert.level }}</n-tag>
                </template>
                <template #description>
                  {{ alert.message }}
                </template>
              </n-thing>
            </n-list-item>
          </n-list>
          <n-empty v-else description="暂无告警" />
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Spider 状态表 -->
    <n-card title="Spider 状态">
      <n-data-table :columns="spiderColumns" :data="dashStore.data.spiders" :bordered="false" />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, computed } from 'vue'
import type { DataTableColumns } from 'naive-ui'
import * as echarts from 'echarts'
import { useDashboardStore } from '@/stores/dashboard'
import { useAuthStore } from '@/stores/auth'
import { useDashboardWs } from '@/api/ws'
import type { SpiderStatus, ComponentHealth } from '@/types'

const dashStore = useDashboardStore()
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.role === 'admin')
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let refreshTimer: ReturnType<typeof setInterval> | null = null

// WebSocket 实时数据
const { data: wsData } = useDashboardWs()
const healthRows = computed<Array<ComponentHealth & { name: string }>>(() => {
  const components = dashStore.health?.components || {}
  return Object.entries(components)
    .map(([name, info]) => ({ name, ...info }))
    .sort((a, b) => {
      // 异常优先展示，其次按延迟从高到低
      if (a.status !== b.status) return a.status === 'error' ? -1 : 1
      return Number(b.latency_ms) - Number(a.latency_ms)
    })
})

const chartData = ref<{ times: string[]; values: number[] }>({
  times: [],
  values: [],
})

watch(wsData, (raw) => {
  if (!raw) return
  try {
    const msg = JSON.parse(raw)
    if (msg.crawl_rate !== undefined) {
      const now = new Date().toLocaleTimeString()
      chartData.value.times.push(now)
      chartData.value.values.push(msg.crawl_rate)
      if (chartData.value.times.length > 60) {
        chartData.value.times.shift()
        chartData.value.values.shift()
      }
      updateChart()
    }
  } catch { /* ignore non-json */ }
})

function updateChart() {
  if (!chart) return
  chart.setOption({
    xAxis: { data: chartData.value.times },
    series: [{ data: chartData.value.values }],
  })
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: chartData.value.times },
    yAxis: { type: 'value', name: 'items/s' },
    series: [{
      type: 'line',
      smooth: true,
      data: chartData.value.values,
      areaStyle: { opacity: 0.3 },
    }],
  })
}

function alertTagType(level: string) {
  if (level === 'P0' || level === 'CRITICAL') return 'error'
  if (level === 'P1' || level === 'ERROR') return 'warning'
  return 'info'
}

function formatCheckedAt(ts: number) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString()
}

function latencyTagType(latencyMs: number) {
  if (latencyMs >= 500) return 'error'
  if (latencyMs >= 100) return 'warning'
  return 'success'
}

function latencyLabel(latencyMs: number) {
  if (latencyMs >= 500) return '高延迟'
  if (latencyMs >= 100) return '偏慢'
  return '正常'
}

const spiderColumns: DataTableColumns<SpiderStatus> = [
  { title: 'Spider ID', key: 'spider_id' },
  { title: '名称', key: 'spider_name' },
  { title: '状态', key: 'status' },
  { title: '重启次数', key: 'restart_count' },
  { title: 'PID', key: 'pid' },
]

onMounted(() => {
  dashStore.fetchDashboard()
  dashStore.fetchHealth()
  initChart()
  refreshTimer = setInterval(() => {
    dashStore.fetchDashboard()
    dashStore.fetchHealth()
  }, 30000)
})

onUnmounted(() => {
  chart?.dispose()
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>
