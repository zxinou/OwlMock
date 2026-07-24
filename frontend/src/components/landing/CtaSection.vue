<template>
  <section :style="{ padding: '5rem 0' }">
    <div class="container text-center">
      <div class="reveal">
        <img
          src="@/assets/owl_interviewer.png"
          alt="OwlMock 猫头鹰面试官"
          class="cta-owl mx-auto mb-4 w-[360px] max-w-full animate-hero-fade-up"
          style="animation-delay: 0.1s"
        >

        <h2 class="text-3xl lg:text-5xl font-bold mb-4" style="font-family: var(--font-heading)">准备好了吗？</h2>
        <p class="text-lg mb-8 mx-auto" style="color: var(--color-ink-light); max-width: 560px; line-height: var(--leading-relaxed)">
          无论你是应届生还是想跳槽的职场人，OwlMock 都能帮你更自信地面对下一场面试
        </p>
        <router-link
          to="/interview"
          class="btn btn--primary no-underline inline-flex"
          style="font-size: var(--text-lg); padding: 1rem 2.5rem"
        >
          立即开始，免费使用
        </router-link>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cta-owl {
  clip-path: inset(0 0 8% 0);
  mix-blend-mode: multiply;
}

html.dark .cta-owl {
  filter: invert(1);
  mix-blend-mode: screen;
}
</style>
