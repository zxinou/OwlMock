<script setup>
import { watch } from 'vue'
import { useRoute } from 'vue-router'

import AppShell from '@/layouts/AppShell.vue'

const route = useRoute()

watch(
  () => route.path,
  () => {
    window.scrollTo({ top: 0 })
  }
)
</script>

<template>
  <router-view v-slot="{ Component, route: viewRoute }">
    <AppShell v-if="viewRoute.meta.appShell">
      <component :is="Component" />
    </AppShell>
    <component :is="Component" v-else />
  </router-view>
</template>
