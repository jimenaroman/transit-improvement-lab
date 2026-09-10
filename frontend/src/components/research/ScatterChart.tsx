import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { colorForGroup } from './chart-colors'

export interface ScatterPoint {
  id: number
  group: string
  label: string
  x: number
  y: number
}

interface ScatterChartProps {
  points: ScatterPoint[]
  xAxisLabel: string
  yAxisLabel: string
  formatX: (value: number) => string
  formatY: (value: number) => string
}

const WIDTH = 600
const HEIGHT = 320
const MARGIN = { top: 16, right: 16, bottom: 40, left: 48 }
const PLOT_WIDTH = WIDTH - MARGIN.left - MARGIN.right
const PLOT_HEIGHT = HEIGHT - MARGIN.top - MARGIN.bottom

function niceRange(values: number[]): [number, number] {
  const min = Math.min(...values)
  const max = Math.min(...values) === Math.max(...values) ? Math.min(...values) + 1 : Math.max(...values)
  const padding = (max - min) * 0.15 || 1
  return [Math.max(0, min - padding), max + padding]
}

export function ScatterChart({ points, xAxisLabel, yAxisLabel, formatX, formatY }: ScatterChartProps) {
  const [hoveredId, setHoveredId] = useState<number | null>(null)
  const navigate = useNavigate()

  if (points.length === 0) return null

  const [xMin, xMax] = niceRange(points.map((p) => p.x))
  const [yMin, yMax] = niceRange(points.map((p) => p.y))
  const groups = points.map((p) => p.group)

  function toPx(x: number, y: number) {
    const px = MARGIN.left + ((x - xMin) / (xMax - xMin)) * PLOT_WIDTH
    const py = MARGIN.top + PLOT_HEIGHT - ((y - yMin) / (yMax - yMin)) * PLOT_HEIGHT
    return { px, py }
  }

  const xTicks = [xMin, (xMin + xMax) / 2, xMax]
  const yTicks = [yMin, (yMin + yMax) / 2, yMax]
  const hovered = points.find((p) => p.id === hoveredId) ?? null
  const hoveredPx = hovered ? toPx(hovered.x, hovered.y) : null

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" role="img" aria-label={`${yAxisLabel} vs ${xAxisLabel} scatter plot`}>
        {yTicks.map((tick) => {
          const { py } = toPx(xMin, tick)
          return (
            <g key={`y-${tick}`}>
              <line x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={py} y2={py} stroke="var(--border)" strokeWidth={1} />
              <text x={MARGIN.left - 6} y={py} textAnchor="end" dominantBaseline="middle" fontSize={10} fill="var(--neutral-700)" fontFamily="var(--font-mono)">
                {formatY(tick)}
              </text>
            </g>
          )
        })}
        {xTicks.map((tick, index) => {
          const { px } = toPx(tick, yMin)
          const textAnchor = index === 0 ? 'start' : index === xTicks.length - 1 ? 'end' : 'middle'
          return (
            <text key={`x-${tick}`} x={px} y={HEIGHT - MARGIN.bottom + 18} textAnchor={textAnchor} fontSize={10} fill="var(--neutral-700)" fontFamily="var(--font-mono)">
              {formatX(tick)}
            </text>
          )
        })}
        <line x1={MARGIN.left} x2={MARGIN.left} y1={MARGIN.top} y2={HEIGHT - MARGIN.bottom} stroke="var(--neutral-700)" strokeWidth={1} />
        <line x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={HEIGHT - MARGIN.bottom} y2={HEIGHT - MARGIN.bottom} stroke="var(--neutral-700)" strokeWidth={1} />
        <text x={(MARGIN.left + WIDTH - MARGIN.right) / 2} y={HEIGHT - 4} textAnchor="middle" fontSize={11} fill="var(--neutral-600)" fontFamily="var(--font-mono)">
          {xAxisLabel}
        </text>
        <text
          x={-(MARGIN.top + PLOT_HEIGHT / 2)}
          y={12}
          textAnchor="middle"
          fontSize={11}
          fill="var(--neutral-600)"
          fontFamily="var(--font-mono)"
          transform="rotate(-90)"
        >
          {yAxisLabel}
        </text>
        {points.map((point) => {
          const { px, py } = toPx(point.x, point.y)
          const color = colorForGroup(point.group, groups)
          return (
            <circle
              key={point.id}
              cx={px}
              cy={py}
              r={hoveredId === point.id ? 8 : 6}
              fill={color}
              stroke="var(--card)"
              strokeWidth={1.5}
              className="cursor-pointer transition-[r]"
              tabIndex={0}
              role="button"
              aria-label={`${point.label}, ${point.group}: ${xAxisLabel} ${formatX(point.x)}, ${yAxisLabel} ${formatY(point.y)}`}
              onMouseEnter={() => setHoveredId(point.id)}
              onMouseLeave={() => setHoveredId(null)}
              onFocus={() => setHoveredId(point.id)}
              onBlur={() => setHoveredId(null)}
              onClick={() => navigate(`/analyze-trip?routeId=${point.id}`)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') navigate(`/analyze-trip?routeId=${point.id}`)
              }}
            >
              <title>{`${point.label} (${point.group})\n${xAxisLabel}: ${formatX(point.x)}\n${yAxisLabel}: ${formatY(point.y)}`}</title>
            </circle>
          )
        })}
      </svg>

      {hovered && hoveredPx && (
        <div
          className="pointer-events-none absolute z-10 flex flex-col gap-0.5 rounded-[6px] border border-border bg-popover px-2.5 py-2 text-[11px] text-popover-foreground shadow-lg"
          style={{
            left: `${(hoveredPx.px / WIDTH) * 100}%`,
            top: `${(hoveredPx.py / HEIGHT) * 100}%`,
            transform: 'translate(-50%, -115%)',
          }}
        >
          <span className="font-semibold">{hovered.label}</span>
          <span className="text-(--neutral-600)">{hovered.group}</span>
          <span className="font-mono">
            {xAxisLabel}: {formatX(hovered.x)}
          </span>
          <span className="font-mono">
            {yAxisLabel}: {formatY(hovered.y)}
          </span>
        </div>
      )}
    </div>
  )
}
