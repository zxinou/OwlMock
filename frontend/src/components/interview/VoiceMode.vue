<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { CircleAlert, LoaderCircle, Mic, PhoneOff, Square, Volume2 } from 'lucide-vue-next'
import OwlLogo from '@/components/common/OwlLogo.vue'
import { useVoiceInterview } from '@/composables/useVoiceInterview.js'
import { isVoiceSupported } from '@/utils/voiceAudio.js'

const props = defineProps({
  sessionId: { type: String, required: true },
  profileId: { type: String, required: true },
  autoStart: { type: Boolean, default: false },
  paused: { type: Boolean, default: false },
})

const emit = defineEmits(['update:transcript', 'voice-started', 'voice-stopped'])
const supported = isVoiceSupported()
const voiceRunning = ref(false)
const elapsed = ref(0)
const answerElapsed = ref(0)
const transcriptContainer = ref(null)
let timer = null
let answerTimer = null

const voice = useVoiceInterview({ sessionId: props.sessionId, profileId: props.profileId })

const formattedTime = computed(() => {
  const minutes = Math.floor(elapsed.value / 60)
  const seconds = elapsed.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const formattedAnswerTime = computed(() => {
  const minutes = Math.floor(answerElapsed.value / 60)
  const seconds = answerElapsed.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const currentQuestion = computed(() => {
  if (voice.liveAiText) return voice.liveAiText
  return [...voice.transcriptEntries].reverse().find((entry) => entry.label === '猫头鹰面试官')?.text || ''
})

const latestAnswer = computed(() => {
  return [...voice.transcriptEntries].reverse().find((entry) => entry.label === '你')?.text || ''
})

const controlLabel = computed(() => {
  if (!voiceRunning.value) {
    if (voice.connecting) return '正在连接'
    return voice.error ? '重新连接' : '开始语音面试'
  }
  if (props.paused) return '面试已暂停'
  if (voice.answerState === 'recording') return '回答完毕'
  if (voice.answerState === 'submitting') return '正在处理'
  if (voice.answerState === 'ready') return '开始回答'
  return '请听题'
})

const controlDisabled = computed(() => {
  if (!voiceRunning.value) return !supported || voice.connecting
  return props.paused || ['waiting', 'submitting'].includes(voice.answerState)
})

function scrollTranscript() {
  nextTick(() => {
    if (transcriptContainer.value) transcriptContainer.value.scrollTop = transcriptContainer.value.scrollHeight
  })
}

function stopSessionTimer() {
  clearInterval(timer)
  timer = null
}

function stopAnswerTimer() {
  clearInterval(answerTimer)
  answerTimer = null
}

watch(() => voice.transcriptEntries, (entries) => {
  scrollTranscript()
  emit('update:transcript', entries)
}, { deep: true })
watch(() => voice.liveAiText, scrollTranscript)

watch(() => voice.connected, (connected) => {
  if (!connected && voiceRunning.value && !voice.connecting) {
    voiceRunning.value = false
    stopSessionTimer()
    stopAnswerTimer()
    emit('voice-stopped', voice.transcriptEntries)
  }
})

async function startVoice() {
  if (!supported || voiceRunning.value) return
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    stream.getTracks().forEach((track) => track.stop())
  } catch {
    voice.hintText = '无法访问麦克风，请先允许浏览器使用麦克风'
    return
  }
  voiceRunning.value = true
  await voice.connect()
  if (voice.connected) {
    stopSessionTimer()
    timer = setInterval(() => elapsed.value++, 1000)
    emit('voice-started')
  } else {
    voiceRunning.value = false
  }
}

function stopVoice() {
  voiceRunning.value = false
  stopSessionTimer()
  stopAnswerTimer()
  voice.disconnect()
  emit('voice-stopped', voice.transcriptEntries)
}

async function handlePrimaryControl() {
  if (!voiceRunning.value) {
    await startVoice()
  } else if (voice.answerState === 'ready') {
    const started = await voice.startAnswer()
    if (started) {
      answerElapsed.value = 0
      stopAnswerTimer()
      answerTimer = setInterval(() => answerElapsed.value++, 1000)
    }
  } else if (voice.answerState === 'recording') {
    stopAnswerTimer()
    voice.finishAnswer()
  }
}

defineExpose({ getTranscript: () => voice.transcriptEntries, clearTranscript: voice.clearTranscript })

watch(() => props.paused, (paused) => {
  voice.setPaused(paused)
  if (paused) stopAnswerTimer()
})
watch(() => voice.answerState, (state) => {
  if (state !== 'recording') stopAnswerTimer()
})

onMounted(() => {
  if (!supported) {
    voice.hintText = '当前浏览器不支持语音面试，请使用 Chrome 并允许麦克风权限'
  } else if (props.autoStart) {
    startVoice()
  }
})

onUnmounted(() => {
  stopSessionTimer()
  stopAnswerTimer()
  voice.disconnect()
})
</script>

<template>
  <div class="voice-page">
    <div class="voice-container">
      <div class="voice-status" :class="{ active: voiceRunning && voice.connected, recording: voice.answerState === 'recording' }" aria-live="polite">
        <span class="voice-status__dot"></span>
        <span>{{ voice.connecting ? '连接中' : controlLabel }}</span>
      </div>

      <div class="voice-avatar" :class="{ speaking: voice.avatarSpeaking, listening: voice.answerState === 'recording' }">
        <div class="voice-avatar__ring"></div>
        <div class="voice-avatar__ring voice-avatar__ring--2"></div>
        <div class="voice-avatar__face"><OwlLogo :size="64" :stroke-width="2.5" /></div>
      </div>

      <div class="voice-heading">
        <h2>猫头鹰面试官</h2>
        <p>{{ voice.hintText }}</p>
      </div>

      <div v-if="voice.error" class="voice-error" role="alert">
        <CircleAlert :size="16" />
        <span>{{ voice.error }}</span>
      </div>

      <div class="voice-waveform" :class="{ active: voice.waveformActive, recording: voice.answerState === 'recording' }" aria-hidden="true">
        <span v-for="number in 20" :key="number"></span>
      </div>

      <div ref="transcriptContainer" class="voice-transcript" aria-live="polite">
        <div class="voice-transcript__title">
          <span>当前问题</span>
          <small v-if="voice.answerState === 'recording'">
            {{ voice.waveformActive ? '已检测到声音' : '等待声音' }} · {{ formattedAnswerTime }}
          </small>
        </div>
        <div v-if="currentQuestion" class="voice-transcript__entry voice-transcript__entry--ai">
          <span class="transcript-label">猫头鹰面试官</span>
          <p>{{ currentQuestion }}</p>
        </div>
        <p v-else class="voice-transcript__placeholder">当前问答会显示在这里</p>

        <div v-if="latestAnswer" class="voice-transcript__answer">
          <span class="transcript-label">你的上一轮回答</span>
          <p>{{ latestAnswer }}</p>
        </div>
      </div>

      <div class="voice-controls">
        <button
          type="button"
          class="voice-answer-control"
          :class="{
            recording: voice.answerState === 'recording',
            processing: voice.answerState === 'submitting',
            waiting: voiceRunning && voice.answerState === 'waiting',
          }"
          :disabled="controlDisabled"
          :aria-label="controlLabel"
          @click="handlePrimaryControl"
        >
          <LoaderCircle v-if="voice.connecting || voice.answerState === 'submitting'" :size="25" class="spin" />
          <Square v-else-if="voice.answerState === 'recording'" :size="23" fill="currentColor" />
          <Volume2 v-else-if="voiceRunning && voice.answerState === 'waiting'" :size="27" />
          <Mic v-else :size="27" />
          <span>{{ controlLabel }}</span>
        </button>

        <button v-if="voiceRunning" type="button" class="voice-disconnect" title="关闭语音连接" aria-label="关闭语音连接" @click="stopVoice">
          <PhoneOff :size="18" />
        </button>
      </div>

      <div class="voice-timer">{{ formattedTime }}</div>
    </div>
  </div>
</template>

<style scoped>
.voice-page { display:flex; align-items:center; justify-content:center; height:100%; padding:var(--space-6); }
.voice-container { width:100%; max-width:600px; display:flex; align-items:center; flex-direction:column; gap:1.2rem; padding:1.5rem; animation:voice-in .4s var(--ease-out) both; }
@keyframes voice-in { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:none; } }
.voice-status { display:inline-flex; align-items:center; gap:.5rem; min-height:1.8rem; padding:.2rem .75rem; border:1px solid var(--color-border-light); border-radius:999px; color:var(--color-ink-muted); background:var(--color-surface); font-size:.72rem; font-weight:600; }
.voice-status__dot { width:.4rem; height:.4rem; border-radius:50%; background:var(--color-ink-muted); }
.voice-status.active { color:var(--color-primary); border-color:color-mix(in srgb,var(--color-primary) 28%,var(--color-border)); background:color-mix(in srgb,var(--color-primary) 7%,var(--color-white)); }
.voice-status.active .voice-status__dot { background:var(--color-primary); }
.voice-status.recording { color:#b8473b; border-color:color-mix(in srgb,var(--color-accent) 35%,var(--color-border)); background:color-mix(in srgb,var(--color-accent) 8%,var(--color-white)); }
.voice-status.recording .voice-status__dot { background:var(--color-accent); animation:status-pulse 1.2s ease-in-out infinite; }
@keyframes status-pulse { 50% { opacity:.35; } }
.voice-avatar { position:relative; width:116px; height:116px; display:grid; place-items:center; }
.voice-avatar__ring { position:absolute; inset:0; border:1.5px solid var(--color-primary-light); border-radius:50%; opacity:0; }
.voice-avatar.speaking .voice-avatar__ring, .voice-avatar.listening .voice-avatar__ring { animation:avatar-ring 1.8s ease-out infinite; }
.voice-avatar.speaking .voice-avatar__ring--2, .voice-avatar.listening .voice-avatar__ring--2 { animation-delay:.55s; }
@keyframes avatar-ring { 0% { opacity:.45; transform:scale(.84); } 100% { opacity:0; transform:scale(1.38); } }
.voice-avatar__face { width:86px; height:86px; display:grid; place-items:center; border:2px solid var(--color-border-light); border-radius:50%; background:var(--color-surface); transition:border-color .2s, box-shadow .2s; }
.voice-avatar.speaking .voice-avatar__face { border-color:var(--color-primary-light); box-shadow:0 0 0 4px color-mix(in srgb,var(--color-primary) 10%,transparent); }
.voice-avatar.listening .voice-avatar__face { border-color:var(--color-accent-light); box-shadow:0 0 0 4px color-mix(in srgb,var(--color-accent) 10%,transparent); }
.voice-heading { text-align:center; }
.voice-heading h2 { font-size:1.15rem; }
.voice-heading p { margin-top:.35rem; color:var(--color-ink-muted); font-size:.78rem; }
.voice-error { width:100%; display:flex; align-items:center; justify-content:center; gap:.45rem; min-height:2.25rem; padding:.45rem .75rem; border:1px solid color-mix(in srgb,var(--color-accent) 28%,var(--color-border)); border-radius:var(--radius-md); color:#a94339; background:color-mix(in srgb,var(--color-accent) 7%,var(--color-surface)); font-size:.73rem; }
.voice-waveform { height:2.25rem; display:flex; align-items:center; gap:3px; opacity:.2; }
.voice-waveform span { width:3px; height:6px; border-radius:2px; background:var(--color-primary); }
.voice-waveform.recording { opacity:.55; }
.voice-waveform.recording span { background:var(--color-accent); }
.voice-waveform.active { opacity:1; }
.voice-waveform.active span { animation:voice-wave .75s ease-in-out infinite alternate; }
.voice-waveform.active span:nth-child(3n) { animation-delay:.18s; }.voice-waveform.active span:nth-child(4n) { animation-delay:.32s; }.voice-waveform.active span:nth-child(5n) { animation-delay:.45s; }
@keyframes voice-wave { from { height:5px; } to { height:28px; } }
.voice-transcript { width:100%; min-height:78px; max-height:190px; overflow:auto; padding:1rem 1.1rem; border:1px solid var(--color-border-light); border-radius:var(--radius-md); color:var(--color-ink-light); background:var(--color-surface); font-size:.78rem; line-height:1.65; }
.voice-transcript__title { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:.65rem; padding-bottom:.55rem; border-bottom:1px solid var(--color-border-light); color:var(--color-ink); font-size:.7rem; font-weight:700; }
.voice-transcript__title small { color:var(--color-accent); font-family:var(--font-mono); font-size:.68rem; }
.transcript-label { display:block; margin-bottom:.2rem; color:var(--color-primary); font-size:.68rem; font-weight:700; }
.voice-transcript__answer { margin-top:.8rem; padding-top:.7rem; border-top:1px dashed var(--color-border-light); color:var(--color-ink-muted); }
.voice-transcript__answer .transcript-label { color:var(--color-ink-muted); }
.voice-transcript__placeholder { color:var(--color-ink-muted); text-align:center; }
.voice-controls { position:relative; display:flex; align-items:center; justify-content:center; min-height:4.25rem; }
.voice-answer-control { min-width:10rem; height:4rem; display:inline-flex; align-items:center; justify-content:center; gap:.6rem; padding:0 1.25rem; border-radius:999px; color:var(--color-white); background:var(--color-primary); font-size:.82rem; font-weight:700; transition:transform .18s, background .18s, box-shadow .18s; }
.voice-answer-control:hover:not(:disabled) { transform:translateY(-2px); background:var(--color-primary-dark); box-shadow:0 8px 22px color-mix(in srgb,var(--color-primary) 24%,transparent); }
.voice-answer-control.recording { background:var(--color-accent); }
.voice-answer-control.recording:hover { background:#bb5544; }
.voice-answer-control.waiting, .voice-answer-control.processing { color:var(--color-ink-muted); background:var(--color-surface-alt); }
.voice-answer-control:disabled { cursor:not-allowed; box-shadow:none; transform:none; }
.voice-disconnect { position:absolute; left:calc(100% + .8rem); width:2.5rem; height:2.5rem; display:grid; place-items:center; border:1px solid var(--color-border); border-radius:50%; color:var(--color-ink-muted); background:var(--color-white); }
.voice-disconnect:hover { color:var(--color-accent); border-color:var(--color-accent-light); background:color-mix(in srgb,var(--color-accent) 7%,var(--color-white)); }
.voice-timer { color:var(--color-ink-muted); font-family:var(--font-mono); font-size:.75rem; }
.spin { animation:spin 1s linear infinite; } @keyframes spin { to { transform:rotate(360deg); } }
:global(.dark) .voice-avatar__face, :global(.dark) .voice-disconnect { background:var(--color-surface); }
@media (max-width:640px) { .voice-page { padding:1rem; } .voice-container { padding:1rem 0; } .voice-disconnect { position:static; margin-left:.65rem; } .voice-controls { width:100%; } }
</style>
