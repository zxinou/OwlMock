import { ref, reactive } from 'vue'
import { api } from '@/api/index.js'
import { eventsToTranscriptEntries, lastTranscriptEntry } from '@/utils/interviewHelpers.js'
import { PcmPlayer, PcmStreamCapture } from '@/utils/voiceAudio.js'

const CONNECT_TIMEOUT_MS = 12000
const SUBMIT_TIMEOUT_MS = 35000
const SPEECH_CONFIRM_FRAMES = 2
const PREBUFFER_CHUNKS = 4

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
  const interactionState = ref('waiting')
  const liveUserText = ref('')
  const isMuted = ref(false)

  let ws = null
  let capture = null
  let player = null
  let isPaused = false
  let inputSampleRate = 24000
  let outputSampleRate = 24000
  let connectionTimer = null
  let submitTimer = null
  let audioChunksSent = 0
  let turnMode = 'none'
  let supportsInterrupt = false
  let activeFrames = 0
  let speechUploadActive = false
  let activeAssistantItemId = ''
  let assistantResponseObserved = false
  const prebuffer = []
  const interruptedAssistantItems = new Set()

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
    audioChunksSent = 0
  }

  function resetSpeechGate() {
    activeFrames = 0
    speechUploadActive = false
    prebuffer.length = 0
    waveformActive.value = false
  }

  function sendAudio(audio) {
    if (!audio || isMuted.value || isPaused || ws?.readyState !== WebSocket.OPEN) return false
    if (!send({ type: 'user.audio.chunk', payload: { audio } })) return false
    audioChunksSent += 1
    return true
  }

  function interruptAssistant() {
    if (!supportsInterrupt || !avatarSpeaking.value || !activeAssistantItemId) return
    interruptedAssistantItems.add(activeAssistantItemId)
    player?.stop(activeAssistantItemId)
    send({ type: 'control.interrupt', payload: { item_id: activeAssistantItemId } })
    avatarSpeaking.value = false
    liveAiText.value = ''
    interactionState.value = 'interrupted'
  }

  function beginSpeechUpload() {
    if (speechUploadActive || isMuted.value || isPaused) return
    interruptAssistant()
    speechUploadActive = true
    resetRecordingEvidence()
    answerState.value = 'recording'
    interactionState.value = 'speech_detected'
    hintText.value = '正在聆听，停顿后将自动提交'
    for (const chunk of prebuffer.splice(0)) sendAudio(chunk)
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
    if (isPaused || !connected.value) return false
    if (capture) {
      isListening.value = true
      return true
    }
    try {
      capture = new PcmStreamCapture({
        sampleRate: inputSampleRate,
        onChunk: (audio) => {
          if (isPaused || isMuted.value || !connected.value) return
          if (speechUploadActive) {
            sendAudio(audio)
            return
          }
          prebuffer.push(audio)
          if (prebuffer.length > PREBUFFER_CHUNKS) prebuffer.shift()
          if (activeFrames >= SPEECH_CONFIRM_FRAMES) beginSpeechUpload()
        },
        onActive: (active) => {
          activeFrames = active ? activeFrames + 1 : 0
          waveformActive.value = active && !isMuted.value
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
    resetSpeechGate()
  }

  function prepareFirstTurn() {
    const last = transcriptEntries.value.at(-1)
    if (last?.label === '猫头鹰面试官') {
      answerState.value = 'ready'
      interactionState.value = turnMode === 'hybrid' ? 'listening' : 'waiting'
      hintText.value = turnMode === 'hybrid' ? '请直接开始回答' : '准备好后，点击麦克风开始回答'
      if (turnMode === 'hybrid') startCapture()
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
    assistantResponseObserved = true
    error.value = null
    answerState.value = 'waiting'
    interactionState.value = 'speaking'
    hintText.value = '请听面试官提问'
    avatarSpeaking.value = true
    waveformActive.value = false
  }

  function finishAssistantTurn() {
    if (answerState.value === 'submitting' && !assistantResponseObserved) return
    clearSubmitTimer()
    avatarSpeaking.value = false
    if (!isPaused && connected.value) {
      resetSpeechGate()
      answerState.value = turnMode === 'hybrid' ? 'recording' : 'ready'
      interactionState.value = turnMode === 'hybrid' ? 'listening' : 'waiting'
      hintText.value = turnMode === 'hybrid' ? '请直接开始回答，停顿后会自动提交' : '准备好后，点击麦克风开始回答'
      if (turnMode === 'hybrid') startCapture()
    }
    assistantResponseObserved = false
  }

  function handleServerEvent(data) {
    switch (data.type) {
      case 'session.started':
        inputSampleRate = Number(data.payload?.audio?.input_sample_rate) || inputSampleRate
        outputSampleRate = Number(data.payload?.audio?.output_sample_rate) || outputSampleRate
        turnMode = data.payload?.turn_mode || 'none'
        supportsInterrupt = Boolean(data.payload?.supports_interrupt)
        interactionState.value = 'waiting'
        if (turnMode === 'hybrid') startCapture()
        prepareFirstTurn()
        break
      case 'user.speech.started':
        interactionState.value = 'speech_detected'
        answerState.value = 'recording'
        break
      case 'user.speech.stopped':
        speechUploadActive = false
        prebuffer.length = 0
        interactionState.value = 'thinking'
        answerState.value = 'submitting'
        hintText.value = '正在整理你的回答'
        startSubmitTimer()
        break
      case 'user.transcript.delta':
        liveUserText.value = data.payload?.text || ''
        break
      case 'user.transcript':
        appendTranscript('你', data.payload?.text || '')
        liveUserText.value = ''
        break
      case 'assistant.transcript.delta':
        activeAssistantItemId = data.payload?.item_id || activeAssistantItemId
        if (interruptedAssistantItems.has(activeAssistantItemId)) break
        beginAssistantTurn()
        liveAiText.value += data.payload?.text ?? ''
        break
      case 'assistant.transcript.done': {
        activeAssistantItemId = data.payload?.item_id || activeAssistantItemId
        if (interruptedAssistantItems.has(activeAssistantItemId)) break
        const text = data.payload?.text || liveAiText.value
        liveAiText.value = ''
        appendTranscript('猫头鹰面试官', text)
        break
      }
      case 'assistant.audio.delta':
        activeAssistantItemId = data.payload?.item_id || activeAssistantItemId
        if (interruptedAssistantItems.has(activeAssistantItemId)) break
        beginAssistantTurn()
        if (!player) player = new PcmPlayer(outputSampleRate, {
          onIdle: () => {
            if (interactionState.value === 'speaking') avatarSpeaking.value = false
          },
        })
        player.playBase64(data.payload?.audio, activeAssistantItemId)
        break
      case 'assistant.audio.done':
        if (player?.isIdle()) avatarSpeaking.value = false
        break
      case 'ai.interrupted':
        if (data.payload?.item_id) interruptedAssistantItems.add(data.payload.item_id)
        player?.stop(data.payload?.item_id || activeAssistantItemId)
        liveAiText.value = ''
        interactionState.value = 'interrupted'
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
        interactionState.value = 'error'
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
    interactionState.value = 'connecting'
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
    interactionState.value = 'listening'
    hintText.value = '正在回答，完成后点击“回答完毕”'
    const started = await startCapture()
    if (!started) {
      answerState.value = 'ready'
      return false
    }
    return true
  }

  function finishAnswer() {
    if (!connected.value || answerState.value !== 'recording') return false

    if (audioChunksSent === 0) {
      resetRecordingEvidence()
      answerState.value = 'ready'
      error.value = '还没有检测到回答，请靠近麦克风后重试'
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
    speechUploadActive = false
    prebuffer.length = 0
    assistantResponseObserved = false
    error.value = null
    answerState.value = 'submitting'
    interactionState.value = 'thinking'
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
    interactionState.value = 'waiting'
    liveUserText.value = ''
    isMuted.value = false
  }

  function setPaused(paused) {
    isPaused = paused
    if (paused) {
      resetRecordingEvidence()
      stopCapture()
      hintText.value = '面试已暂停'
      interactionState.value = 'waiting'
    } else if (connected.value) {
      answerState.value = avatarSpeaking.value ? 'waiting' : (turnMode === 'hybrid' ? 'recording' : 'ready')
      interactionState.value = avatarSpeaking.value ? 'speaking' : (turnMode === 'hybrid' ? 'listening' : 'waiting')
      hintText.value = avatarSpeaking.value ? '请听面试官提问' : (turnMode === 'hybrid' ? '请直接开始回答' : '准备好后，点击麦克风开始回答')
      if (turnMode === 'hybrid') startCapture()
    }
  }

  function clearTranscript() {
    transcriptEntries.value = []
    liveAiText.value = ''
    liveUserText.value = ''
  }

  function toggleMute() {
    isMuted.value = !isMuted.value
    resetSpeechGate()
    if (isMuted.value) {
      hintText.value = '麦克风已静音'
    } else if (connected.value && !isPaused) {
      answerState.value = turnMode === 'hybrid' ? 'recording' : 'ready'
      interactionState.value = turnMode === 'hybrid' ? 'listening' : 'waiting'
      hintText.value = turnMode === 'hybrid' ? '请直接开始回答' : '准备好后，点击麦克风开始回答'
    }
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
    interactionState,
    liveUserText,
    isMuted,
    connect,
    disconnect,
    startAnswer,
    finishAnswer,
    setPaused,
    loadHistory,
    clearTranscript,
    toggleMute,
  })
}
