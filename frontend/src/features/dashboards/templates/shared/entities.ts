import { http } from '@/api/http'
import { urnTail } from '@/lib/format'
import { getEntity } from '@/features/entities/api/entities'
import { geoJsonLatLon } from '@/features/entities/lib/location'
import type { Entity } from '@/types'
import type { Point, TemplateDashboard } from './types'

/** Tope de puntos por cuadro: mas alla de esto ni el mapa ni la leyenda se leen. */
export const MAX_POINTS_PER_DASHBOARD = 40

/** Resoluciones de id numerico a entidad completa que se intentan por carga, como maximo. */
const MAX_ID_RESOLUTIONS = 20

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
