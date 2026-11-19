// Single entry point for render-voice.mjs: one module graph, so the locale the script sets
// is the one the texts are read in.
export { spokenTexts } from '../src/content/spoken'
export { planRecordings, recordingKey } from '../src/domain/voice'
export { locales, overwriteGetLocale } from '../src/paraglide/runtime.js'
