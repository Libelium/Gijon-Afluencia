import { ApiError, http } from '@/api/http'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import type { Aggregation, Dashboard, Entity, LayoutItem, Measure, PageQuery, Paginated, Panel, PanelSeries } from '@/types'
import { SERIES_LIGHT } from '../palette'
import { resolveChartKind, type ChartData, type ChartKind } from '../charts'
import { resolveAggregation, resolveRange, type AggregationOption, type RangeInput } from '../lib/range'

const LAYOUT_KEYS = ['lg', 'md', 'sm', 'xs', 'xxs']

/** Graficos de ultimo valor: solo necesitan la lectura mas reciente. */
const LAST_VALUE_KINDS: ChartKind[] = ['kpi', 'gauge']

/**
 * Tope de puntos por serie. El servicio de datos no impone ninguno: una consulta sin limite
 * sobre una entidad con historico largo devuelve millones de filas y lo tumba.
 */
const MAX_POINTS = 2000

interface RawDashboard {
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

function normalizeDashboard(raw: RawDashboard): DashboardDetail {
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

export async function listDashboards(query: PageQuery): Promise<Paginated<DashboardDetail>> {
  const { data } = await http.post<{ rows?: RawDashboard[]; count?: number }>('/dashboards/paginate', {
    page: query.page,
    // Se envian los dos nombres del tamano de pagina: no todos los despliegues leen el mismo.
    perPage: query.paginationSize,
    paginationSize: query.paginationSize,
    search: query.search?.trim() || undefined,
    sort: 'dashboards.name',
    order: 'asc',
  })

  const rows = (data.rows ?? []).map(normalizeDashboard)
  return { count: Number(data.count ?? rows.length), rows }
}

export async function getDashboard(id: number | string): Promise<DashboardDetail> {
  const { data } = await http.get<RawDashboard>(`/dashboards/${id}`)
  return normalizeDashboard(data)
}

/**
 * Naturaleza del panel tal y como la nombra el servidor. No es una etiqueta de presentacion:
 * de ella depende que el detalle cargue la plantilla o la rejilla de graficos.
 */
export type DashboardKind = 'Custom' | 'Template'

export interface NewDashboard {
  name: string
  description?: string
  /** Huso del usuario: el panel guarda el suyo y la vista lo prefiere al de la sesion. */
  timezone?: string
  /** Obligatorio para el servidor: sin el, el alta responde 422. */
  type: DashboardKind
}

/** Minimo que exige la validacion del servidor para el nombre. */
export const NAME_MIN_LENGTH = 3

/** El identificador del recurso creado llega con tres envoltorios distintos segun el despliegue. */
function readId(data: unknown): number | null {
  const candidates = [data, (data as Record<string, unknown>)?.data, (data as Record<string, unknown>)?.dashboard]
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== 'object') continue
    const id = Number((candidate as Record<string, unknown>).id)
    if (Number.isFinite(id) && id > 0) return id
  }
  return null
}

export async function createDashboard(input: NewDashboard): Promise<number> {
  const { data } = await http.post<unknown>('/dashboards', {
    name: input.name.trim(),
    description: input.description?.trim() || null,
    timezone: input.timezone || null,
    type: input.type,
  })
  const id = readId(data)
  if (!id) throw new ApiError('server', t('dashboards.create.noId'))
  return id
}

export async function updateDashboard(
  id: number | string,
  patch: { name: string; description?: string },
): Promise<void> {
  await http.put(`/dashboards/${id}`, {
    name: patch.name.trim(),
    description: patch.description?.trim() || null,
  })
}

export async function setDashboardTemplate(id: number | string, typeId: string): Promise<void> {
  await http.post(`/dashboards/setTemplateType/${id}`, { template_type: typeId })
}

export async function setDashboardTemplateEntities(
  id: number | string,
  entityIds: number[],
): Promise<void> {
  await http.post(`/dashboards/setTemplateEntities/${id}`, { entities: entityIds })
}

export interface NewPanel {
  dashboardId: number
  title: string
  /** Identificador del catalogo de chartTypes.ts; se persiste tal cual en chart.type. */
  chartType: string
  /** Rotulo del tipo, en espanol; solo sirve para que el panel sea legible en la API. */
  chartTitle: string
  entity: Pick<Entity, 'id' | 'name' | 'urn' | 'tenant' | 'scope' | 'datamodel'>
  measure: Pick<Measure, 'id' | 'name' | 'units'>
  aggregation: Aggregation
  /** Duracion ISO 8601 en horas, o vacio para automatico. */
  interval?: string
}

/**
 * Color con el que se da de alta una serie. El servidor lo exige con contenido, pero no decide
 * nada: los graficos toman su paleta del tema, que es la unica que tiene calculado el contraste
 * sobre cada superficie. Se guarda un valor valido y coherente con el tema claro.
 */
const DEFAULT_SERIE_COLOR = SERIES_LIGHT[0]

/**
 * Alta de un grafico. La forma de `series` la fija `SerieRepository::validateSerie` del servidor,
 * y tiene tres trampas comprobadas contra su codigo:
 *
 *  - `type`, `alias` y `color` son `required|min:1`. Enviarlos nulos, o no enviarlos, no da un 422:
 *    el validador consulta `$serie['type']` ANTES de validar, asi que su ausencia es un error de
 *    clave indefinida en PHP y la respuesta es un 500 sin explicacion.
 *  - La unidad se llama `unit` en singular en el validador, pero el objeto `measure` se persiste
 *    como JSON literal y esta misma aplicacion lo lee luego por `units`. Se mandan las dos claves:
 *    una la valida el servidor y la otra la necesita la lectura.
 *  - Los identificadores planos (`entity_id`, `measure_id`) y `config` no se validan ni se guardan;
 *    el servidor resuelve la entidad desde `series[].entity`.
 */
export async function createPanel(input: NewPanel): Promise<void> {
  await http.post('/panels', {
    dashboard_id: input.dashboardId,
    title: input.title.trim(),
    chart: { type: input.chartType, title: input.chartTitle },
    series: [
      {
        type: 'Measure',
        alias: input.measure.name.trim() || input.title.trim(),
        color: DEFAULT_SERIE_COLOR,
        visible: true,
        entity: {
          id: input.entity.id,
          name: input.entity.name,
          urn: input.entity.urn,
          tenant: input.entity.tenant,
          scope: input.entity.scope,
          datamodel: input.entity.datamodel,
        },
        measure: {
          id: input.measure.id,
          name: input.measure.name,
          unit: input.measure.units ?? null,
          units: input.measure.units ?? null,
        },
        grouping_function: input.aggregation,
        grouping_interval: input.interval || null,
        // Estas dos claves tienen que VIAJAR, aunque vayan nulas. `storeMeasureSerie` decide si
        // leerlas mirando si existe `grouping_function`, y para `grouping_interval_value` no
        // comprueba que exista ella misma (a diferencia de `grouping_function_value`, que si lo
        // hace). Omitirla es una clave indefinida en PHP dentro de un `try` que captura todo y
        // responde 422 «Measure or entity not found», que no tiene nada que ver con la causa.
        grouping_function_value: null,
        grouping_interval_value: null,
      },
    ],
  })
}

export async function deletePanel(id: number | string): Promise<void> {
  await http.delete(`/panels/${id}`)
}

/**
 * Borra el panel entero, con sus graficos. El servidor responde 204 sin cuerpo, y 403 cuando la
 * cuenta no es la propietaria: ese caso llega como ApiError 'forbidden' y la vista lo dice, en
 * lugar de dejar creer que se ha borrado.
 */
export async function deleteDashboard(id: number | string): Promise<void> {
  await http.delete(`/dashboards/${id}`)
}

interface TimeSeriesRequest {
  device_ids: string[]
  measure_ids: string[]
  options: {
    start_date: string
    end_date: string
    order: 'asc' | 'desc'
    limit: number
    tenant: string
    scope: string
    aggregation?: AggregationOption
  }
}

interface RawValue {
  timestamp?: string
  value?: unknown
}

interface RawTimeSeries {
  device_id?: string
  measure_id?: string
  values?: RawValue[]
}

interface RawTimeSeriesResponse {
  time_series?: RawTimeSeries[]
}

interface QueryableSeries {
  serie: PanelSeries
  urn: string
  measure: string
  tenant: string
  scope: string
}

/**
 * Solo las series de medida se pueden consultar: las calculadas o multidimensionales
 * dependen de una formula que resolvia la herramienta de origen.
 */
export function queryableSeries(series: PanelSeries[] | undefined): QueryableSeries[] {
  return (series ?? []).flatMap((serie) => {
    const urn = serie.entity?.urn
    const measure = serie.measure?.id
    const tenant = serie.entity?.tenant
    const scope = serie.entity?.scope
    if (!urn || !measure || !tenant || !scope) return []
    return [{ serie, urn, measure, tenant, scope }]
  })
}

function seriesName(item: QueryableSeries, withEntity: boolean): string {
  if (item.serie.alias) return item.serie.alias
  const measure = item.serie.measure?.name || item.measure
  if (!withEntity) return measure
  const entity = item.serie.entity?.name || urnTail(item.urn)
  return `${entity} · ${measure}`
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'boolean') return value ? 1 : 0
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function readPoints(response: RawTimeSeriesResponse | undefined, item: QueryableSeries) {
  const list = response?.time_series ?? []
  const match = list.find((s) => s.device_id === item.urn && s.measure_id === item.measure) ?? list[0]

  return (match?.values ?? [])
    .filter((value): value is RawValue & { timestamp: string } => typeof value.timestamp === 'string')
    .map((value) => ({ t: value.timestamp, v: toNumber(value.value) }))
    // La consulta va en orden descendente para quedarse con lo mas reciente; el grafico lo pinta al contrario.
    .sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : 0))
}

export async function fetchPanelData(
  panel: Panel,
  range: RangeInput,
  timeZone?: string,
): Promise<ChartData> {
  const items = queryableSeries(panel.series)
  if (!items.length) return { series: [] }

  const resolved = resolveRange(range, timeZone)
  const lastValueOnly = LAST_VALUE_KINDS.includes(resolveChartKind(panel))

  const body: TimeSeriesRequest[] = items.map((item) => {
    const aggregation = lastValueOnly
      ? null
      : resolveAggregation(resolved, item.serie.grouping_function, item.serie.grouping_interval)
    return {
      device_ids: [item.urn],
      measure_ids: [item.measure],
      options: {
        start_date: resolved.start,
        end_date: resolved.end,
        // El limite se aplica sobre el orden pedido, de modo que descendente conserva lo ultimo.
        order: 'desc',
        limit: lastValueOnly ? 1 : MAX_POINTS,
        tenant: item.tenant,
        scope: item.scope,
        ...(aggregation ? { aggregation } : {}),
      },
    }
  })

  const { data } = await http.post<RawTimeSeriesResponse[]>('/timeseries', body)
  const responses = Array.isArray(data) ? data : []
  const withEntity = new Set(items.map((item) => item.urn)).size > 1

  return {
    series: items.map((item, index) => ({
      name: seriesName(item, withEntity),
      units: item.serie.measure?.units || undefined,
      points: readPoints(responses[index], item),
    })),
  }
}
