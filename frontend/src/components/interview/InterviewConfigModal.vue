<script setup>
import { useInterviewConfig } from '@/composables/useInterviewConfig.js'

defineProps({
  show: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const {
  resumes,
  githubRepos,
  selectedGithubRepos,
  interviewTypes,
  selectedResume,
  selectedType,
  isConfigValid,
  starting,
  startError,
  handleStartInterview: startInterview,
  handleGoToUpload,
  handleGoToAnalysis,
} = useInterviewConfig()

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

async function handleStartInterview() {
  await startInterview()
  if (!startError.value) emit('close')
}

function handleClose() {
  if (!starting.value) emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click.self="handleClose">
      <div class="modal" role="dialog" aria-modal="true" aria-label="面试配置">
        <div class="modal__header">
          <div class="modal__header-left">
            <div class="modal__icon">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                <rect x="4" y="3" width="14" height="16" rx="2" stroke="#D86C57" stroke-width="1.8"/>
                <circle cx="11" cy="9" r="3" stroke="#D86C57" stroke-width="1.3"/>
                <path d="M6 17c0-3 2.2-5 5-5s5 2 5 5" stroke="#D86C57" stroke-width="1.3" stroke-linecap="round"/>
              </svg>
            </div>
            <div>
              <h2 class="modal__title">面试配置</h2>
              <p class="modal__subtitle">选择面试类型后即可开始，简历和项目会作为加分上下文。</p>
            </div>
          </div>
          <button class="modal__close" :disabled="starting" @click="handleClose">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M15 5L5 15M5 5l10 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <div class="modal__content">
          <div class="config-step">
            <div class="config-step__header">
              <div class="config-step__number">1</div>
              <span class="config-step__title">选择简历（可选）</span>
            </div>

            <div v-if="resumes.length > 0" class="config-step__options">
              <label
                v-for="resume in resumes"
                :key="resume.id"
                class="config-option"
                :class="{ 'config-option--selected': selectedResume === resume.id }"
              >
                <input
                  v-model="selectedResume"
                  type="radio"
                  :value="resume.id"
                  class="config-option__radio"
                />
                <div class="config-option__content">
                  <div class="config-option__name">{{ resume.file_name }}</div>
                  <div class="config-option__desc">{{ resume.file_type?.toUpperCase() }} · 上传于 {{ formatDate(resume.created_at) }}</div>
                </div>
              </label>
              <button
                v-if="selectedResume"
                type="button"
                class="config-clear"
                @click="selectedResume = null"
              >
                不使用简历
              </button>
            </div>

            <div v-else class="config-step__empty">
              <p class="text-sm text-ink-muted mb-2">暂无简历，也可以先直接开始通用面试。</p>
              <button class="text-sm text-primary hover:underline" @click="handleGoToUpload">去上传 →</button>
            </div>
          </div>

          <div class="config-step">
            <div class="config-step__header">
              <div class="config-step__number">2</div>
              <span class="config-step__title">面试类型</span>
            </div>

            <div class="config-step__options">
              <label
                v-for="type in interviewTypes"
                :key="type.id"
                class="config-option"
                :class="{ 'config-option--selected': selectedType === type.id }"
              >
                <input
                  v-model="selectedType"
                  type="radio"
                  :value="type.id"
                  class="config-option__radio"
                />
                <div class="config-option__content">
                  <div class="config-option__name">{{ type.label }}</div>
                  <div class="config-option__desc">{{ type.description }}</div>
                </div>
              </label>
            </div>
          </div>

          <div class="config-step">
            <div class="config-step__header">
              <div class="config-step__number">3</div>
              <span class="config-step__title">GitHub 仓库（可选）</span>
            </div>
            <p class="config-step__hint">选择已分析的仓库，让面试官了解你的项目经验。</p>

            <div v-if="githubRepos.length > 0" class="config-step__options">
              <label
                v-for="repo in githubRepos"
                :key="repo.id"
                class="config-option"
                :class="{ 'config-option--selected': selectedGithubRepos.includes(repo.id) }"
              >
                <input
                  v-model="selectedGithubRepos"
                  type="checkbox"
                  :value="repo.id"
                  class="config-option__checkbox"
                />
                <div class="config-option__content">
                  <div class="config-option__name">{{ repo.fullName }}</div>
                  <div class="config-option__desc">{{ repo.description || '暂无描述' }}</div>
                </div>
              </label>
            </div>

            <div v-else class="config-step__empty">
              <p class="text-sm text-ink-muted mb-2">暂无已分析的仓库</p>
              <button class="text-sm text-primary hover:underline" @click="handleGoToAnalysis">去分析 →</button>
            </div>
          </div>
        </div>

        <div class="modal__footer">
          <p v-if="startError" class="modal__error">{{ startError }}</p>
          <p v-else-if="!isConfigValid" class="modal__hint">请选择面试类型后开始面试</p>
          <div class="modal__actions">
            <button class="modal-btn modal-btn--secondary" :disabled="starting" @click="handleClose">取消</button>
            <button
              class="modal-btn modal-btn--primary"
              :disabled="!isConfigValid || starting"
              :class="{ 'opacity-50 cursor-not-allowed': !isConfigValid || starting }"
              @click="handleStartInterview"
            >
              {{ starting ? '正在创建...' : '开始面试 →' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(17, 24, 39, 0.36);
  backdrop-filter: blur(6px);
  padding: var(--space-4);
}

.modal {
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-2xl);
  background: var(--color-white);
  box-shadow: var(--shadow-xl);
  animation: modalIn 0.24s var(--ease-out) both;
}

@keyframes modalIn {
  from { opacity: 0; transform: scale(0.97) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-6) var(--space-6) var(--space-4);
}

.modal__header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.modal__icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, #f7ddd6, #efc7bb);
}

.modal__title {
  color: var(--color-ink);
  font-family: var(--font-heading);
  font-size: var(--text-xl);
  font-weight: 700;
}

.modal__subtitle {
  margin-top: 2px;
  color: var(--color-ink-muted);
  font-size: var(--text-sm);
  line-height: 1.5;
}

.modal__close {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  color: var(--color-ink-muted);
  transition: all var(--duration-fast) var(--ease-out);
}

.modal__close:hover:not(:disabled) {
  background: var(--color-surface);
  color: var(--color-ink);
}

.modal__content {
  flex: 1;
  overflow-y: auto;
  padding: 0 var(--space-6) var(--space-4);
}

.config-step {
  margin-bottom: var(--space-5);
}

.config-step:last-child {
  margin-bottom: 0;
}

.config-step__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.config-step__number {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: var(--color-white);
  font-size: var(--text-xs);
  font-weight: 700;
}

.config-step__title {
  color: var(--color-ink);
  font-size: var(--text-sm);
  font-weight: 600;
}

.config-step__options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.config-step__empty {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  text-align: center;
}

.config-step__hint {
  margin-top: calc(var(--space-2) * -1);
  margin-bottom: var(--space-3);
  color: var(--color-ink-muted);
  font-size: var(--text-xs);
}

.config-option {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1.5px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.config-option:hover {
  border-color: var(--color-primary-light);
}

.config-option--selected {
  border-color: var(--color-primary);
  background: rgba(196, 149, 106, 0.06);
}

.config-option__radio,
.config-option__checkbox {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  accent-color: var(--color-primary);
}

.config-option__content {
  min-width: 0;
  flex: 1;
}

.config-option__name {
  color: var(--color-ink);
  font-size: var(--text-sm);
  font-weight: 500;
}

.config-option__desc {
  margin-top: 2px;
  color: var(--color-ink-muted);
  font-size: var(--text-xs);
}

.config-clear {
  align-self: flex-start;
  color: var(--color-ink-muted);
  font-size: var(--text-xs);
}

.config-clear:hover {
  color: var(--color-primary);
}

.modal__footer {
  padding: var(--space-4) var(--space-6) var(--space-6);
  border-top: 1px solid var(--color-border-light);
}

.modal__hint {
  margin-bottom: var(--space-4);
  color: var(--color-ink-muted);
  font-size: var(--text-xs);
  text-align: center;
}

.modal__error {
  padding: 0.75rem 0.9rem;
  margin-bottom: var(--space-4);
  border-radius: var(--radius-lg);
  background: rgba(217, 87, 69, 0.1);
  color: #d95745;
  font-size: var(--text-sm);
}

.modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.modal-btn {
  min-height: 2.5rem;
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  font-weight: 500;
  transition: all var(--duration-fast) var(--ease-out);
}

.modal-btn:disabled {
  cursor: not-allowed;
}

.modal-btn--secondary {
  border: 1px solid var(--color-border-light);
  color: var(--color-ink-muted);
}

.modal-btn--secondary:hover:not(:disabled) {
  background: var(--color-surface);
  color: var(--color-ink);
}

.modal-btn--primary {
  background: var(--color-primary);
  color: var(--color-white);
}

.modal-btn--primary:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

html.dark .modal {
  background: var(--color-surface);
}

html.dark .config-option {
  border-color: var(--color-border);
}

html.dark .config-option--selected {
  border-color: var(--color-primary);
  background: rgba(196, 149, 106, 0.1);
}

@media (max-width: 640px) {
  .modal {
    max-height: 95vh;
  }

  .modal__header,
  .modal__content,
  .modal__footer {
    padding-left: var(--space-4);
    padding-right: var(--space-4);
  }
}
</style>
