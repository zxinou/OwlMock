import { ref, reactive } from 'vue'
import { api } from '@/api/index.js'
import { eventsToTranscriptEntries, lastTranscriptEntry } from '@/utils/interviewHelpers.js'
import { PcmPlayer, PcmStreamCapture } from '@/utils/voiceAudio.js'

const CONNECT_TIMEOUT_MS = 12000
const SUBMIT_TIMEOUT_MS = 35000
const MIN_ANSWER_MS = 700

export function useVoiceInterview({ sessionId, profileId, userId = 'default' }) {
  const connected = ref(false)
  const connecting = ref(false)
  const error = ref(null)
  const hintText = ref('等待开始')
  const avatarSpeaking = ref(false)
  const isListening = ref(false)
  const transcriptEntries = ref([])
  const liveAiText = ref('')
  const waveformActive = ref(false)
  const answerState = ref('waiting')

  let ws = null
  let capture = null
  let player = null
  let isPaused = false
  let inputSampleRate = 24000
  let outputSampleRate = 24000
  let connectionTimer = null
  let submitTimer = null
  let recordingStartedAt = 0
  let speechDetected = false

  function formatVoiceError(payload) {
    const code = payload?.code || ''
    const message = payload?.message || ''
    if (code === 'realtime_not_configured' || message.includes('DASHSCOPE_API_KEY') || message.includes('OPENAI_API_KEY') || message.includes('未配置')) {
      return '语音面试 API Key 未配置，请检查 backend/.env 后重启后端'
    }
    if (message.includes('websocket connection') || message.includes('无法连接 DashScope')) {
      return '无法连接 DashScope 实时语音服务，请检查网络、API Key 与防火墙设置'
    }
    return message || '语音连接出错'
  }

  function send(message) {
    if (ws?.readyState !== WebSocket.OPEN) return false
    try {
      ws.send(JSON.stringify(message))
      return true
    } catch {
      return false
    }
  }

  function clearConnectionTimer() {
    clearTimeout(connectionTimer)
    connectionTimer = null
  }

  function clearSubmitTimer() {
    clearTimeout(submitTimer)
    submitTimer = null
  }

  function resetRecordingEvidence() {
    recordingStartedAt = 0
    speechDetected = false
  }

  function startSubmitTimer() {
    clearSubmitTimer()
    submitTimer = setTimeout(() => {
      if (answerState.value !== 'submitting') return
      answerState.value = 'ready'
      error.value = '回答处理超时，请重新回答本题'
      hintText.value = error.value
    }, SUBMIT_TIMEOUT_MS)
  }

  function appendTranscript(label, text) {
    const trimmed = (text || '').trim()
    if (trimmed) transcriptEntries.value.push({ label, text: trimmed })
  }

  async function loadHistory() {
    const data = await api.getSessionEvents(sessionId)
    const entries = eventsToTranscriptEntries(data.events || [])
    const last = lastTranscriptEntry(data.events || [])
    transcriptEntries.value = last ? [last] : entries.slice(-1)
  }

  async function startCapture() {
    if (isPaused || capture || !connected.value) return false
    try {
      capture = new PcmStreamCapture({
        sampleRate: inputSampleRate,
        onChunk: (audio) => {
          if (!isPaused && answerState.value === 'recording' && ws?.readyState === WebSocket.OPEN) {
            send({ type: 'user.audio.chunk', payload: { audio } })
          }
        },
        onActive: (active) => {
          waveformActive.value = active && answerState.value === 'recording'
          if (active && answerState.value === 'recording') speechDetected = true
        },
      })
      await capture.start()
      isListening.value = true
      return true
    } catch (e) {
      error.value = '无法访问麦克风，请检查浏览器权限'
      hintText.value = error.value
      capture = null
      return false
    }
  }

  function stopCapture() {
    capture?.stop()
    capture = null
    isListening.value = false
    waveformActive.value = false
  }

  function prepareFirstTurn() {
    const last = transcriptEntries.value.at(-1)
    if (last?.label === '猫头鹰面试官') {
      answerState.value = 'ready'
      hintText.value = '准备好后，点击麦克风开始回答'
      return
    }
    answerState.value = 'waiting'
    hintText.value = '面试官正在准备第一个问题'
    if (!send({
      type: 'user.text',
      payload: { text: '我已经准备好，请开始面试并提出第一个问题。' },
    })) {
      error.value = '语音连接已断开，请重新连接'
      hintText.value = error.value
    }
  }

  function beginAssistantTurn() {
    clearSubmitTimer()
    error.value = null
    stopCapture()
    answerState.value = 'waiting'
    hintText.value = '请听面试官提问'
    avatarSpeaking.value = true
    waveformActive.value = false
  }

  function finishAssistantTurn() {
    clearSubmitTimer()
    avatarSpeaking.value = false
    if (!isPaused && connected.value) {
      answerState.value = 'ready'
      hintText.value = '准备好后，点击麦克风开始回答'
    }
  }

  function handleServerEvent(data) {
    switch (data.type) {
      case 'session.started':
        inputSampleRate = Number(data.payload?.audio?.input_sample_rate) || inputSampleRate
        outputSampleRate = Number(data.payload?.audio?.output_sample_rate) || outputSampleRate
        prepareFirstTurn()
        break
      case 'user.transcript':
        appendTranscript('你', data.payload?.text || '')
        break
      case 'assistant.transcript.delta':
        beginAssistantTurn()
        liveAiText.value += data.payload?.text ?? ''
        break
      case 'assistant.transcript.done': {
        const text = data.payload?.text || liveAiText.value
        liveAiText.value = ''
        appendTranscript('猫头鹰面试官', text)
        break
      }
      case 'assistant.audio.delta':
        beginAssistantTurn()
        if (!player) player = new PcmPlayer(outputSampleRate)
        player.playBase64(data.payload?.audio)
        break
      case 'assistant.audio.done':
        avatarSpeaking.value = false
        break
      case 'ai.interrupted':
        player?.stop()
        liveAiText.value = ''
        finishAssistantTurn()
        break
      case 'state.changed':
        if (data.payload?.state === 'listening') finishAssistantTurn()
        break
      case 'error':
        clearSubmitTimer()
        stopCapture()
        error.value = formatVoiceError(data.payload)
        hintText.value = error.value
        answerState.value = connected.value && !isPaused ? 'ready' : 'waiting'
        break
      case 'cost.limit_reached':
        error.value = '语音面试时长已达上限'
        hintText.value = error.value
        disconnect()
        break
      case 'turn.done':
        disconnect()
        break
      default:
        break
    }
  }

  async function connect() {
    if (connecting.value || connected.value) return
    connecting.value = true
    error.value = null
    hintText.value = '正在连接语音面试官'

    try {
      try {
        await loadHistory()
      } catch (historyError) {
        console.warn('Unable to load voice interview history:', historyError)
      }

      const socket = new WebSocket(api.getVoiceWebSocketUrl(sessionId, { profileId, userId }))
      ws = socket

      await new Promise((resolve, reject) => {
        let settled = false
        const settle = (callback, value) => {
          if (settled) return
          settled = true
          clearConnectionTimer()
          callback(value)
        }

        connectionTimer = setTimeout(() => {
          settle(reject, new Error('连接语音服务超时，请重试'))
          socket.close()
        }, CONNECT_TIMEOUT_MS)

        socket.onmessage = (event) => {
          try {
            handleServerEvent(JSON.parse(event.data))
          } catch (eventError) {
            console.error('Invalid WS message:', eventError)
          }
        }
        socket.onopen = () => {
          if (ws !== socket) return
          connected.value = true
          connecting.value = false
          settle(resolve)
        }
        socket.onerror = () => {
          if (!settled) settle(reject, new Error('WebSocket 连接失败'))
        }
        socket.onclose = (event) => {
          if (ws !== socket) return
          const wasConnected = connected.value
          ws = null
          connected.value = false
          connecting.value = false
          clearConnectionTimer()
          clearSubmitTimer()
          stopCapture()
          player?.destroy()
          player = null
          avatarSpeaking.value = false
          answerState.value = 'waiting'

          if (!settled) {
            settle(reject, new Error(`WebSocket 已关闭 (${event.code})`))
          } else if (wasConnected && event.code !== 1000) {
            error.value = '语音连接已断开，请重新连接'
            hintText.value = error.value
          }
        }
      })
    } catch (e) {
      clearConnectionTimer()
      connecting.value = false
      connected.value = false
      error.value = e.message || '连接失败'
      hintText.value = error.value
      const socket = ws
      ws = null
      if (socket) {
        socket.onclose = null
        socket.close()
      }
    }
  }

  async function startAnswer() {
    if (!connected.value || isPaused || answerState.value !== 'ready') return false
    clearSubmitTimer()
    resetRecordingEvidence()
    error.value = null
    answerState.value = 'recording'
    hintText.value = '正在回答，完成后点击“回答完毕”'
    const started = await startCapture()
    if (!started) {
      answerState.value = 'ready'
      return false
    }
    recordingStartedAt = Date.now()
    return true
  }

  function finishAnswer() {
    if (!connected.value || answerState.value !== 'recording') return false
    const recordingDuration = Date.now() - recordingStartedAt
    stopCapture()

    if (recordingDuration < MIN_ANSWER_MS || !speechDetected) {
      resetRecordingEvidence()
      answerState.value = 'ready'
      error.value = '没有检测到有效回答，请靠近麦克风后重试'
      hintText.value = error.value
      return false
    }

    if (!send({ type: 'control.commit', payload: {} })) {
      resetRecordingEvidence()
      answerState.value = 'ready'
      error.value = '语音连接已断开，请重新连接'
      hintText.value = error.value
      return false
    }

    resetRecordingEvidence()
    error.value = null
    answerState.value = 'submitting'
    hintText.value = '正在整理你的回答'
    startSubmitTimer()
    return true
  }

  function disconnect() {
    clearConnectionTimer()
    clearSubmitTimer()
    resetRecordingEvidence()
    stopCapture()
    player?.destroy()
    player = null
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    connected.value = false
    connecting.value = false
    avatarSpeaking.value = false
    answerState.value = 'waiting'
  }

  function setPaused(paused) {
    isPaused = paused
    if (paused) {
      resetRecordingEvidence()
      stopCapture()
      hintText.value = '面试已暂停'
    } else if (connected.value) {
      answerState.value = avatarSpeaking.value ? 'waiting' : 'ready'
      hintText.value = avatarSpeaking.value ? '请听面试官提问' : '准备好后，点击麦克风开始回答'
    }
  }

  function clearTranscript() {
    transcriptEntries.value = []
    liveAiText.value = ''
  }

  return reactive({
    connected,
    connecting,
    error,
    hintText,
    avatarSpeaking,
    isListening,
    transcriptEntries,
    liveAiText,
    waveformActive,
    answerState,
    connect,
    disconnect,
    startAnswer,
    finishAnswer,
    setPaused,
    loadHistory,
    clearTranscript,
  })
}
