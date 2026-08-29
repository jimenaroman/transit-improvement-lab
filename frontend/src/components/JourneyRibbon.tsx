interface JourneyRibbonProps {
  drivingMinutes: number
  transitMinutes: number
  walkingMinutes: number
  waitTransferMinutes: number
}

export function JourneyRibbon({
  drivingMinutes,
  transitMinutes,
  walkingMinutes,
  waitTransferMinutes,
}: JourneyRibbonProps) {
  const rideMinutes = Math.max(transitMinutes - walkingMinutes - waitTransferMinutes, 0)
  const maxMinutes = Math.max(drivingMinutes, transitMinutes, 1)

  const drivePct = (drivingMinutes / maxMinutes) * 100
  const walkPct = (walkingMinutes / maxMinutes) * 100
  const waitPct = (waitTransferMinutes / maxMinutes) * 100
  const ridePct = (rideMinutes / maxMinutes) * 100

  const ticks = [0, 0.25, 0.5, 0.75].map((fraction) => Math.round(maxMinutes * fraction))

  return (
    <div className="grid grid-cols-[56px_1fr_48px] items-center gap-3 sm:grid-cols-[70px_1fr_52px]">
      <div className="font-mono text-[11px] font-medium text-(--neutral-500)">DRIVE</div>
      <div className="h-8 overflow-hidden rounded-md bg-white/4">
        <div
          className="flex h-full items-center bg-(--transit-drive) pl-3 font-sans text-[11px] font-medium text-(--neutral-100)"
          style={{ width: `${drivePct}%` }}
        >
          {drivingMinutes} min
        </div>
      </div>
      <div className="text-right font-mono text-sm font-semibold text-(--neutral-300)">{drivingMinutes}m</div>

      <div className="font-mono text-[11px] font-medium text-primary">TRANSIT</div>
      <div className="flex h-8 gap-0.5 overflow-hidden rounded-md">
        {walkPct > 0 && (
          <div
            className="flex items-center justify-center bg-(--transit-walk) font-sans text-[10px] font-medium text-(--neutral-100)"
            style={{ width: `${walkPct}%` }}
          >
            {walkPct > 8 ? `Walk ${walkingMinutes}` : ''}
          </div>
        )}
        {waitPct > 0 && (
          <div
            className="flex items-center justify-center bg-(--transit-wait) font-sans text-[10px] font-semibold text-[#241a05]"
            style={{ width: `${waitPct}%` }}
          >
            {waitPct > 8 ? `Wait ${waitTransferMinutes}` : ''}
          </div>
        )}
        {ridePct > 0 && (
          <div
            className="flex items-center justify-center bg-primary font-sans text-[10px] font-semibold text-primary-foreground"
            style={{ width: `${ridePct}%` }}
          >
            {ridePct > 8 ? `Ride ${rideMinutes}` : ''}
          </div>
        )}
      </div>
      <div className="text-right font-mono text-sm font-semibold text-primary">{transitMinutes}m</div>

      <div />
      <div className="flex justify-between border-t border-border pt-1.5 font-mono text-[10px] text-(--neutral-800)">
        {ticks.map((tick) => (
          <span key={tick}>{tick}</span>
        ))}
        <span>{maxMinutes} min</span>
      </div>
      <div />
    </div>
  )
}
