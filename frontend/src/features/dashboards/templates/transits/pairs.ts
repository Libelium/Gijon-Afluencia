import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import type { EntityRef } from '@/types'
import { datamodelOf } from '../contract'
import { topByRecency } from '../shared/aggregate'
import type { Point } from '../shared/types'

/**
 * Tope de series por carga. Son cuatro lotes de REQUEST_BATCH, el mismo orden de magnitud que la
 * plantilla de clasificacion (8 puntos x 12 categorias). Aqui el tope no es una precaucion sino
 * una necesidad: un panel con los 40 puntos que admite un cuadro daria 1560 recorridos dirigidos.
 */
export const MAX_PAIR_SERIES = 100

/** n puntos combinados dan n(n-1) recorridos dirigidos: con 10 son 90 series y con 11 ya 110. */
export const MAX_DERIVED_POINTS = 10

/** De donde salen los pares: combinados por la plantilla o declarados por el propio sensor. */
export type PairMode = 'derived' | 'explicit'

/** Un extremo de un recorrido. */
export interface FlowNode {
  /** Cola del URN: es el identificador con el que un par nombra a sus dos extremos. */
  id: string
  label: string
  lat: number | null
  lon: number | null
}

/** Un recorrido dirigido, ya listo para pedir su serie. */
export interface FlowPair {
  key: string
  /** URN del par: compuesto en modo derivado, el de la propia entidad en modo explicito. */
  urn: string
  /** Tenant y scope con los que pedir la serie del par. */
  ref: EntityRef
  origin: FlowNode
  target: FlowNode
  label: string
}

export interface PairSet {
  mode: PairMode
  pairs: FlowPair[]
  /** Extremos que intervienen en `pairs`, sin repetir y ordenados por rotulo. */
  nodes: FlowNode[]
  /** Puntos combinables del panel. Sostiene el estado «hacen falta al menos dos puntos». */
  sources: number
  /** Recorte aplicado para no pasar del tope de series, o null si no ha hecho falta. */
  limited: { shown: number; total: number; kind: 'sources' | 'pairs' } | null
}

const FLOW_EVENT = datamodelOf('flowEvent')

function routeLabel(origin: string, target: string): string {
  return t('templates.transits.routeLabel', { origin, target })
}

function nodeOf(id: string, place?: Point): FlowNode {
  if (!place) return { id, label: id, lat: null, lon: null }
  return { id, label: place.label, lat: place.lat, lon: place.lon }
}

function byRecency(a: Point, b: Point): number {
  return (b.entity.time_last_data ?? '').localeCompare(a.entity.time_last_data ?? '')
}

interface Source {
  id: string
  point: Point
}

function uniqueById(points: Point[]): Source[] {
  const seen = new Set<string>()
  const out: Source[] = []
  for (const point of points) {
    const id = urnTail(point.entity.urn)
    // Dos puntos con la misma cola de URN serian el mismo extremo del par: se queda el primero.
    if (seen.has(id)) continue
    seen.add(id)
    out.push({ id, point })
  }
  return out
}

/**
 * Combina los puntos del panel en todos los recorridos dirigidos posibles. El URN de cada par se
 * arma como lo hace la plataforma —el modelo de transitos seguido de las colas de los URN de
 * origen y destino—, que es lo que permite pedir su serie aunque el par no sea una entidad
 * asignada al cuadro. Al no serlo tampoco tiene tenant ni scope propios: se usan los del origen.
 */
function derivedPairs(places: Point[]): PairSet {
  const unique = uniqueById(places)
  const kept =
    unique.length <= MAX_DERIVED_POINTS
      ? unique
      : [...unique].sort((a, b) => byRecency(a.point, b.point)).slice(0, MAX_DERIVED_POINTS)
  // El recorte por recencia rompe el orden alfabetico, y de ese orden dependen la matriz y los
  // colores: se restablece antes de construir nada.
  const ordered = [...kept].sort((a, b) => a.point.label.localeCompare(b.point.label, 'es'))

  const nodes = ordered.map((source) => nodeOf(source.id, source.point))
  const prefix = `urn:ngsi-ld:${FLOW_EVENT}`
  const pairs: FlowPair[] = []

  nodes.forEach((origin, i) => {
    nodes.forEach((target, j) => {
      if (i === j) return
      pairs.push({
        key: `${origin.id}>${target.id}`,
        urn: `${prefix}:${origin.id}:${target.id}`,
        ref: ordered[i].point.ref,
        origin,
        target,
        label: routeLabel(origin.label, target.label),
      })
    })
  })

  return {
    mode: 'derived',
    pairs,
    nodes,
    sources: unique.length,
    limited:
      unique.length > ordered.length
        ? { shown: ordered.length, total: unique.length, kind: 'sources' }
        : null,
  }
}

/**
 * Usa los pares que el sensor ya publica como entidades. Sus dos ultimos segmentos de URN son los
 * identificadores de origen y destino; un URN que no llegue a tenerlos no se puede situar en el
 * mapa ni en la matriz, asi que se descarta en lugar de dibujarse a medias.
 */
function explicitPairs(events: Point[], places: Map<string, Point>): PairSet {
  const kept = topByRecency(events, MAX_PAIR_SERIES)
  const nodes = new Map<string, FlowNode>()
  const pairs = new Map<string, FlowPair>()

  for (const event of kept) {
    const parts = event.entity.urn.split(':')
    if (parts.length < 5) continue
    const originId = parts[parts.length - 2]
    const targetId = parts[parts.length - 1]
    if (!originId || !targetId || originId === targetId) continue

    const key = `${originId}>${targetId}`
    if (pairs.has(key)) continue

    const origin = nodes.get(originId) ?? nodeOf(originId, places.get(originId))
    nodes.set(originId, origin)
    const target = nodes.get(targetId) ?? nodeOf(targetId, places.get(targetId))
    nodes.set(targetId, target)

    pairs.set(key, {
      key,
      urn: event.entity.urn,
      ref: event.ref,
      origin,
      target,
      label: routeLabel(origin.label, target.label),
    })
  }

  return {
    mode: 'explicit',
    pairs: [...pairs.values()].sort((a, b) => a.label.localeCompare(b.label, 'es')),
    nodes: [...nodes.values()].sort((a, b) => a.label.localeCompare(b.label, 'es')),
    sources: places.size,
    limited:
      events.length > kept.length
        ? { shown: kept.length, total: events.length, kind: 'pairs' }
        : null,
  }
}

/**
 * Resuelve los recorridos de un panel. Si entre las entidades asignadas hay alguna del modelo de
 * transitos manda ese modo: el sensor sabe que recorridos existen de verdad, y combinar los
 * puntos por encima de eso inventaria pares que nadie publica.
 */
export function buildPairs(points: Point[]): PairSet {
  const events = points.filter((point) => point.entity.datamodel === FLOW_EVENT)
  const places = points.filter((point) => point.entity.datamodel !== FLOW_EVENT)

  const byId = new Map<string, Point>()
  for (const source of uniqueById(places)) byId.set(source.id, source.point)

  return events.length > 0 ? explicitPairs(events, byId) : derivedPairs(places)
}
