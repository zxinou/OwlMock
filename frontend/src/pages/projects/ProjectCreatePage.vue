<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, FileImage, FileText, LoaderCircle, Sparkles, Upload } from 'lucide-vue-next'

import { projectsStore } from '@/stores/projects.js'

const router = useRouter()
const mode = ref('text')
const title = ref('')
const company = ref('')
const location = ref('')
const jdText = ref('')
const file = ref(null)
const error = ref('')
const draftProjectId = ref('')

const canSubmit = computed(() => (
  (mode.value === 'text' ? jdText.value.trim().length >= 20 : file.value)
  && !projectsStore.saving
))

function selectFile(event) {
  file.value = event.target.files?.[0] || null
}

async function submit() {
  if (!canSubmit.value) return
  error.value = ''
  try {
    const input = {
      title: title.value.trim() || 'Untitled role',
      company: company.value.trim() || null,
      location: location.value.trim() || null,
    }
    let result
    if (draftProjectId.value) {
      const task = await projectsStore.submitJd(draftProjectId.value, {
        text: mode.value === 'text' ? jdText.value.trim() : '',
        file: mode.value === 'image' ? file.value : null,
      })
      result = { project: { id: draftProjectId.value }, taskId: task.task_id }
    } else {
      result = mode.value === 'text'
        ? await projectsStore.createFromText({ ...input, jdText: jdText.value.trim() })
        : await projectsStore.createFromImage({ ...input, file: file.value })
    }
    await router.push({
      name: 'project-jd-task',
      params: { projectId: result.project.id, taskId: result.taskId },
    })
  } catch (cause) {
    if (cause.projectId) draftProjectId.value = cause.projectId
    error.value = cause.message
  }
}
</script>

<template>
  <div class="project-create-page">
    <router-link :to="{ name: 'projects' }" class="project-create-page__back"><ArrowLeft :size="15" />返回项目</router-link>
    <header>
      <p>新建岗位</p>
      <h1>从一份真实 JD 开始</h1>
      <span>先创建项目草稿，再由分析结果补全岗位、公司和地点。</span>
    </header>

    <form class="project-create-form" @submit.prevent="submit">
      <section class="project-create-form__meta" aria-labelledby="project-meta-heading">
        <div class="project-create-form__section-heading">
          <span>01</span><div><p>项目信息</p><h2 id="project-meta-heading">为这次准备命名</h2></div>
        </div>
        <label>岗位名称<input v-model="title" maxlength="160" placeholder="留空则由 JD 自动识别"></label>
        <div class="project-create-form__row">
          <label>公司<input v-model="company" maxlength="160" placeholder="可稍后补充"></label>
          <label>地点<input v-model="location" maxlength="160" placeholder="可稍后补充"></label>
        </div>
      </section>

      <section class="project-create-form__jd" aria-labelledby="project-jd-heading">
        <div class="project-create-form__section-heading">
          <span>02</span><div><p>岗位描述</p><h2 id="project-jd-heading">选择输入方式</h2></div>
        </div>
        <div class="project-create-form__modes" role="tablist" aria-label="JD 输入方式">
          <button type="button" role="tab" :aria-selected="mode === 'text'" :class="{ active: mode === 'text' }" @click="mode = 'text'"><FileText :size="16" />粘贴文字</button>
          <button type="button" role="tab" :aria-selected="mode === 'image'" :class="{ active: mode === 'image' }" @click="mode = 'image'"><FileImage :size="16" />上传图片</button>
        </div>
        <textarea v-if="mode === 'text'" v-model="jdText" rows="12" minlength="20" placeholder="粘贴完整岗位描述，建议包含职责、要求与加分项。" />
        <label v-else class="project-create-form__upload">
          <Upload :size="24" />
          <strong>{{ file?.name || '选择 PNG 或 JPEG' }}</strong>
          <span>请上传清晰、完整的岗位截图</span>
          <input type="file" accept="image/png,image/jpeg" @change="selectFile">
        </label>
      </section>

      <p v-if="error || projectsStore.error" class="project-create-form__error" role="alert">{{ error || projectsStore.error }}</p>
      <div class="project-create-form__footer">
        <p><Sparkles :size="15" />{{ draftProjectId ? '项目草稿已保存，再次提交不会重复创建。' : '项目会立即保存，分析中途刷新也能恢复。' }}</p>
        <button type="submit" :disabled="!canSubmit">
          <LoaderCircle v-if="projectsStore.saving" :size="17" class="spin" />
          <Sparkles v-else :size="17" />
          {{ projectsStore.saving ? '正在提交' : draftProjectId ? '重试 JD 分析' : '创建并分析 JD' }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.project-create-page { width:min(100%,920px); margin:0 auto; }
.project-create-page__back { display:inline-flex; align-items:center; gap:.4rem; margin:.2rem 0 1.1rem; color:var(--color-ink-muted); font-size:.72rem; }
.project-create-page header { padding-bottom:1.35rem; border-bottom:1px solid var(--color-border); }
.project-create-page header p { color:var(--color-primary); font-size:.7rem; font-weight:750; }
.project-create-page header h1 { margin-top:.3rem; font-size:1.6rem; }
.project-create-page header span { display:block; margin-top:.45rem; color:var(--color-ink-muted); font-size:.76rem; }
.project-create-form { display:grid; gap:1rem; margin-top:1rem; }
.project-create-form > section { padding:1.35rem; background:var(--color-white); border:1px solid var(--color-border); border-radius:8px; }
.project-create-form__section-heading { display:flex; align-items:center; gap:.7rem; margin-bottom:1.1rem; }
.project-create-form__section-heading > span { width:32px; height:32px; display:grid; place-items:center; color:var(--color-primary); background:var(--color-surface); border-radius:6px; font-size:.65rem; font-weight:800; }
.project-create-form__section-heading p { color:var(--color-ink-muted); font-size:.62rem; }
.project-create-form__section-heading h2 { margin-top:.1rem; font-size:.95rem; }
.project-create-form label { display:grid; gap:.4rem; color:var(--color-ink-light); font-size:.7rem; font-weight:650; }
.project-create-form input,.project-create-form textarea { width:100%; color:var(--color-ink); background:var(--color-base); border:1px solid var(--color-border); border-radius:6px; outline:0; }
.project-create-form input { min-height:42px; padding:0 .75rem; }
.project-create-form textarea { min-height:220px; padding:.8rem; line-height:1.65; resize:vertical; }
.project-create-form input:focus,.project-create-form textarea:focus { border-color:var(--color-primary); box-shadow:var(--shadow-glow); }
.project-create-form__row { display:grid; grid-template-columns:1fr 1fr; gap:.8rem; margin-top:.8rem; }
.project-create-form__modes { display:flex; gap:.25rem; margin-bottom:.8rem; padding:.2rem; background:var(--color-surface); border-radius:6px; }
.project-create-form__modes button { min-height:34px; display:inline-flex; align-items:center; justify-content:center; gap:.4rem; flex:1; color:var(--color-ink-muted); border-radius:4px; font-size:.7rem; font-weight:700; }
.project-create-form__modes button.active { color:var(--color-primary); background:var(--color-white); box-shadow:var(--shadow-sm); }
.project-create-form__upload { min-height:230px; place-items:center; align-content:center; gap:.4rem!important; color:var(--color-ink-muted)!important; background:var(--color-base); border:1px dashed var(--color-border); border-radius:6px; cursor:pointer; text-align:center; }
.project-create-form__upload strong { color:var(--color-ink); font-size:.78rem; }
.project-create-form__upload span { font-size:.65rem; font-weight:400; }
.project-create-form__upload input { position:absolute; width:1px; height:1px; opacity:0; }
.project-create-form__error { padding:.75rem; color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 8%,transparent); border-left:3px solid var(--color-accent); font-size:.72rem; }
.project-create-form__footer { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1rem 0 0; }
.project-create-form__footer p,.project-create-form__footer button { display:flex; align-items:center; gap:.45rem; }
.project-create-form__footer p { color:var(--color-ink-muted); font-size:.67rem; }
.project-create-form__footer button { min-height:42px; padding:0 1rem; color:#17312f; background:var(--color-secondary); border-radius:6px; font-size:.73rem; font-weight:750; }
.project-create-form__footer button:disabled { opacity:.45; }
.spin { animation:spin .9s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
@media (max-width:620px) { .project-create-form > section { padding:1rem; } .project-create-form__row { grid-template-columns:1fr; } .project-create-form__footer { align-items:stretch; flex-direction:column; } .project-create-form__footer button { justify-content:center; } }
</style>
