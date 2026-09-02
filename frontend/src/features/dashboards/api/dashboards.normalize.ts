import type { Dashboard, LayoutItem, Panel } from '@/types'

/**
 * Normalizacion del recurso «panel» tal y como lo devuelve el servidor a la forma que consume la
 * aplicacion. El servidor entrega la misma informacion bajo nombres distintos segun el despliegue
 * (la lista de entidades, el tipo de plantilla, la rejilla responsive), asi que aqui se reduce a
 * una unica forma estable antes de que la vea el resto del codigo.
 */

const LAYOUT_KEYS = ['lg', 'md', 'sm', 'xs', 'xxs']

export interface RawDashboard {
  id?: number | string
  name?: string
  description?: string | null
  slug?: string | null
  timezone?: string | null
  layout?: unknown
  responsiveLayout?: unknown
  templateDrawer?: unknown
  panels?: unknown
  entities?: unknown
  templateEntities?: unknown
  template_entities?: unknown
}

export interface DashboardDetail extends Dashboard {
  /** Entidades asignadas a la plantilla, si el servidor las declara. */
  templateEntityIds: number[]
  /** false = el servidor no informa de la asignacion; no equivale a «no hay ninguna». */
  templateEntitiesKnown: boolean
}

/** Los identificadores de entidad llegan como numeros o como objetos, y bajo cuatro nombres distintos. */
function readTemplateEntities(raw: RawDashboard): { ids: number[]; known: boolean } {
  const drawer = raw.templateDrawer && typeof raw.templateDrawer === 'object'
    ? (raw.templateDrawer as Record<string, unknown>).entities
    : undefined
  const sources = [raw.entities, raw.templateEntities, raw.template_entities, drawer]
  const found = sources.find((value) => Array.isArray(value))
  if (!Array.isArray(found)) return { ids: [], known: false }

  const ids = found
    .map((item) => {
      if (typeof item === 'number' || typeof item === 'string') return Number(item)
      if (item && typeof item === 'object') return Number((item as Record<string, unknown>).id)
      return Number.NaN
    })
    .filter((id) => Number.isFinite(id) && id > 0)

  return { ids: [...new Set(ids)], known: true }
}

function normalizeLayout(raw: unknown): Record<string, LayoutItem[]> | undefined {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return undefined
  const source = raw as Record<string, unknown>
  const layout: Record<string, LayoutItem[]> = {}

  for (const key of LAYOUT_KEYS) {
    const items = source[key]
    if (!Array.isArray(items)) continue
    layout[key] = items
      .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
      .map((item) => ({
        i: (item.i as string | number | undefined) ?? '',
        x: Number(item.x) || 0,
        y: Number(item.y) || 0,
        w: Number(item.w) || 0,
        h: Number(item.h) || 0,
      }))
  }

  return Object.keys(layout).length ? layout : undefined
}

/** El tipo de plantilla llega unas veces como cadena y otras envuelto en un objeto. */
function normalizeTemplateType(raw: unknown): string | null {
  if (typeof raw === 'string') return raw || null
  if (raw && typeof raw === 'object') {
    const type = (raw as Record<string, unknown>).type
    if (typeof type === 'string') return type || null
  }
  return null
}

export function normalizeDashboard(raw: RawDashboard): DashboardDetail {
  const entities = readTemplateEntities(raw)
  return {
    id: Number(raw.id ?? 0),
    name: raw.name ?? '',
    description: raw.description ?? undefined,
    slug: raw.slug ?? undefined,
    timezone: raw.timezone ?? undefined,
    templateType: normalizeTemplateType(raw.templateDrawer),
    panels: Array.isArray(raw.panels) ? (raw.panels as Panel[]) : [],
    responsiveLayout: normalizeLayout(raw.layout ?? raw.responsiveLayout),
    templateEntityIds: entities.ids,
    templateEntitiesKnown: entities.known,
  }
}
