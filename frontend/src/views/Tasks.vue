<template>
  <n-space vertical :size="16">
    <n-space justify="space-between">
      <n-h3 style="margin: 0">任务列表</n-h3>
      <n-button type="primary" @click="showCreate = true">创建任务</n-button>
    </n-space>

    <n-data-table
      :columns="columns"
      :data="tasksStore.tasks"
      :loading="tasksStore.loading"
      :bordered="false"
    />

    <!-- 创建任务弹窗 -->
    <n-modal v-model:show="showCreate" preset="dialog" title="创建任务" positive-text="确认" @positive-click="handleCreate">
      <n-form :model="createForm">
        <n-form-item label="Spider 名称">
          <n-input v-model:value="createForm.spider_name" placeholder="example_spider" />
        </n-form-item>
        <n-form-item label="调度类型">
          <n-radio-group v-model:value="createForm.schedule_type">
            <n-radio value="cron">Cron</n-radio>
            <n-radio value="interval">Interval</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="调度表达式">
          <n-input v-model:value="createForm.schedule_expr" placeholder="*/30 * * * * 或 3600" />
        </n-form-item>
        <n-form-item label="Spider 参数 (URL)" help="可选，某些爬虫自带初始请求">
          <n-input v-model:value="createForm.spider_args" placeholder="https://example.com (可选)" />
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- 日志抽屉 -->
    <n-drawer v-model:show="showLogs" :width="600" placement="right">
      <n-drawer-content :title="`日志 - ${logSpiderId}`">
        <log-viewer :spider-id="logSpiderId" />
      </n-drawer-content>
    </n-drawer>
  </n-space>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NSpace, NTag, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useTasksStore } from '@/stores/tasks'
import LogViewer from '@/components/LogViewer.vue'
import type { Task } from '@/types'

const tasksStore = useTasksStore()
const message = useMessage()

const showCreate = ref(false)
const showLogs = ref(false)
const logSpiderId = ref('')

const createForm = reactive({
  spider_name: '',
  schedule_type: 'cron' as 'cron' | 'interval',
  schedule_expr: '',
  spider_args: '',
})

const columns: DataTableColumns<Task> = [
  { title: 'Task ID', key: 'task_id', width: 180 },
  { title: 'Spider', key: 'spider_name' },
  { title: '调度类型', key: 'schedule_type', width: 100 },
  { title: '调度表达式', key: 'schedule_expr' },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      const typeMap: Record<string, 'success' | 'warning' | 'default'> = {
        running: 'success',
        paused: 'warning',
        idle: 'default',
      }
      return h(NTag, { type: typeMap[row.status] || 'default', size: 'small' }, () => row.status)
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 240,
    render(row) {
      return h(NSpace, {}, () => [
        row.status !== 'running'
          ? h(NButton, { size: 'small', type: 'success', onClick: () => handleStart(row) }, () => '启动')
          : h(NButton, { size: 'small', type: 'warning', onClick: () => handleStop(row) }, () => '停止'),
        h(NButton, { size: 'small', onClick: () => openLogs(row) }, () => '日志'),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, () => '删除'),
      ])
    },
  },
]

async function handleCreate() {
  if (!createForm.spider_name || !createForm.schedule_expr) {
    message.warning('请填写 Spider 名称和调度表达式')
    return
  }
  try {
    await tasksStore.createTask(createForm)
    message.success('任务创建成功')
    showCreate.value = false
    Object.assign(createForm, { spider_name: '', schedule_type: 'cron', schedule_expr: '', spider_args: '' })
  } catch (error) {
    message.error('创建失败')
    throw error
  }
}

async function handleStart(task: Task) {
  try {
    await tasksStore.startTask(task.task_id)
    message.success('已启动')
  } catch {
    message.error('启动失败')
  }
}

async function handleStop(task: Task) {
  try {
    await tasksStore.stopTask(task.task_id)
    message.success('已停止')
  } catch {
    message.error('停止失败')
  }
}

async function handleDelete(task: Task) {
  try {
    await tasksStore.deleteTask(task.task_id)
    message.success('已删除')
  } catch {
    message.error('删除失败')
  }
}

function openLogs(task: Task) {
  logSpiderId.value = task.task_id
  showLogs.value = true
}

onMounted(() => tasksStore.fetchTasks())
</script>
