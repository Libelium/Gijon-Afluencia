import { getEntityMeasures } from '@/features/entities/api/entities'
import type { Measure } from '@/types'
import type { Category, MeasureIntent, MeasureOption, Point } from './types'

export interface MeasureIndex {
  /** Medidas por URN de punto. */
  byPoint: Map<string, Measure[]>
  /** Union deduplicada por id, ordenada alfabeticamente en español. */
  all: Measure[]
  /** URN de los puntos cuya lectura en vivo ha fallado. */
  failed: string[]
}

/**
 * Candidatas a medida de aforo, en orden de preferencia. `peopleCount` va primero porque es el
 * total instantaneo del periodo de observacion; las variantes por intervalo son lo que publican
 * los sensores cuando no exponen el total suelto.
 */
const OCCUPANCY_CANDIDATES = [
  'peopleCount',
  'peopleCountMediumInterval',
  'peopleCountLongInterval',
  'peopleCountShortInterval',
  'personCount',
  'pedestrianCount',
  'occupancy',
  'occupancyRate',
  'count',
]

const TRANSIT_CANDIDATES = [
  'visits',
  'transits',
  'crossings',
  'passages',
  'flow',
  'peopleCount',
  'count',
]

const OCCUPANCY_HINT = /(people|person|pedestrian|aforo|ocupa|occupan)/i
const TRANSIT_HINT = /(visit|transit|cross|pass|flow|trayect|desplaz)/i

/** Contadores acumulativos por su nombre. Sumar sus lecturas multiplica el valor real. */
const CUMULATIVE_HINT = /(visits?|transits?|acumulad|accumulat|cumulat|counter|total)$/i

/** Nunca son una medida de aforo ni una categoria: son metadatos, geometria o telemetria. */
const NOT_A_MEASURE =
  /(^id$|^type$|location|coordinates|^lat$|^lon$|^lng$|latitude|longitude|dateobserved|datemodified|datecreated|timestamp|battery|rssi|firmware|storage|temperature|humidity|pressure|windspeed|speed|congested|direction|address|district|postalcode|source|dataprovider|owner|seealso|bbox|name|description)/i

const NUMERIC_VALUE_TYPES = new Set(['double', 'integer', 'float', 'number', 'int', 'long', 'decimal'])
const NON_NUMERIC_VALUE_TYPES = new Set(['bool', 'boolean', 'string', 'text'])

export function isNumericMeasure(measure: Measure): boolean {
  if (typeof measure.value === 'boolean') return false
  const valueType = measure.value_type?.toLowerCase()
  if (valueType && NON_NUMERIC_VALUE_TYPES.has(valueType)) return false
  if (valueType && NUMERIC_VALUE_TYPES.has(valueType)) return true
  if (typeof measure.value === 'number' && Number.isFinite(measure.value)) return true
  if (typeof measure.value === 'string') {
    const trimmed = measure.value.trim()
    if (trimmed !== '' && Number.isFinite(Number(trimmed))) return true
  }
  return false
}

/** Contadores que solo crecen: se agregan por maximo y se leen por incremento. */
export function isCumulative(measureId: string): boolean {
  return CUMULATIVE_HINT.test(measureId)
}

function pickShortest(list: Measure[]): Measure {
  return [...list].sort(
    (a, b) => a.id.length - b.id.length || a.id.localeCompare(b.id, 'es'),
  )[0]
}

/** Medida principal segun la intencion, o null si no hay ninguna numerica utilizable. */
export function pickMeasure(all: Measure[], intent: MeasureIntent): string | null {
  const candidates = all.filter(isNumericMeasure).filter((m) => !NOT_A_MEASURE.test(m.id))
  const list = intent === 'occupancy' ? OCCUPANCY_CANDIDATES : TRANSIT_CANDIDATES
  const hint = intent === 'occupancy' ? OCCUPANCY_HINT : TRANSIT_HINT

  for (const name of list) {
    const found = candidates.find((m) => m.id.toLowerCase() === name.toLowerCase())
    if (found) return found.id
  }
  for (const name of list) {
    const found = candidates.find((m) => m.name.toLowerCase() === name.toLowerCase())
    if (found) return found.id
  }

  const byId = candidates.filter((m) => hint.test(m.id))
  if (byId.length) return pickShortest(byId).id

  const byName = candidates.filter((m) => hint.test(m.name))
  if (byName.length) return pickShortest(byName).id

  return candidates.length ? candidates[0].id : null
}

export interface CategorySet {
  /** Prefijo comun del grupo ganador, para poder rotularlo. null si no se ha detectado nada. */
  base: string | null
  categories: Category[]
}

interface SplitId {
  base: string
  suffix: string
}

function splitMeasureId(id: string): SplitId | null {
  const snake = /^(.+)[_-]([A-Za-z0-9]+)$/.exec(id)
  if (snake) return { base: snake[1], suffix: snake[2] }
  const camel = /^(.*[a-z0-9])([A-Z][A-Za-z0-9]*)$/.exec(id)
  if (camel) return { base: camel[1], suffix: camel[2] }
  return null
}

const DISCARDED_SUFFIXES = new Set([
  'interval',
  'rate',
  'average',
  'mean',
  'max',
  'min',
  'total',
  'sum',
  'percent',
  'ratio',
  'index',
])

/** Mas de 12 sectores no se leen en un donut. */
const MAX_CATEGORIES = 12

const CATEGORY_SUFFIXES: Record<string, string> = {
  // Sentido de circulacion
  towards: 'Entrada',
  away: 'Salida',
  inbound: 'Entrada',
  outbound: 'Salida',
  in: 'Entrada',
  out: 'Salida',
  entry: 'Entradas',
  exit: 'Salidas',
  // Sexo
  male: 'Hombres',
  female: 'Mujeres',
  // Edad
  baby: 'Bebés',
  child: 'Niños',
  children: 'Niños',
  young: 'Jóvenes',
  youth: 'Jóvenes',
  adult: 'Adultos',
  senior: 'Mayores',
  elder: 'Mayores',
  // Modo de desplazamiento
  pedestrian: 'Peatones',
  bicycle: 'Bicicletas',
  bike: 'Bicicletas',
  cyclist: 'Ciclistas',
  scooter: 'Patinetes',
  motorbike: 'Motos',
  motorcycle: 'Motos',
  car: 'Coches',
  van: 'Furgonetas',
  truck: 'Camiones',
  bus: 'Autobuses',
  // Agrupacion
  group: 'Grupos',
  individual: 'Individuales',
  staff: 'Personal',
  visitor: 'Visitantes',
  // Lado / sentido vertical
  left: 'Izquierda',
  right: 'Derecha',
  up: 'Subida',
  down: 'Bajada',
  // Cierre
  other: 'Otros',
  unknown: 'Sin clasificar',
}

const DICTIONARY_ORDER = Object.keys(CATEGORY_SUFFIXES)

function humanizeSuffix(suffix: string): string {
  const words = suffix.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/[_-]/g, ' ').trim()
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : words
}

interface GroupMember {
  measureId: string
  suffix: string
}

interface Group {
  base: string
  members: GroupMember[]
}

export function detectCategories(all: Measure[]): CategorySet {
  const candidates = all.filter(isNumericMeasure).filter((m) => !NOT_A_MEASURE.test(m.id))

  const groups = new Map<string, Group>()
  for (const measure of candidates) {
    const split = splitMeasureId(measure.id)
    if (!split) continue
    if (split.base.length < 4) continue
    if (DISCARDED_SUFFIXES.has(split.suffix.toLowerCase())) continue
    const key = split.base.toLowerCase()
    const group = groups.get(key) ?? { base: split.base, members: [] }
    group.members.push({ measureId: measure.id, suffix: split.suffix })
    groups.set(key, group)
  }

  const eligible = [...groups.values()].filter((g) => g.members.length >= 2)
  if (!eligible.length) return { base: null, categories: [] }

  const scored = eligible
    .map((group) => ({
      group,
      known: group.members.filter((m) => CATEGORY_SUFFIXES[m.suffix.toLowerCase()] !== undefined),
    }))
    .sort((a, b) => {
      if (b.known.length !== a.known.length) return b.known.length - a.known.length
      if (b.group.members.length !== a.group.members.length) {
        return b.group.members.length - a.group.members.length
      }
      return a.group.base.localeCompare(b.group.base, 'es')
    })

  const winner = scored[0]
  // Dos medidas hermanas con sufijos que no reconozco pueden ser cualquier cosa; tres ya es un patron.
  if (winner.known.length === 0 && winner.group.members.length < 3) return { base: null, categories: [] }

  const categories: Category[] = winner.group.members
    .map((m) => {
      const suffixLower = m.suffix.toLowerCase()
      return {
        measureId: m.measureId,
        label: CATEGORY_SUFFIXES[suffixLower] ?? humanizeSuffix(m.suffix),
        order: DICTIONARY_ORDER.indexOf(suffixLower),
      }
    })
    .sort((a, b) => {
      const oa = a.order < 0 ? 999 : a.order
      const ob = b.order < 0 ? 999 : b.order
      return oa - ob || a.label.localeCompare(b.label, 'es')
    })
    .slice(0, MAX_CATEGORIES)

  return { base: winner.group.base, categories }
}

/** Nombre presentable de una medida: su `name`, y si no lo hay el id partido en palabras. */
export function humanizeMeasure(measure: Measure): string {
  return measure.name?.trim() || humanizeSuffix(measure.id)
}

/** Items para un VSelect de correccion manual. */
export function measureOptions(all: Measure[]): MeasureOption[] {
  return all
    .filter(isNumericMeasure)
    .map((m) => ({
      value: m.id,
      title: m.units ? `${humanizeMeasure(m)} (${m.units})` : humanizeMeasure(m),
    }))
    .sort((a, b) => a.title.localeCompare(b.title, 'es'))
}

/**
 * Etiqueta de una categoria elegida a mano (no detectada). Se busca la medida entre las
 * conocidas para aprovechar su `name`; si no aparece, se humaniza el propio id.
 */
export function categoryLabelOf(measureId: string, all: Measure[]): string {
  const measure = all.find((m) => m.id === measureId)
  return measure ? humanizeMeasure(measure) : humanizeSuffix(measureId)
}

/**
 * Lee las medidas de cada punto con GET /realtime/entities/{urn}. Los fallos se acumulan en
 * `failed` en lugar de propagarse: un sensor caido no puede dejar la plantilla sin dibujar.
 */
export async function loadMeasures(points: Point[]): Promise<MeasureIndex> {
  const settled = await Promise.allSettled(points.map((p) => getEntityMeasures(p.ref)))

  const byPoint = new Map<string, Measure[]>()
  const byId = new Map<string, Measure>()
  const failed: string[] = []

  settled.forEach((result, index) => {
    const point = points[index]
    if (result.status === 'fulfilled') {
      byPoint.set(point.key, result.value)
      for (const measure of result.value) {
        const current = byId.get(measure.id)
        if (!current || (measure.timestamp ?? '') > (current.timestamp ?? '')) byId.set(measure.id, measure)
      }
    } else {
      failed.push(point.key)
    }
  })

  const all = [...byId.values()].sort((a, b) => a.name.localeCompare(b.name, 'es'))

  return { byPoint, all, failed }
}
