<template>
  <n-layout has-sider style="height: 100vh">
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      show-trigger
      :collapsed="collapsed"
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div style="padding: 16px; text-align: center; font-size: 18px; font-weight: bold">
        {{ collapsed ? 'AI' : 'AIspider' }}
      </div>
      <n-menu
        :options="menuOptions"
        :value="activeKey"
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        @update:value="handleMenuClick"
      />
    </n-layout-sider>
    <n-layout>
      <n-layout-header
        bordered
        style="height: 56px; padding: 0 24px; display: flex; align-items: center; justify-content: space-between"
      >
        <span style="font-size: 16px; font-weight: 500">{{ pageTitle }}</span>
        <n-space align="center">
          <span>{{ authStore.username }}</span>
          <n-tag :type="authStore.role === 'admin' ? 'success' : 'info'" size="small">
            {{ authStore.role }}
          </n-tag>
          <n-button text @click="handleLogout">退出</n-button>
        </n-space>
      </n-layout-header>
      <n-layout-content style="padding: 24px">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { h, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import {
  GridOutline,
  ListOutline,
  LeafOutline,
  ShieldOutline,
  SearchOutline,
  DocumentTextOutline,
} from '@vicons/ionicons5'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  { label: 'Dashboard', key: 'dashboard', icon: renderIcon(GridOutline) },
  { label: '任务管理', key: 'tasks', icon: renderIcon(ListOutline) },
  { label: '种子管理', key: 'seeds', icon: renderIcon(LeafOutline) },
  { label: '代理池', key: 'proxies', icon: renderIcon(ShieldOutline) },
  { label: '数据查询', key: 'data', icon: renderIcon(SearchOutline) },
  { label: '日志查询', key: 'logs', icon: renderIcon(DocumentTextOutline) },
]

const titleMap: Record<string, string> = {
  dashboard: 'Dashboard',
  tasks: '任务管理',
  seeds: '种子管理',
  proxies: '代理池管理',
  data: '数据查询',
  logs: '日志查询',
}

const activeKey = computed(() => {
  const name = route.path.split('/').pop() || 'dashboard'
  return name
})

const pageTitle = computed(() => titleMap[activeKey.value] || 'AIspider')

function handleMenuClick(key: string) {
  router.push(`/${key}`)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
