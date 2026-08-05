<script setup>
import { ArrowRight, Target } from 'lucide-vue-next'

defineProps({
  items: { type: Array, default: () => [] },
  nextAction: { type: Object, required: true },
})
</script>

<template>
  <section class="project-focus" aria-labelledby="focus-heading">
    <div class="project-focus__heading">
      <span aria-hidden="true"><Target :size="18" /></span>
      <div>
        <p>准备重点</p>
        <h2 id="focus-heading">把时间花在最有影响的地方</h2>
      </div>
    </div>
    <ul>
      <li v-for="item in items" :key="item">{{ item }}</li>
    </ul>
    <div class="project-focus__next">
      <div>
        <small>建议下一步</small>
        <strong>{{ nextAction.title }}</strong>
      </div>
      <ArrowRight :size="18" aria-hidden="true" />
    </div>
  </section>
</template>

<style scoped>
.project-focus { min-height:100%; padding:1.45rem; color:#edf7f4; background:#173f3b; border:1px solid rgba(255,255,255,.08); border-radius:8px; box-shadow:var(--shadow-md); }
.project-focus__heading { display:flex; align-items:center; gap:.75rem; padding-bottom:1rem; border-bottom:1px solid rgba(255,255,255,.12); }
.project-focus__heading > span { width:38px; height:38px; display:grid; place-items:center; flex:none; color:#173f3b; background:var(--color-secondary); border-radius:7px; }
.project-focus__heading p { color:#a9c2bd; font-size:.65rem; font-weight:700; }
.project-focus__heading h2 { margin-top:.2rem; color:#fff; font-size:.98rem; }
.project-focus ul { display:grid; gap:.75rem; margin:1.15rem 0 1.35rem; list-style:none; }
.project-focus li { position:relative; padding-left:1rem; color:#cee0dc; font-size:.78rem; line-height:1.45; }
.project-focus li::before { content:''; position:absolute; top:.48rem; left:0; width:5px; height:5px; background:var(--color-secondary); border-radius:50%; }
.project-focus__next { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding-top:1rem; border-top:1px solid rgba(255,255,255,.12); }
.project-focus__next small,.project-focus__next strong { display:block; }
.project-focus__next small { color:#91afa9; font-size:.62rem; }
.project-focus__next strong { margin-top:.25rem; color:#fff; font-size:.78rem; }
.project-focus__next > svg { color:var(--color-secondary); }
</style>
