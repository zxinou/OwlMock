import assert from 'node:assert/strict'
import test from 'node:test'
import { createServer } from 'vite'

test('captured audio commits without relying on the local volume threshold', async (t) => {
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
  globalThis.fetch = async () => ({
    ok: true,
    json: async () => ({ events: [] }),
  })
  const audio = await vite.ssrLoadModule('/src/utils/voiceAudio.js')
  let stopCalls = 0
  audio.PcmStreamCapture.prototype.start = async function start() {
    this.onActive?.(false)
    this.onChunk?.('AAAA')
  }
  audio.PcmStreamCapture.prototype.stop = function stop() {
    stopCalls += 1
  }

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
  })
  socket.emit('state.changed', { state: 'listening' })

  const originalNow = Date.now
  let now = 1000
  Date.now = () => now
  t.after(() => { Date.now = originalNow })

  assert.equal(await voice.startAnswer(), true)
  now = 2000
  assert.equal(voice.finishAnswer(), true)
  assert.equal(
    socket.sent.filter((message) => message.type === 'control.commit').length,
    1,
  )
  assert.equal(stopCalls, 0)

  voice.disconnect()
})
