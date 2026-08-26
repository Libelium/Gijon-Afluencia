export interface Paginated<T> {
  count: number
  rows: T[]
  items?: number
}

export interface PageQuery {
  page: number
  paginationSize: number
  search?: string
  /** Lista de modelos de datos separada por comas. */
  types?: string
  tenant?: string
  scope?: string
  groups?: number[]
  urn?: string
  bounds?: Bounds
}

export interface Bounds {
  south: number
  west: number
  north: number
  east: number
}

export interface GeoPoint {
  type: 'Point'
  coordinates: [number, number]
}

export interface GeoPolygon {
  type: 'Polygon'
  coordinates: [number, number][][]
}

export type Geolocation = GeoPoint | GeoPolygon

export interface Entity {
  id: number
  name: string
  urn: string
  datamodel: string
  tenant: string
  tenant_id?: number
  scope: string
  scope_id?: number
  devices?: number[]
  geolocation?: Geolocation
  time_last_data?: string
}

/** Identidad minima para pedir datos de una entidad: el backend exige tenant y scope. */
export type EntityRef = Pick<Entity, 'urn' | 'tenant' | 'scope'>

export interface Measure {
  id: string
  name: string
  units?: string
  value_type?: string
  value?: unknown
  timestamp?: string
  type?: string
}

export interface UserPreferences {
  language?: string
  timeZone?: string
  datetimeFormat?: string
  displayskinMode?: string
  numberFormat?: string
  [key: string]: string | undefined
}

export interface CurrentUser {
  id: number
  name?: string
  email?: string
  preferences: UserPreferences
  organization?: { id: number; name: string }
}

export type Aggregation = 'mean' | 'max' | 'min' | 'sum' | 'count'

export interface TimeSeriesQuery {
  entities: EntityRef[]
  measures: string[]
  start: string
  end: string
  aggregation?: { type: Aggregation; interval: string }
  /** Los widgets de ultimo valor deben pedir limit 1: sin limite se piden millones de filas. */
  limit?: number
  order?: 'asc' | 'desc'
}

export interface SeriesPoint {
  timestamp: string
  value: number | null
}

export interface TimeSeries {
  urn: string
  measure: string
  units?: string
  points: SeriesPoint[]
}

export interface Dashboard {
  id: number
  name: string
  description?: string
  slug?: string
  timezone?: string
  templateType?: string | null
  panels?: Panel[]
  responsiveLayout?: Record<string, LayoutItem[]>
}

export interface LayoutItem {
  i: string | number
  x: number
  y: number
  w: number
  h: number
}

/** El chart persistido lo creo otra herramienta: se traduce en un unico adaptador. */
export interface Panel {
  id: number
  title?: string
  chart?: { type?: string; title?: string } & Record<string, unknown>
  series?: PanelSeries[]
  config?: Record<string, unknown>
}

export interface PanelSeries {
  alias?: string
  entity?: Partial<Entity>
  measure?: Partial<Measure>
  grouping_function?: string
  grouping_interval?: string
  color?: string
}

export interface Alarm {
  id: number
  name: string
  type?: string
  disabled?: boolean
  up?: boolean
  description?: string
  createdAt?: string
}

export interface LogLine {
  id?: number
  datetime: string
  level_name?: string
  message: string
  extra?: Record<string, unknown>
}
