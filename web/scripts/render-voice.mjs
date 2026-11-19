// Records every fixed text the app reads aloud ("Ouvir") with Gemini TTS, once, as static MP3 files
// in public/voice/, listed in src/content/recordings.json. Re-running records only new or changed
// texts; another --model or --voice records everything again. Only product copy is sent to Google,
// never anything a person typed.
//
// From web/:  npm run voice                       (reads GEMINI_API_KEY from ../.env or the shell)
//             npm run voice -- --model gemini-3.8-flash-lite-tts --voice Sulafat
import { Mp3Encoder } from '@breezystack/lamejs'
import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { parseArgs } from 'node:util'
import { runnerImport } from 'vite'

const WEB = join(import.meta.dirname, '..')
const AUDIO_DIR = join(WEB, 'public', 'voice')
const MANIFEST = join(WEB, 'src', 'content', 'recordings.json')
const API = 'https://generativelanguage.googleapis.com/v1beta/models'
const KBPS = 48 // Clear speech at about 6 KB per second.
const RETRYABLE = new Set([429, 500, 503])
const MAX_ATTEMPTS = 5

const { values: options } = parseArgs({
  options: {
    model: { type: 'string', default: 'gemini-3.8-flash-tts' },
    // Prebuilt Gemini voice described as "warm"; try others by ear with --voice.
    voice: { type: 'string', default: 'Sulafat' },
  },
})

const apiKey = process.env.GEMINI_API_KEY
if (!apiKey) {
  console.error('GEMINI_API_KEY is not set (put it in the repository .env or export it in the shell).')
  process.exit(1)
}

const { module: catalog } = await runnerImport(join(WEB, 'scripts', 'voice-catalog.ts'), {
  configFile: false,
  root: WEB,
  logLevel: 'error',
})

const wanted = catalog.locales.flatMap((locale) => {
  catalog.overwriteGetLocale(() => locale)
  return catalog.spokenTexts().map((text) => ({ key: catalog.recordingKey(locale, text), locale, text }))
})
const voice = { model: options.model, voice: options.voice }
const { keep, render } = catalog.planRecordings(JSON.parse(await readFile(MANIFEST, 'utf-8')), voice, wanted)

// The manifest never lists a file that is missing or recorded with another voice, so an
// interrupted run is resumed by running it again.
const manifest = { ...voice, keys: [...keep] }
await saveManifest()
await removeRecordingsExcept(new Set(keep))

for (const [index, recording] of render.entries()) {
  console.log(`[${index + 1}/${render.length}] ${recording.locale} ${recording.text.slice(0, 60)}...`)
  const { pcm, rate } = await synthesize(recording)
  await writeFile(join(AUDIO_DIR, `${recording.key}.mp3`), encodeMp3(pcm, rate))
  manifest.keys.push(recording.key)
  await saveManifest()
}
console.log(`Done: ${render.length} recorded, ${keep.length} unchanged (${voice.model}, ${voice.voice}).`)

async function saveManifest() {
  const keys = [...manifest.keys].sort()
  await writeFile(MANIFEST, `${JSON.stringify({ ...manifest, keys }, null, 2)}\n`)
}

async function removeRecordingsExcept(keys) {
  await mkdir(AUDIO_DIR, { recursive: true })
  const stale = (await readdir(AUDIO_DIR)).filter((file) => file.endsWith('.mp3') && !keys.has(file.slice(0, -4)))
  await Promise.all(stale.map((file) => rm(join(AUDIO_DIR, file))))
}

async function synthesize({ locale, text }) {
  const body = {
    contents: [{ parts: [{ text: `Read this ${locale} text aloud slowly, in a calm, warm and clear voice, for an older listener:\n\n${text}` }] }],
    generationConfig: {
      responseModalities: ['AUDIO'],
      speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voice.voice } } },
    },
  }
  for (let attempt = 1; ; attempt += 1) {
    // The key goes in a header, never in the URL.
    const response = await fetch(`${API}/${voice.model}:generateContent`, {
      method: 'POST',
      headers: { 'x-goog-api-key': apiKey, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (response.ok) return audioFrom(await response.json())
    if (!RETRYABLE.has(response.status) || attempt === MAX_ATTEMPTS) {
      throw new Error(`Gemini TTS answered ${response.status}: ${await response.text()}`)
    }
    console.log(`  Gemini busy (${response.status}), trying again in ${attempt * 20}s`)
    await new Promise((resolve) => setTimeout(resolve, attempt * 20_000))
  }
}

// Gemini TTS answers raw 16-bit little-endian mono PCM, e.g. "audio/L16;codec=pcm;rate=24000".
function audioFrom(answer) {
  const audio = answer.candidates?.[0]?.content?.parts?.find((part) => part.inlineData)?.inlineData
  if (!audio) throw new Error(`Gemini TTS answered without audio: ${JSON.stringify(answer).slice(0, 300)}`)
  const rate = Number(/rate=(\d+)/.exec(audio.mimeType)?.[1] ?? 24000)
  return { pcm: Buffer.from(audio.data, 'base64'), rate }
}

function encodeMp3(pcm, rate) {
  const samples = new Int16Array(pcm.length >> 1)
  for (let i = 0; i < samples.length; i += 1) samples[i] = pcm.readInt16LE(i * 2)
  const encoder = new Mp3Encoder(1, rate, KBPS)
  // lamejs hands back Int8Array chunks, which Buffer.concat refuses.
  const chunks = [encoder.encodeBuffer(samples), encoder.flush()]
  return Buffer.concat(chunks.map((chunk) => new Uint8Array(chunk.buffer, chunk.byteOffset, chunk.length)))
}
