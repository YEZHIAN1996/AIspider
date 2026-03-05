<template>
  <n-space vertical :size="16">
    <n-h3 style="margin: 0">数据查询</n-h3>

    <!-- 查询构建器 -->
    <n-card title="查询条件">
      <n-form inline :model="query">
        <n-form-item label="数据表">
          <n-select
            v-model:value="query.table"
            :options="tableOptions"
            style="width: 200px"
          />
        </n-form-item>
        <n-form-item label="排序字段">
          <n-input v-model:value="query.sort_by" placeholder="字段名" style="width: 150px" />
        </n-form-item>
        <n-form-item label="排序方向">
          <n-radio-group v-model:value="query.sort_order">
            <n-radio value="desc">降序</n-radio>
            <n-radio value="asc">升序</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="loading" @click="handleQuery">查询</n-button>
        </n-form-item>
        <n-form-item>
          <n-button @click="handleExport" :disabled="!results.length">导出 CSV</n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <!-- 过滤条件 -->
    <n-card title="过滤条件">
      <n-dynamic-input v-model:value="filters" :on-create="onCreateFilter">
        <template #default="{ value }">
          <n-space>
            <n-input v-model:value="value.key" placeholder="字段名" style="width: 150px" />
            <n-input v-model:value="value.val" placeholder="值" style="width: 200px" />
          </n-space>
        </template>
      </n-dynamic-input>
    </n-card>

    <!-- 查询结果 -->
    <n-card title="查询结果">
      <n-data-table
        :columns="resultColumns"
        :data="results"
        :loading="loading"
        :bordered="false"
        :pagination="pagination"
        remote
        @update:page="handlePageChange"
      />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { dataApi } from '@/api/data'

const message = useMessage()
const loading = ref(false)
const results = ref<Record<string, any>[]>([])
const totalCount = ref(0)

const tableOptions = [
  { label: 'spider_results', value: 'spider_results' },
  { label: 'spider_logs', value: 'spider_logs' },
  { label: 'spider_tasks', value: 'spider_tasks' },
]

const query = reactive({
  table: 'spider_results',
  sort_by: '' as string | undefined,
  sort_order: 'desc' as 'asc' | 'desc',
  page: 1,
  page_size: 20,
})

const filters = ref<{ key: string; val: string }[]>([])

function onCreateFilter() {
  return { key: '', val: '' }
}

const pagination = computed(() => ({
  page: query.page,
  pageSize: query.page_size,
  itemCount: totalCount.value,
}))

const resultColumns = computed<DataTableColumns>(() => {
  if (!results.value.length) return []
  return Object.keys(results.value[0]).map((key) => ({
    title: key,
    key,
    ellipsis: { tooltip: true },
  }))
})

async function handleQuery() {
  loading.value = true
  try {
    const filterObj: Record<string, any> = {}
    for (const f of filters.value) {
      if (f.key) filterObj[f.key] = f.val
    }
    const res = await dataApi.query({
      table: query.table,
      filters: filterObj,
      sort_by: query.sort_by || undefined,
      sort_order: query.sort_order,
      page: query.page,
      page_size: query.page_size,
    })
    results.value = res.data.data
    totalCount.value = res.data.total
  } catch {
    message.error('查询失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  query.page = page
  handleQuery()
}

function handleExport() {
  if (!results.value.length) return
  const keys = Object.keys(results.value[0])
  const header = keys.join(',')
  const rows = results.value.map((r) =>
    keys.map((k) => JSON.stringify(r[k] ?? '')).join(','),
  )
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${query.table}_export.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
