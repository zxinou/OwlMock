<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, Check, ClipboardCheck, FileSearch, LayoutGrid,
  ListTree, LoaderCircle, RefreshCw, ShieldAlert,
} from 'lucide-vue-next'
import AnalysisLayout from '@/layouts/AnalysisLayout.vue'
import { api } from '@/api/index.js'
import { useJdTask } from '@/composables/useJdTask.js'

const route = useRoute()
const router = useRouter()
const taskId = route.params.taskId
const task = useJdTask()
const taskLayout = computed(() => route.params.projectId ? 'div' : AnalysisLayout)

const steps = [
  { key: 'extracting', title: '识别岗位信息', detail: '职位、公司、地点与薪资', icon: FileSearch },
  { key: 'structuring', title: '拆解要求与技能', detail: '硬性要求、优先项、技能权重', icon: ListTree },
  { key: 'analyzing', title: '判断风险与面试重点', detail: '形成有原文依据的判断', icon: ShieldAlert },
  { key: 'saving', title: '整理结构化报告', detail: '保存后自动进入报告页', icon: ClipboardCheck },
]

const stageIndex = computed(() => {
  if (task.status.value === 'completed') return steps.length
  const index = steps.findIndex((step) => step.key === task.stage.value)
  return index < 0 ? 0 : index
})

const title = computed(() => (
  task.analysis.value?.result?.job?.title
  || task.analysis.value?.text?.replace(/^图片 JD：/, '')
  || '正在读取 JD'
))

onMounted(() => task.start(taskId))

watch(task.status, (status) => {
  if (status === 'completed') {
    router.replace({ name: 'jd-report', params: { analysisId: taskId } })
  }
})

async function retry() {
  await api.resumeJdAnalysis(taskId)
  await task.start(taskId)
}
</script>

<template>
  <component :is="taskLayout">
    <div class="jd-task-nav">
      <router-link to="/analysis/jd"><ArrowLeft :size="16" />返回 JD 列表</router-link>
      <router-link to="/analysis/github"><LayoutGrid :size="16" />前往其他模块</router-link>
    </div>

    <section v-if="task.status.value === 'failed'" class="jd-task-error">
      <ShieldAlert :size="30" />
      <h1>这次分析没有完成</h1>
      <p>{{ task.error.value || '分析服务暂时没有生成报告，请稍后重试。' }}</p>
      <button type="button" class="btn btn--primary" @click="retry">
        <RefreshCw :size="16" />重新分析
      </button>
    </section>

    <section v-else class="jd-task-card">
      <div class="jd-task-head">
        <div>
          <span>JD 分析任务</span>
          <h1>{{ title }}</h1>
        </div>
        <strong>{{ Math.round(task.progress.value * 100) }}%</strong>
      </div>

      <div class="jd-progress-track" aria-label="分析进度">
        <span :style="{ width: `${Math.max(4, task.progress.value * 100)}%` }"></span>
      </div>

      <div class="jd-task-steps">
        <div
          v-for="(step, index) in steps"
          :key="step.key"
          class="jd-task-step"
          :class="{ done: index < stageIndex, active: index === stageIndex }"
        >
          <div class="jd-step-icon">
            <Check v-if="index < stageIndex" :size="16" />
            <LoaderCircle v-else-if="index === stageIndex" :size="16" class="spin" />
            <component :is="step.icon" v-else :size="16" />
          </div>
          <div>
            <strong>{{ step.title }}</strong>
            <span>{{ step.detail }}</span>
          </div>
          <small>{{ index < stageIndex ? '完成' : index === stageIndex ? '进行中' : '等待' }}</small>
        </div>
      </div>
    </section>
  </component>
</template>

<style scoped>
.jd-task-nav { display:flex; justify-content:space-between; gap:1rem; margin-bottom:1.25rem; }
.jd-task-nav a { display:inline-flex; align-items:center; gap:.4rem; color:var(--color-ink-muted); font-size:.82rem; }
.jd-task-nav a:hover { color:var(--color-primary); }
.jd-task-card, .jd-task-error { padding:1.75rem; border:1px solid var(--color-border); border-radius:var(--radius-lg); background:var(--color-white); box-shadow:var(--shadow-sm); }
.jd-task-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; }
.jd-task-head span { color:var(--color-ink-muted); font-size:.75rem; }
.jd-task-head h1 { margin-top:.35rem; font-size:1.25rem; overflow-wrap:anywhere; }
.jd-task-head > strong { color:var(--color-primary); font-size:1rem; }
.jd-progress-track { height:.45rem; overflow:hidden; margin:1.25rem 0 1.5rem; border-radius:999px; background:var(--color-surface-alt); }
.jd-progress-track span { display:block; height:100%; border-radius:inherit; background:var(--color-primary); transition:width .35s var(--ease-out); }
.jd-task-steps { display:grid; }
.jd-task-step { display:grid; grid-template-columns:2.25rem minmax(0,1fr) auto; align-items:center; gap:.8rem; padding:1rem 0; border-bottom:1px solid var(--color-border-light); }
.jd-task-step:last-child { border-bottom:0; }
.jd-step-icon { width:2.1rem; height:2.1rem; display:grid; place-items:center; border-radius:var(--radius-sm); color:var(--color-ink-muted); background:var(--color-surface); }
.jd-task-step.done .jd-step-icon { color:var(--color-primary); background:color-mix(in srgb, var(--color-primary) 13%, transparent); }
.jd-task-step.active .jd-step-icon { color:#8a6515; background:color-mix(in srgb, var(--color-secondary) 22%, transparent); }
.jd-task-step strong, .jd-task-step span { display:block; }
.jd-task-step strong { color:var(--color-ink); font-size:.88rem; }
.jd-task-step span { margin-top:.2rem; color:var(--color-ink-muted); font-size:.75rem; }
.jd-task-step small { color:var(--color-ink-muted); font-size:.7rem; }
.jd-task-step.done small { color:var(--color-primary); }
.jd-task-step.active small { color:#8a6515; }
.spin { animation:spin 1s linear infinite; }
.jd-task-error { display:grid; justify-items:center; gap:.8rem; text-align:center; color:var(--color-accent); }
.jd-task-error h1 { font-size:1.2rem; }
.jd-task-error p { max-width:30rem; color:var(--color-ink-muted); font-size:.86rem; }
@keyframes spin { to { transform:rotate(360deg); } }
@media (max-width:560px) { .jd-task-card, .jd-task-error { padding:1.15rem; } .jd-task-step { grid-template-columns:2.25rem minmax(0,1fr); } .jd-task-step small { grid-column:2; } }
</style>
