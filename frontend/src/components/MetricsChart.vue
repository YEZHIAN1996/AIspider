<template>
  <div ref="chartRef" class="metrics-chart" style="height: 300px"></div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  metrics: Array<{
    task_id: string
    success_rate: number
    duration: number
    items_scraped: number
  }>
}>()

const chartRef = ref<HTMLDivElement>()

onMounted(() => {
  if (!chartRef.value) return

  const chart = echarts.init(chartRef.value)
  chart.setOption({
    xAxis: { type: 'category', data: props.metrics.map(m => m.task_id) },
    yAxis: { type: 'value', name: '成功率 (%)' },
    series: [{ data: props.metrics.map(m => m.success_rate * 100), type: 'bar' }]
  })
})
</script>
