<script setup>
import { CheckCircle2, PlusCircle, Star } from 'lucide-vue-next'

const props = defineProps({
  title: { type: String, required: true },
  items: { type: Array, default: () => [] },
  tone: { type: String, default: 'must' },
})

const icons = { must: CheckCircle2, prefer: Star, bonus: PlusCircle }
</script>

<template>
  <section class="jd-req-group" :class="`tone-${tone}`">
    <header>
      <component :is="icons[props.tone]" :size="17" />
      <h2>{{ title }}</h2>
      <span>{{ items.length }}</span>
    </header>
    <div v-if="items.length" class="jd-req-list">
      <article v-for="(item, index) in items" :key="`${item.title}-${index}`">
        <div class="jd-req-mark">{{ tone === 'must' ? '必' : tone === 'prefer' ? '优' : '+' }}</div>
        <div class="jd-req-copy">
          <h3>{{ item.title }}</h3>
          <p>{{ item.detail }}</p>
          <div v-if="item.keywords?.length" class="jd-keywords">
            <span v-for="keyword in item.keywords" :key="keyword">{{ keyword }}</span>
          </div>
          <blockquote v-if="item.evidence">依据：{{ item.evidence }}</blockquote>
        </div>
      </article>
    </div>
    <p v-else class="jd-empty">该 JD 没有识别出此类要求</p>
  </section>
</template>

<style scoped>
.jd-req-group { min-width:0; padding-top:.2rem; border-top:1px solid var(--color-border); }
.jd-req-group > header { display:flex; align-items:center; gap:.55rem; margin-bottom:.25rem; padding:.2rem 0 .7rem; color:var(--color-primary); }
.jd-req-group > header h2 { flex:1; font-size:.95rem; }
.jd-req-group > header span { min-width:1.65rem; height:1.65rem; display:grid; place-items:center; border-radius:999px; background:var(--color-surface); color:var(--color-ink-muted); font-size:.72rem; }
.jd-req-list { display:grid; }
.jd-req-list article { min-width:0; display:grid; grid-template-columns:1.75rem minmax(0,1fr); gap:.9rem; padding:1rem .15rem; border-bottom:1px solid var(--color-border-light); }
.jd-req-mark { width:1.75rem; height:1.75rem; display:grid; place-items:center; border-radius:6px; color:var(--color-accent); background:color-mix(in srgb, var(--color-accent) 12%, transparent); font-size:.75rem; font-weight:700; }
.tone-prefer .jd-req-mark { color:#926714; background:color-mix(in srgb, var(--color-secondary) 20%, transparent); }
.tone-bonus .jd-req-mark { color:var(--color-primary); background:color-mix(in srgb, var(--color-primary) 12%, transparent); }
.jd-req-copy { min-width:0; }
.jd-req-copy h3 { font-size:.84rem; overflow-wrap:anywhere; }
.jd-req-copy p { margin-top:.3rem; color:var(--color-ink-light); font-size:.78rem; line-height:1.65; overflow-wrap:anywhere; }
.jd-keywords { display:flex; flex-wrap:wrap; gap:.35rem; margin-top:.55rem; }
.jd-keywords span { padding:.18rem .42rem; border-radius:5px; color:var(--color-primary); background:color-mix(in srgb, var(--color-primary) 9%, transparent); font-size:.66rem; }
.jd-req-copy blockquote { margin-top:.55rem; padding-left:.6rem; border-left:2px solid var(--color-border); color:var(--color-ink-muted); font-size:.7rem; line-height:1.55; overflow-wrap:anywhere; }
.jd-empty { padding:1.5rem .5rem; color:var(--color-ink-muted); font-size:.8rem; text-align:center; }
@media (max-width:560px) { .jd-req-list article { grid-template-columns:1fr; gap:.55rem; padding-inline:0; } }
</style>
