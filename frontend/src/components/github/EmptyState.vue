<script setup>
import OwlLogo from '@/components/common/OwlLogo.vue'

const emit = defineEmits(['add'])
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 px-6 text-center">
    <!-- Owl illustration -->
    <div class="mb-6 opacity-60">
      <OwlLogo :size="112" />
    </div>

    <h3 class="text-lg font-bold text-ink mb-2">还没有分析过仓库</h3>
    <p class="text-sm text-ink-muted mb-6 max-w-xs leading-relaxed">
      粘贴一个 GitHub 仓库链接，猫头鹰助手帮你分析代码结构、技术栈和项目亮点
    </p>

    <button class="btn btn--primary" @click="emit('add')">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      添加第一个仓库
    </button>
  </div>
</template>
