import { NavLink } from 'react-router-dom'
import { MoonIcon, SunIcon } from 'lucide-react'
import { useTheme } from '@/lib/theme'
import { Button } from '@/components/ui/button'

const NAV_LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/about', label: 'About' },
  { to: '/analyze-trip', label: 'Analyze Trip' },
  { to: '/research', label: 'Research' },
  { to: '/methodology', label: 'Methodology' },
]

function LogoMark() {
  return (
    <svg width="26" height="12" viewBox="0 0 26 12" fill="none" className="block shrink-0">
      <line x1="3" y1="6" x2="23" y2="6" stroke="var(--primary)" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="3" cy="6" r="3.4" fill="var(--background)" stroke="var(--primary)" strokeWidth="2.5" />
      <circle cx="23" cy="6" r="3.4" fill="var(--background)" stroke="var(--primary)" strokeWidth="2.5" />
    </svg>
  )
}

export function SiteHeader() {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3.5 border-b border-border bg-background/92 px-5 py-3.5 backdrop-blur-sm sm:px-14">
      <NavLink to="/" className="flex items-center gap-2.5">
        <LogoMark />
        <span className="font-sans text-sm font-semibold tracking-tight text-foreground">
          Transit Improvement Lab
        </span>
      </NavLink>
      <nav className="flex flex-wrap items-center gap-4 sm:gap-6">
        {NAV_LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              `font-sans text-[13px] ${isActive ? 'font-semibold text-primary' : 'font-medium text-(--neutral-500)'}`
            }
          >
            {link.label}
          </NavLink>
        ))}
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          onClick={toggleTheme}
          className="text-(--neutral-500)"
        >
          {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </Button>
      </nav>
    </header>
  )
}
