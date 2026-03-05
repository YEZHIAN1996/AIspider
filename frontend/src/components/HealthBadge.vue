<template>
  <n-tag :type="status === 'ok' ? 'success' : 'error'" size="small">
    {{ name }}: {{ status }}
  </n-tag>
</template>

<script setup lang="ts">
defineProps<{
  name: string
  status: string
}>()
</script>
