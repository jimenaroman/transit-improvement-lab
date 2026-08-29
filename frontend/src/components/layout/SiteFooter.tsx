import { Link } from 'react-router-dom'

interface SiteFooterProps {
  note: string
  maxWidthClassName?: string
}

export function SiteFooter({ note, maxWidthClassName = 'max-w-[1180px]' }: SiteFooterProps) {
  return (
    <footer className="mt-9 border-t border-border px-5 py-8 sm:px-14">
      <div className={`mx-auto flex flex-wrap items-center justify-between gap-3.5 ${maxWidthClassName}`}>
        <div className="font-mono text-xs text-(--neutral-800)">{note}</div>
        <div className="flex gap-5">
          <Link to="/" className="font-sans text-xs font-medium text-(--neutral-500) hover:text-foreground">
            Home
          </Link>
          <Link to="/analyze-trip" className="font-sans text-xs font-medium text-(--neutral-500) hover:text-foreground">
            Analyze Trip
          </Link>
          <Link to="/research" className="font-sans text-xs font-medium text-(--neutral-500) hover:text-foreground">
            Research
          </Link>
          <Link to="/methodology" className="font-sans text-xs font-medium text-(--neutral-500) hover:text-foreground">
            Methodology
          </Link>
        </div>
      </div>
    </footer>
  )
}
