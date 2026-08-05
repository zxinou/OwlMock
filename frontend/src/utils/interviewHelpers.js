/**
 * Extract conversational turns from session events.
 * Shared between TextMode, VoiceMode and InterviewSummaryPage.
 *
 * @param {object} opts - shape: { role:'role', content:'content' } for messages
 *                        or { role:'label', content:'text', userLabel:'你', aiLabel:'猫头鹰面试官' } for transcript
 */
function _extractTurns(events, { role = 'role', content = 'content', userLabel = 'user', aiLabel = 'ai' } = {}) {
  const result = []
  for (const event of events) {
    if (event.type === 'user.text' || event.type === 'user.transcript') {
      const text = (event.payload?.text || '').trim()
      if (text) result.push({ [role]: userLabel, [content]: text })
    } else if (event.type === 'assistant.text.done' || event.type === 'assistant.transcript.done') {
      const text = (event.payload?.text || '').trim()
      if (text) result.push({ [role]: aiLabel, [content]: text })
    }
  }
  return result
}

/** Convert backend session events to frontend message objects ({ role, content }). */
export function eventsToMessages(events) {
  return _extractTurns(events)
}

/** Convert session events to voice transcript entries ({ label, text }). */
export function eventsToTranscriptEntries(events) {
  return _extractTurns(events, { role: 'label', content: 'text', userLabel: '你', aiLabel: '猫头鹰面试官' })
}

/** Last conversational turn for compact voice UI (user answer or assistant question). */
export function lastTranscriptEntry(events) {
  const entries = eventsToTranscriptEntries(events)
  return entries.at(-1) ?? null
}

/** Restore only modes supported by the interview UI. */
export function normalizeSessionMode(mode) {
  return mode === 'voice' ? 'voice' : 'text'
}

/** Prefer the owning job workspace when a session belongs to a project. */
export function sessionReturnPath(projectId) {
  return projectId ? `/projects/${encodeURIComponent(projectId)}` : '/interview'
}
