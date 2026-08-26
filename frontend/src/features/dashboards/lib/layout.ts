import type { LayoutItem, Panel } from '@/types'

export type LayoutBreakpoint = 'lg' | 'md' | 'sm' | 'xs' | 'xxs'

/**
 * La rejilla persistida no usa 12 columnas en todos los tamanos: cada punto de ruptura
 * tiene el suyo. Se reescala todo a 12 para poder pintarlo con la rejilla de la interfaz.
 */
const COLUMNS: Record<LayoutBreakpoint, number> = { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }

/** Altura de una fila de la rejilla original, en pixeles. */
const ROW_HEIGHT = 30
const MIN_HEIGHT = 220
const DEFAULT_SPAN = 6
const DEFAULT_ROWS = 10
const TOTAL_COLUMNS = 12

export interface PanelPlacement {
  key: string
  panel: Panel
  /** Columnas que ocupa sobre 12. */
  span: number
  offset: number
  /** Altura del contenido en pixeles. */
  height: number
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

const rescale = (value: number, columns: number) =>
  columns === TOTAL_COLUMNS ? Math.round(value) : Math.round((value * TOTAL_COLUMNS) / columns)

const heightOf = (rows?: number) => Math.max(MIN_HEIGHT, (rows || DEFAULT_ROWS) * ROW_HEIGHT)

interface PickedLayout {
  items: LayoutItem[]
  columns: number
}

/** Un dashboard puede no tener guardado el tamano pedido; se cae al mas parecido que exista. */
function pickLayout(
  layout: Record<string, LayoutItem[]> | undefined,
  breakpoint: LayoutBreakpoint,
): PickedLayout | null {
  if (!layout) return null
  const candidates: LayoutBreakpoint[] = [breakpoint, 'lg', 'md', 'sm', 'xs', 'xxs']
  for (const candidate of candidates) {
    const items = layout[candidate]
    if (Array.isArray(items) && items.length) return { items, columns: COLUMNS[candidate] }
  }
  return null
}

export function placePanels(
  panels: Panel[],
  layout: Record<string, LayoutItem[]> | undefined,
  breakpoint: LayoutBreakpoint,
): PanelPlacement[] {
  const pending = new Map(panels.map((panel) => [String(panel.id), panel]))
  const placements: PanelPlacement[] = []
  const picked = pickLayout(layout, breakpoint)

  if (picked) {
    const ordered = picked.items
      .filter((item) => pending.has(String(item.i)))
      .slice()
      .sort((a, b) => a.y - b.y || a.x - b.x)

    let band = Number.NaN
    let used = 0

    for (const item of ordered) {
      const id = String(item.i)
      const panel = pending.get(id)
      if (!panel) continue
      pending.delete(id)

      const span = clamp(rescale(item.w || DEFAULT_SPAN, picked.columns), 1, TOTAL_COLUMNS)
      const start = clamp(rescale(item.x, picked.columns), 0, TOTAL_COLUMNS - 1)

      if (item.y !== band) {
        band = item.y
        used = 0
      }

      let offset = Math.max(0, start - used)
      if (used + offset + span > TOTAL_COLUMNS) {
        offset = 0
        used = 0
      }
      used += offset + span

      placements.push({ key: id, panel, span, offset, height: heightOf(item.h) })
    }
  }

  for (const panel of pending.values()) {
    placements.push({
      key: String(panel.id),
      panel,
      span: DEFAULT_SPAN,
      offset: 0,
      height: heightOf(),
    })
  }

  return placements
}
