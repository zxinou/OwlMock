<script setup>
import { computed } from 'vue'
import { AlertTriangle, ArrowUpRight, BadgeCheck, BarChart3, BookOpenCheck, Braces, CheckCircle2, MessageSquareText, Target, Wrench } from 'lucide-vue-next'
import ResumeRequirementGroup from './ResumeRequirementGroup.vue'

const props = defineProps({
  report: { type: Object, required: true },
  resumeName: { type: String, default: '简历' },
})

const requirementGroups = computed(() => ['硬性要求', '优先条件', '加分项'].map((title) => ({
  title,
  items: (props.report.requirements || []).filter((item) => item.category === title),
})).filter((group) => group.items.length))

const metrics = computed(() => [
  { label: '硬性要求覆盖', value: props.report.metrics?.required_coverage ?? 0, icon: Target },
  { label: '优先条件覆盖', value: props.report.metrics?.preferred_coverage ?? 0, icon: BadgeCheck },
  { label: '技能覆盖', value: props.report.metrics?.skill_coverage ?? 0, icon: Braces },
  { label: '证据质量', value: props.report.metrics?.evidence_quality ?? 0, icon: BarChart3 },
])
</script>

<template>
  <div class="match-dashboard">
    <header class="match-hero">
      <div class="match-hero-main">
        <div class="match-title">
          <span>简历匹配报告</span>
          <h1>{{ report.job.title }}</h1>
          <p>{{ resumeName }} · {{ report.candidate.headline }} · {{ report.candidate.seniority }}</p>
          <small v-if="report.job.company">{{ report.job.company }}</small>
        </div>
        <div class="match-score" :data-level="report.score.level">
          <div class="score-dial" :style="{ '--score': report.score.value }">
            <div><strong>{{ report.score.value }}</strong><span>/100</span></div>
          </div>
          <div class="score-copy">
            <span>综合匹配</span>
            <strong>{{ report.score.level }}</strong>
            <p>{{ report.score.reason }}</p>
          </div>
        </div>
      </div>
      <section class="metric-grid" aria-label="匹配指标">
        <article v-for="item in metrics" :key="item.label">
          <component :is="item.icon" :size="17" />
          <div><span>{{ item.label }}</span><strong>{{ item.value }}%</strong></div>
          <div class="metric-track"><span :style="{ width: `${item.value}%` }"></span></div>
        </article>
      </section>
    </header>

    <section class="dashboard-section">
      <div class="section-title"><BookOpenCheck :size="19" /><div><span>岗位要求</span><h2>逐条证据匹配</h2></div></div>
      <div class="requirements-grid">
        <ResumeRequirementGroup v-for="group in requirementGroups" :key="group.title" :title="group.title" :items="group.items" />
      </div>
    </section>

    <section class="dashboard-section">
      <div class="section-title"><Braces :size="19" /><div><span>技能矩阵</span><h2>技术能力覆盖</h2></div></div>
      <div class="skill-list">
        <article v-for="(skill, index) in report.skills" :key="`${skill.name}-${index}`" :data-status="skill.status">
          <div><strong>{{ skill.name }}</strong><small>{{ skill.importance }}</small></div>
          <span>{{ skill.status }}</span>
          <p>{{ skill.resume_evidence }}</p>
          <p v-if="skill.gap" class="skill-gap">{{ skill.gap }}</p>
        </article>
      </div>
    </section>

    <div class="insight-grid">
      <section class="dashboard-section compact-section">
        <div class="section-title"><CheckCircle2 :size="19" /><div><span>优势</span><h2>值得放大的证据</h2></div></div>
        <article v-for="(item, index) in report.strengths" :key="index" class="insight-row strength-row">
          <strong>{{ item.title }}</strong><p>{{ item.evidence }}</p><small>{{ item.impact }}</small>
        </article>
      </section>
      <section class="dashboard-section compact-section">
        <div class="section-title"><AlertTriangle :size="19" /><div><span>缺口</span><h2>影响投递的风险</h2></div></div>
        <article v-for="(item, index) in report.gaps" :key="index" class="insight-row gap-row">
          <div><strong>{{ item.title }}</strong><span>{{ item.severity }}</span></div><p>{{ item.evidence }}</p><small>{{ item.action }}</small>
        </article>
      </section>
    </div>

    <section class="dashboard-section">
      <div class="section-title"><MessageSquareText :size="19" /><div><span>面试准备</span><h2>高概率追问</h2></div></div>
      <div class="interview-list">
        <article v-for="(item, index) in report.interview_focus" :key="index">
          <span>{{ String(index + 1).padStart(2, '0') }}</span>
          <div><strong>{{ item.question }}</strong><p>{{ item.why }}</p><small>{{ item.preparation }}</small></div>
        </article>
      </div>
    </section>

    <section class="dashboard-section">
      <div class="section-title"><Wrench :size="19" /><div><span>简历修改</span><h2>按优先级行动</h2></div></div>
      <div class="action-list">
        <article v-for="(item, index) in report.resume_actions" :key="index">
          <span :data-priority="item.priority">{{ item.priority }}</span>
          <div><small>{{ item.section }}</small><strong>{{ item.action }}</strong><p v-if="item.example">{{ item.example }}</p></div>
          <ArrowUpRight :size="16" />
        </article>
      </div>
    </section>

    <footer class="match-summary">
      <div><span>猫头鹰总结</span><h2>{{ report.summary.text }}</h2></div>
      <div class="summary-tags"><span v-for="tag in report.summary.tags" :key="tag">{{ tag }}</span></div>
    </footer>
  </div>
</template>

<style scoped>
.match-dashboard { display:grid; gap:1.4rem; }
.match-hero { display:grid; gap:1.25rem; padding:1.25rem 0 1.5rem; border-bottom:1px solid var(--color-border); }
.match-hero-main { display:grid; grid-template-columns:minmax(0,1fr) minmax(19rem,23rem); align-items:center; gap:2rem; }
.match-title > span, .section-title span, .match-summary span { color:var(--color-ink-muted); font-size:.7rem; }
.match-title h1 { margin-top:.45rem; font-size:1.75rem; }
.match-title p { max-width:44rem; margin-top:.55rem; color:var(--color-ink-light); font-size:.82rem; line-height:1.55; overflow-wrap:anywhere; }
.match-title small { display:block; margin-top:.45rem; color:var(--color-primary); font-size:.72rem; }
.match-score { min-width:0; display:grid; grid-template-columns:5.4rem minmax(0,1fr); align-items:center; gap:1rem; padding:.85rem 1rem; border:1px solid color-mix(in srgb,var(--color-primary) 20%,var(--color-border)); border-radius:var(--radius-sm); background:color-mix(in srgb,var(--color-primary) 6%,var(--color-white)); }
.score-dial { --score:0; position:relative; width:5.25rem; aspect-ratio:1; display:grid; place-items:center; border-radius:50%; background:conic-gradient(var(--color-primary) calc(var(--score) * 1%),var(--color-surface-alt) 0); }
.score-dial::before { content:""; position:absolute; inset:.38rem; border-radius:50%; background:var(--color-white); box-shadow:inset 0 0 0 1px var(--color-border-light); }
.score-dial > div { position:relative; z-index:1; display:flex; align-items:baseline; }
.score-dial strong { color:var(--color-ink); font-size:1.8rem; line-height:1; }
.score-dial span { margin-left:.12rem; color:var(--color-ink-muted); font-size:.58rem; }
.score-copy { min-width:0; }
.score-copy > span { display:block; color:var(--color-ink-muted); font-size:.66rem; }
.score-copy > strong { display:block; margin-top:.18rem; color:var(--color-primary); font-size:.9rem; }
.score-copy p { margin-top:.38rem; color:var(--color-ink-light); font-size:.68rem; line-height:1.5; overflow-wrap:anywhere; }
.metric-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); border-block:1px solid var(--color-border-light); }
.metric-grid article { --metric-color:var(--color-primary); min-width:0; display:grid; grid-template-columns:2rem minmax(0,1fr); align-items:center; gap:.25rem .65rem; padding:.8rem 1rem; }
.metric-grid article + article { border-left:1px solid var(--color-border-light); }
.metric-grid article:nth-child(2) { --metric-color:#a77b1e; }
.metric-grid article:nth-child(3) { --metric-color:#567ca0; }
.metric-grid article:nth-child(4) { --metric-color:var(--color-accent); }
.metric-grid svg { width:2rem; height:2rem; padding:.45rem; border-radius:50%; color:var(--metric-color); background:color-mix(in srgb,var(--metric-color) 10%,transparent); }
.metric-grid article > div:first-of-type { display:flex; align-items:baseline; justify-content:space-between; gap:.45rem; min-width:0; }
.metric-grid strong { color:var(--metric-color); font-size:.9rem; }
.metric-grid article > div > span { min-width:0; color:var(--color-ink-muted); font-size:.65rem; overflow-wrap:anywhere; }
.metric-track { grid-column:2; height:3px; overflow:hidden; background:var(--color-surface-alt); }
.metric-track span { display:block; height:100%; background:var(--metric-color); transition:width .5s var(--ease-out); }
.dashboard-section { padding-top:1.2rem; border-top:1px solid var(--color-border-light); }
.section-title { display:flex; align-items:center; gap:.65rem; margin-bottom:1rem; color:var(--color-primary); }
.section-title h2 { margin-top:.12rem; color:var(--color-ink); font-size:1rem; }
.requirements-grid { display:grid; grid-template-columns:1fr; gap:1.15rem; }
.requirements-grid > :only-child, .requirements-grid > :last-child:nth-child(odd) { grid-column:auto; }
.skill-list { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0 1.5rem; }
.skill-list article { min-width:0; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:.35rem .75rem; padding:.8rem 0; border-bottom:1px solid var(--color-border-light); }
.skill-list article > div { display:flex; align-items:center; gap:.45rem; min-width:0; }
.skill-list strong { color:var(--color-ink); font-size:.8rem; overflow-wrap:anywhere; }
.skill-list small { padding:.1rem .35rem; border-radius:4px; color:var(--color-ink-muted); background:var(--color-surface); font-size:.6rem; }
.skill-list article > span { color:var(--color-ink-muted); font-size:.68rem; font-weight:700; }
.skill-list [data-status="匹配"] > span { color:var(--color-primary); }
.skill-list [data-status="部分匹配"] > span { color:#9a7418; }
.skill-list [data-status="缺失"] > span { color:var(--color-accent); }
.skill-list p { grid-column:1 / -1; color:var(--color-ink-light); font-size:.71rem; line-height:1.5; overflow-wrap:anywhere; }
.skill-list .skill-gap { padding-left:.55rem; border-left:2px solid color-mix(in srgb,var(--color-accent) 45%,transparent); color:var(--color-ink-muted); }
.insight-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1.5rem; }
.compact-section { min-width:0; }
.insight-row { padding:.85rem 0; border-bottom:1px solid var(--color-border-light); }
.insight-row strong { color:var(--color-ink); font-size:.8rem; }
.insight-row p { margin-top:.35rem; color:var(--color-ink-light); font-size:.72rem; line-height:1.55; overflow-wrap:anywhere; }
.insight-row small { display:block; margin-top:.45rem; padding-left:.55rem; border-left:2px solid var(--color-primary); color:var(--color-ink-muted); font-size:.68rem; line-height:1.5; }
.gap-row > div { display:flex; align-items:center; justify-content:space-between; gap:.5rem; }
.gap-row > div span { color:var(--color-accent); font-size:.65rem; }
.gap-row small { border-left-color:var(--color-accent); }
.interview-list { display:grid; }
.interview-list article { display:grid; grid-template-columns:2rem minmax(0,1fr); gap:.75rem; padding:.9rem 0; border-bottom:1px solid var(--color-border-light); }
.interview-list article > span { color:var(--color-secondary); font-size:.72rem; font-weight:800; }
.interview-list strong { color:var(--color-ink); font-size:.8rem; }
.interview-list p { margin-top:.35rem; color:var(--color-ink-light); font-size:.72rem; line-height:1.55; }
.interview-list small { display:block; margin-top:.4rem; color:var(--color-primary); font-size:.68rem; line-height:1.5; }
.action-list { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0 1.5rem; }
.action-list article { min-width:0; display:grid; grid-template-columns:1.6rem minmax(0,1fr) auto; gap:.65rem; padding:.85rem 0; border-bottom:1px solid var(--color-border-light); }
.action-list article > span { width:1.6rem; height:1.6rem; display:grid; place-items:center; border-radius:5px; color:var(--color-primary); background:var(--color-surface-alt); font-size:.62rem; }
.action-list [data-priority="高"] { color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 10%,transparent); }
.action-list small, .action-list strong { display:block; }
.action-list small { color:var(--color-ink-muted); font-size:.62rem; }
.action-list strong { margin-top:.2rem; color:var(--color-ink); font-size:.75rem; line-height:1.45; }
.action-list p { margin-top:.4rem; color:var(--color-ink-light); font-size:.68rem; line-height:1.5; overflow-wrap:anywhere; }
.action-list svg { color:var(--color-ink-muted); }
.match-summary { display:flex; align-items:flex-start; justify-content:space-between; gap:1.25rem; padding:1.2rem; border-left:3px solid var(--color-primary); background:var(--color-surface-alt); }
.match-summary h2 { max-width:45rem; margin-top:.3rem; color:var(--color-ink); font-size:.9rem; line-height:1.7; }
.summary-tags { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:.35rem; }
.summary-tags span { padding:.2rem .45rem; border-radius:4px; color:var(--color-primary); background:var(--color-white); white-space:nowrap; }
@media (max-width:900px) { .match-hero-main { grid-template-columns:1fr; gap:1.2rem; } .match-score { max-width:32rem; } .metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } .metric-grid article:nth-child(3) { border-left:0; border-top:1px solid var(--color-border-light); } .metric-grid article:nth-child(4) { border-top:1px solid var(--color-border-light); } .requirements-grid, .insight-grid, .skill-list, .action-list { grid-template-columns:1fr; } .requirements-grid > :last-child:nth-child(odd) { grid-column:auto; } }
@media (max-width:560px) { .match-title h1 { font-size:1.45rem; } .match-score { grid-template-columns:4.75rem minmax(0,1fr); padding:.75rem; } .score-dial { width:4.6rem; } .score-dial strong { font-size:1.55rem; } .metric-grid { grid-template-columns:1fr; } .metric-grid article + article { border-left:0; border-top:1px solid var(--color-border-light); } .match-summary { flex-direction:column; } .summary-tags { justify-content:flex-start; } }
</style>
