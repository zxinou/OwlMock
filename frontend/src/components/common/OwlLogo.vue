<script setup>
import owlAvatar from '@/assets/owl_avatar.png'

defineProps({
  size: { type: Number, default: 36 },
  color: { type: String, default: 'var(--color-primary, #2D6B65)' },
  strokeWidth: { type: Number, default: 2.2 },
  light: { type: Boolean, default: false },
})
</script>

<template>
  <img
    :src="owlAvatar"
    alt="OwlMock 猫头鹰面试官"
    :width="size"
    :height="size"
    class="owl-avatar shrink-0"
    :class="{ 'owl-avatar--light': light }"
    :style="color === 'white' ? { filter: 'brightness(0) invert(1)' } : undefined"
  >
</template>

<style scoped>
.owl-avatar {
  display: block;
  object-fit: contain;
}

html.dark .owl-avatar:not(.owl-avatar--light) {
  filter: brightness(0) invert(1);
  opacity: 0.9;
}
</style>
