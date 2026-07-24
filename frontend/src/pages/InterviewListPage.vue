<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/index.js'
import { PROFILE_TO_TYPE } from '@/data/interview.js'
import AnalysisLayout from '@/layouts/AnalysisLayout.vue'
import InterviewCard from '@/components/interview/InterviewCard.vue'
import InterviewConfigModal from '@/components/interview/InterviewConfigModal.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import AnalysisErrorNotice from '@/components/common/AnalysisErrorNotice.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const router = useRouter()
const loading = ref(false)
const deleting = ref(false)
const sessions = ref([])
const filterType = ref('all')
const filterStatus = ref('all')
const sortBy = ref('date')
const showConfigModal = ref(false)
const error = ref(null)
const pendingDeleteId = ref(null)

const interviews = computed(() => {
  return sessions.value.map((session) => ({
    id: session.id,
    type: PROFILE_TO_TYPE[session.profile_id] || 'technical',
    resume: session.resume_id ? '已关联简历' : '通用面试',
    projects: [],
    duration: Math.round((new Date(session.updated_at) - new Date(session.created_at)) / 60000) || 0,
    status: session.status === 'active' ? 'paused' : session.status,
    date: session.created_at,
    summary: session.summary,
  }))
})

const filteredInterviews = computed(() => {
  let result = [...interviews.value]

  if (filterType.value !== 'all') {
    result = result.filter((item) => item.type === filterType.value)
  }

  if (filterStatus.value !== 'all') {
    result = result.filter((item) => item.status === filterStatus.value)
  }

  if (sortBy.value === 'date') {
    result.sort((a, b) => new Date(b.date) - new Date(a.date))
  } else if (sortBy.value === 'duration') {
    result.sort((a, b) => b.duration - a.duration)
  }

  return result
})

async function loadSessions() {
  loading.value = true
  error.value = null
  try {
    const data = await api.getSessions()
    sessions.value = data.sessions || []
  } catch (e) {
    console.error('Failed to load sessions:', e)
    sessions.value = []
    error.value = e.message || '面试记录加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSessions()
})

function handleViewSummary(id) {
  router.push(`/interview/${id}/summary`)
}

function handleContinueInterview(id) {
  router.push(`/interview/${id}`)
}

function handleStartNew() {
  showConfigModal.value = true
}

function handleCloseModal() {
  showConfigModal.value = false
}

function requestDeleteInterview(id) {
  pendingDeleteId.value = id
}

function cancelDeleteInterview() {
  if (!deleting.value) pendingDeleteId.value = null
}

async function confirmDeleteInterview() {
  if (!pendingDeleteId.value || deleting.value) return
  deleting.value = true
  error.value = null
  try {
    await api.deleteSession(pendingDeleteId.value)
    sessions.value = sessions.value.filter((session) => session.id !== pendingDeleteId.value)
    pendingDeleteId.value = null
  } catch (e) {
    error.value = e.message || '删除面试记录失败，请稍后重试'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <AnalysisLayout>
    <div class="mb-6">
      <h2 class="text-xl font-bold text-ink">模拟面试</h2>
      <p class="text-sm text-ink-muted mt-1">
        {{ interviews.length > 0 ? `你已有 ${interviews.length} 场模拟面试记录，可以继续练习或回看总结。` : '选择面试类型即可开始，也可以关联简历和项目上下文。' }}
      </p>
    </div>

    <AnalysisErrorNotice
      v-if="error"
      class="mb-4"
      :message="error"
      :retryable="true"
      retry-label="重新加载"
      @retry="loadSessions"
    />

    <div v-if="interviews.length > 0" class="flex flex-wrap items-center gap-4 mb-6">
      <div class="flex items-center gap-2">
        <label class="text-sm text-ink-muted">筛选</label>
        <select
          v-model="filterType"
          class="px-3 py-2 bg-surface dark:bg-surface-alt border border-border-light dark:border-border rounded-lg text-sm text-ink outline-none focus:border-primary transition-theme"
        >
          <option value="all">全部类型</option>
          <option value="technical">技术面试</option>
          <option value="behavioral">行为面试</option>
          <option value="comprehensive">综合面试</option>
        </select>
      </div>

      <div class="flex items-center gap-2">
        <label class="text-sm text-ink-muted">状态</label>
        <select
          v-model="filterStatus"
          class="px-3 py-2 bg-surface dark:bg-surface-alt border border-border-light dark:border-border rounded-lg text-sm text-ink outline-none focus:border-primary transition-theme"
        >
          <option value="all">全部状态</option>
          <option value="completed">已完成</option>
          <option value="paused">可继续</option>
        </select>
      </div>

      <div class="flex items-center gap-2">
        <label class="text-sm text-ink-muted">排序</label>
        <select
          v-model="sortBy"
          class="px-3 py-2 bg-surface dark:bg-surface-alt border border-border-light dark:border-border rounded-lg text-sm text-ink outline-none focus:border-primary transition-theme"
        >
          <option value="date">最近日期</option>
          <option value="duration">面试时长</option>
        </select>
      </div>
    </div>

    <div v-if="interviews.length === 0 && !loading" class="text-center py-12">
      <div class="w-20 h-20 mx-auto mb-4 rounded-full bg-surface flex items-center justify-center">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" class="text-ink-muted">
          <rect x="8" y="6" width="24" height="28" rx="3" stroke="currentColor" stroke-width="2"/>
          <circle cx="20" cy="16" r="4" stroke="currentColor" stroke-width="1.5"/>
          <path d="M12 28c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-ink mb-2">还没有面试记录</h3>
      <p class="text-sm text-ink-muted mb-6">可以直接开始通用面试，也可以先选择简历和 GitHub 项目作为上下文。</p>
      <button class="btn btn--primary" @click="handleStartNew">
        开始配置 →
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <InterviewCard
        v-for="interview in filteredInterviews"
        :key="interview.id"
        :interview="interview"
        @view-summary="handleViewSummary"
        @continue="handleContinueInterview"
        @delete="requestDeleteInterview"
      />
    </div>

    <div v-if="interviews.length > 0" class="mt-4">
      <div
        class="bg-white dark:bg-surface border-2 border-dashed border-border-light dark:border-border rounded-xl p-6 text-center cursor-pointer hover:border-primary hover:bg-primary/5 transition-all"
        @click="handleStartNew"
      >
        <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-surface flex items-center justify-center">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" class="text-primary">
            <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <h3 class="font-semibold text-ink mb-1">开始新面试</h3>
        <p class="text-sm text-ink-muted">选择面试类型后即可开始练习。</p>
      </div>
    </div>

    <InterviewConfigModal
      :show="showConfigModal"
      @close="handleCloseModal"
    />

    <ConfirmDialog
      :show="Boolean(pendingDeleteId)"
      title="删除面试记录？"
      message="这条面试记录和对应对话会被删除，操作后无法恢复。"
      confirm-text="删除"
      cancel-text="取消"
      :loading="deleting"
      @confirm="confirmDeleteInterview"
      @cancel="cancelDeleteInterview"
    />

    <LoadingOverlay
      :active="loading"
      text="正在加载"
      subtext="正在同步面试记录"
    />
  </AnalysisLayout>
</template>
