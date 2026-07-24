<script setup>
defineProps({
  tags: { type: Array, default: () => [] },
})
</script>

<template>
  <div class="github-tech-panel">
    <div class="github-tech-heading">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" class="text-primary"><rect x="2" y="2" width="14" height="14" rx="3" stroke="currentColor" stroke-width="1.3"/><path d="M6 8l3 3 3-3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <div><strong>技术栈识别</strong><span>从项目配置与源码中提取</span></div>
    </div>
    <div class="github-tech-tags">
      <span v-for="tag in tags" :key="tag">{{ tag }}</span>
      <span v-if="!tags.length" class="github-tech-empty">暂未识别到技术栈</span>
    </div>
  </div>
</template>

<style scoped>
.github-tech-panel { display:flex; flex-direction:column; justify-content:center; min-width:0; padding:1rem 1.25rem; border:1px solid var(--color-border-light); border-radius:var(--radius-md); background:var(--color-white); }
.github-tech-heading { display:flex; align-items:flex-start; gap:.55rem; color:var(--color-primary); }
.github-tech-heading svg { flex:none; margin-top:.05rem; }
.github-tech-heading strong, .github-tech-heading span { display:block; }
.github-tech-heading strong { color:var(--color-ink); font-size:.82rem; }
.github-tech-heading span { margin-top:.18rem; color:var(--color-ink-muted); font-size:.67rem; }
.github-tech-tags { display:flex; flex-wrap:wrap; gap:.45rem; margin-top:.8rem; }
.github-tech-tags span { padding:.3rem .55rem; border:1px solid color-mix(in srgb,var(--color-primary) 18%,var(--color-border-light)); border-radius:999px; color:var(--color-primary-dark); background:color-mix(in srgb,var(--color-primary) 7%,var(--color-white)); font-size:.68rem; font-weight:600; }
.github-tech-empty { color:var(--color-ink-muted) !important; background:transparent !important; }
:global(.dark) .github-tech-panel { background:var(--color-surface); }
:global(.dark) .github-tech-tags span { color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 12%,var(--color-surface)); }
</style>
