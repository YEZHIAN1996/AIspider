<template>
  <div style="position: relative">
    <div
      ref="containerRef"
      style="height: 400px; overflow-y: auto; background: #1e1e1e; color: #d4d4d4; padding: 12px; font-family: monospace; font-size: 13px; border-radius: 4px"
    >
      <div v-for="(line, i) in lines" :key="i" :style="lineStyle(line)">
        {{ line }}
      </div>
      <div v-if="!lines.length" style="color: #666">等待日志...</div>
    </div>
    <n-button
      size="small"
      style="position: absolute; top: 8px; right: 8px"
      @click="autoScroll = !autoScroll"
    >
      {{ autoScroll ? '暂停滚动' : '自动滚动' }}
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useLogWs } from '@/api/ws'

const props = defineProps<{ spiderId: string }>()

const containerRef = ref<HTMLElement>()
const lines = ref<string[]>([])
const autoScroll = ref(true)

const { data: wsData } = useLogWs(props.spiderId)

watch(wsData, (raw) => {
  if (!raw) return
  try {
    const msg = JSON.parse(raw)
    const text = msg.message || raw
    lines.value.push(text)
    if (lines.value.length > 500) {
      lines.value = lines.value.slice(-300)
    }
    if (autoScroll.value) {
      nextTick(() => {
        const el = containerRef.value
        if (el) el.scrollTop = el.scrollHeight
      })
    }
  } catch {
    lines.value.push(raw)
  }
})

function lineStyle(line: string) {
  if (line.includes('ERROR') || line.includes('CRITICAL')) {
    return { color: '#f44336' }
  }
  if (line.includes('WARNING')) {
    return { color: '#ff9800' }
  }
  if (line.includes('DEBUG')) {
    return { color: '#888' }
  }
  return {}
}
</script>
