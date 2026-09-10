// Small fixed palette for distinguishing a handful of cities/groups across
// the Research page's charts. Assigned by alphabetical city name so a given
// city always gets the same color across every chart on the page.
const PALETTE = ['var(--primary)', 'var(--accent)', 'var(--transit-walk)', 'var(--transit-drive)']

export function colorForGroup(groupName: string, allGroups: string[]): string {
  const sorted = [...new Set(allGroups)].sort()
  const index = sorted.indexOf(groupName)
  return PALETTE[index % PALETTE.length]
}
