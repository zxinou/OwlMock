<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AlertCircle, ArrowLeft, Eye, EyeOff, LoaderCircle, LockKeyhole, LogIn, Mail, ShieldCheck, UserPlus, UserRound } from 'lucide-vue-next'
import OwlLogo from '@/components/common/OwlLogo.vue'
import ThemeToggle from '@/components/common/ThemeToggle.vue'
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
const formDescription = computed(() => isRegister.value ? '使用邮箱创建你的个人账户，不需要管理员账号。' : '继续上次的岗位准备与面试复盘。')
const submitDisabled = computed(() => !email.value.trim() || !password.value || (isRegister.value && password.value.length < 10) || authStore.loading)
function clearError() { error.value = '' }
watch(isRegister, () => { password.value = ''; passwordVisible.value = false; clearError() })
async function submit() {
  if (submitDisabled.value) return
  clearError()
  try {
    const input = { email: email.value.trim(), password: password.value }
    if (isRegister.value) input.displayName = displayName.value.trim()
    if (isRegister.value) await authStore.register(input)
    else await authStore.login(input)
    await router.replace(normalizeAuthRedirect(route.query.redirect))
  } catch (cause) { error.value = cause?.message || '账户操作未完成，请稍后重试。' }
}
</script>

<template>
  <main class="login-page">
    <section class="login-page__brand" aria-labelledby="login-brand-title">
      <router-link to="/" class="login-page__brand-lockup" aria-label="OwlMock 首页">
        <span class="login-page__brand-mark"><OwlLogo :size="36" /></span><strong>OwlMock</strong>
      </router-link>
      <div class="login-page__brand-copy">
        <div class="login-page__owl" aria-hidden="true"><OwlLogo :size="176" /></div>
        <p id="login-brand-title" class="login-page__brand-title">把每一次准备，<br>留在属于你的工作台</p>
        <p class="login-page__brand-support">为下一次更从容的回答，保留完整的准备过程。</p>
      </div>
      <p class="login-page__privacy"><ShieldCheck :size="16" /><span>你的准备内容只属于你的账户</span></p>
    </section>

    <section class="login-page__form-panel" aria-labelledby="login-heading">
      <header class="login-page__panel-actions">
        <router-link to="/" class="login-page__back"><ArrowLeft :size="16" /><span>返回首页</span></router-link>
        <ThemeToggle />
      </header>
      <div class="login-page__form-area">
        <router-link to="/" class="login-page__mobile-brand" aria-label="OwlMock 首页">
          <span class="login-page__brand-mark"><OwlLogo :size="32" /></span><strong>OwlMock</strong>
        </router-link>
        <nav class="login-form__modes" aria-label="账户操作">
          <router-link :to="{ name: 'login', query: { redirect: route.query.redirect } }" :class="{ active: !isRegister }" :aria-current="!isRegister ? 'page' : undefined">登录</router-link>
          <router-link :to="{ name: 'register', query: { redirect: route.query.redirect } }" :class="{ active: isRegister }" :aria-current="isRegister ? 'page' : undefined">注册</router-link>
        </nav>
        <form class="login-form" :aria-busy="authStore.loading" @submit.prevent="submit">
          <div class="login-form__heading">
            <span class="login-form__heading-icon" aria-hidden="true"><LockKeyhole :size="20" /></span>
            <div><h1 id="login-heading">{{ heading }}</h1><p>{{ formDescription }}</p></div>
          </div>
          <div class="login-form__field">
            <label for="email">邮箱</label>
            <div class="login-form__input-wrap" :class="{ 'login-form__input-wrap--error': error }">
              <span class="login-form__input-icon" aria-hidden="true"><Mail :size="18" /></span>
              <input id="email" v-model="email" type="email" name="email" inputmode="email" autocomplete="email" placeholder="name@example.com" required autofocus :disabled="authStore.loading" :aria-invalid="Boolean(error)" :aria-describedby="error ? 'login-error' : undefined" @input="clearError">
            </div>
          </div>
          <div v-if="isRegister" class="login-form__field">
            <label for="display-name">昵称 <span>可选</span></label>
            <div class="login-form__input-wrap"><span class="login-form__input-icon" aria-hidden="true"><UserRound :size="18" /></span><input id="display-name" v-model="displayName" type="text" name="display-name" autocomplete="name" maxlength="80" placeholder="例如：小林" :disabled="authStore.loading"></div>
          </div>
          <div class="login-form__field">
            <label for="password">密码</label>
            <div class="login-form__input-wrap login-form__input-wrap--password" :class="{ 'login-form__input-wrap--error': error }">
              <span class="login-form__input-icon" aria-hidden="true"><LockKeyhole :size="18" /></span>
              <input id="password" v-model="password" :type="passwordVisible ? 'text' : 'password'" name="password" :autocomplete="isRegister ? 'new-password' : 'current-password'" :minlength="isRegister ? 10 : undefined" placeholder="输入你的密码" required :disabled="authStore.loading" :aria-invalid="Boolean(error)" :aria-describedby="error ? 'login-error' : isRegister ? 'password-hint' : undefined" @input="clearError">
              <button type="button" class="login-form__reveal" :aria-label="passwordVisible ? '隐藏密码' : '显示密码'" :title="passwordVisible ? '隐藏密码' : '显示密码'" @click="passwordVisible = !passwordVisible"><EyeOff v-if="passwordVisible" :size="18" /><Eye v-else :size="18" /></button>
            </div>
            <p v-if="isRegister" id="password-hint" class="login-form__hint">至少 10 个字符</p>
          </div>
          <p v-if="error" id="login-error" class="login-form__error" role="alert"><AlertCircle :size="17" /><span>{{ error }}</span></p>
          <button class="login-form__submit" type="submit" :disabled="submitDisabled"><LoaderCircle v-if="authStore.loading" class="login-form__spinner" :size="18" /><UserPlus v-else-if="isRegister" :size="18" /><LogIn v-else :size="18" /><span>{{ authStore.loading ? '正在提交' : submitLabel }}</span></button>
        </form>
      </div>
      <p class="login-page__service">OwlMock 账户服务</p>
    </section>
  </main>
</template>

<style scoped>
.login-page{min-height:100vh;min-height:100dvh;display:grid;grid-template-columns:minmax(420px,.92fr) minmax(520px,1.08fr);background:var(--color-base)}
.login-page__brand{min-height:100vh;min-height:100dvh;display:flex;flex-direction:column;padding:2rem clamp(2.5rem,5vw,5.5rem);overflow:hidden;color:var(--color-rail-ink);background:var(--color-rail);border-right:1px solid var(--color-border)}
.login-page__brand-lockup,.login-page__mobile-brand{width:fit-content;min-height:44px;display:inline-flex;align-items:center;gap:.75rem;color:var(--color-rail-ink);font-family:var(--font-heading);font-size:1.15rem}.login-page__brand-lockup:hover{color:var(--color-primary)}
.login-page__brand-mark{width:44px;height:44px;display:grid;place-items:center;flex:none;overflow:hidden;background:var(--color-white);border:1px solid var(--color-border-light);border-radius:7px;box-shadow:var(--shadow-sm)}
.login-page__brand-copy{width:min(100%,530px);margin:auto 0;padding:3rem 0}.login-page__owl{width:188px;height:172px;display:grid;place-items:center;margin-bottom:2.25rem;overflow:hidden}.login-page__brand-title{max-width:530px;color:var(--color-rail-ink);font-family:var(--font-heading);font-size:clamp(2rem,3vw,2.75rem);font-weight:700;line-height:1.22}.login-page__brand-support{max-width:440px;margin-top:1rem;color:var(--color-rail-muted);font-size:.92rem;line-height:1.75}.login-page__privacy{min-height:44px;display:flex;align-items:center;gap:.5rem;color:var(--color-rail-muted);font-size:.76rem}
.login-page__form-panel{min-width:0;min-height:100vh;min-height:100dvh;display:grid;grid-template-rows:auto minmax(0,1fr) auto;padding:1.5rem clamp(2rem,5vw,5rem)}.login-page__panel-actions{min-height:44px;display:flex;align-items:center;justify-content:space-between;gap:1rem}.login-page__back{min-height:44px;display:inline-flex;align-items:center;gap:.45rem;color:var(--color-ink-muted);font-size:.76rem;font-weight:650}.login-page__back:hover{color:var(--color-primary)}
.login-page__form-area{width:min(100%,430px);display:flex;flex-direction:column;justify-content:center;justify-self:center;padding:2.5rem 0}.login-page__mobile-brand{display:none}.login-form__modes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.25rem;padding:.25rem;background:var(--color-surface);border:1px solid var(--color-border-light);border-radius:8px}.login-form__modes a{min-height:40px;display:grid;place-items:center;color:var(--color-ink-muted);border-radius:5px;font-size:.78rem;font-weight:700;transition:color var(--duration-fast),background var(--duration-fast),box-shadow var(--duration-fast)}.login-form__modes a:hover{color:var(--color-primary)}.login-form__modes a.active{color:var(--color-ink);background:var(--color-white);box-shadow:var(--shadow-sm)}
.login-form__heading{display:flex;align-items:center;gap:.9rem;margin:2rem 0 1.75rem}.login-form__heading-icon{width:44px;height:44px;display:grid;place-items:center;flex:none;color:var(--color-primary);background:var(--color-surface);border:1px solid var(--color-border-light);border-radius:7px}.login-form__heading h1{font-size:1.72rem;line-height:1.25}.login-form__heading p{margin-top:.35rem;color:var(--color-ink-muted);font-size:.76rem;line-height:1.55}
.login-form__field+.login-form__field{margin-top:1rem}.login-form__field label{display:inline-flex;align-items:center;gap:.45rem;margin-bottom:.45rem;color:var(--color-ink-light);font-size:.78rem;font-weight:650}.login-form__field label span{color:var(--color-ink-muted);font-size:.68rem;font-weight:500}.login-form__input-wrap{min-height:48px;display:grid;grid-template-columns:44px minmax(0,1fr);align-items:center;background:var(--color-white);border:1px solid var(--color-border);border-radius:7px;transition:border-color var(--duration-fast),box-shadow var(--duration-fast)}.login-form__input-wrap--password{grid-template-columns:44px minmax(0,1fr) 44px}.login-form__input-wrap:hover:not(:focus-within){border-color:var(--color-primary-light)}.login-form__input-wrap:focus-within{border-color:var(--color-primary);box-shadow:var(--shadow-glow)}.login-form__input-wrap--error{border-color:var(--color-accent)}.login-form__input-icon{display:grid;place-items:center;color:var(--color-ink-muted)}.login-form__input-wrap:focus-within .login-form__input-icon{color:var(--color-primary)}.login-form__input-wrap input{width:100%;height:46px;min-width:0;padding:0 .75rem 0 0;color:var(--color-ink);background:transparent;border:0;outline:0}.login-form__input-wrap input::placeholder{color:var(--color-ink-muted);opacity:.72}.login-form__reveal{width:44px;height:44px;display:grid;place-items:center;color:var(--color-ink-muted);border-radius:5px}.login-form__reveal:hover{color:var(--color-primary);background:var(--color-surface)}.login-form__hint{margin-top:.4rem;color:var(--color-ink-muted);font-size:.72rem}
.login-form__error{display:flex;align-items:flex-start;gap:.5rem;margin-top:.85rem;padding:.7rem .8rem;color:var(--color-accent);background:color-mix(in srgb,var(--color-accent) 8%,transparent);border:1px solid color-mix(in srgb,var(--color-accent) 28%,transparent);border-radius:6px;font-size:.76rem;line-height:1.5}.login-form__error svg{flex:none;margin-top:.1rem}.login-form__submit{width:100%;min-height:48px;display:inline-flex;align-items:center;justify-content:center;gap:.5rem;margin-top:1.25rem;color:var(--color-on-primary);background:var(--color-primary);border-radius:7px;font-size:.82rem;font-weight:700;transition:background var(--duration-fast),transform var(--duration-fast),opacity var(--duration-fast)}.login-form__submit:hover:not(:disabled){background:var(--color-primary-dark);transform:translateY(-1px)}.login-form__submit:active:not(:disabled){transform:translateY(0)}.login-form__submit:disabled{opacity:.52}.login-form__spinner{animation:login-spin .8s linear infinite}.login-page__service{min-height:44px;display:grid;place-items:center;color:var(--color-ink-muted);font-size:.7rem}@keyframes login-spin{to{transform:rotate(360deg)}}
@media(max-width:900px){.login-page{grid-template-columns:1fr}.login-page__brand{display:none}.login-page__form-panel{padding-inline:clamp(1.25rem,6vw,3rem)}.login-page__form-area{padding:1.5rem 0}.login-page__mobile-brand{display:inline-flex;margin-bottom:1.5rem}}
@media(max-width:480px){.login-page__form-panel{padding:1rem}.login-page__back span{display:none}.login-page__back{width:44px;justify-content:center}.login-page__form-area{width:100%;padding:1.25rem 0}.login-page__mobile-brand{margin-bottom:1.25rem}.login-form__heading{margin:1.5rem 0}.login-form__heading h1{font-size:1.5rem}}
@media(max-height:720px) and (min-width:901px){.login-page__brand-copy{padding:1.5rem 0}.login-page__owl{width:132px;height:116px;margin-bottom:1rem}.login-page__owl :deep(img){width:124px!important;height:124px!important}.login-page__form-area{padding:1.25rem 0}.login-form__heading{margin:1.25rem 0}}
</style>
