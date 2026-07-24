<script setup>
import { CheckCircle2, CircleAlert, CircleMinus } from 'lucide-vue-next'

defineProps({
  title: { type: String, required: true },
  items: { type: Array, default: () => [] },
})

const icons = { 匹配: CheckCircle2, 部分匹配: CircleAlert, 缺失: CircleMinus }
</script>

<template>
  <section class="requirement-group">
    <header><h3>{{ title }}</h3><span>{{ items.length }}</span></header>
    <div v-if="items.length" class="requirement-list">
      <article v-for="(item, index) in items" :key="`${item.requirement}-${index}`" class="requirement-row" :data-status="item.status">
        <div class="requirement-status">
          <component :is="icons[item.status] || CircleMinus" :size="17" />
          <span>{{ item.status }}</span>
        </div>
        <div class="requirement-copy">
          <div class="requirement-title"><strong>{{ item.requirement }}</strong><small>{{ item.importance }}</small></div>
          <p><b>简历证据</b>{{ item.resume_evidence }}</p>
          <p class="requirement-advice"><b>建议</b>{{ item.recommendation }}</p>
        </div>
      </article>
    </div>
    <p v-else class="requirement-empty">该分组没有识别到要求。</p>
  </section>
</template>

<style scoped>
.requirement-group { min-width:0; }
.requirement-group > header { display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.2rem 0 .7rem; border-bottom:1px solid var(--color-border); }
.requirement-group h3 { font-size:.95rem; }
.requirement-group header span { min-width:1.5rem; height:1.5rem; display:grid; place-items:center; border-radius:50%; color:var(--color-ink-muted); background:var(--color-surface); font-size:.68rem; }
.requirement-list { display:grid; }
.requirement-row { display:grid; grid-template-columns:7.5rem minmax(0,1fr); gap:1.25rem; padding:1rem .15rem; border-bottom:1px solid var(--color-border-light); }
.requirement-status { display:flex; align-items:flex-start; gap:.4rem; color:var(--color-ink-muted); font-size:.72rem; font-weight:700; }
[data-status="匹配"] .requirement-status { color:var(--color-primary); }
[data-status="部分匹配"] .requirement-status { color:#9a7418; }
[data-status="缺失"] .requirement-status { color:var(--color-accent); }
.requirement-copy { min-width:0; }
.requirement-title { display:flex; align-items:flex-start; justify-content:space-between; gap:.75rem; }
.requirement-title strong { color:var(--color-ink); font-size:.82rem; overflow-wrap:anywhere; }
.requirement-title small { flex:none; padding:.12rem .4rem; border-radius:4px; color:var(--color-ink-muted); background:var(--color-surface); font-size:.62rem; }
.requirement-copy p { margin-top:.55rem; color:var(--color-ink-light); font-size:.74rem; line-height:1.6; overflow-wrap:anywhere; }
.requirement-copy b { margin-right:.45rem; color:var(--color-ink-muted); font-size:.66rem; }
.requirement-advice { padding-left:.65rem; border-left:2px solid color-mix(in srgb,var(--color-secondary) 55%,transparent); }
.requirement-empty { padding:1rem 0; color:var(--color-ink-muted); font-size:.75rem; }
@media (max-width:560px) { .requirement-row { grid-template-columns:1fr; gap:.55rem; padding-inline:0; } }
</style>
