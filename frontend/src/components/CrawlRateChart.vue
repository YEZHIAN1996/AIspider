<template>
  <div ref="chartRef" style="width: 100%; height: 300px"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  times: string[]
  values: number[]
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function updateChart() {
  if (!chart) return
  chart.setOption({
    xAxis: { data: props.times },
    series: [{ data: props.values }],
  })
}

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: props.times },
    yAxis: { type: 'value', name: 'items/s' },
    series: [{
      type: 'line',
      smooth: true,
      data: props.values,
      areaStyle: { opacity: 0.3 },
    }],
  })
})

watch(() => [props.times, props.values], updateChart, { deep: true })

onUnmounted(() => chart?.dispose())
</script>
