import { http } from '@/api/http'
import type { Bounds, Entity, Paginated } from '@/types'

export interface BoundsQuery {
  search?: string
  /** Modelos de datos separados por comas, tal y como los espera el backend. */
  types?: string
  page?: number
  paginationSize?: number
  signal?: AbortSignal
}

/**
 * Entidades cuya ubicacion cae dentro del rectangulo visible. El backend rechaza el filtro
 * si el objeto `bounds` lleva alguna clave que no sea una de las cuatro coordenadas.
 */
export async function listEntitiesInBounds(
  bounds: Bounds,
  opts: BoundsQuery = {},
): Promise<Paginated<Entity>> {
  const body: Record<string, unknown> = {
    bounds: {
      south: bounds.south,
      west: bounds.west,
      north: bounds.north,
      east: bounds.east,
    },
    page: opts.page ?? 1,
    paginationSize: opts.paginationSize ?? 200,
  }
  if (opts.search) body.search = opts.search
  if (opts.types) body.types = opts.types

  const { data } = await http.post<Paginated<Entity>>('/entities/paginate', body, {
    signal: opts.signal,
  })

  return { count: data?.count ?? 0, rows: data?.rows ?? [] }
}

export interface SampleQuery {
  search?: string
  types?: string
  paginationSize?: number
  signal?: AbortSignal
}

/**
 * Muestra de entidades SIN restringir el area, para averiguar donde estan los datos.
 *
 * Hace falta porque el mapa arranca en el centro configurado en el despliegue, y ese centro no
 * tiene por que ser donde el usuario tiene entidades. Cuando no coinciden, el mapa abre vacio y
 * la unica salida es arrastrarlo a ciegas por medio continente. Se respetan los filtros para que
 * la respuesta sea «donde hay datos de lo que estas buscando», no «donde hay datos».
 */
export async function sampleEntities(opts: SampleQuery = {}): Promise<Entity[]> {
  const body: Record<string, unknown> = {
    page: 1,
    paginationSize: opts.paginationSize ?? 300,
  }
  if (opts.search) body.search = opts.search
  if (opts.types) body.types = opts.types

  const { data } = await http.post<Paginated<Entity>>('/entities/paginate', body, {
    signal: opts.signal,
  })

  return data?.rows ?? []
}

interface DatamodelRow {
  datamodel?: string
}

/** Catalogo de modelos de datos para el desplegable de filtro, ya ordenado y sin repetidos. */
export async function listDatamodels(signal?: AbortSignal): Promise<string[]> {
  const { data } = await http.post<Paginated<DatamodelRow>>(
    '/entities/datamodels/paginate',
    {},
    { signal },
  )

  const names = (data?.rows ?? [])
    .map((row) => row?.datamodel)
    .filter((name): name is string => typeof name === 'string' && name.length > 0)

  return [...new Set(names)].sort((a, b) => a.localeCompare(b, 'es'))
}
