import { ApiError, http } from '@/api/http'
import { t } from '@/i18n'
import type { Aggregation, Entity, Measure, PageQuery, Paginated } from '@/types'
import { SERIES_LIGHT } from '../palette'
import { normalizeDashboard, type DashboardDetail, type RawDashboard } from './dashboards.normalize'

/**
 * Operaciones HTTP sobre paneles y sus graficos: listado, alta, edicion, borrado, tipo de
 * plantilla y entidades asignadas. La normalizacion del recurso vive en `dashboards.normalize.ts`
 * y la consulta de datos de un panel en `panelData.ts`; este modulo reexporta lo que el resto de
 * la aplicacion venia importando desde aqui, para no cambiar sus rutas de importacion.
 */

export type { DashboardDetail } from './dashboards.normalize'
export { fetchPanelData, queryableSeries } from './panelData'

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
