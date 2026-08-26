import { http } from '@/api/http'
import { parseApiDateTime } from '@/lib/format'
import type { Entity, EntityRef, Measure, PageQuery, Paginated } from '@/types'

/** Solo las propiedades son medidas: relaciones y comandos no representan un valor observado. */
const MEASURE_TYPES = 'Property'

interface RawMeasure {
  id?: string
  name?: string
  units?: string | null
  value_type?: string
  value?: unknown
  timestamp?: string | null
  type?: string
  urn?: string
  internal?: boolean | string
}

type DatamodelRow = string | { datamodel?: string; name?: string; type?: string }

interface RawLastData {
  id?: number
  last_timestamp?: string | null
}

export async function listEntities(q: PageQuery): Promise<Paginated<Entity>> {
  const body: Record<string, unknown> = {
    page: q.page,
    paginationSize: q.paginationSize,
  }
  if (q.search) body.search = q.search
  if (q.types) body.types = q.types
  if (q.groups?.length) body.groups = q.groups.join(',')
  if (q.urn) body.urn = q.urn
  if (q.bounds) body.bounds = q.bounds
  // Un ambito sin espacio de datos es ambiguo y el servidor lo rechaza con un 400.
  if (q.tenant) {
    body.tenant = q.tenant
    if (q.scope) body.scope = q.scope
  }

  const { data } = await http.post<Paginated<Entity>>('/entities/paginate', body)
  return { count: data?.count ?? 0, rows: data?.rows ?? [] }
}

export async function getEntity(id: number | string): Promise<Entity> {
  const { data } = await http.get<Entity>(`/entities/${id}`)
  return data
}

export async function listDatamodels(search?: string): Promise<string[]> {
  const { data } = await http.post<Paginated<DatamodelRow> | DatamodelRow[]>(
    '/entities/datamodels/paginate',
    { search: search ?? '' },
  )
  const rows = Array.isArray(data) ? data : (data?.rows ?? [])
  const names = rows.map(datamodelName).filter((n): n is string => n !== null)
  return Array.from(new Set(names)).sort((a, b) => a.localeCompare(b, 'es'))
}

export async function getEntityMeasures(ref: EntityRef): Promise<Measure[]> {
  const { data } = await http.get<RawMeasure[]>(`/realtime/entities/${ref.urn}`, {
    headers: { tenant: ref.tenant, scope: ref.scope },
    params: { referenceDataNesting: 0, attrTypeFilter: MEASURE_TYPES },
  })

  const measures = (data ?? [])
    .filter((raw) => !!raw?.id && !isInternal(raw))
    .map(toMeasure)

  return dedupeLatest(measures).sort((a, b) => a.name.localeCompare(b.name, 'es'))
}

/**
 * El servidor puede devolver la misma medida repetida (una entrada por entidad referenciada),
 * lo que llena la tabla de filas identicas. Se conserva solo la lectura mas reciente de cada una.
 */
function dedupeLatest(measures: Measure[]): Measure[] {
  const byId = new Map<string, Measure>()
  for (const m of measures) {
    const current = byId.get(m.id)
    if (!current || (m.timestamp ?? '') > (current.timestamp ?? '')) byId.set(m.id, m)
  }
  return [...byId.values()]
}

/**
 * Marca temporal del ultimo dato de cada entidad, indexada por identificador interno. Se pide
 * en una sola llamada para toda la pagina de la tabla: preguntar entidad por entidad
 * multiplica la espera.
 *
 * Se pregunta por `id` y no por URN a proposito. Las alternativas que consultan el almacen de
 * datos en vivo (POST /realtime/entities y POST /realtime/entities/timeLastData) tardan cerca
 * de nueve segundos para veinticinco entidades frente a los ciento cincuenta milisegundos de
 * esta, porque descargan todas las medidas de cada entidad solo para quedarse con la mas
 * reciente. Ademas ambas reciben el espacio de datos y el ambito en las cabeceras, uno solo
 * para toda la peticion, asi que darian un resultado incorrecto en cuanto una pagina mezclase
 * entidades de ambitos distintos. Este endpoint no tiene ninguno de los dos problemas.
 */
export async function getLastDataTimes(ids: (number | string)[]): Promise<Record<string, string>> {
  const entities = ids
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id))
    .map((id) => ({ id }))
  if (!entities.length) return {}

  const { data } = await http.post<RawLastData[]>('/entities/getLastDataTimestamps', { entities })

  const times: Record<string, string> = {}
  for (const row of data ?? []) {
    if (row?.id !== undefined && row.last_timestamp) times[String(row.id)] = row.last_timestamp
  }
  return times
}

/** El ultimo dato de una entidad es el mas reciente de sus medidas. */
export function latestTimestamp(measures: { timestamp?: string | null }[]): string | null {
  let best: string | null = null
  let bestAt = 0
  for (const m of measures) {
    const at = epoch(m?.timestamp)
    if (at > bestAt) {
      bestAt = at
      best = m.timestamp ?? null
    }
  }
  return best
}

function datamodelName(row: DatamodelRow): string | null {
  if (typeof row === 'string') return row.trim() || null
  const value = row?.datamodel || row?.name || row?.type
  return value ? String(value).trim() || null : null
}

/**
 * Valor centinela que el modelo de datos usa para «sin unidad». No es una unidad, asi que
 * rotularlo dejaba tarjetas como «42 dimensionless». Se descarta en el unico punto donde se
 * construye una medida, y no en cada componente que la pinta.
 */
const NO_UNITS = 'dimensionless'

function measureUnits(value?: string | null): string | undefined {
  const units = value?.trim()
  return units && units.toLowerCase() !== NO_UNITS ? units : undefined
}

function toMeasure(raw: RawMeasure): Measure {
  const id = String(raw.id)
  return {
    id,
    name: raw.name?.trim() || id,
    units: measureUnits(raw.units),
    value_type: raw.value_type,
    value: raw.value,
    timestamp: raw.timestamp ?? undefined,
    type: raw.type,
  }
}

/** Las propiedades internas son de uso tecnico del sistema y no se muestran al usuario. */
function isInternal(raw: RawMeasure): boolean {
  return raw.internal === true || raw.internal === 'true'
}

function epoch(value?: string | null): number {
  return parseApiDateTime(value)?.toMillis() ?? 0
}
