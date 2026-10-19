// Current image-extractor limit (5 MB). Update here when R3 raises it to 8 MB.
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024
export const ACCEPTED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp']

// Returns the plain-language reason to reject the image; null when it's acceptable.
export function imageProblem(file: { type: string; size: number }): string | null {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
    return 'Esse arquivo não é uma foto que o Verifica consiga ler. Use PNG, JPEG ou WebP.'
  }
  if (file.size > MAX_IMAGE_BYTES) {
    return 'Essa foto é grande demais. Tente um print da tela em vez da foto.'
  }
  return null
}
