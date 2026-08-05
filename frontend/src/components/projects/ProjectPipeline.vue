<script setup>
import { computed } from 'vue'
import { Check, FileSearch, FileUser, MessagesSquare } from 'lucide-vue-next'

const props = defineProps({
  steps: { type: Array, default: () => [] },
  score: { type: Number, default: null },
})

const definitions = [
  { key: 'job', number: '01', title: '岗位理解', description: 'JD 分析与要求拆解', icon: FileSearch },
  { key: 'resume', number: '02', title: '材料适配', description: '主简历与岗位匹配', icon: FileUser },
  { key: 'interview', number: '03', title: '模拟面试', description: '文字或语音练习', icon: MessagesSquare },
]

const items = computed(() => definitions.map((definition) => {
  const source = props.steps.find((step) => step.key === definition.key) || {}
  return { ...definition, status: source.status || 'not_started' }
}))

function statusLabel(item) {
  if (item.status === 'completed') return item.key === 'resume' && props.score !== null
    ? `${Math.round(props.score)} 分`
    : '已完成'
  if (item.status === 'in_progress') return '进行中'
  return '待开始'
}
</script>

<template>
  <section class="project-pipeline" aria-labelledby="pipeline-heading">
    <div class="project-pipeline__heading">
      <div>
        <p>准备进度</p>
        <h2 id="pipeline-heading">从理解岗位到稳定表达</h2>
      </div>
      <span>{{ items.filter((item) => item.status === 'completed').length }} / 3</span>
    </div>

    <div class="project-pipeline__track">
      <article
        v-for="(item, index) in items"
        :key="item.key"
        class="project-pipeline__step"
        :class="`is-${item.status}`"
      >
        <div class="project-pipeline__marker" aria-hidden="true">
          <Check v-if="item.status === 'completed'" :size="17" :stroke-width="2.4" />
          <component :is="item.icon" v-else :size="17" :stroke-width="1.9" />
        </div>
        <div class="project-pipeline__copy">
          <small>{{ item.number }}</small>
          <strong>{{ item.title }}</strong>
          <span>{{ item.description }}</span>
        </div>
        <em>{{ statusLabel(item) }}</em>
        <span v-if="index < items.length - 1" class="project-pipeline__line" aria-hidden="true" />
      </article>
    </div>
  </section>
</template>

<style scoped>
.project-pipeline { padding:1.35rem 1.45rem 1.5rem; background:var(--color-white); border:1px solid var(--color-border); border-radius:8px; box-shadow:var(--shadow-sm); }
.project-pipeline__heading { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; margin-bottom:1.4rem; }
.project-pipeline__heading p { color:var(--color-primary); font-size:.68rem; font-weight:750; }
.project-pipeline__heading h2 { margin-top:.25rem; font-size:1.05rem; }
.project-pipeline__heading > span { padding:.28rem .5rem; color:var(--color-ink-muted); background:var(--color-surface); border-radius:5px; font-size:.7rem; font-weight:700; }
.project-pipeline__track { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; }
.project-pipeline__step { position:relative; min-width:0; display:grid; grid-template-columns:38px minmax(0,1fr); gap:.75rem; align-items:center; padding-right:.85rem; }
.project-pipeline__marker { position:relative; z-index:2; width:38px; height:38px; display:grid; place-items:center; color:var(--color-ink-muted); background:var(--color-surface); border:1px solid var(--color-border); border-radius:7px; }
.project-pipeline__copy { min-width:0; }
.project-pipeline__copy small,.project-pipeline__copy strong,.project-pipeline__copy span { display:block; }
.project-pipeline__copy small { color:var(--color-ink-muted); font-size:.58rem; font-weight:700; }
.project-pipeline__copy strong { margin-top:.12rem; color:var(--color-ink); font-size:.82rem; }
.project-pipeline__copy span { margin-top:.12rem; overflow:hidden; color:var(--color-ink-muted); font-size:.66rem; text-overflow:ellipsis; white-space:nowrap; }
.project-pipeline__step em { grid-column:2; width:max-content; margin-top:-.2rem; color:var(--color-ink-muted); font-size:.62rem; font-style:normal; font-weight:700; }
.project-pipeline__line { position:absolute; top:19px; left:38px; right:-1rem; height:1px; background:var(--color-border); }
.project-pipeline__step.is-completed .project-pipeline__marker { color:#fff; background:var(--color-primary); border-color:var(--color-primary); }
.project-pipeline__step.is-completed em { color:var(--color-primary); }
.project-pipeline__step.is-in_progress .project-pipeline__marker { color:#6b4b0f; background:color-mix(in srgb,var(--color-secondary) 24%,var(--color-white)); border-color:color-mix(in srgb,var(--color-secondary) 60%,var(--color-border)); }
.project-pipeline__step.is-in_progress em { color:#8a6515; }
@media (max-width:760px) {
  .project-pipeline { padding:1.15rem; }
  .project-pipeline__track { grid-template-columns:1fr; gap:.2rem; }
  .project-pipeline__step { min-height:72px; padding:0 0 .7rem; }
  .project-pipeline__line { top:38px; bottom:-.2rem; left:19px; right:auto; width:1px; height:auto; }
}
</style>
