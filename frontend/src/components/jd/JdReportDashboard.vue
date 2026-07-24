<script setup>
import {
  AlertTriangle, BarChart3, Brain, BriefcaseBusiness, CheckCircle2,
  CircleDot, Code2, Lightbulb, MapPin, MessageSquareText, ShieldAlert,
  Sparkles, Target, WalletCards,
} from 'lucide-vue-next'
import JdRequirementGroup from '@/components/jd/JdRequirementGroup.vue'

const props = defineProps({
  report: { type: Object, required: true },
})

const requirementGroups = {
  must: () => props.report.requirements?.filter((item) => item.category === '硬性要求') || [],
  prefer: () => props.report.requirements?.filter((item) => item.category === '优先条件') || [],
  bonus: () => props.report.requirements?.filter((item) => item.category === '加分项') || [],
}

function importanceWidth(value) {
  return value === '核心' ? '100%' : value === '重要' ? '68%' : '38%'
}
</script>

<template>
  <div class="jd-dashboard">
    <section class="jd-report-overview">
      <div class="jd-role-copy">
        <span>JD 分析报告</span>
        <h1>{{ report.job.title }}</h1>
        <div class="jd-role-meta">
          <span v-if="report.job.company"><BriefcaseBusiness :size="14" />{{ report.job.company }}</span>
          <span v-if="report.job.location"><MapPin :size="14" />{{ report.job.location }}</span>
          <span v-if="report.job.salary"><WalletCards :size="14" />{{ report.job.salary }}</span>
          <span v-if="!report.job.company && !report.job.location && !report.job.salary">JD 未提供公司、地点或薪资信息</span>
        </div>
      </div>
      <div class="jd-difficulty">
        <div class="jd-difficulty-label"><span>岗位难度</span><Sparkles :size="15" /></div>
        <strong>{{ report.job.difficulty.level }}</strong>
        <p>{{ report.job.difficulty.reason }}</p>
      </div>
    </section>

    <section class="jd-kpis" aria-label="岗位分析指标">
      <article class="accent"><CheckCircle2 :size="18" /><strong>{{ requirementGroups.must().length }}</strong><span>硬性要求</span></article>
      <article class="warning"><Target :size="18" /><strong>{{ requirementGroups.prefer().length }}</strong><span>优先条件</span></article>
      <article class="primary"><Code2 :size="18" /><strong>{{ report.skills?.length || 0 }}</strong><span>核心技能</span></article>
      <article class="accent"><AlertTriangle :size="18" /><strong>{{ report.risks?.length || 0 }}</strong><span>风险信号</span></article>
    </section>

    <section class="jd-requirement-grid">
      <JdRequirementGroup title="硬性要求" :items="requirementGroups.must()" tone="must" />
      <JdRequirementGroup title="优先条件" :items="requirementGroups.prefer()" tone="prefer" />
    </section>
    <JdRequirementGroup
      v-if="requirementGroups.bonus().length"
      title="加分项"
      :items="requirementGroups.bonus()"
      tone="bonus"
    />

    <section class="jd-panel jd-skills-panel">
      <header><BarChart3 :size="18" /><h2>技能权重</h2></header>
      <div v-if="report.skills?.length" class="jd-skill-grid">
        <article v-for="skill in report.skills" :key="skill.name">
          <div><strong>{{ skill.name }}</strong><span>{{ skill.importance }}</span></div>
          <div class="jd-skill-track"><i :style="{ width: importanceWidth(skill.importance) }"></i></div>
          <p>{{ skill.reason }}</p>
        </article>
      </div>
      <p v-else class="jd-section-empty">没有识别出明确技能关键词</p>
    </section>

    <section class="jd-insight-grid">
      <article class="jd-panel">
        <header><Brain :size="18" /><h2>隐含期待</h2></header>
        <div v-if="report.implicit_expectations?.length" class="jd-insight-list">
          <div v-for="(item, index) in report.implicit_expectations" :key="index">
            <CircleDot :size="14" /><p><strong>{{ item.text }}</strong><span>依据：{{ item.evidence }}</span></p>
          </div>
        </div>
        <p v-else class="jd-section-empty">没有发现需要额外说明的隐含期待</p>
      </article>

      <article class="jd-panel">
        <header><ShieldAlert :size="18" /><h2>风险与证据</h2></header>
        <div v-if="report.risks?.length" class="jd-risk-list">
          <div v-for="(risk, index) in report.risks" :key="index">
            <span :class="`severity-${risk.severity}`">{{ risk.severity }}</span>
            <p><strong>{{ risk.title }}</strong><small>{{ risk.evidence }}</small><em>{{ risk.suggestion }}</em></p>
          </div>
        </div>
        <p v-else class="jd-section-empty">没有识别出明显风险信号</p>
      </article>
    </section>

    <section class="jd-panel jd-interview-panel">
      <header><MessageSquareText :size="18" /><h2>面试重点</h2></header>
      <div v-if="report.interview_focus?.length" class="jd-interview-list">
        <article v-for="(focus, index) in report.interview_focus" :key="index">
          <span>{{ String(index + 1).padStart(2, '0') }}</span>
          <div><h3>{{ focus.question }}</h3><p>{{ focus.why }}</p><aside><Lightbulb :size="14" />{{ focus.preparation }}</aside></div>
        </article>
      </div>
      <p v-else class="jd-section-empty">这份历史报告没有面试重点数据</p>
    </section>

    <section v-if="report.recommendations?.length" class="jd-panel jd-recommendations">
      <header><Target :size="18" /><h2>准备建议</h2></header>
      <ul><li v-for="item in report.recommendations" :key="item">{{ item }}</li></ul>
    </section>

    <section class="jd-summary">
      <Sparkles :size="19" />
      <div><h2>猫头鹰总结</h2><p>{{ report.summary.text }}</p><div><span v-for="tag in report.summary.tags" :key="tag">{{ tag }}</span></div></div>
    </section>
  </div>
</template>

<style scoped>
.jd-dashboard { display:grid; gap:1.35rem; }
.jd-report-overview { display:grid; grid-template-columns:1fr; gap:1rem; padding:1.25rem 0 1.35rem; border-bottom:1px solid var(--color-border); }
.jd-role-copy { min-width:0; padding:.75rem 0 .35rem; }
.jd-role-copy > span { color:var(--color-ink-muted); font-size:.72rem; }
.jd-role-copy h1 { margin-top:.35rem; font-size:1.55rem; overflow-wrap:anywhere; }
.jd-role-meta { display:flex; flex-wrap:wrap; gap:.55rem 1rem; margin-top:.65rem; color:var(--color-ink-muted); font-size:.78rem; }
.jd-role-meta span { display:inline-flex; align-items:center; gap:.3rem; }
.jd-difficulty { min-width:0; display:grid; grid-template-columns:7rem 4rem minmax(0,1fr); align-items:center; gap:1rem; padding:.85rem 0; border-block:1px solid color-mix(in srgb,var(--color-primary) 25%,var(--color-border)); color:var(--color-ink); background:color-mix(in srgb,var(--color-primary) 5%,var(--color-white)); }
.jd-difficulty-label { display:flex; align-items:center; justify-content:space-between; gap:.5rem; padding-right:1rem; border-right:1px solid #c7dfd7; color:var(--color-primary); }
.jd-difficulty-label span { color:var(--color-primary); font-size:.72rem; font-weight:700; }
.jd-difficulty-label svg { color:var(--color-secondary); }
.jd-difficulty strong { display:block; color:var(--color-primary); font-size:1.9rem; line-height:1; text-align:center; }
.jd-difficulty p { padding-left:1rem; border-left:1px solid #c7dfd7; color:var(--color-ink-light); font-size:.74rem; line-height:1.55; overflow-wrap:anywhere; }
.jd-kpis { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); border-block:1px solid var(--color-border-light); }
.jd-kpis article { min-width:0; display:grid; grid-template-columns:2rem minmax(0,1fr); align-items:center; gap:.2rem .6rem; padding:.85rem 1rem; }
.jd-kpis article + article { border-left:1px solid var(--color-border-light); }
.jd-kpis article > svg { width:2rem; height:2rem; padding:.45rem; border-radius:50%; background:var(--color-surface); }
.jd-kpis svg { grid-row:1 / 3; color:var(--color-primary); }
.jd-kpis strong { color:var(--color-ink); font-size:1.25rem; }
.jd-kpis span { color:var(--color-ink-muted); font-size:.7rem; }
.jd-kpis .accent svg { color:var(--color-accent); } .jd-kpis .warning svg { color:#a87618; }
.jd-requirement-grid { display:grid; grid-template-columns:1fr; gap:1rem; }
.jd-insight-grid { display:grid; grid-template-columns:1fr 1fr; gap:2rem; }
.jd-panel { min-width:0; padding:1.2rem 0; border-top:1px solid var(--color-border-light); background:transparent; }
.jd-panel > header { display:flex; align-items:center; gap:.55rem; margin-bottom:1rem; color:var(--color-primary); }
.jd-panel > header h2 { font-size:.95rem; }
.jd-skill-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem 1.5rem; }
.jd-skill-grid article { min-width:0; }
.jd-skill-grid article > div:first-child { display:flex; align-items:center; justify-content:space-between; gap:.6rem; }
.jd-skill-grid strong { font-size:.8rem; overflow-wrap:anywhere; }
.jd-skill-grid span { color:var(--color-primary); font-size:.68rem; font-weight:600; }
.jd-skill-track { height:.4rem; overflow:hidden; margin:.42rem 0; border-radius:99px; background:var(--color-surface-alt); }
.jd-skill-track i { display:block; height:100%; border-radius:inherit; background:var(--color-primary); }
.jd-skill-grid p { color:var(--color-ink-muted); font-size:.7rem; overflow-wrap:anywhere; }
.jd-insight-list, .jd-risk-list { display:grid; gap:.75rem; }
.jd-insight-list > div { display:grid; grid-template-columns:auto 1fr; gap:.55rem; color:#9a6a0c; }
.jd-insight-list strong, .jd-insight-list span { display:block; }
.jd-insight-list strong { color:var(--color-ink); font-size:.8rem; }
.jd-insight-list span { margin-top:.25rem; color:var(--color-ink-muted); font-size:.7rem; line-height:1.5; overflow-wrap:anywhere; }
.jd-risk-list > div { display:grid; grid-template-columns:1.6rem 1fr; gap:.6rem; }
.jd-risk-list > div > span { width:1.55rem; height:1.55rem; display:grid; place-items:center; border-radius:6px; font-size:.65rem; font-weight:700; }
.severity-高 { color:#b94f3e; background:color-mix(in srgb,var(--color-accent) 14%,transparent); }
.severity-中 { color:#946914; background:color-mix(in srgb,var(--color-secondary) 20%,transparent); }
.severity-低 { color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 12%,transparent); }
.jd-risk-list strong, .jd-risk-list small, .jd-risk-list em { display:block; font-style:normal; }
.jd-risk-list strong { font-size:.8rem; }.jd-risk-list small { margin-top:.2rem; color:var(--color-ink-muted); font-size:.7rem; overflow-wrap:anywhere; }.jd-risk-list em { margin-top:.3rem; color:var(--color-ink-light); font-size:.72rem; }
.jd-interview-list { display:grid; gap:.85rem; }
.jd-interview-list article { display:grid; grid-template-columns:2rem minmax(0,1fr); gap:.8rem; }
.jd-interview-list article > span { color:var(--color-primary); font-family:var(--font-mono); font-size:.8rem; font-weight:700; }
.jd-interview-list h3 { font-size:.84rem; overflow-wrap:anywhere; }
.jd-interview-list p { margin-top:.25rem; color:var(--color-ink-muted); font-size:.75rem; line-height:1.55; }
.jd-interview-list aside { display:flex; align-items:flex-start; gap:.35rem; margin-top:.4rem; padding:.55rem .65rem; border-radius:var(--radius-sm); color:#805d18; background:color-mix(in srgb,var(--color-secondary) 13%,transparent); font-size:.72rem; }
.jd-recommendations ul { display:grid; gap:.55rem; padding-left:1.15rem; color:var(--color-ink-light); font-size:.8rem; line-height:1.6; }
.jd-summary { display:grid; grid-template-columns:auto 1fr; gap:.85rem; padding:1.2rem 0; border-top:2px solid var(--color-primary); color:var(--color-ink); background:transparent; }
.jd-summary h2 { color:var(--color-ink); font-size:.95rem; }.jd-summary p { margin-top:.45rem; color:var(--color-ink-light); font-size:.8rem; line-height:1.65; overflow-wrap:anywhere; }.jd-summary div div { display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.75rem; }.jd-summary span { padding:.22rem .5rem; border:1px solid var(--color-border); border-radius:5px; color:var(--color-primary); background:var(--color-white); font-size:.66rem; }
.jd-section-empty { padding:1rem 0; color:var(--color-ink-muted); font-size:.78rem; text-align:center; }
:global(.dark) .jd-difficulty { border-color:#31564f; background:#193c37; box-shadow:0 10px 24px rgba(0,0,0,.16); }
:global(.dark) .jd-difficulty-label, :global(.dark) .jd-difficulty p { border-color:#31564f; }
:global(.dark) .jd-difficulty strong { color:#c5f0e2; }
:global(.dark) .jd-difficulty p { color:#d3e8e1; }
:global(.dark) .jd-summary { background:transparent; border-color:var(--color-primary); }
@media (max-width:900px) { .jd-requirement-grid, .jd-insight-grid { grid-template-columns:1fr; } .jd-kpis { grid-template-columns:1fr 1fr; } .jd-skill-grid { grid-template-columns:1fr 1fr; } }
@media (max-width:620px) { .jd-difficulty { grid-template-columns:minmax(0,1fr) 3rem; gap:.7rem; } .jd-difficulty-label { padding-right:.7rem; } .jd-difficulty p { grid-column:1 / -1; padding:.7rem 0 0; border-top:1px solid #c7dfd7; border-left:0; } }
@media (max-width:520px) { .jd-kpis { grid-template-columns:1fr; } .jd-kpis article + article { border-left:0; border-top:1px solid var(--color-border-light); } .jd-skill-grid { grid-template-columns:1fr; } }
</style>
