import { describe, expect, it } from 'vitest'
import { m } from '../paraglide/messages.js'
import { imageProblem, MAX_IMAGE_BYTES } from './image'

const file = (type: string, size: number) => ({ type, size })

describe('imageProblem', () => {
  it('accepts PNG, JPEG and WebP within the size limit', () => {
    expect(imageProblem(file('image/png', 1000))).toBeNull()
    expect(imageProblem(file('image/jpeg', MAX_IMAGE_BYTES))).toBeNull()
    expect(imageProblem(file('image/webp', 10))).toBeNull()
  })

  it('rejects other formats with a friendly message', () => {
    expect(imageProblem(file('application/pdf', 10))).toBe(m.home_image_error_type())
    expect(imageProblem(file('image/gif', 10))).not.toBeNull()
  })

  it('rejects images above the limit and suggests a screenshot', () => {
    expect(imageProblem(file('image/png', MAX_IMAGE_BYTES + 1))).toBe(m.home_image_error_size())
  })
})
