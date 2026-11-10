import { useState } from 'react'
import { imageProblem } from '../domain/image'
import { m } from '../paraglide/messages.js'

export interface ImageInput {
  imageB64: string | null
  error: string | null
  pick: (file: File) => void
  clear: () => void
}

function readDataUrl(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

/** The photo to check, whether picked on screen or shared from another app. */
export function useImageInput(): ImageInput {
  const [imageB64, setImageB64] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const pick = (file: File) => {
    const problem = imageProblem(file)
    setError(problem)
    if (problem) return
    // A file the browser cannot read is, for the person, a photo the Verifica cannot read.
    readDataUrl(file).then(setImageB64, () => setError(m.home_image_error_type()))
  }

  const clear = () => {
    setImageB64(null)
    setError(null)
  }

  return { imageB64, error, pick, clear }
}
