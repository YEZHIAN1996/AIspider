<template>
  <n-space vertical :size="16">
    <n-h3 style="margin: 0">日志查询</n-h3>

    <!-- 过滤栏 -->
    <n-card>
      <n-form inline>
        <n-form-item label="关键词">
          <n-input v-model:value="keyword" placeholder="搜索关键词" clearable style="width: 200px" />
        </n-form-item>
        <n-form-item label="日志等级">
          <n-select
            v-model:value="level"
            :options="levelOptions"
            clearable
            style="width: 150px"
          />
        </n-form-item>
        <n-form-item label="时间范围">
          <n-date-picker v-model:value="timeRange" type="datetimerange" clearable />
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="loading" @click="handleSearch">查询</n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <!-- 结果表 -->
    <n-card>
      <n-data-table
        :columns="columns"
        :data="logs"
        :loading="loading"
        :bordered="false"
        :pagination="pagination"
        :row-class-name="rowClassName"
        remote
        @update:page="handlePageChange"
      />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { dataApi } from '@/api/data'

const message = useMessage()
const loading = ref(false)
const logs = ref<Record<string, any>[]>([])
const totalCount = ref(0)
const page = ref(1)

const keyword = ref('')
const level = ref<string | null>(null)
const timeRange = ref<[number, number] | null>(null)

const levelOptions = [
  { label: 'DEBUG', value: 'DEBUG' },
  { label: 'INFO', value: 'INFO' },
  { label: 'WARNING', value: 'WARNING' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'CRITICAL', value: 'CRITICAL' },
]

const columns: DataTableColumns = [
  { title: '时间', key: 'timestamp', width: 180 },
  { title: 'Spider ID', key: 'spider_id', width: 160 },
  { title: '等级', key: 'level', width: 100 },
  { title: '消息', key: 'message', ellipsis: { tooltip: true } },
]

const pagination = computed(() => ({
  page: page.value,
  pageSize: 20,
  itemCount: totalCount.value,
}))

function rowClassName(row: Record<string, any>) {
  const lvl = row.level || ''
  if (lvl === 'ERROR' || lvl === 'CRITICAL') return 'log-row-error'
  if (lvl === 'WARNING') return 'log-row-warn'
  return ''
}

async function handleSearch() {
  loading.value = true
  try {
    const filters: Record<string, any> = {}
    if (keyword.value) filters.message = keyword.value
    if (level.value) filters.level = level.value
    if (timeRange.value) {
      filters.time_start = timeRange.value[0]
      filters.time_end = timeRange.value[1]
    }
    const res = await dataApi.query({
      table: 'spider_logs',
      filters,
      sort_by: 'timestamp',
      sort_order: 'desc',
      page: page.value,
      page_size: 20,
    })
    logs.value = res.data.data
    totalCount.value = res.data.total
  } catch {
    message.error('查询失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(p: number) {
  page.value = p
  handleSearch()
}
</script>

<style>
.log-row-error td {
  background-color: rgba(255, 0, 0, 0.06) !important;
}
.log-row-warn td {
  background-color: rgba(255, 165, 0, 0.06) !important;
}
</style>
