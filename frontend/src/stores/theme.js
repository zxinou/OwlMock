import { reactive, watchEffect } from 'vue'

function getInitialDarkMode() {
  if (typeof window === 'undefined' || typeof localStorage === 'undefined') return false

  const saved = localStorage.getItem('owlmock-dark')
  if (saved !== null) return saved === '1'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const state = reactive({
  dark: getInitialDarkMode(),
})

function toggle() {
  state.dark = !state.dark
}

function set(val) {
  state.dark = val
}

watchEffect(() => {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('dark', state.dark)
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('owlmock-dark', state.dark ? '1' : '0')
  }
})

export function useTheme() {
  return { state, toggle, set }
}
