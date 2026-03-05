# 前端 Bug 修复报告

## 发现的问题

### 1. 创建任务表单缺少必填字段 ❌
**位置**: `frontend/src/views/Tasks.vue`
**问题**: 创建任务时缺少 `spider_args` 参数，后端要求至少一个 URL
**影响**: 点击"创建任务"按钮会报错 400

**修复**:
```typescript
// 添加 spider_args 字段
const createForm = reactive({
  spider_name: '',
  schedule_type: 'cron' as 'cron' | 'interval',
  schedule_expr: '',
  spider_args: '',  // 新增
})

// 表单中添加输入框
<n-form-item label="Spider 参数 (URL)" required>
  <n-input v-model:value="createForm.spider_args" placeholder="https://example.com" />
</n-form-item>
```

### 2. 创建任务数据格式错误 ❌
**位置**: `frontend/src/stores/tasks.ts`
**问题**: `spider_args` 应该是数组，但表单传的是字符串
**影响**: 后端接收到错误的数据格式

**修复**:
```typescript
async function createTask(data: Record<string, any>) {
  const payload = {
    ...data,
    spider_args: data.spider_args ? [data.spider_args] : []
  }
  await tasksApi.create(payload)
  await fetchTasks()
}
```

### 3. 错误处理不完整 ⚠️
**位置**: `frontend/src/views/Tasks.vue`
**问题**: `handleStart` 和 `handleStop` 没有 try-catch
**影响**: 操作失败时没有错误提示

**修复**:
```typescript
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
```

### 4. 表单验证缺失 ⚠️
**位置**: `frontend/src/views/Tasks.vue`
**问题**: 没有验证必填字段
**影响**: 可以提交空表单

**修复**:
```typescript
async function handleCreate() {
  if (!createForm.spider_name || !createForm.schedule_expr || !createForm.spider_args) {
    message.warning('请填写所有必填字段')
    return false
  }
  try {
    await tasksStore.createTask(createForm)
    message.success('任务创建成功')
    showCreate.value = false
    // 重置表单
    Object.assign(createForm, {
      spider_name: '',
      schedule_type: 'cron',
      schedule_expr: '',
      spider_args: ''
    })
  } catch {
    message.error('创建失败')
  }
}
```

## 优先级

- 🔴 高优先级: 问题 1、2（导致功能完全不可用）
- 🟡 中优先级: 问题 3、4（影响用户体验）
