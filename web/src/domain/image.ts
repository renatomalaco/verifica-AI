import { m } from '../paraglide/messages.js'

// Current image-extractor limit (5 MB). Update here when R3 raises it to 8 MB.
export const MAX_IMAGE_MB = 5
export const MAX_IMAGE_BYTES = MAX_IMAGE_MB * 1024 * 1024
export const ACCEPTED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp']

// Returns the plain-language reason to reject the image; null when it's acceptable.
export function imageProblem(file: { type: string; size: number }): string | null {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) return m.home_image_error_type()
  if (file.size > MAX_IMAGE_BYTES) return m.home_image_error_size()
  return null
}
