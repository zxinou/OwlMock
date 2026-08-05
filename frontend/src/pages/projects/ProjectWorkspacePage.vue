<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Archive, ArrowLeft, ArrowRight, Building2, FileSearch, FileUser, LoaderCircle, MapPin, MessageSquareText, RefreshCw } from 'lucide-vue-next'

import { api } from '@/api/index.js'
import ProjectFocus from '@/components/projects/ProjectFocus.vue'
import ProjectInterviewHistory from '@/components/projects/ProjectInterviewHistory.vue'
import ProjectPipeline from '@/components/projects/ProjectPipeline.vue'
import { createWorkspaceViewModel } from '@/components/projects/workspaceViewModel.js'
import { projectsStore } from '@/stores/projects.js'

const route = useRoute()
const router = useRouter()
const resumes = ref([])
const resumeId = ref('')
const localError = ref('')

const project = computed(() => projectsStore.current)
const view = computed(() => createWorkspaceViewModel(project.value))
const projectId = computed(() => String(route.params.projectId))

async function load() {
  localError.value = ''
  try {
    await Promise.all([
      projectsStore.loadProject(projectId.value),
      api.getResumes().then((payload) => { resumes.value = payload.items || payload.resumes || payload || [] }),
    ])
    resumeId.value = project.value?.current_resume?.id || resumes.value[0]?.id || ''
  } catch (error) {
    localError.value = error.message
  }
}

async function startMatch() {
  if (!resumeId.value || projectsStore.saving) return
  localError.value = ''
  try {
    const task = await projectsStore.startResumeMatch(projectId.value, resumeId.value)
    await router.push({
      name: 'project-resume-task',
      params: { projectId: projectId.value, taskId: task.task_id },
    })
  } catch (error) {
    localError.value = error.message
  }
}

async function archiveProject() {
  try {
    await projectsStore.archive(projectId.value)
    await router.replace({ name: 'projects' })
  } catch (error) {
    localError.value = error.message
  }
}

onMounted(load)
</script>

<template>
  <div class="project-workspace">
    <div v-if="projectsStore.loading && !project" class="project-workspace__loading">
      <LoaderCircle :size="21" class="spin" />正在恢复项目工作台
    </div>

    <section v-else-if="!project" class="project-workspace__error">
      <FileSearch :size="24" />
      <h1>暂时无法打开这个项目</h1>
      <p>{{ localError || projectsStore.error || '请检查项目是否仍然存在。' }}</p>
      <button type="button" @click="load"><RefreshCw :size="15" />重新读取</button>
    </section>

    <template v-else>
      <router-link :to="{ name: 'projects' }" class="project-workspace__back"><ArrowLeft :size="15" />返回项目</router-link>
      <header class="project-workspace__header">
        <div>
          <p>岗位项目工作台</p>
          <h1>{{ project.title === 'Untitled role' ? '正在识别岗位' : project.title }}</h1>
          <div class="project-workspace__meta">
            <span><Building2 :size="13" />{{ project.company || '公司待补充' }}</span>
            <span><MapPin :size="13" />{{ project.location || '地点待补充' }}</span>
          </div>
        </div>
        <div class="project-workspace__header-actions">
          <button type="button" class="project-workspace__archive" @click="archiveProject"><Archive :size="15" />归档</button>
          <router-link :to="{ name: 'interview-config', query: { projectId } }" class="project-workspace__interview"><MessageSquareText :size="16" />开始模拟面试</router-link>
        </div>
      </header>

      <p v-if="localError || projectsStore.error" class="project-workspace__notice" role="alert">{{ localError || projectsStore.error }}</p>

      <ProjectPipeline :steps="view.steps" :score="view.score" />

      <div class="project-workspace__feature-grid">
        <ProjectFocus :items="view.focusItems" :next-action="view.nextAction" />

        <section class="project-workspace__summary" aria-labelledby="job-summary-heading">
          <div class="project-workspace__section-heading">
            <span><FileSearch :size="17" /></span>
            <div><p>岗位摘要</p><h2 id="job-summary-heading">你需要解决什么问题</h2></div>
          </div>
          <p class="project-workspace__summary-copy">{{ view.summary }}</p>
          <router-link
            v-if="project.current_jd?.id"
            :to="{ name: 'jd-report', params: { analysisId: project.current_jd.id } }"
          >查看完整 JD 报告<ArrowRight :size="14" /></router-link>
          <span v-else class="project-workspace__muted">JD 分析完成后会显示完整报告。</span>
        </section>
      </div>

      <div class="project-workspace__lower-grid">
        <section class="project-workspace__next" aria-labelledby="next-heading">
          <div class="project-workspace__section-heading">
            <span><FileUser :size="17" /></span>
            <div><p>下一步</p><h2 id="next-heading">{{ view.nextAction.title }}</h2></div>
          </div>
          <p>{{ view.nextAction.description }}</p>

          <template v-if="view.nextAction.key === 'job'">
            <router-link :to="{ name: 'jd' }" class="project-workspace__action">补充 JD<ArrowRight :size="14" /></router-link>
          </template>
          <template v-else-if="view.nextAction.key === 'resume'">
            <div v-if="resumes.length" class="project-workspace__resume-action">
              <label for="workspace-resume">选择主简历</label>
              <select id="workspace-resume" v-model="resumeId">
                <option v-for="resume in resumes" :key="resume.id" :value="resume.id">{{ resume.file_name }}</option>
              </select>
              <button type="button" :disabled="!resumeId || projectsStore.saving" @click="startMatch">
                <LoaderCircle v-if="projectsStore.saving" :size="15" class="spin" />
                <FileUser v-else :size="15" />生成匹配报告
              </button>
            </div>
            <router-link v-else :to="{ name: 'resume' }" class="project-workspace__action">先上传简历<ArrowRight :size="14" /></router-link>
          </template>
          <template v-else>
            <router-link :to="{ name: 'interview-config', query: { projectId } }" class="project-workspace__action">配置模拟面试<ArrowRight :size="14" /></router-link>
          </template>

          <router-link
            v-if="project.latest_match?.id"
            :to="{ name: 'resume-match-report', params: { matchId: project.latest_match.id } }"
            class="project-workspace__secondary-link"
          >最近匹配：{{ view.score ?? '—' }} 分</router-link>
        </section>

        <ProjectInterviewHistory :sessions="view.interviews" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.project-workspace { display:grid; gap:1rem; }
.project-workspace__loading,.project-workspace__error { min-height:420px; display:grid; place-items:center; align-content:center; gap:.65rem; color:var(--color-ink-muted); border-top:1px solid var(--color-border); border-bottom:1px solid var(--color-border); font-size:.76rem; }
.project-workspace__error { text-align:center; }
.project-workspace__error h1 { font-size:1rem; }
.project-workspace__error button { display:inline-flex; align-items:center; gap:.4rem; margin-top:.4rem; color:var(--color-primary); font-size:.72rem; font-weight:700; }
.project-workspace__back { width:max-content; display:inline-flex; align-items:center; gap:.4rem; margin:.15rem 0 .2rem; color:var(--color-ink-muted); font-size:.7rem; }
.project-workspace__header { display:flex; align-items:flex-end; justify-content:space-between; gap:1.5rem; padding:.5rem 0 1.25rem; border-bottom:1px solid var(--color-border); }
.project-workspace__header p { color:var(--color-primary); font-size:.68rem; font-weight:750; }
.project-workspace__header h1 { margin-top:.3rem; font-size:1.65rem; }
.project-workspace__meta { display:flex; flex-wrap:wrap; gap:.9rem; margin-top:.5rem; }
.project-workspace__meta span { display:inline-flex; align-items:center; gap:.35rem; color:var(--color-ink-muted); font-size:.69rem; }
.project-workspace__header-actions { display:flex; align-items:center; gap:.5rem; }
.project-workspace__archive,.project-workspace__interview { min-height:38px; display:inline-flex; align-items:center; gap:.4rem; padding:0 .78rem; border-radius:6px; font-size:.7rem; font-weight:700; }
.project-workspace__archive { color:var(--color-ink-muted); border:1px solid var(--color-border); }
.project-workspace__interview { color:#17312f; background:var(--color-secondary); }
.project-workspace__notice { padding:.72rem .85rem; color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 8%,transparent); border-left:3px solid var(--color-accent); font-size:.72rem; }
.project-workspace__feature-grid { display:grid; grid-template-columns:minmax(260px,.8fr) minmax(0,1.2fr); gap:1rem; }
.project-workspace__lower-grid { display:grid; grid-template-columns:minmax(260px,.85fr) minmax(0,1.15fr); gap:1rem; }
.project-workspace__summary,.project-workspace__next { padding:1.35rem 1.45rem; background:var(--color-white); border:1px solid var(--color-border); border-radius:8px; }
.project-workspace__section-heading { display:flex; align-items:center; gap:.7rem; padding-bottom:1rem; border-bottom:1px solid var(--color-border-light); }
.project-workspace__section-heading > span { width:36px; height:36px; display:grid; place-items:center; color:var(--color-primary); background:var(--color-surface); border-radius:6px; }
.project-workspace__section-heading p { color:var(--color-primary); font-size:.63rem; font-weight:700; }
.project-workspace__section-heading h2 { margin-top:.16rem; font-size:.92rem; }
.project-workspace__summary-copy { display:-webkit-box; margin:1rem 0; overflow:hidden; color:var(--color-ink-light); font-size:.75rem; line-height:1.65; -webkit-box-orient:vertical; -webkit-line-clamp:5; }
.project-workspace__summary > a,.project-workspace__action { display:inline-flex; align-items:center; gap:.4rem; color:var(--color-primary); font-size:.7rem; font-weight:750; }
.project-workspace__muted { color:var(--color-ink-muted); font-size:.68rem; }
.project-workspace__next > p { margin:.9rem 0; color:var(--color-ink-muted); font-size:.72rem; line-height:1.55; }
.project-workspace__resume-action { display:grid; gap:.45rem; }
.project-workspace__resume-action label { color:var(--color-ink-light); font-size:.65rem; font-weight:700; }
.project-workspace__resume-action select { width:100%; min-height:38px; padding:0 .65rem; color:var(--color-ink); background:var(--color-base); border:1px solid var(--color-border); border-radius:5px; font-size:.7rem; }
.project-workspace__resume-action button { min-height:38px; display:flex; align-items:center; justify-content:center; gap:.4rem; color:#17312f; background:var(--color-secondary); border-radius:5px; font-size:.7rem; font-weight:750; }
.project-workspace__secondary-link { display:block; margin-top:.75rem; color:var(--color-ink-muted); font-size:.65rem; text-decoration:underline; text-underline-offset:3px; }
.spin { animation:spin .9s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
@media (max-width:820px) { .project-workspace__feature-grid,.project-workspace__lower-grid { grid-template-columns:1fr; } }
@media (max-width:620px) { .project-workspace__header { align-items:flex-start; flex-direction:column; } .project-workspace__header-actions { width:100%; } .project-workspace__interview { flex:1; justify-content:center; } .project-workspace__summary,.project-workspace__next { padding:1.1rem; } }
</style>
