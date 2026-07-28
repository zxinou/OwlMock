import assert from 'node:assert/strict'
import test from 'node:test'
import { createServer } from 'vite'

test('hybrid voice interview keeps listening, supports manual finish and interruption', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())

  const sockets = []
  class FakeWebSocket {
    static OPEN = 1

    constructor() {
      this.readyState = FakeWebSocket.OPEN
      this.sent = []
      sockets.push(this)
      queueMicrotask(() => this.onopen?.())
    }

    send(message) {
      this.sent.push(JSON.parse(message))
    }

    close() {
      this.readyState = 3
    }

    emit(type, payload = {}) {
      this.onmessage?.({ data: JSON.stringify({ type, payload }) })
    }
  }

  globalThis.window = { location: { protocol: 'http:', host: 'test.local' } }
  globalThis.WebSocket = FakeWebSocket
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ events: [] }) })

  const audio = await vite.ssrLoadModule('/src/utils/voiceAudio.js')
  let captureInstance = null
  let playerStopCalls = 0
  const playedItems = []
  audio.PcmStreamCapture.prototype.start = async function start() {
    captureInstance = this
  }
  audio.PcmStreamCapture.prototype.stop = function stop() {}
  audio.PcmPlayer.prototype.playBase64 = function playBase64(_audio, itemId) {
    playedItems.push(itemId)
  }
  audio.PcmPlayer.prototype.stop = function stop() {
    playerStopCalls += 1
  }
  audio.PcmPlayer.prototype.destroy = function destroy() {}

  const { useVoiceInterview } = await vite.ssrLoadModule(
    `/src/composables/useVoiceInterview.js?test=${Date.now()}`,
  )
  const voice = useVoiceInterview({
    sessionId: 'voice-test',
    profileId: 'interviewer-technical',
  })

  await voice.connect()
  const socket = sockets.at(-1)
  socket.emit('session.started', {
    audio: { input_sample_rate: 16000, output_sample_rate: 24000 },
    turn_mode: 'hybrid',
    supports_interrupt: true,
    vad_silence_duration_ms: 1800,
  })
  socket.emit('assistant.audio.delta', { item_id: 'assistant-1', audio: 'AAAA' })
  socket.emit('state.changed', { state: 'listening' })

  assert.ok(captureInstance, 'microphone capture should be reused for the whole session')
  assert.equal(voice.interactionState, 'listening')
  assert.equal(voice.answerState, 'recording')

  captureInstance.onActive(true)
  captureInstance.onChunk('PREBUFFER')
  captureInstance.onActive(true)
  captureInstance.onChunk('SPEECH')

  assert.equal(voice.interactionState, 'speech_detected')
  assert.ok(socket.sent.some((message) => message.type === 'user.audio.chunk'))
  assert.equal(voice.finishAnswer(), true)
  assert.equal(
    socket.sent.filter((message) => message.type === 'control.commit').length,
    1,
  )

  socket.emit('assistant.audio.delta', { item_id: 'assistant-2', audio: 'BBBB' })
  captureInstance.onActive(true)
  captureInstance.onChunk('BARGE-1')
  captureInstance.onActive(true)
  captureInstance.onChunk('BARGE-2')

  assert.ok(socket.sent.some((message) => message.type === 'control.interrupt'))
  assert.ok(playerStopCalls > 0)
  const playedBeforeLateChunk = playedItems.length
  socket.emit('assistant.audio.delta', { item_id: 'assistant-2', audio: 'LATE' })
  assert.equal(playedItems.length, playedBeforeLateChunk)

  socket.emit('user.speech.stopped', { item_id: 'user-barge-1' })
  socket.emit('assistant.transcript.delta', { item_id: 'assistant-3', text: '下一道' })
  captureInstance.onActive(true)
  captureInstance.onChunk('TEXT-BARGE-1')
  captureInstance.onActive(true)
  captureInstance.onChunk('TEXT-BARGE-2')
  const interrupts = socket.sent.filter((message) => message.type === 'control.interrupt')
  assert.equal(interrupts.at(-1).payload.item_id, 'assistant-3')

  socket.emit('user.transcript.delta', { item_id: 'user-1', text: '我负责了核心模块' })
  assert.equal(voice.liveUserText, '我负责了核心模块')
  socket.emit('user.transcript', { item_id: 'user-1', text: '我负责了核心模块的设计' })
  assert.equal(voice.liveUserText, '')
  assert.equal(voice.transcriptEntries.at(-1).text, '我负责了核心模块的设计')

  voice.disconnect()
})

test('muting a hybrid session pauses upload without closing the websocket', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())

  const sockets = []
  class FakeWebSocket {
    static OPEN = 1
    constructor() {
      this.readyState = 1
      this.sent = []
      sockets.push(this)
      queueMicrotask(() => this.onopen?.())
    }
    send(message) { this.sent.push(JSON.parse(message)) }
    close() { this.readyState = 3 }
    emit(type, payload = {}) {
      this.onmessage?.({ data: JSON.stringify({ type, payload }) })
    }
  }

  globalThis.window = { location: { protocol: 'http:', host: 'test.local' } }
  globalThis.WebSocket = FakeWebSocket
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ events: [] }) })

  const audio = await vite.ssrLoadModule('/src/utils/voiceAudio.js')
  let captureInstance = null
  audio.PcmStreamCapture.prototype.start = async function start() { captureInstance = this }
  audio.PcmStreamCapture.prototype.stop = function stop() {}

  const { useVoiceInterview } = await vite.ssrLoadModule(
    `/src/composables/useVoiceInterview.js?mute=${Date.now()}`,
  )
  const voice = useVoiceInterview({ sessionId: 'mute-test', profileId: 'interviewer-technical' })
  await voice.connect()
  const socket = sockets.at(-1)
  socket.emit('session.started', { turn_mode: 'hybrid' })
  socket.emit('state.changed', { state: 'listening' })

  voice.toggleMute()
  captureInstance.onActive(true)
  captureInstance.onChunk('MUTED')
  captureInstance.onActive(true)
  captureInstance.onChunk('MUTED-2')

  assert.equal(voice.isMuted, true)
  assert.equal(socket.readyState, FakeWebSocket.OPEN)
  assert.equal(socket.sent.filter((message) => message.type === 'user.audio.chunk').length, 0)

  voice.toggleMute()
  captureInstance.onActive(true)
  captureInstance.onChunk('LIVE-1')
  captureInstance.onActive(true)
  captureInstance.onChunk('LIVE-2')
  assert.ok(socket.sent.some((message) => message.type === 'user.audio.chunk'))

  voice.disconnect()
})
