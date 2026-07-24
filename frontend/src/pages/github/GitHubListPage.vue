<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGithubAnalysis } from '@/composables/useGithubAnalysis.js'
import RepoCard from '@/components/github/RepoCard.vue'
import AddRepoCard from '@/components/github/AddRepoCard.vue'
import EmptyState from '@/components/github/EmptyState.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import AnalysisErrorNotice from '@/components/common/AnalysisErrorNotice.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const router = useRouter()
const { repos, loading, error, phase, progressMessage, activeTaskId, fetchRepos, analyzeNewRepo, deleteRepo, reconnectTask } = useGithubAnalysis()
const addRepoRef = ref(null)
const addRepoCardRef = ref(null)
const pendingDeleteRepo = ref(null)
const deleting = ref(false)

const busy = computed(() => loading.value || ['submitting', 'analyzing', 'fetching'].includes(phase.value))
const loadingText = computed(() => {
  if (phase.value === 'submitting') return '正在提交仓库'
  if (phase.value === 'analyzing') return '正在分析代码仓库'
  if (phase.value === 'fetching') return '正在加载分析结果'
  return '正在加载'
})

onMounted(async () => {
  await fetchRepos()
  if (activeTaskId.value) {
    reconnectTask(activeTaskId.value)
  }
})

async function handleAnalyzed(url) {
  const result = await analyzeNewRepo(url)
  if (result?.id) {
    router.push(`/analysis/github/${result.id}`)
  }
}

function triggerAdd() {
  addRepoRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  addRepoCardRef.value?.expand()
}

function handleDelete(repo) {
  pendingDeleteRepo.value = repo
}

function cancelDelete() {
  if (!deleting.value) pendingDeleteRepo.value = null
}

async function confirmDelete() {
  if (!pendingDeleteRepo.value || deleting.value) return
  deleting.value = true
  try {
    await deleteRepo(pendingDeleteRepo.value.id)
    pendingDeleteRepo.value = null
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h2 class="text-xl font-bold text-ink">GitHub 源码分析</h2>
      <p class="text-sm text-ink-muted mt-1">管理分析过的代码仓库，随时回顾和深入研究。</p>
    </div>

    <EmptyState v-if="repos.length === 0 && !loading" @add="triggerAdd" />

    <AnalysisErrorNotice
      v-if="error"
      class="mb-4"
      :message="error"
      :retryable="false"
    />

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <RepoCard
        v-for="repo in repos"
        :key="repo.id"
        :repo="repo"
        @retry="handleAnalyzed"
        @delete="handleDelete"
      />
    </div>

    <div ref="addRepoRef" :class="repos.length > 0 ? 'mt-4' : 'mt-0'">
      <AddRepoCard ref="addRepoCardRef" @analyzed="handleAnalyzed" />
    </div>

    <ConfirmDialog
      :show="Boolean(pendingDeleteRepo)"
      title="删除源码分析记录？"
      :message="`将删除「${pendingDeleteRepo?.fullName || pendingDeleteRepo?.url || '该仓库'}」的分析记录，操作后无法恢复。`"
      confirm-text="删除"
      cancel-text="取消"
      :loading="deleting"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
    />

    <LoadingOverlay
      :active="busy"
      :text="loadingText"
      :subtext="progressMessage || '猫头鹰助手正在获取数据...'"
    />
  </div>
</template>
