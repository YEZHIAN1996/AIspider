<template>
  <n-space vertical :size="16">
    <n-space justify="space-between">
      <n-h3 style="margin: 0">代理池管理</n-h3>
      <n-button type="primary" :loading="refreshing" @click="handleRefresh">
        刷新代理池
      </n-button>
    </n-space>

    <n-grid :cols="3" :x-gap="16">
      <n-gi>
        <n-card>
          <n-statistic label="可用代理" :value="status.pool_size" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic label="失效代理" :value="status.bad_count" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic
            label="可用率"
            :value="availRate"
            suffix="%"
          />
        </n-card>
      </n-gi>
    </n-grid>

    <n-card title="代理池状态">
      <n-empty v-if="!status.pool_size" description="代理池为空，请刷新获取代理" />
      <n-alert v-else type="info">
        代理池模块为预留接口，当前显示汇总状态。
        详细代理列表将在代理池模块融入后展示。
      </n-alert>
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { proxiesApi } from '@/api/proxies'

const message = useMessage()
const refreshing = ref(false)
const status = reactive({ pool_size: 0, bad_count: 0 })

const availRate = computed(() => {
  const total = status.pool_size + status.bad_count
  if (!total) return 0
  return Math.round((status.pool_size / total) * 100)
})

async function fetchStatus() {
  try {
    const res = await proxiesApi.status()
    Object.assign(status, res.data)
  } catch { /* ignore */ }
}

async function handleRefresh() {
  refreshing.value = true
  try {
    await proxiesApi.refresh()
    message.success('代理池刷新成功')
    await fetchStatus()
  } catch {
    message.error('刷新失败')
  } finally {
    refreshing.value = false
  }
}

onMounted(fetchStatus)
</script>
