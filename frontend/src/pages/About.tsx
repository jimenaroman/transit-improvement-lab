import { Link } from 'react-router-dom'
import { buttonVariants } from '@/components/ui/button'
import { SiteFooter } from '@/components/layout/SiteFooter'

const QUESTIONS = [
  'How much longer does public transit take compared with driving?',
  'How much time is lost to waiting, walking, and transfers?',
  'Which service improvements would reduce commute burden the most?',
  'How do Dallas and Chicago differ across similar trip types?',
]

const FEATURES = [
  {
    accent: 'var(--primary)',
    title: 'Scenario search and analysis',
    body: 'Curated route scenarios across Dallas and Chicago, filtered by city, origin, or destination, then analyzed on demand.',
  },
  {
    accent: 'var(--accent)',
    title: 'Transit penalty',
    body: 'Transit time divided by driving time, plus a 0–100 car dependency score and a weekly extra-time estimate.',
  },
  {
    accent: 'var(--transit-drive)',
    title: 'Emissions comparison',
    body: 'Driving against transit for the same trip.',
  },
  {
    accent: 'rgba(255,255,255,.2)',
    title: 'Scheduled-service dashboard',
    body: 'Aggregate view across every scenario: average transit penalty, worst routes, and route counts by city and category.',
  },
]

const STACK = [
  { label: 'Frontend', value: 'React · TypeScript · Vite · Tailwind · shadcn/ui' },
  { label: 'Backend', value: 'FastAPI · Python' },
  { label: 'Database', value: 'SQLite' },
  { label: 'Testing', value: 'Pytest · ESLint · tsc' },
]

const ROADMAP = [
  {
    status: 'DONE',
    color: 'text-primary',
    body: 'API with route, comparison, and dashboard-summary endpoints, the search → select → analyze flow, SQLite data layer, curated route scenarios, and a manually verified GTFS link per scenario.',
  },
  {
    status: 'V1',
    color: 'text-accent',
    body: 'This visual refresh — shared navigation, the journey-time ribbon, and scheduled-service detail (headway, frequency, service span) surfaced per route.',
  },
  {
    status: 'V2',
    color: 'text-(--neutral-700)',
    body: 'Full DART and CTA GTFS ingestion, then external route/search API integration.',
  },
]

export default function About() {
  return (
    <>
      <div className="mx-auto flex max-w-[1100px] flex-col gap-9 px-5 pt-10 sm:gap-11 sm:px-14 sm:pt-14">
        <div className="flex flex-col gap-4">
          <div className="font-mono text-[11px] font-medium tracking-[.14em] text-primary uppercase">
            About the project
          </div>
          <blockquote className="flex max-w-[820px] flex-col gap-3.5 border-l-2 border-primary pl-5 sm:pl-6">
            <div className="text-3xl leading-tight font-normal tracking-tight text-balance text-foreground sm:text-4xl">
              "Frequency is freedom."
            </div>
            <div className="font-mono text-xs font-medium tracking-wide text-primary">
              Jarrett Walker, transit planner and author of Human Transit
            </div>
          </blockquote>
        </div>

        <div className="grid items-start gap-8 sm:grid-cols-2 sm:gap-11">
          <div className="flex flex-col gap-3.5">
            <h2 className="text-xl leading-tight font-semibold tracking-tight text-foreground">
              Why I'm building this
            </h2>
            <p className="text-[15px] leading-relaxed text-(--neutral-500)">
              I grew up in the Dallas area, where public transit often felt limited to special trips — going to the
              Texas State Fair — rather than everyday mobility. After living in Chicago, where I could use buses and
              trains to go downtown, cross the city, and reach the airport, I wanted to better reason about what
              makes transit usable in one place and difficult in another.
            </p>
          </div>
          <div className="flex flex-col gap-3.5">
            <div className="font-mono text-[11px] font-medium tracking-[.14em] text-(--neutral-700) uppercase">
              The questions it asks
            </div>
            <div className="flex flex-col">
              {QUESTIONS.map((question) => (
                <div key={question} className="border-t border-border py-3 text-sm leading-relaxed text-(--neutral-300)">
                  {question}
                </div>
              ))}
            </div>
          </div>
        </div>

        <section className="flex flex-col gap-4.5">
          <h2 className="text-xl leading-tight font-semibold tracking-tight text-foreground">What it does today</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((feature) => (
              <div key={feature.title} className="flex flex-col gap-2 border-t-2 pt-3.5" style={{ borderTopColor: feature.accent }}>
                <div className="text-sm font-semibold text-(--neutral-200)">{feature.title}</div>
                <p className="text-[13px] leading-relaxed text-(--neutral-600)">{feature.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="flex flex-col gap-2.5 rounded-[9px] border border-accent/35 bg-accent/7 p-5.5">
          <div className="font-mono text-[10px] font-medium tracking-[.12em] text-accent uppercase">
            Data and accuracy
          </div>
          <p className="max-w-[760px] text-[15px] leading-relaxed text-(--neutral-300)">
            Distances, drive and transit times, fares, and emissions are manually estimated for V1 — not sourced from
            an official transit API. They exist to test the data flow and UI end to end before real transit data is
            integrated. Every route's notes field says so:{' '}
            <span className="font-mono text-[13px] text-accent">
              Manual V1 sample estimate; verify before research use.
            </span>
          </p>
        </section>

        <div className="grid items-start gap-8 sm:grid-cols-2 sm:gap-11">
          <section className="flex flex-col gap-3.5">
            <h2 className="text-xl leading-tight font-semibold tracking-tight text-foreground">Stack</h2>
            <div className="flex flex-col">
              {STACK.map((row) => (
                <div key={row.label} className="flex justify-between gap-4 border-b border-border py-2.5 last:border-b-0">
                  <span className="text-[13px] text-(--neutral-500)">{row.label}</span>
                  <span className="text-right font-mono text-xs font-medium text-(--neutral-300)">{row.value}</span>
                </div>
              ))}
            </div>
          </section>
          <section className="flex flex-col gap-3.5">
            <h2 className="text-xl leading-tight font-semibold tracking-tight text-foreground">Roadmap</h2>
            <div className="flex flex-col gap-3">
              {ROADMAP.map((item) => (
                <div key={item.status} className="flex gap-3">
                  <span className={`min-w-[46px] font-mono text-[11px] leading-relaxed font-medium ${item.color}`}>
                    {item.status}
                  </span>
                  <span className="text-[13px] leading-relaxed text-(--neutral-500)">{item.body}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="flex flex-wrap gap-3 pb-2">
          <Link to="/analyze-trip" className={buttonVariants({ size: 'lg', className: 'h-auto px-6 py-3.5 text-sm font-semibold' })}>
            Analyze a trip
          </Link>
          <Link
            to="/methodology"
            className={buttonVariants({
              variant: 'outline',
              size: 'lg',
              className: 'h-auto px-6 py-3.5 text-sm font-semibold text-(--neutral-300)',
            })}
          >
            How the data works
          </Link>
        </div>
      </div>

      <SiteFooter note="Personal research project · Dallas and Chicago" maxWidthClassName="max-w-[1100px]" />
    </>
  )
}
