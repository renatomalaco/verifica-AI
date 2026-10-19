// Stroke icons drawn for Verifica (24×24, inherit currentColor).
import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement> & { size?: number }

function Svg({ size = 24, children, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  )
}

export const SpeakerIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" />
    <path d="M15.5 9a4 4 0 0 1 0 6" />
    <path d="M18 6.5a7.5 7.5 0 0 1 0 11" />
  </Svg>
)

export const StopIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="6.5" y="6.5" width="11" height="11" rx="2" />
  </Svg>
)

export const BackIcon = (p: IconProps) => (
  <Svg strokeWidth={2.2} {...p}>
    <path d="M15 5l-7 7 7 7" />
  </Svg>
)

export const HelpIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.6 9.4a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.2-2.4 3.7" />
    <path d="M12 17v.01" />
  </Svg>
)

export const SlidersIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 7h10" />
    <path d="M18 7h2" />
    <circle cx="16" cy="7" r="2" />
    <path d="M4 17h4" />
    <path d="M12 17h8" />
    <circle cx="10" cy="17" r="2" />
  </Svg>
)

export const ClipboardIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="7" y="4" width="10" height="4" rx="1.5" />
    <path d="M7 6H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-1" />
  </Svg>
)

export const ImageIcon = (p: IconProps) => (
  <Svg strokeWidth={1.8} {...p}>
    <rect x="3" y="5" width="18" height="14" rx="3" />
    <circle cx="9" cy="10" r="1.6" />
    <path d="M21 16l-5-5-8 8" />
  </Svg>
)

export const CheckIcon = (p: IconProps) => (
  <Svg strokeWidth={3} {...p}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </Svg>
)

export const ChevronIcon = (p: IconProps) => (
  <Svg strokeWidth={2.2} {...p}>
    <path d="M6 9l6 6 6-6" />
  </Svg>
)

export const CloseIcon = (p: IconProps) => (
  <Svg strokeWidth={2.2} {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Svg>
)

export const BookIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v15H5.5A1.5 1.5 0 0 0 4 20.5z" />
    <path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v15h5.5a1.5 1.5 0 0 1 1.5 1.5z" />
  </Svg>
)

/* Verdict shapes: each level has its own shape, not just a color. */

export const ScamShape = (p: IconProps) => (
  <Svg strokeWidth={2.3} {...p}>
    <path d="M8 3h8l5 5v8l-5 5H8l-5-5V8z" />
    <path d="M12 8v5" />
    <path d="M12 16.5v.01" />
  </Svg>
)

export const CautionShape = (p: IconProps) => (
  <Svg strokeWidth={2.3} {...p}>
    <path d="M12 3.5L21.5 20h-19z" />
    <path d="M12 10v4" />
    <path d="M12 17v.01" />
  </Svg>
)

export const SafeShape = (p: IconProps) => (
  <Svg strokeWidth={2.3} {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M8 12.5l2.8 2.8L16.5 9.5" />
  </Svg>
)

export const UnknownShape = (p: IconProps) => (
  <Svg strokeWidth={2.2} {...p}>
    <circle cx="12" cy="12" r="9" strokeDasharray="3 3.2" />
    <path d="M9.6 9.4a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.2-2.4 3.7" />
    <path d="M12 17v.01" />
  </Svg>
)
