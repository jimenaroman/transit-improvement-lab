import { Link } from 'react-router-dom'

export interface HorizontalBarItem {
  key: string
  label: string
  sublabel?: string
  value: number
  color: string
  href?: string
}

interface HorizontalBarListProps {
  items: HorizontalBarItem[]
  formatValue: (value: number) => string
  showRank?: boolean
}

export function HorizontalBarList({ items, formatValue, showRank }: HorizontalBarListProps) {
  if (items.length === 0) return null

  const maxValue = Math.max(...items.map((item) => item.value)) || 1

  return (
    <div className="flex flex-col gap-3">
      {items.map((item, index) => {
        const row = (
          <div className="flex items-center gap-3">
            {showRank && (
              <span className="w-4 shrink-0 font-mono text-[11px] text-(--neutral-700)">{index + 1}</span>
            )}
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-[13px] text-(--neutral-300)">{item.label}</span>
                <span className="shrink-0 font-mono text-[13px] font-semibold text-(--neutral-200)">
                  {formatValue(item.value)}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${(item.value / maxValue) * 100}%`, backgroundColor: item.color }}
                />
              </div>
              {item.sublabel && <span className="text-[11px] text-(--neutral-700)">{item.sublabel}</span>}
            </div>
          </div>
        )

        return item.href ? (
          <Link key={item.key} to={item.href} className="rounded-[6px] transition-colors hover:bg-muted/60">
            {row}
          </Link>
        ) : (
          <div key={item.key}>{row}</div>
        )
      })}
    </div>
  )
}
