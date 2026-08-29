import { SiteFooter } from '@/components/layout/SiteFooter'

const SECTIONS = [
  { id: 'gtfs', label: 'What GTFS is' },
  { id: 'service-date', label: 'Filtering service by date' },
  { id: 'calendar', label: 'Holidays and calendar exceptions' },
  { id: 'headway', label: 'Calculating headways' },
  { id: 'scenarios', label: 'Linking scenarios to routes' },
  { id: 'unlinked', label: 'Why some scenarios are unlinked' },
  { id: 'limits', label: 'Limitations' },
  { id: 'future', label: 'Planned work' },
]

const FREQUENCY_CLASSES = [
  { name: 'Frequent', range: 'headway ≤ 15 min', tone: 'border-primary/35 bg-primary/6 text-primary' },
  { name: 'Moderate', range: '16 – 30 min', tone: 'border-border text-(--neutral-200)' },
  { name: 'Infrequent', range: '> 30 min', tone: 'border-accent/35 bg-accent/6 text-accent' },
]

const LIMITATIONS = [
  { label: 'Schedule', body: 'Published times, as published. No delays, bunching, or cancellations.' },
  { label: 'Driving', body: 'Fixed per scenario. No traffic, no time of day.' },
  { label: 'Coverage', body: 'Curated scenarios only. Not a citywide accessibility measure.' },
  { label: 'Wait model', body: 'Derived from average headway, which understates irregular service.' },
]

const PLANNED = [
  {
    title: 'Full GTFS ingestion for DART and CTA',
    body: 'The scheduled service shown today comes from a manually verified route link per scenario. Full static GTFS ingestion for both agencies is designed but not yet built — see the GTFS integration plan.',
  },
  {
    title: 'Real-time service',
    body: 'Schedule against observed service, to show reliability and not just frequency.',
  },
  {
    title: 'Route geometry',
    body: 'A map panel drawn from GTFS shapes and stops, with real route length.',
  },
]

export default function Methodology() {
  return (
    <>
      <div className="mx-auto flex max-w-[1180px] flex-col gap-9 px-5 pt-10 sm:gap-11 sm:px-14 sm:pt-14">
        <div className="flex flex-col gap-3.5">
          <div className="font-mono text-[11px] font-medium tracking-[.14em] text-primary uppercase">
            Methodology
          </div>
          <h1 className="max-w-[760px] text-3xl leading-tight font-semibold tracking-tight text-balance text-foreground sm:text-4xl">
            How scheduled service becomes a travel-time comparison
          </h1>
          <p className="max-w-[640px] text-[15px] leading-relaxed text-(--neutral-500)">
            Every number traces back to a published schedule and a curated trip. What follows is what gets computed,
            what gets assumed, and what is not claimed.
          </p>
        </div>

        <div className="grid items-start gap-7 sm:grid-cols-[260px_1fr] sm:gap-9">
          <aside className="flex flex-col gap-2.5 rounded-[9px] border border-border p-5">
            <div className="font-mono text-[10px] font-medium tracking-[.12em] text-(--neutral-700) uppercase">
              On this page
            </div>
            {SECTIONS.map((section) => (
              <a
                key={section.id}
                href={`#${section.id}`}
                className="border-l-2 border-transparent pl-0 text-[13px] text-(--neutral-300) transition-all hover:border-primary hover:pl-2.5 hover:font-semibold hover:text-foreground"
              >
                {section.label}
              </a>
            ))}
          </aside>

          <div className="flex min-w-0 flex-col gap-9">
            <section id="gtfs" className="scroll-mt-28">
              <h2 className="mb-2.5 text-xl leading-tight font-semibold tracking-tight text-foreground">
                What GTFS is
              </h2>
              <p className="max-w-[680px] text-[15px] leading-relaxed text-(--neutral-500)">
                The standard format agencies publish timetables in: routes, trips, stop times, and a calendar of
                which days each trip runs. A schedule, not a sensor feed. Every service figure in the app comes from
                these files.
              </p>
            </section>

            <section id="service-date" className="scroll-mt-28">
              <h2 className="mb-2.5 text-xl leading-tight font-semibold tracking-tight text-foreground">
                Filtering service by date
              </h2>
              <p className="max-w-[680px] text-[15px] leading-relaxed text-(--neutral-500)">
                A route has several schedules, one per service day. The app resolves a date — the current date in the
                agency's own timezone by default — keeps the service IDs active on it, then keeps only their trips.
              </p>
            </section>

            <section id="calendar" className="scroll-mt-28">
              <h2 className="mb-2.5 text-xl leading-tight font-semibold tracking-tight text-foreground">
                Holidays and calendar exceptions
              </h2>
              <p className="max-w-[680px] text-[15px] leading-relaxed text-(--neutral-500)">
                Holidays arrive as exceptions: a service removed for one date, or a special one added. Exceptions
                apply after the weekly pattern and override it, so a holiday uses the reduced service the agency
                published, not an ordinary weekday.
              </p>
            </section>

            <section id="headway" className="scroll-mt-28">
              <h2 className="mb-3 text-xl leading-tight font-semibold tracking-tight text-foreground">
                Calculating headways
              </h2>
              <p className="mb-3.5 max-w-[680px] text-[15px] leading-relaxed text-(--neutral-500)">
                Sort the active departures, measure the gaps between them, average the gaps. Span is first departure
                to last. Frequency class is a threshold on the average — a convention widely used across US transit
                agencies, not derived from this app's own data.
              </p>
              <div className="mb-3.5 grid max-w-[680px] gap-3 sm:grid-cols-3">
                {FREQUENCY_CLASSES.map((tier) => (
                  <div key={tier.name} className={`rounded-lg border px-4 py-3.5 ${tier.tone}`}>
                    <div className="mb-2 text-[13px] font-semibold">{tier.name}</div>
                    <div className="font-mono text-xs font-medium text-(--neutral-300)">{tier.range}</div>
                  </div>
                ))}
              </div>
              <p className="max-w-[680px] text-sm leading-relaxed text-(--neutral-600)">
                Expected wait comes from that average, so the simulated improvement moves the trip time by shortening
                the wait and nothing else. Separate peak, midday, and evening headways are also computed for the
                07:00–09:00 and 16:00–18:00, 09:00–15:00, and 18:00–22:00 windows.
              </p>
            </section>

            <section id="scenarios" className="scroll-mt-28">
              <h2 className="mb-2.5 text-xl leading-tight font-semibold tracking-tight text-foreground">
                Linking curated scenarios to GTFS routes
              </h2>
              <p className="max-w-[680px] text-[15px] leading-relaxed text-(--neutral-500)">
                Trips are a curated set of origin and destination pairs, not arbitrary address routing. Each one is
                manually tied to the route that serves it, and that link is checked against the feed before any
                service data appears. Honest, but limited to trips someone has verified.
              </p>
            </section>

            <section id="unlinked" className="scroll-mt-28">
              <h2 className="mb-2.5 text-xl leading-tight font-semibold tracking-tight text-foreground">
                Why some scenarios are intentionally unlinked
              </h2>
              <p className="mb-3.5 max-w-[680px] text-[15px] leading-relaxed text-(--neutral-500)">
                Some trips have no single route that plausibly serves them, or the match could not be verified. They
                stay in the set with an empty service state instead of a guess: times still compare, service quality
                and the improvement do not.
              </p>
              <div className="flex max-w-[680px] flex-col gap-1.5 rounded-lg border border-dashed border-border px-4.5 py-4">
                <div className="font-mono text-[10px] font-medium tracking-[.12em] text-(--neutral-700) uppercase">
                  Empty state
                </div>
                <div className="text-sm font-medium text-(--neutral-300)">
                  No verified GTFS association for this scenario.
                </div>
              </div>
            </section>

            <section id="limits" className="scroll-mt-28">
              <h2 className="mb-3 text-xl leading-tight font-semibold tracking-tight text-foreground">
                Limitations
              </h2>
              <div className="flex max-w-[680px] flex-col">
                {LIMITATIONS.map((item) => (
                  <div key={item.label} className="flex gap-3.5 border-b border-border py-3 last:border-b-0">
                    <span className="min-w-[74px] font-mono text-xs leading-relaxed font-medium text-accent">
                      {item.label}
                    </span>
                    <span className="text-sm leading-relaxed text-(--neutral-500)">{item.body}</span>
                  </div>
                ))}
              </div>
            </section>

            <section id="future" className="scroll-mt-28">
              <h2 className="mb-3 text-xl leading-tight font-semibold tracking-tight text-foreground">
                Planned work
              </h2>
              <div className="grid max-w-[680px] gap-3.5 sm:grid-cols-2">
                {PLANNED.map((item) => (
                  <div key={item.title} className="flex flex-col gap-2 border-t-2 border-white/16 pt-3.5">
                    <div className="text-sm font-semibold text-(--neutral-200)">{item.title}</div>
                    <p className="text-[13px] leading-relaxed text-(--neutral-600)">{item.body}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>

      <SiteFooter note="Scheduled GTFS only · no real-time vehicle data" />
    </>
  )
}
