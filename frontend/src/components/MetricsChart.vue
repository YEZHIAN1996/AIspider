<template>
  <div class="metrics-chart">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps<{
  metrics: Array<{
    task_id: string
    success_rate: number
    duration: number
    items_scraped: number
  }>
}>()

const chartCanvas = ref<HTMLCanvasElement>()

onMounted(() => {
  if (!chartCanvas.value) return

  new Chart(chartCanvas.value, {
    type: 'bar',
    data: {
      labels: props.metrics.map(m => m.task_id),
      datasets: [{
        label: '成功率 (%)',
        data: props.metrics.map(m => m.success_rate * 100),
        backgroundColor: 'rgba(75, 192, 192, 0.6)'
      }]
    }
  })
})
</script>
