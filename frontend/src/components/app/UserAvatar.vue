<script setup>
import { computed } from 'vue'

const props = defineProps({
  user: { type: Object, default: null },
  size: { type: Number, default: 34 },
})

const palettes = [
  { background: '#D5A43F', color: '#382B10' },
  { background: '#2D6B65', color: '#FFFFFF' },
  { background: '#D86C57', color: '#FFFFFF' },
  { background: '#58758A', color: '#FFFFFF' },
  { background: '#5E7E62', color: '#FFFFFF' },
  { background: '#866478', color: '#FFFFFF' },
]

const displayName = computed(() => (
  props.user?.display_name
  || props.user?.email?.split('@')[0]
  || 'OwlMock 用户'
))

const identity = computed(() => props.user?.email || props.user?.id || displayName.value)
const palette = computed(() => {
  const hash = Array.from(identity.value).reduce((total, character) => (
    ((total << 5) - total) + character.codePointAt(0)
  ), 0)
  return palettes[Math.abs(hash) % palettes.length]
})

const initials = computed(() => {
  const value = displayName.value.trim()
  if (!value) return 'OM'
  if (/^[\u3400-\u9fff]/u.test(value)) return value.slice(0, 2)
  return value
    .split(/[\s._-]+/)
    .filter(Boolean)
    .map((part) => part.slice(0, 1))
    .join('')
    .slice(0, 2)
    .toUpperCase()
})

const avatarStyle = computed(() => ({
  '--avatar-background': palette.value.background,
  '--avatar-color': palette.value.color,
  '--avatar-size': `${props.size}px`,
  '--avatar-font-size': `${Math.max(10, Math.round(props.size * 0.34))}px`,
}))
</script>

<template>
  <span
    class="user-avatar"
    :style="avatarStyle"
    role="img"
    :aria-label="`${displayName} 的头像`"
    :title="displayName"
  >{{ initials }}</span>
</template>

<style scoped>
.user-avatar {
  width: var(--avatar-size);
  height: var(--avatar-size);
  display: inline-grid;
  place-items: center;
  flex: none;
  overflow: hidden;
  color: var(--avatar-color);
  background: var(--avatar-background);
  border: 1px solid color-mix(in srgb, var(--avatar-color) 18%, transparent);
  border-radius: 50%;
  font-family: var(--font-heading);
  font-size: var(--avatar-font-size);
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0;
  user-select: none;
}
</style>
