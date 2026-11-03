import { http } from '@/api/http'
import { urnTail } from '@/lib/format'
import { getEntity } from '@/features/entities/api/entities'
import { geoJsonLatLon } from '@/features/entities/lib/location'
import type { Entity } from '@/types'
import { datamodelOf } from '../contract'
import type { Point, TemplateDashboard } from './types'

/** Tope de puntos por cuadro: mas alla de esto ni el mapa ni la leyenda se leen. */
export const MAX_POINTS_PER_DASHBOARD = 40

/** Resoluciones de id numerico a entidad completa que se intentan por carga, como maximo. */
const MAX_ID_RESOLUTIONS = 20

/** Entidades de eventos en bruto que se piden para situar las de la ETL: una por sensor, de sobra. */
const MAX_RAW_EVENT_ENTITIES = 200

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function isNonEmptyArray(value: unknown): value is unknown[] {
  return Array.isArray(value) && value.length > 0
}

/**
 * Puntos de medida asignados al cuadro. Si el anfitrion ya los trae, se usan tal cual; si no,
 * se piden con el detalle del cuadro, que es la unica llamada que los devuelve (el listado
 * paginado siempre responde entities vacio).
 */
export async function loadTemplateEntities(dashboard: TemplateDashboard): Promise<Entity[]> {
  if (dashboard.entities?.length) return dashboard.entities
  const { data } = await http.get<unknown>(`/dashboards/${dashboard.id}`)
  return readEntityList(data)
}

/** Traduce la respuesta cruda del detalle a entidades, tolerando las cuatro formas conocidas. */
export async function readEntityList(raw: unknown): Promise<Entity[]> {
  const source = isRecord(raw) ? raw : {}
  const templateDrawer = isRecord(source.templateDrawer) ? source.templateDrawer : undefined
  const templateDrawerSnake = isRecord(source.template_drawer) ? source.template_drawer : undefined

  const candidates: unknown[] = [
    source.entities,
    templateDrawer?.entities,
    templateDrawerSnake?.entities,
    source.templateEntities,
  ]
  const list = candidates.find(isNonEmptyArray) ?? []

  const direct: Entity[] = []
  const toResolve: (number | string)[] = []

  for (const item of list) {
    if (isRecord(item) && typeof item.urn === 'string') {
      direct.push(item as unknown as Entity)
      continue
    }
    if (isRecord(item) && isRecord(item.entity)) {
      direct.push(item.entity as unknown as Entity)
      continue
    }
    if (typeof item === 'number') {
      toResolve.push(item)
      continue
    }
    if (typeof item === 'string' && /^\d+$/.test(item)) {
      toResolve.push(item)
    }
  }

  // Un punto borrado en la plataforma no debe tumbar el cuadro: los fallos se descartan.
  const resolved = await Promise.all(
    toResolve.slice(0, MAX_ID_RESOLUTIONS).map((id) => getEntity(id).catch(() => null)),
  )
  for (const entity of resolved) if (entity) direct.push(entity)

  const usable = direct.filter((entity) => !!entity?.urn && !!entity?.tenant && !!entity?.scope)

  const byUrn = new Map<string, Entity>()
  for (const entity of usable) byUrn.set(entity.urn, entity)

  return [...byUrn.values()]
}

/**
 * Las entidades de eventos de la ETL (`…_CFE`) no publican ubicacion, pero la de eventos en bruto
 * del mismo sensor, cuyo URN acaba igual, si. A las que llegan sin ubicacion se les pone la de esa,
 * para que el sensor salga en el mapa. Es una ayuda: si la consulta falla o el sensor no tiene esa
 * entidad, se quedan como estaban.
 */
export async function locateEventEntities(entities: Entity[]): Promise<Entity[]> {
  const etl = datamodelOf('flowEvent')
  const raw = datamodelOf('rawEvent')
  const unlocated = (entity: Entity) => entity.datamodel === etl && !entity.geolocation
  if (!entities.some(unlocated)) return entities

  let located: Map<string, Entity['geolocation']>
  try {
    const { data } = await http.post<{ rows?: Entity[] }>('/entities/paginate', {
      page: 1,
      paginationSize: MAX_RAW_EVENT_ENTITIES,
      types: raw,
    })
    located = new Map(
      (data?.rows ?? [])
        .filter((row) => row?.datamodel === raw && !!row.urn && !!row.geolocation)
        .map((row) => [urnTail(row.urn), row.geolocation]),
    )
  } catch {
    return entities
  }

  return entities.map((entity) => {
    const geolocation = unlocated(entity) ? located.get(urnTail(entity.urn)) : undefined
    return geolocation ? { ...entity, geolocation } : entity
  })
}

export function toPoint(entity: Entity): Point {
  const location = geoJsonLatLon(entity.geolocation)
  return {
    key: entity.urn,
    entity,
    ref: { urn: entity.urn, tenant: entity.tenant, scope: entity.scope },
    label: entity.name?.trim() || urnTail(entity.urn),
    lat: location?.lat ?? null,
    lon: location?.lon ?? null,
  }
}

/** Puntos ordenados por etiqueta en español y recortados al tope. */
export function pointsOf(entities: Entity[]): Point[] {
  return entities
    .map(toPoint)
    .sort((a, b) => a.label.localeCompare(b.label, 'es'))
    .slice(0, MAX_POINTS_PER_DASHBOARD)
}
