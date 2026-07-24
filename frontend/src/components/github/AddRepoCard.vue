<script setup>
import { nextTick, ref } from 'vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'

const emit = defineEmits(['analyzed'])

const expanded = ref(false)
const repoUrl = ref('')
const loading = ref(false)
const inputRef = ref(null)
const validationError = ref('')

async function expand({ clearValidation = true } = {}) {
  expanded.value = true
  if (clearValidation) validationError.value = ''
  await nextTick()
  inputRef.value?.focus()
}

function cancel() {
  expanded.value = false
  repoUrl.value = ''
  validationError.value = ''
}

function isGithubRepoUrl(value) {
  return /^(https:\/\/)?github\.com\/[^/\s]+\/[^/\s]+(?:\.git)?(?:\/.*)?(?:\?.*)?$/.test(extractGithubUrl(value))
}

function extractGithubUrl(value) {
  const text = value.trim()
  const markdownUrl = text.match(/\((https:\/\/github\.com\/[^)\s]+)\)/)
  if (markdownUrl) return markdownUrl[1]
  return text
}

async function submit() {
  const url = extractGithubUrl(repoUrl.value)
  if (!url) {
    validationError.value = '请先粘贴 GitHub 仓库链接'
    await expand({ clearValidation: false })
    return
  }
  if (!isGithubRepoUrl(url)) {
    validationError.value = '请输入类似 https://github.com/username/repository 的仓库链接'
    await expand({ clearValidation: false })
    return
  }
  loading.value = true
  validationError.value = ''
  try {
    emit('analyzed', url)
  } finally {
    loading.value = false
  }
}

function handleInput() {
  validationError.value = ''
}

defineExpose({ expand })
</script>

<template>
  <!-- Collapsed state -->
  <div
    v-if="!expanded"
    class="border-2 border-dashed border-border-light dark:border-border rounded-xl p-5 flex items-center justify-center gap-3 cursor-pointer transition-all hover:border-primary hover:bg-primary/5 min-h-[120px]"
    @click="expand"
  >
    <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" class="text-primary">
        <path d="M10 4v12M4 10h12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </div>
    <span class="text-sm font-medium text-ink-light">分析新仓库</span>
  </div>

  <!-- Expanded state -->
  <div
    v-else
    class="bg-white dark:bg-surface border-2 border-border-light dark:border-border rounded-xl p-5 transition-theme focus-within:border-primary focus-within:shadow-glow animate-fade-in"
  >
    <div class="flex items-center gap-3 mb-4">
      <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-[#dcece8] to-[#c9dfd9] flex items-center justify-center shrink-0">
        <svg width="18" height="18" viewBox="0 0 22 22" fill="none">
          <path d="M5 11l5 5L19 5" stroke="#2D6B65" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div>
        <h3 class="text-sm font-bold">粘贴 GitHub 仓库链接</h3>
        <p class="text-xs text-ink-muted">猫头鹰助手会分析代码结构、技术栈和项目亮点</p>
      </div>
    </div>

    <input
      ref="inputRef"
      v-model="repoUrl"
      type="url"
      class="w-full px-4 py-2.5 bg-surface dark:bg-surface-alt border-2 border-border-light dark:border-border rounded-xl text-sm font-mono text-ink outline-none focus:border-primary focus:shadow-glow transition-theme placeholder:text-ink-muted placeholder:font-sans"
      placeholder="https://github.com/username/repository"
      @input="handleInput"
      @keydown.enter.prevent="submit"
    />

    <p v-if="validationError" class="mt-2 text-xs text-red-500">{{ validationError }}</p>

    <div class="flex items-center justify-between mt-4">
      <button class="text-xs text-ink-muted hover:text-ink transition-colors" @click="cancel">取消</button>
      <button class="btn btn--primary text-sm" :disabled="loading" @click="submit">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8a6 6 0 1 1 12 0A6 6 0 0 1 2 8z" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3l2 1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        开始分析
      </button>
    </div>
  </div>

  <LoadingOverlay
    :active="loading"
    text="正在分析代码仓库"
    subtext="猫头鹰助手正在阅读代码、理解架构..."
  />
</template>
