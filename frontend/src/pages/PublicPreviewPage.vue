<script setup>
import {
  ArrowRight,
  BriefcaseBusiness,
  FileText,
  Github,
  LogIn,
  Mic2,
  ShieldCheck,
  UserRoundPlus,
} from 'lucide-vue-next'

import OwlLogo from '@/components/common/OwlLogo.vue'
</script>

<template>
  <main class="public-preview">
    <header class="public-preview__header">
      <router-link :to="{ name: 'root' }" class="public-preview__brand" aria-label="OwlMock 首页">
        <span class="public-preview__logo"><OwlLogo :size="28" style="filter: none; opacity: 1" /></span>
        <strong>OwlMock</strong>
      </router-link>
      <nav class="public-preview__nav" aria-label="公开导航">
        <a href="#workflow">工作流程</a>
        <a href="#workspace">工作台</a>
      </nav>
      <div class="public-preview__actions">
        <router-link :to="{ name: 'login' }" class="public-preview__login"><LogIn :size="16" />登录</router-link>
        <router-link :to="{ name: 'register' }" class="public-preview__signup"><UserRoundPlus :size="16" />免费开始</router-link>
      </div>
    </header>

    <section class="public-preview__hero" aria-labelledby="preview-title">
      <div class="public-preview__hero-copy">
        <p class="public-preview__eyebrow">求职准备工作台</p>
        <h1 id="preview-title">把每个目标岗位，变成一套可持续的准备过程</h1>
        <p class="public-preview__lede">从 JD、简历到模拟面试，OwlMock 把零散准备整理成一条清晰的路径，让每一次练习都留下可复用的成果。</p>
        <div class="public-preview__hero-actions">
          <router-link :to="{ name: 'register' }" class="public-preview__primary">创建我的工作台<ArrowRight :size="17" /></router-link>
          <router-link :to="{ name: 'login' }" class="public-preview__secondary">已有账户，直接登录</router-link>
        </div>
        <p class="public-preview__note"><ShieldCheck :size="15" />先浏览，开始准备时再用邮箱创建个人账户</p>
      </div>

      <div id="workspace" class="public-preview__workspace" aria-label="OwlMock 工作台预览">
        <div class="preview-window__topbar">
          <span class="preview-window__dots" aria-hidden="true"><i /><i /><i /></span>
          <span>OwlMock / 岗位项目</span>
          <span class="preview-window__status">准备开始</span>
        </div>
        <div class="preview-window__body">
          <aside class="preview-window__sidebar">
            <div class="preview-window__mini-brand"><span><OwlLogo :size="18" /></span>OwlMock</div>
            <div class="preview-window__account"><b>我的求职空间</b><small>登录后查看你的项目</small></div>
            <p>工作区</p>
            <span class="preview-window__nav preview-window__nav--active"><BriefcaseBusiness :size="15" />岗位项目</span>
            <span class="preview-window__nav"><FileText :size="15" />简历库</span>
            <span class="preview-window__nav"><Github :size="15" />GitHub 分析</span>
          </aside>
          <div class="preview-window__content">
            <div class="preview-window__content-heading"><span>岗位项目</span><strong>你的准备，从这里开始</strong></div>
            <div class="preview-window__empty">
              <span class="preview-window__empty-icon"><BriefcaseBusiness :size="22" /></span>
              <b>还没有岗位项目</b>
              <small>粘贴一份 JD，建立完整的准备工作台</small>
              <router-link :to="{ name: 'project-create' }" class="preview-window__fake-button">新建岗位 <ArrowRight :size="14" /></router-link>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="workflow" class="public-preview__workflow" aria-labelledby="workflow-title">
      <div class="public-preview__section-heading">
        <p>一条准备路径</p>
        <h2 id="workflow-title">从理解岗位，到准备好面对面试</h2>
      </div>
      <div class="public-preview__steps">
        <article class="public-preview__step">
          <span><BriefcaseBusiness :size="19" /></span>
          <strong>建立目标岗位</strong>
          <p>保存 JD 和岗位背景，形成一个持续更新的准备项目。</p>
        </article>
        <article class="public-preview__step">
          <span><FileText :size="19" /></span>
          <strong>找到简历重点</strong>
          <p>对照岗位要求，识别你的优势、缺口和可以补充的证据。</p>
        </article>
        <article class="public-preview__step">
          <span><Mic2 :size="19" /></span>
          <strong>练习真实面试</strong>
          <p>用文字或语音完成模拟面试，把每次表现沉淀为下一次的准备。</p>
        </article>
      </div>
    </section>

    <footer class="public-preview__footer">
      <span>OwlMock</span>
      <span>为每一次认真准备，留下一点确定感。</span>
    </footer>
  </main>
</template>

<style scoped>
.public-preview { min-height: 100vh; color: var(--color-ink); background: var(--color-base); }
.public-preview__header { width: min(1180px, calc(100% - 3rem)); min-height: 74px; display: flex; align-items: center; gap: 2rem; margin: 0 auto; border-bottom: 1px solid var(--color-border); }
.public-preview__brand { display: inline-flex; align-items: center; gap: .65rem; color: var(--color-ink); font-family: var(--font-heading); font-size: 1.08rem; }
.public-preview__logo { width: 34px; height: 34px; display: grid; place-items: center; overflow: hidden; background: var(--color-white); border-radius: 6px; }
.public-preview__nav { display: flex; gap: 1.35rem; margin-left: auto; }
.public-preview__nav a,.public-preview__login { color: var(--color-ink-muted); font-size: .72rem; font-weight: 650; }
.public-preview__nav a:hover,.public-preview__login:hover { color: var(--color-primary); }
.public-preview__actions { display: flex; align-items: center; gap: .85rem; }
.public-preview__login,.public-preview__signup { display: inline-flex; align-items: center; gap: .35rem; }
.public-preview__signup { min-height: 37px; padding: 0 .8rem; color: var(--color-on-secondary); background: var(--color-secondary); border-radius: 6px; font-size: .72rem; font-weight: 750; }
.public-preview__hero { width: min(1180px, calc(100% - 3rem)); display: grid; grid-template-columns: minmax(0, .8fr) minmax(540px, 1.2fr); align-items: center; gap: clamp(2rem, 6vw, 6rem); margin: 0 auto; padding: clamp(4.5rem, 10vh, 7rem) 0 6rem; }
.public-preview__hero-copy { max-width: 520px; }
.public-preview__eyebrow,.public-preview__section-heading p { margin-bottom: .7rem; color: var(--color-primary); font-size: .7rem; font-weight: 750; }
.public-preview__hero h1 { max-width: 540px; font-size: clamp(2.25rem, 4vw, 3.5rem); line-height: 1.14; }
.public-preview__lede { max-width: 500px; margin-top: 1.25rem; color: var(--color-ink-muted); font-size: .9rem; line-height: 1.8; }
.public-preview__hero-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 1rem; margin-top: 1.8rem; }
.public-preview__primary { min-height: 45px; display: inline-flex; align-items: center; gap: .45rem; padding: 0 1rem; color: var(--color-on-primary); background: var(--color-primary); border-radius: 6px; font-size: .76rem; font-weight: 750; }
.public-preview__primary:hover { background: var(--color-primary-dark); }
.public-preview__secondary { color: var(--color-primary); font-size: .75rem; font-weight: 700; }
.public-preview__secondary:hover { text-decoration: underline; }
.public-preview__note { display: inline-flex; align-items: center; gap: .4rem; margin-top: 1.2rem; color: var(--color-ink-muted); font-size: .68rem; }
.public-preview__workspace { min-width: 0; overflow: hidden; background: var(--color-white); border: 1px solid var(--color-border); border-radius: 8px; box-shadow: 0 20px 55px color-mix(in srgb, var(--color-primary) 14%, transparent); }
.preview-window__topbar { height: 42px; display: flex; align-items: center; gap: .7rem; padding: 0 .85rem; color: var(--color-ink-muted); background: var(--color-surface); border-bottom: 1px solid var(--color-border); font-size: .62rem; }
.preview-window__dots { display: flex; gap: .24rem; }
.preview-window__dots i { width: 6px; height: 6px; display: block; background: var(--color-border); border-radius: 50%; }
.preview-window__status { margin-left: auto; color: var(--color-primary); font-size: .58rem; }
.preview-window__body { min-height: 350px; display: grid; grid-template-columns: 165px minmax(0, 1fr); }
.preview-window__sidebar { padding: 1rem .7rem; color: var(--color-rail-muted); background: var(--color-rail); }
.preview-window__mini-brand { display: flex; align-items: center; gap: .4rem; color: var(--color-rail-ink); font-size: .68rem; font-weight: 750; }
.preview-window__mini-brand span { width: 24px; height: 24px; display: grid; place-items: center; background: var(--color-white); border-radius: 5px; }
.preview-window__account { margin: 1.1rem 0; padding: .55rem; background: var(--color-white); border: 1px solid var(--color-border); border-radius: 5px; }
.preview-window__account b,.preview-window__account small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.preview-window__account b { color: var(--color-rail-ink); font-size: .6rem; }
.preview-window__account small { margin-top: .2rem; color: var(--color-rail-muted); font-size: .5rem; }
.preview-window__sidebar > p { margin: 1rem .45rem .45rem; color: var(--color-rail-subtle); font-size: .52rem; font-weight: 750; text-transform: uppercase; }
.preview-window__nav { min-height: 31px; display: flex; align-items: center; gap: .4rem; padding: 0 .45rem; border-radius: 4px; font-size: .57rem; }
.preview-window__nav--active { color: var(--color-rail-ink); background: var(--color-rail-hover); font-weight: 700; }
.preview-window__content { padding: 1.3rem; background: var(--color-base); }
.preview-window__content-heading span { color: var(--color-primary); font-size: .57rem; font-weight: 750; }
.preview-window__content-heading strong { display: block; margin-top: .3rem; font-size: 1rem; }
.preview-window__empty { min-height: 220px; display: grid; place-items: center; align-content: center; gap: .5rem; margin-top: 1.2rem; border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); text-align: center; }
.preview-window__empty-icon { width: 42px; height: 42px; display: grid; place-items: center; color: var(--color-primary); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; }
.preview-window__empty b { font-size: .72rem; }
.preview-window__empty small { color: var(--color-ink-muted); font-size: .58rem; }
.preview-window__fake-button { min-height: 30px; display: inline-flex; align-items: center; gap: .35rem; margin-top: .4rem; padding: 0 .65rem; color: var(--color-on-secondary); background: var(--color-secondary); border-radius: 4px; font-size: .58rem; font-weight: 750; }
.public-preview__workflow { width: min(1180px, calc(100% - 3rem)); margin: 0 auto; padding: 1rem 0 6rem; }
.public-preview__section-heading { max-width: 520px; padding-bottom: 1.5rem; border-bottom: 1px solid var(--color-border); }
.public-preview__section-heading h2 { font-size: 1.65rem; line-height: 1.3; }
.public-preview__steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; padding-top: 1.3rem; }
.public-preview__step { padding: 1.2rem 0; border-top: 2px solid var(--color-primary); }
.public-preview__step > span { width: 35px; height: 35px; display: grid; place-items: center; color: var(--color-primary); background: var(--color-surface); border-radius: 6px; }
.public-preview__step strong { display: block; margin-top: .9rem; font-size: .86rem; }
.public-preview__step p { margin-top: .5rem; color: var(--color-ink-muted); font-size: .72rem; line-height: 1.7; }
.public-preview__footer { width: min(1180px, calc(100% - 3rem)); display: flex; justify-content: space-between; gap: 1rem; margin: 0 auto; padding: 1rem 0 1.5rem; color: var(--color-ink-muted); border-top: 1px solid var(--color-border); font-size: .65rem; }
@media (max-width: 960px) { .public-preview__hero { grid-template-columns: 1fr; gap: 3rem; padding-top: 3.8rem; } .public-preview__hero-copy { max-width: 700px; } }
@media (max-width: 650px) { .public-preview__header,.public-preview__hero,.public-preview__workflow,.public-preview__footer { width: min(100% - 2rem, 1180px); } .public-preview__nav { display: none; } .public-preview__header { gap: .75rem; } .public-preview__actions { margin-left: auto; gap: .55rem; } .public-preview__login { font-size: .65rem; } .public-preview__signup { min-height: 34px; padding-inline: .65rem; font-size: .64rem; } .public-preview__hero { padding-top: 3.1rem; padding-bottom: 4rem; } .public-preview__hero h1 { font-size: 2.2rem; } .public-preview__workspace { margin-inline: -.35rem; } .preview-window__body { grid-template-columns: 126px minmax(0, 1fr); } .preview-window__content { padding: .9rem; } .preview-window__steps { grid-template-columns: 1fr; } .public-preview__steps { grid-template-columns: 1fr; } .public-preview__footer { flex-direction: column; gap: .35rem; } }
</style>
