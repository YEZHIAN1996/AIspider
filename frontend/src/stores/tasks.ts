import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tasksApi } from '@/api/tasks'
import type { Task } from '@/types'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchTasks() {
    loading.value = true
    try {
      const res = await tasksApi.list()
      tasks.value = res.data.tasks
      total.value = res.data.total
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: Record<string, any>) {
    const payload = {
      ...data,
      spider_args: data.spider_args ? [data.spider_args] : []
    }
    await tasksApi.create(payload)
    await fetchTasks()
  }

  async function startTask(id: string) {
    await tasksApi.start(id)
    await fetchTasks()
  }

  async function stopTask(id: string) {
    await tasksApi.stop(id)
    await fetchTasks()
  }

  async function deleteTask(id: string) {
    await tasksApi.delete(id)
    await fetchTasks()
  }

  return { tasks, total, loading, fetchTasks, createTask, startTask, stopTask, deleteTask }
})
