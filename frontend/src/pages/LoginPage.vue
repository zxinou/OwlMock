<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  LogIn,
  UserPlus,
} from 'lucide-vue-next'

import OwlLogo from '@/components/common/OwlLogo.vue'
import { normalizeAuthRedirect } from '@/router/authGuard.js'
import { authStore } from '@/stores/auth.js'

const route = useRoute()
const router = useRouter()
const email = ref('')
const displayName = ref('')
const password = ref('')
const passwordVisible = ref(false)
const error = ref('')

const isRegister = computed(() => route.name === 'register')
const heading = computed(() => (isRegister.value ? '创建 OwlMock 账户' : '登录 OwlMock'))
const submitLabel = computed(() => (isRegister.value ? '创建账户' : '进入工作台'))
const alternateRoute = computed(() => (isRegister.value ? 'login' : 'register'))
const alternateLabel = computed(() => (isRegister.value ? '已有账户？登录' : '还没有账户？创建账户'))
const submitDisabled = computed(() => !email.value || !password.value || authStore.loading)

async function submit() {
  if (submitDisabled.value) return

  error.value = ''
  try {
    const input = {
      email: email.value.trim(),
      password: password.value,
    }
    if (isRegister.value) input.displayName = displayName.value.trim()
    if (isRegister.value) await authStore.register(input)
    else await authStore.login(input)
    await router.replace(normalizeAuthRedirect(route.query.redirect))
  } catch (cause) {
    error.value = cause?.message || '账户操作未完成，请稍后重试。'
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-page__brand" aria-labelledby="login-brand-title">
      <div class="login-page__brand-lockup">
        <span class="login-page__logo"><OwlLogo :size="36" style="filter: none; opacity: 1" /></span>
        <span>OwlMock</span>
      </div>

      <div class="login-page__brand-copy">
        <div class="login-page__owl" aria-hidden="true">
          <OwlLogo :size="136" style="filter: none; opacity: 1" />
        </div>
        <p>求职准备工作台</p>
        <h1 id="login-brand-title">把每一次准备，留在属于你的安全空间里</h1>
      </div>

      <p class="login-page__instance">OwlMock 账户服务</p>
    </section>

    <section class="login-page__form-panel" aria-labelledby="login-heading">
      <div class="login-page__mobile-brand">
        <span class="login-page__logo"><OwlLogo :size="30" style="filter: none; opacity: 1" /></span>
        <strong>OwlMock</strong>
      </div>

      <form class="login-form" :aria-busy="authStore.loading" @submit.prevent="submit">
        <div class="login-form__heading">
          <span class="login-form__heading-icon" aria-hidden="true"><LockKeyhole :size="19" /></span>
          <p>{{ isRegister ? '创建账户' : '安全登录' }}</p>
          <h2 id="login-heading">{{ heading }}</h2>
          <p v-if="isRegister" class="login-form__access-note">使用邮箱创建你的个人账户，不需要管理员账号。</p>
        </div>

        <div class="login-form__field">
          <label for="email">邮箱</label>
          <div class="login-form__input-wrap login-form__input-wrap--plain" :class="{ 'login-form__input-wrap--error': error }">
            <input
              id="email"
              v-model="email"
              type="email"
              name="email"
              autocomplete="email"
              required
              autofocus
              :disabled="authStore.loading"
              :aria-invalid="Boolean(error)"
              :aria-describedby="error ? 'login-error' : undefined"
            >
          </div>
        </div>

        <div v-if="isRegister" class="login-form__field">
          <label for="display-name">昵称（可选）</label>
          <div class="login-form__input-wrap login-form__input-wrap--plain">
            <input
              id="display-name"
              v-model="displayName"
              type="text"
              name="display-name"
              autocomplete="name"
              maxlength="80"
              :disabled="authStore.loading"
            >
          </div>
        </div>

        <div class="login-form__field">
          <label for="password">密码</label>
          <div class="login-form__input-wrap" :class="{ 'login-form__input-wrap--error': error }">
            <input
              id="password"
              v-model="password"
              :type="passwordVisible ? 'text' : 'password'"
              name="password"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
              minlength="10"
              required
              :disabled="authStore.loading"
              :aria-invalid="Boolean(error)"
              :aria-describedby="error ? 'login-error' : undefined"
            >
            <button
              type="button"
              class="login-form__reveal"
              :aria-label="passwordVisible ? '隐藏密码' : '显示密码'"
              :title="passwordVisible ? '隐藏密码' : '显示密码'"
              @click="passwordVisible = !passwordVisible"
            >
              <EyeOff v-if="passwordVisible" :size="18" />
              <Eye v-else :size="18" />
            </button>
          </div>
          <p v-if="isRegister" class="login-form__hint">至少 10 个字符</p>
        </div>

        <p v-if="error" id="login-error" class="login-form__error" role="alert">{{ error }}</p>

        <button class="login-form__submit" type="submit" :disabled="submitDisabled">
          <LoaderCircle v-if="authStore.loading" class="login-form__spinner" :size="18" />
          <UserPlus v-else-if="isRegister" :size="18" />
          <LogIn v-else :size="18" />
          <span>{{ authStore.loading ? '正在提交' : submitLabel }}</span>
        </button>

        <p class="login-form__alternate">
          <router-link :to="{ name: alternateRoute, query: { redirect: route.query.redirect } }">
            {{ alternateLabel }}
          </router-link>
        </p>
      </form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(340px, 0.9fr) minmax(460px, 1.1fr);
  background: var(--color-base);
}

.login-page__brand {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 2rem clamp(2rem, 6vw, 5rem);
  overflow: hidden;
  color: var(--color-rail-ink);
  background: var(--color-rail);
  border-right: 1px solid var(--color-border);
}

.login-page__brand-lockup,
.login-page__mobile-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 750;
}

.login-page__logo {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  flex: none;
  overflow: hidden;
  background: var(--color-white);
  border-radius: 7px;
}

.login-page__brand-copy {
  width: min(100%, 470px);
  margin: auto 0;
}

.login-page__owl {
  width: 188px;
  height: 188px;
  display: grid;
  place-items: center;
  margin-bottom: 2rem;
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 18px 18px 0 color-mix(in srgb, var(--color-secondary) 20%, transparent);
}

.login-page__brand-copy p {
  margin-bottom: 0.65rem;
  color: var(--color-secondary-light);
  font-size: 0.75rem;
  font-weight: 700;
}

.login-page__brand-copy h1 {
  max-width: 460px;
  color: var(--color-rail-ink);
  font-size: 2.2rem;
  line-height: 1.28;
}

.login-page__instance {
  color: var(--color-rail-muted);
  font-size: 0.72rem;
}

.login-page__form-panel {
  min-width: 0;
  display: grid;
  place-items: center;
  padding: 2rem;
}

.login-page__mobile-brand {
  display: none;
}

.login-form {
  width: min(100%, 390px);
}

.login-form__heading {
  margin-bottom: 2rem;
}

.login-form__heading-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  margin-bottom: 1rem;
  color: var(--color-primary);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: 7px;
}

.login-form__heading p {
  margin-bottom: 0.35rem;
  color: var(--color-primary);
  font-size: 0.72rem;
  font-weight: 700;
}

.login-form__heading h2 {
  font-size: 1.8rem;
}

.login-form__access-note {
  margin-top: 0.6rem;
  color: var(--color-ink-muted);
  font-size: 0.76rem;
  line-height: 1.6;
}

.login-form__field + .login-form__field {
  margin-top: 1rem;
}

.login-form__field label {
  display: inline-block;
  margin-bottom: 0.5rem;
  color: var(--color-ink-light);
  font-size: 0.78rem;
  font-weight: 650;
}

.login-form__input-wrap {
  height: 48px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 44px;
  align-items: center;
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: 7px;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}

.login-form__input-wrap--plain {
  grid-template-columns: minmax(0, 1fr);
}

.login-form__input-wrap:focus-within {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
}

.login-form__input-wrap--error {
  border-color: var(--color-accent);
}

.login-form__input-wrap input {
  width: 100%;
  height: 100%;
  min-width: 0;
  padding: 0 0.9rem;
  color: var(--color-ink);
  background: transparent;
  border: 0;
  outline: 0;
}

.login-form__reveal {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  color: var(--color-ink-muted);
  border-radius: 5px;
}

.login-form__reveal:hover {
  color: var(--color-primary);
  background: var(--color-surface);
}

.login-form__hint {
  margin-top: 0.4rem;
  color: var(--color-ink-muted);
  font-size: 0.72rem;
}

.login-form__error {
  margin-top: 0.75rem;
  padding-left: 0.7rem;
  color: var(--color-accent);
  border-left: 2px solid var(--color-accent);
  font-size: 0.76rem;
  line-height: 1.5;
}

.login-form__submit {
  width: 100%;
  min-height: 46px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1.15rem;
  color: var(--color-on-primary);
  background: var(--color-primary);
  border-radius: 7px;
  font-size: 0.82rem;
  font-weight: 700;
  transition: background var(--duration-fast), transform var(--duration-fast);
}

.login-form__submit:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
}

.login-form__submit:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.login-form__alternate {
  margin-top: 1rem;
  text-align: center;
  font-size: 0.78rem;
}

.login-form__alternate a {
  color: var(--color-primary);
  font-weight: 650;
}

.login-form__alternate a:hover {
  text-decoration: underline;
}

.login-form__spinner {
  animation: login-spin 0.8s linear infinite;
}

:global(.dark) .login-form__submit {
  color: var(--color-on-secondary);
  background: var(--color-secondary);
}

@keyframes login-spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 820px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .login-page__brand {
    display: none;
  }

  .login-page__form-panel {
    align-content: center;
    gap: 2.5rem;
    padding: 1.5rem;
  }

  .login-page__mobile-brand {
    width: min(100%, 390px);
    display: flex;
  }
}

@media (max-width: 420px) {
  .login-page__form-panel {
    place-items: stretch;
    padding: 1.15rem;
  }

  .login-form__heading h2 {
    font-size: 1.6rem;
  }
}
</style>
