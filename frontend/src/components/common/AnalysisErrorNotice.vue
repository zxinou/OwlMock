<script setup>
defineProps({
  title: { type: String, default: '这次分析没有完成' },
  message: { type: String, default: '模型返回的结果不够完整，请再试一次。' },
  retryLabel: { type: String, default: '重新分析' },
  retryable: { type: Boolean, default: true },
})

defineEmits(['retry'])
</script>

<template>
  <div class="analysis-error" role="alert">
    <div class="analysis-error__icon" aria-hidden="true">!</div>
    <div class="min-w-0 flex-1">
      <p class="text-sm font-semibold text-ink">{{ title }}</p>
      <p class="mt-1 text-sm text-ink-light leading-relaxed">{{ message }}</p>
    </div>
    <button
      v-if="retryable"
      class="btn btn--secondary shrink-0 text-sm"
      type="button"
      @click="$emit('retry')"
    >
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M20 6v5h-5M4 18v-5h5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M18.2 9A7 7 0 0 0 6.3 6.3L4 8m16 8-2.3 1.7A7 7 0 0 1 5.8 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      {{ retryLabel }}
    </button>
  </div>
</template>

<style scoped>
.analysis-error {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.125rem;
  border: 1px solid color-mix(in srgb, var(--color-accent) 42%, var(--color-border-light));
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-accent) 7%, var(--color-white));
}

.analysis-error__icon {
  width: 2rem;
  height: 2rem;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--color-accent);
  color: #fff;
  font-size: 0.875rem;
  font-weight: 700;
}

@media (max-width: 640px) {
  .analysis-error {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .analysis-error .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
