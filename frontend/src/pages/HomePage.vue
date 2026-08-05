<script setup>
import { onMounted } from 'vue'

import { useScrollReveal } from '@/composables/useScrollReveal.js'
import NavSection from '@/components/landing/NavSection.vue'
import HeroSection from '@/components/landing/HeroSection.vue'
import FeaturesSection from '@/components/landing/FeaturesSection.vue'
import InterviewSection from '@/components/landing/InterviewSection.vue'
import CtaSection from '@/components/landing/CtaSection.vue'
import FooterSection from '@/components/landing/FooterSection.vue'
import { authStore } from '@/stores/auth.js'

useScrollReveal()
onMounted(() => authStore.bootstrap())
</script>

<template>
  <div class="landing-page min-h-screen bg-base transition-theme">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <NavSection />
    <main id="main-content">
      <HeroSection />
      <FeaturesSection />
      <InterviewSection />
      <CtaSection />
    </main>
    <FooterSection />
  </div>
</template>

<style scoped>
.skip-link {
  position: fixed;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 110;
  padding: 0.65rem 0.85rem;
  color: var(--color-on-primary);
  background: var(--color-primary);
  border-radius: 6px;
  transform: translateY(-160%);
}

.skip-link:focus {
  transform: translateY(0);
}
</style>
