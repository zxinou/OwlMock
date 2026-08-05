<script setup>
import { MessageSquareText, Mic, Play } from 'lucide-vue-next'

defineProps({
  sessions: { type: Array, default: () => [] },
})

function destination(session) {
  return session.status === 'completed'
    ? { name: 'interview-summary', params: { id: session.id } }
    : { name: 'interview-session', params: { id: session.id } }
}

function formatDate(value) {
  if (!value) return '刚刚'
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' }).format(new Date(value))
}
</script>

<template>
  <section class="interview-history" aria-labelledby="history-heading">
    <div class="interview-history__heading">
      <div>
        <p>练习记录</p>
        <h2 id="history-heading">最近面试</h2>
      </div>
      <router-link :to="{ name: 'interview-list' }">查看全部</router-link>
    </div>

    <div v-if="sessions.length" class="interview-history__list">
      <router-link
        v-for="session in sessions"
        :key="session.id"
        :to="destination(session)"
        class="interview-history__item"
      >
        <span class="interview-history__icon" aria-hidden="true">
          <Mic v-if="session.mode === 'voice'" :size="16" />
          <MessageSquareText v-else :size="16" />
        </span>
        <span>
          <strong>{{ session.mode === 'voice' ? '语音面试' : '文字面试' }}</strong>
          <small>{{ formatDate(session.updated_at || session.created_at) }} · {{ session.turn_count || 0 }} 轮</small>
        </span>
        <em>{{ session.status === 'completed' ? '查看总结' : '继续' }}</em>
        <Play :size="14" aria-hidden="true" />
      </router-link>
    </div>
    <div v-else class="interview-history__empty">
      <MessageSquareText :size="22" />
      <p>还没有练习记录</p>
      <span>完成岗位和简历准备后，从一次短面试开始。</span>
    </div>
  </section>
</template>

<style scoped>
.interview-history { padding:1.35rem 1.45rem; background:var(--color-white); border:1px solid var(--color-border); border-radius:8px; }
.interview-history__heading { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
.interview-history__heading p { color:var(--color-primary); font-size:.66rem; font-weight:700; }
.interview-history__heading h2 { margin-top:.2rem; font-size:1rem; }
.interview-history__heading a { color:var(--color-primary); font-size:.7rem; font-weight:700; }
.interview-history__list { display:grid; }
.interview-history__item { display:grid; grid-template-columns:34px minmax(0,1fr) auto 14px; align-items:center; gap:.7rem; padding:.78rem 0; border-top:1px solid var(--color-border-light); }
.interview-history__icon { width:34px; height:34px; display:grid; place-items:center; color:var(--color-primary); background:var(--color-surface); border-radius:6px; }
.interview-history__item strong,.interview-history__item small { display:block; }
.interview-history__item strong { font-size:.76rem; }
.interview-history__item small { margin-top:.15rem; color:var(--color-ink-muted); font-size:.64rem; }
.interview-history__item em { color:var(--color-primary); font-size:.66rem; font-style:normal; font-weight:700; }
.interview-history__item > svg { color:var(--color-ink-muted); }
.interview-history__empty { display:grid; justify-items:center; gap:.3rem; padding:1.8rem .5rem; color:var(--color-ink-muted); text-align:center; border-top:1px solid var(--color-border-light); }
.interview-history__empty p { margin-top:.25rem; color:var(--color-ink); font-size:.8rem; font-weight:700; }
.interview-history__empty span { font-size:.68rem; }
</style>
