import { http } from '@/api/http'
import { urnTail } from '@/lib/format'
import type { EntityRef, Measure } from '@/types'

/** Lo minimo que necesita el area: identificar la entidad y poder pedirle datos. */
export interface EntityOption {
  id: number
  name: string
  urn: string
  tenant: string
  scope: string
  datamodel: string
}

const MEASURE_TYPES = 'Property'

export interface EntitySearch {
  search?: string
  /** Modelos de datos por los que acotar; se leen del descriptor de la plantilla. */
  datamodels?: string[]
  /** Pagina a pedir, empezando en 1. */
  page?: number
  limit?: number
}

/** Se devuelve tambien el total para poder saber si queda mas por traer. */
export interface EntityPage {
  rows: EntityOption[]
  count: number
}

interface RawEntity {
  id?: number | string
  name?: string | null
  urn?: string
  tenant?: string
  scope?: string
  datamodel?: string
}

export async function searchEntities(query: EntitySearch): Promise<EntityPage> {
  const { data } = await http.post<{ rows?: RawEntity[]; count?: number }>('/entities/paginate', {
    page: query.page ?? 1,
    paginationSize: query.limit ?? 25,
    ...(query.search?.trim() ? { search: query.search.trim() } : {}),
    ...(query.datamodels?.length ? { types: query.datamodels.join(',') } : {}),
  })

  const rows = (data?.rows ?? [])
    .filter((row): row is RawEntity & { urn: string } => !!row?.urn)
    .map((row) => ({
      id: Number(row.id ?? 0),
      name: row.name?.trim() || urnTail(row.urn),
      urn: row.urn,
      tenant: row.tenant ?? '',
      scope: row.scope ?? '',
      datamodel: row.datamodel ?? '',
    }))
    .filter((option) => option.id > 0 && !!option.tenant && !!option.scope)

  return { rows, count: Number(data?.count) || 0 }
}

interface RawMeasure {
  id?: string
  name?: string
  units?: string | null
  value_type?: string
  timestamp?: string | null
  internal?: boolean | string
}

/**
 * El servidor exige tenant y scope en CABECERAS (no en la query) y puede devolver la misma
 * medida repetida: se conserva la lectura mas reciente de cada identificador.
 */
export async function listMeasures(ref: EntityRef): Promise<Measure[]> {
  const { data } = await http.get<RawMeasure[]>(`/realtime/entities/${ref.urn}`, {
    headers: { tenant: ref.tenant, scope: ref.scope },
    params: { referenceDataNesting: 0, attrTypeFilter: MEASURE_TYPES },
  })

  const byId = new Map<string, Measure>()
  for (const raw of data ?? []) {
    if (!raw?.id || raw.internal === true || raw.internal === 'true') continue
    const measure: Measure = {
      id: String(raw.id),
      name: raw.name?.trim() || String(raw.id),
      units: raw.units?.trim() || undefined,
      value_type: raw.value_type,
      timestamp: raw.timestamp ?? undefined,
    }
    const current = byId.get(measure.id)
    if (!current || (measure.timestamp ?? '') > (current.timestamp ?? '')) byId.set(measure.id, measure)
  }

  return [...byId.values()].sort((a, b) => a.name.localeCompare(b.name, 'es'))
}
