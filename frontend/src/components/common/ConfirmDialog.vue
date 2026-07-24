<script setup>
const props = defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: '确认' },
  cancelText: { type: String, default: '取消' },
  loading: { type: Boolean, default: false },
  tone: { type: String, default: 'danger' },
})

const emit = defineEmits(['confirm', 'cancel'])

function cancel() {
  if (!props.loading) emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div
        v-if="show"
        class="confirm-backdrop"
        role="presentation"
        @click.self="cancel"
      >
        <section
          class="confirm-dialog"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
        >
          <div class="confirm-icon" :class="`confirm-icon--${tone}`">
            <svg v-if="tone === 'danger'" width="19" height="19" viewBox="0 0 20 20" fill="none">
              <path d="M5 6h10l-.8 10.5H5.8L5 6zM8 6V4.7A1.7 1.7 0 0 1 9.7 3h.6A1.7 1.7 0 0 1 12 4.7V6M3.8 6h12.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </svg>
            <svg v-else width="19" height="19" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.6"/>
              <path d="M10 6.5v4M10 13.5h.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </div>

          <div class="confirm-body">
            <h3 class="confirm-title">{{ title }}</h3>
            <p class="confirm-message">{{ message }}</p>
          </div>

          <div class="confirm-actions">
            <button
              type="button"
              class="btn btn--ghost"
              :disabled="loading"
              @click="cancel"
            >
              {{ cancelText }}
            </button>
            <button
              type="button"
              class="confirm-primary"
              :class="`confirm-primary--${tone}`"
              :disabled="loading"
              @click="emit('confirm')"
            >
              {{ loading ? '处理中...' : confirmText }}
            </button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(17, 24, 39, 0.28);
  backdrop-filter: blur(6px);
}

.confirm-dialog {
  width: min(25rem, 100%);
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  background: var(--color-white);
  box-shadow: var(--shadow-xl);
}

.confirm-icon {
  width: 2.6rem;
  height: 2.6rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
}

.confirm-icon--danger {
  color: #d95745;
  background: rgba(217, 87, 69, 0.1);
}

.confirm-icon--info {
  color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
}

.confirm-body {
  min-width: 0;
}

.confirm-title {
  margin: 0;
  color: var(--color-ink);
  font-size: 1rem;
  font-weight: 700;
}

.confirm-message {
  margin: 0.4rem 0 0;
  color: var(--color-ink-muted);
  font-size: 0.875rem;
  line-height: 1.65;
}

.confirm-actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.35rem;
}

.confirm-primary {
  min-height: 2.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 1rem;
  border-radius: var(--radius-md);
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  transition: opacity var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}

.confirm-primary:hover:not(:disabled) {
  transform: translateY(-1px);
}

.confirm-primary:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.confirm-primary--danger {
  background: #d95745;
}

.confirm-primary--info {
  background: var(--color-primary);
}

.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.18s ease;
}

.dialog-fade-enter-active .confirm-dialog,
.dialog-fade-leave-active .confirm-dialog {
  transition: transform 0.18s ease, opacity 0.18s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

.dialog-fade-enter-from .confirm-dialog,
.dialog-fade-leave-to .confirm-dialog {
  opacity: 0;
  transform: translateY(0.5rem) scale(0.98);
}
</style>
