<template>
  <n-card>
    <n-statistic :label="label" :value="value">
      <template v-if="suffix" #suffix>{{ suffix }}</template>
    </n-statistic>
  </n-card>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: number | string
  suffix?: string
}>()
</script>
