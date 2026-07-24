<script setup>
import owlCoach from '@/assets/owl_interviewer.png'

defineProps({
  active: { type: Boolean, default: false },
  text: { type: String, default: '正在分析中' },
  subtext: { type: String, default: '猫头鹰教练正在处理中...' },
  blocking: { type: Boolean, default: false },
})
</script>

<template>
  <Transition name="fade">
    <div
      v-if="active"
      :class="[
        'fixed z-50 flex pointer-events-none',
        blocking
          ? 'inset-0 items-center justify-center loading-overlay--blocking'
          : 'right-5 items-start justify-end loading-overlay--floating',
      ]"
    >
      <div
        :class="[
          'text-center animate-fade-in loading-card',
          blocking ? 'loading-card--blocking' : 'loading-card--floating',
        ]"
        :style="{
          background: 'var(--color-white)',
          boxShadow: 'var(--shadow-xl)',
        }"
      >
        <div v-if="blocking" class="owl-loading-frame mx-auto mb-4 animate-bounce-subtle">
          <img :src="owlCoach" alt="猫头鹰面试官正在分析" class="owl-loading-image" />
        </div>
        <div v-else class="loading-spinner" aria-hidden="true"></div>
        <div class="loading-copy">
          <p class="text-base font-medium mb-2" style="color: var(--color-ink)">
            {{ text }}<span class="loading-dots"><span></span><span></span><span></span></span>
          </p>
          <p class="text-sm" style="color: var(--color-ink-muted)">{{ subtext }}</p>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.loading-overlay--blocking {
  background: rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(4px);
  pointer-events: auto;
}

.loading-card {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
}

.loading-card--blocking {
  padding: 2.5rem 3rem;
}

.loading-card--floating {
  width: min(21rem, calc(100vw - 2rem));
  padding: 0.8rem 0.95rem;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 0.75rem;
  text-align: left;
  background: color-mix(in srgb, var(--color-white) 94%, transparent) !important;
  backdrop-filter: blur(16px);
  box-shadow: var(--shadow-md) !important;
}

.loading-overlay--floating {
  top: calc(var(--nav-height) + 0.875rem);
}

.owl-loading-frame {
  width: 9rem;
  height: 7rem;
  overflow: hidden;
}

.loading-copy {
  min-width: 0;
}

.loading-card--floating .loading-copy p:first-child {
  margin-bottom: 0.15rem;
  font-size: 0.875rem;
}

.loading-card--floating .loading-copy p:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.75rem;
}

.owl-loading-image {
  width: 16rem;
  max-width: none;
  transform: translate(-2.2rem, -0.7rem);
  mix-blend-mode: multiply;
}

.loading-spinner {
  width: 2rem;
  height: 2rem;
  border-radius: var(--radius-full);
  border: 2px solid color-mix(in srgb, var(--color-primary) 18%, transparent);
  border-top-color: var(--color-primary);
  animation: spin 0.85s linear infinite;
}

html.dark .owl-loading-image {
  filter: invert(1);
  mix-blend-mode: screen;
}

@media (max-width: 640px) {
  .loading-overlay--floating {
    right: 0.75rem;
    top: calc(var(--nav-height) + 0.75rem);
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
