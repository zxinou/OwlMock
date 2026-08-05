<script setup>
import { ArrowDown, LogIn, ShieldCheck } from 'lucide-vue-next'
</script>

<template>
  <section class="landing-hero">
    <div class="container grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
      <!-- Content -->
      <div class="text-center lg:text-left">
        <!-- Badge -->
        <div
          class="inline-flex items-center gap-2 rounded-full text-xs font-medium mb-6 animate-hero-fade-up"
          style="padding: 0.25rem 1rem; background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-ink-muted); animation-delay: 0.1s"
        >
          <span class="w-1.5 h-1.5 rounded-full" style="background: var(--color-secondary)"></span>
          AI 驱动的求职辅助平台
        </div>

        <!-- Title -->
        <h1
          class="font-bold mb-6 animate-hero-fade-up leading-[1.1]"
          style="font-family: var(--font-heading); font-size: var(--text-hero); margin-bottom: 1.5rem; animation-delay: 0.2s"
        >
          让求职变得<br>
          <span style="color: var(--color-primary)">更有把握</span>
        </h1>

        <!-- Description -->
        <p
          class="mb-8 max-w-[480px] mx-auto lg:mx-0 animate-hero-fade-up"
          style="font-size: var(--text-lg); color: var(--color-ink-light); line-height: var(--leading-relaxed); animation-delay: 0.35s"
        >
          从源码分析到模拟面试，OwlMock 用 AI 帮你拆解每一个求职环节。
          像有位耐心的朋友陪你准备，而不是冰冷的工具。
        </p>

        <!-- Actions -->
        <div class="flex flex-wrap gap-4 justify-center lg:justify-start animate-hero-fade-up" style="animation-delay: 0.5s">
          <a href="#features" class="btn btn--primary no-underline" style="font-size: var(--text-base)">
            <ArrowDown :size="18" />
            开始使用
          </a>
          <router-link :to="{ name: 'login' }" class="btn btn--secondary no-underline" style="font-size: var(--text-base)">
            <LogIn :size="18" />
            已有账户，登录
          </router-link>
        </div>
        <p class="hero-access-note justify-center lg:justify-start animate-hero-fade-up" style="animation-delay: 0.58s">
          <ShieldCheck :size="16" />
          可直接查看全部功能介绍，实际使用时再登录或注册
        </p>
      </div>

      <!-- Illustration -->
      <div class="flex justify-center items-center animate-hero-fade-scale" style="animation-delay: 0.3s">
        <img
          src="@/assets/owl_interviewer.png"
          alt="OwlMock 猫头鹰面试官在审阅简历"
          class="owl-interviewer-art w-full max-w-xl"
          width="2142"
          height="1537"
          fetchpriority="high"
          decoding="async"
        >
      </div>
    </div>
  </section>
</template>

<style scoped>
.landing-hero {
  padding-top: calc(var(--nav-height) + 3.5rem);
  padding-bottom: 4rem;
  overflow: hidden;
}

.owl-interviewer-art {
  clip-path: inset(0 0 8% 0);
  mix-blend-mode: multiply;
}

.hero-access-note {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-top: 1rem;
  color: var(--color-ink-muted);
  font-size: 0.82rem;
}

@media (max-width: 640px) {
  .landing-hero {
    padding-top: calc(var(--nav-height) + 2.5rem);
    padding-bottom: 3rem;
  }
}
</style>
