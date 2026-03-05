<template>
  <n-space vertical :size="16">
    <n-space justify="space-between">
      <n-h3 style="margin: 0">种子管理</n-h3>
      <n-space>
        <n-button @click="showAdd = true">手动添加</n-button>
        <n-upload
          :show-file-list="false"
          accept=".csv,.json"
          :custom-request="handleImport"
        >
          <n-button type="primary">批量导入</n-button>
        </n-upload>
      </n-space>
    </n-space>

    <!-- 统计卡片 -->
    <n-grid :cols="3" :x-gap="16">
      <n-gi>
        <n-card>
          <n-statistic label="队列总数" :value="queues.length" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic label="种子总量" :value="totalSeeds" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card>
          <n-statistic label="Spider 数" :value="queues.length" />
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 队列表 -->
    <n-data-table
      :columns="columns"
      :data="queues"
      :loading="loading"
      :bordered="false"
    />

    <!-- 手动添加弹窗 -->
    <n-modal
      v-model:show="showAdd"
      preset="dialog"
      title="添加种子"
      positive-text="确认"
      @positive-click="handleAdd"
    >
      <n-form :model="addForm">
        <n-form-item label="URL">
          <n-input v-model:value="addForm.url" placeholder="https://example.com" />
        </n-form-item>
        <n-form-item label="Spider 名称">
          <n-input v-model:value="addForm.spider_name" placeholder="example_spider" />
        </n-form-item>
        <n-form-item label="优先级">
          <n-input-number v-model:value="addForm.priority" :min="0" :max="10" />
        </n-form-item>
      </n-form>
    </n-modal>
  </n-space>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import type { DataTableColumns, UploadCustomRequestOptions } from 'naive-ui'
import { seedsApi } from '@/api/seeds'
import type { SeedQueue } from '@/types'

const message = useMessage()
const loading = ref(false)
const queues = ref<SeedQueue[]>([])
const showAdd = ref(false)

const addForm = reactive({
  url: '',
  spider_name: '',
  priority: 5,
})

const totalSeeds = computed(() =>
  queues.value.reduce((sum, q) => sum + q.size, 0),
)

const columns: DataTableColumns<SeedQueue> = [
  { title: 'Spider', key: 'spider_name' },
  { title: '队列大小', key: 'size' },
  {
    title: '优先级范围',
    key: 'priority_range',
    render(row) {
      return `${row.priority_range[0]} - ${row.priority_range[1]}`
    },
  },
]

async function fetchQueues() {
  loading.value = true
  try {
    const res = await seedsApi.list()
    queues.value = res.data.queues
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  if (!addForm.url || !addForm.spider_name) {
    message.warning('请填写 URL 和 Spider 名称')
    return
  }
  try {
    await seedsApi.importSeeds({
      url: addForm.url,
      spider_name: addForm.spider_name,
      priority: addForm.priority
    })
    message.success('种子添加成功')
    showAdd.value = false
    Object.assign(addForm, { url: '', spider_name: '', priority: 5 })
    await fetchQueues()
  } catch (error) {
    message.error('添加失败')
    throw error
  }
}

async function handleImport(options: UploadCustomRequestOptions) {
  const file = options.file.file
  if (!file) return
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    await seedsApi.importSeeds(data)
    message.success('导入成功')
    await fetchQueues()
  } catch {
    message.error('导入失败，请检查文件格式')
  }
}

onMounted(fetchQueues)
</script>
