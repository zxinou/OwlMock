const NEXT_ACTIONS = {
  job: {
    key: 'job',
    title: '完成岗位理解',
    description: '补充或重新分析 JD，建立这次准备的岗位上下文。',
  },
  resume: {
    key: 'resume',
    title: '匹配一份主简历',
    description: '选择简历并生成岗位匹配报告，定位证据与缺口。',
  },
  interview: {
    key: 'interview',
    title: '开始针对性模拟面试',
    description: '围绕当前 JD 和简历进行文字或语音练习。',
  },
}

function uniqueStrings(values) {
  return [...new Set(values.filter((value) => typeof value === 'string' && value.trim()).map((value) => value.trim()))]
}

function collectFocus(result) {
  if (!result || typeof result !== 'object') return []
  const interview = result.interview || result.interview_focus || {}
  const requirements = result.requirements || {}
  return uniqueStrings([
    ...(Array.isArray(interview) ? interview : []),
    ...(Array.isArray(interview.focus) ? interview.focus : []),
    ...(Array.isArray(interview.focus_areas) ? interview.focus_areas : []),
    ...(Array.isArray(requirements.must_have) ? requirements.must_have : []),
    ...(Array.isArray(requirements.required) ? requirements.required : []),
  ]).slice(0, 6)
}

function findSummary(result) {
  if (!result || typeof result !== 'object') return ''
  const job = result.job || {}
  return job.summary || result.summary || result.overview || ''
}

export function createWorkspaceViewModel(project) {
  const source = project || {}
  const steps = Array.isArray(source.steps) ? source.steps : []
  const firstIncomplete = steps.find((step) => step.status !== 'completed')
  const nextKey = firstIncomplete?.key || 'interview'
  const focusItems = collectFocus(source.current_jd?.result)

  return {
    readOnly: Boolean(source.archived_at),
    steps,
    score: Number.isFinite(Number(source.latest_match?.score))
      ? Number(source.latest_match.score)
      : null,
    nextAction: NEXT_ACTIONS[nextKey] || NEXT_ACTIONS.interview,
    focusItems: focusItems.length ? focusItems : ['梳理核心经历', '准备量化成果', '练习清晰表达'],
    summary: findSummary(source.current_jd?.result) || source.current_jd?.text || '完成 JD 分析后，这里会形成可复用的岗位摘要。',
    interviews: Array.isArray(source.recent_sessions) ? source.recent_sessions : [],
  }
}
