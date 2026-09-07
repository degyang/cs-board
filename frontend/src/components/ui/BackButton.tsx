import { Link } from 'react-router-dom'

interface BackButtonProps {
  to: string
  label: string
}

export function BackButton({ to, label }: BackButtonProps) {
  return (
    <Link to={to} className="back-btn" title={label}>
      <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M10 3.5 5.5 8l4.5 4.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {label}
    </Link>
  )
}
