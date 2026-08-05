<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const contentMaxWidth = computed(() => {
  const widths = { narrow: '760px', wide: '1200px', default: '960px' }
  return widths[route.meta.contentWidth] || widths.default
})
</script>

<template>
  <div class="analysis-content" :style="{ maxWidth: contentMaxWidth }">
    <slot />
  </div>
</template>

<style scoped>
.analysis-content {
  width: 100%;
  margin: 0 auto;
}
</style>
