<script setup>
import { computed, onMounted, ref } from 'vue'
import { Archive, ArrowRight, BriefcaseBusiness, Building2, CalendarClock, MapPin, Plus, RefreshCw } from 'lucide-vue-next'

import { projectsStore } from '@/stores/projects.js'

const archived = ref(false)
const actionError = ref('')
const projects = computed(() => projectsStore.items)

async function load() {
  actionError.value = ''
  try {
    await projectsStore.load({ archived: archived.value })
  } catch (error) {
    actionError.value = error.message
  }
}

async function setArchived(value) {
  archived.value = value
  await load()
}

async function archiveProject(project) {
  if (archived.value) return
  actionError.value = ''
  try {
    await projectsStore.archive(project.id)
  } catch (error) {
    actionError.value = error.message
  }
}

function formatDate(value) {
  if (!value) return '刚刚更新'
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' }).format(new Date(value))
}

onMounted(load)
</script>

<template>
  <div class="project-list-page">
    <header class="project-list-page__header">
      <div>
        <p>岗位项目</p>
        <h1>把每个目标岗位，变成一套可持续的准备过程</h1>
        <span>{{ archived ? '查看已经结束的岗位准备。' : '从 JD 开始，串联简历匹配和模拟面试。' }}</span>
      </div>
      <router-link :to="{ name: 'project-create' }" class="project-list-page__primary">
        <Plus :size="17" />新建岗位
      </router-link>
    </header>

    <div class="project-list-page__toolbar">
      <div class="project-list-page__tabs" aria-label="项目状态">
        <button type="button" :class="{ active: !archived }" @click="setArchived(false)">进行中</button>
        <button type="button" :class="{ active: archived }" @click="setArchived(true)">已归档</button>
      </div>
      <button type="button" class="project-list-page__refresh" :disabled="projectsStore.loading" @click="load">
        <RefreshCw :size="15" :class="{ spin: projectsStore.loading }" />刷新
      </button>
    </div>

    <p v-if="actionError || projectsStore.error" class="project-list-page__error" role="alert">
      {{ actionError || projectsStore.error }}
    </p>

    <div v-if="projectsStore.loading && !projects.length" class="project-list-page__loading" aria-live="polite">
      <RefreshCw :size="20" class="spin" />正在读取岗位项目
    </div>

    <section v-else-if="projects.length" class="project-list-page__grid" aria-label="岗位项目列表">
      <article v-for="project in projects" :key="project.id" class="project-card">
        <div class="project-card__top">
          <span class="project-card__icon" aria-hidden="true"><BriefcaseBusiness :size="19" /></span>
          <button
            v-if="!archived"
            type="button"
            class="project-card__archive"
            aria-label="归档项目"
            title="归档项目"
            @click="archiveProject(project)"
          ><Archive :size="15" /></button>
        </div>
        <div class="project-card__copy">
          <h2>{{ project.title === 'Untitled role' ? '正在识别岗位' : project.title }}</h2>
          <p><Building2 :size="13" />{{ project.company || '公司待补充' }}</p>
          <p><MapPin :size="13" />{{ project.location || '地点待补充' }}</p>
        </div>
        <div class="project-card__footer">
          <span><CalendarClock :size="13" />{{ formatDate(project.updated_at) }}</span>
          <router-link :to="{ name: 'project-workspace', params: { projectId: project.id } }">
            打开工作台<ArrowRight :size="14" />
          </router-link>
        </div>
      </article>
    </section>

    <section v-else class="project-list-page__empty">
      <span aria-hidden="true"><BriefcaseBusiness :size="24" /></span>
      <p>{{ archived ? '还没有已归档项目' : '从第一个目标岗位开始' }}</p>
      <small>{{ archived ? '结束的项目会安全保留在这里。' : '粘贴或上传 JD，OwlMock 会建立完整的准备工作台。' }}</small>
      <router-link v-if="!archived" :to="{ name: 'project-create' }">新建岗位<ArrowRight :size="15" /></router-link>
    </section>
  </div>
</template>

<style scoped>
.project-list-page { display:grid; gap:1.25rem; }
.project-list-page__header { display:flex; align-items:flex-end; justify-content:space-between; gap:2rem; padding:1.1rem 0 1.5rem; border-bottom:1px solid var(--color-border); }
.project-list-page__header p { color:var(--color-primary); font-size:.7rem; font-weight:750; }
.project-list-page__header h1 { max-width:720px; margin-top:.35rem; font-size:1.65rem; line-height:1.3; }
.project-list-page__header span { display:block; margin-top:.55rem; color:var(--color-ink-muted); font-size:.78rem; }
.project-list-page__primary { min-height:40px; display:inline-flex; align-items:center; gap:.45rem; flex:none; padding:0 .95rem; color:#17312f; background:var(--color-secondary); border-radius:6px; font-size:.76rem; font-weight:750; }
.project-list-page__toolbar { display:flex; align-items:center; justify-content:space-between; gap:1rem; }
.project-list-page__tabs { display:flex; gap:.2rem; padding:.2rem; background:var(--color-surface); border:1px solid var(--color-border-light); border-radius:6px; }
.project-list-page__tabs button { min-height:32px; padding:0 .75rem; color:var(--color-ink-muted); border-radius:4px; font-size:.7rem; font-weight:700; }
.project-list-page__tabs button.active { color:var(--color-ink); background:var(--color-white); box-shadow:var(--shadow-sm); }
.project-list-page__refresh { display:inline-flex; align-items:center; gap:.4rem; color:var(--color-ink-muted); font-size:.7rem; }
.project-list-page__error { padding:.75rem .9rem; color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 9%,transparent); border-left:3px solid var(--color-accent); font-size:.76rem; }
.project-list-page__loading,.project-list-page__empty { min-height:300px; display:grid; place-items:center; align-content:center; gap:.6rem; color:var(--color-ink-muted); border-top:1px solid var(--color-border); border-bottom:1px solid var(--color-border); font-size:.75rem; }
.project-list-page__empty > span { width:46px; height:46px; display:grid; place-items:center; color:var(--color-primary); background:var(--color-surface); border:1px solid var(--color-border); border-radius:7px; }
.project-list-page__empty p { color:var(--color-ink); font-size:.9rem; font-weight:700; }
.project-list-page__empty small { text-align:center; }
.project-list-page__empty a { display:inline-flex; align-items:center; gap:.4rem; margin-top:.4rem; color:var(--color-primary); font-size:.72rem; font-weight:750; }
.project-list-page__grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; }
.project-card { min-width:0; display:flex; flex-direction:column; padding:1.15rem; background:var(--color-white); border:1px solid var(--color-border); border-radius:8px; box-shadow:var(--shadow-sm); transition:transform var(--duration-fast),border-color var(--duration-fast); }
.project-card:hover { transform:translateY(-2px); border-color:var(--color-primary-light); }
.project-card__top { display:flex; align-items:center; justify-content:space-between; }
.project-card__icon { width:38px; height:38px; display:grid; place-items:center; color:var(--color-primary); background:var(--color-surface); border-radius:7px; }
.project-card__archive { width:32px; height:32px; display:grid; place-items:center; color:var(--color-ink-muted); border-radius:5px; }
.project-card__archive:hover { color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 8%,transparent); }
.project-card__copy { padding:1rem 0 1.1rem; }
.project-card__copy h2 { margin-bottom:.65rem; overflow-wrap:anywhere; font-size:1rem; }
.project-card__copy p { display:flex; align-items:center; gap:.4rem; margin-top:.3rem; color:var(--color-ink-muted); font-size:.69rem; }
.project-card__footer { display:flex; align-items:center; justify-content:space-between; gap:.75rem; margin-top:auto; padding-top:.8rem; border-top:1px solid var(--color-border-light); }
.project-card__footer span,.project-card__footer a { display:inline-flex; align-items:center; gap:.35rem; font-size:.65rem; }
.project-card__footer span { color:var(--color-ink-muted); }
.project-card__footer a { color:var(--color-primary); font-weight:750; }
.spin { animation:spin .9s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
@media (max-width:980px) { .project-list-page__grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:620px) { .project-list-page__header { align-items:flex-start; flex-direction:column; gap:1rem; } .project-list-page__header h1 { font-size:1.4rem; } .project-list-page__primary { width:100%; justify-content:center; } .project-list-page__grid { grid-template-columns:1fr; } }
</style>
