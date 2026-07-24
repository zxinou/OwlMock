<script setup>
import owlAvatar from '@/assets/owl_avatar.png'

defineProps({
  size: { type: Number, default: 36 },
  color: { type: String, default: 'var(--color-primary, #2D6B65)' },
  strokeWidth: { type: Number, default: 2.2 },
})
</script>

<template>
  <img
    :src="owlAvatar"
    alt="OwlMock 猫头鹰面试官"
    :width="size"
    :height="size"
    class="owl-avatar shrink-0"
    :style="color === 'white' ? { filter: 'brightness(0) invert(1)' } : undefined"
  >
</template>

<style scoped>
.owl-avatar {
  display: block;
  object-fit: contain;
}

html.dark .owl-avatar {
  filter: brightness(0) invert(1);
  opacity: 0.9;
}
</style>
