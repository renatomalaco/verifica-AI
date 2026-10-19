import { useRef, useState, type DragEvent } from 'react'
import { ACCEPTED_IMAGE_TYPES, imageProblem } from '../domain/image'
import { ImageIcon } from './Icons'

interface ImagePickerProps {
  imageB64: string | null
  onImageChange: (imageB64: string | null) => void
}

export function ImagePicker({ imageB64, onImageChange }: ImagePickerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)

  const pick = (file: File | undefined) => {
    if (!file) return
    const problem = imageProblem(file)
    setError(problem)
    if (problem) return
    const reader = new FileReader()
    reader.onload = () => onImageChange(reader.result as string)
    reader.readAsDataURL(file)
  }

  const drop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    pick(e.dataTransfer.files?.[0])
  }

  return (
    <>
      <span className="field-label" id="rotulo-foto">
        Envie a foto ou o print da tela
      </span>
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_IMAGE_TYPES.join(',')}
        className="sr-only"
        aria-labelledby="rotulo-foto"
        tabIndex={-1}
        onChange={(e) => pick(e.target.files?.[0])}
      />
      {imageB64 ? (
        <>
          <img src={imageB64} alt="A foto ou print que você escolheu" className="image-preview" />
          <button type="button" className="btn btn-ghost align-start" onClick={() => onImageChange(null)}>
            Trocar foto
          </button>
        </>
      ) : (
        <button
          type="button"
          className="dropzone"
          data-dragging={dragging || undefined}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={drop}
        >
          <ImageIcon size={34} className="accent-icon" />
          <span className="text-strong">Escolher foto ou print</span>
          {/* On desktop the file can also be dragged in; the hint only shows with a mouse. */}
          <span className="text-muted text-small only-pointer">ou arraste a imagem para cá</span>
          <span className="text-muted text-small">PNG, JPEG ou WebP, até 5 MB</span>
        </button>
      )}
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </>
  )
}
