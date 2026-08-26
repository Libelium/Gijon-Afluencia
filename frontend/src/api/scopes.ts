import { http } from '@/api/http'

/**
 * Un ambito de datos legible por el usuario, junto al espacio de datos al que pertenece.
 *
 * Los dos valores viajan siempre juntos porque el servidor los exige juntos: pasarle un ambito
 * sin su espacio de datos devuelve 400 «Undefined tenant for given scope». Modelarlo como un
 * unico objeto evita que quien lo use pueda formar esa combinacion invalida.
 */
export interface DataScope {
  /** Identificador del ambito. Es el valor que guardan las preferencias del usuario. */
  id: string
  tenant: string
  scope: string
}

interface ScopeRow {
  id?: number | string
  name?: string
  tenant?: { name?: string } | null
}

let request: Promise<ScopeRow[]> | null = null

/**
 * Los ambitos legibles no cambian durante la sesion: se piden una sola vez y se comparte la
 * misma promesa. Un fallo descarta la memorizacion, para que el siguiente intento vuelva a
 * preguntar en lugar de heredar el error.
 *
 * Este listado responde con el array en la raiz, a diferencia del resto de listados, que van
 * envueltos en {rows, count}. Se aceptan las dos formas para no depender de ese detalle.
 */
function readableScopeRows(): Promise<ScopeRow[]> {
  if (!request) {
    request = http
      .get<ScopeRow[] | { rows?: ScopeRow[] }>('/fiwareScopes')
      .then(({ data }) => {
        if (Array.isArray(data)) return data
        return Array.isArray(data?.rows) ? data.rows : []
      })
      .catch((error: unknown) => {
        request = null
        throw error
      })
  }
  return request
}

/** Ambitos de datos utilizables. Se descartan los que no traen espacio de datos y ambito. */
export async function listDataScopes(): Promise<DataScope[]> {
  const rows = await readableScopeRows()

  return rows
    .map((row) => ({
      id: row.id === undefined || row.id === null ? '' : String(row.id),
      tenant: row.tenant?.name?.trim() ?? '',
      scope: row.name?.trim() ?? '',
    }))
    .filter((row): row is DataScope => !!row.id && !!row.tenant && !!row.scope)
    .sort((a, b) => a.tenant.localeCompare(b.tenant, 'es') || a.scope.localeCompare(b.scope, 'es'))
}

/**
 * Rotulo de un ambito de datos. El ambito raiz es «/», que por si solo no dice nada, asi que el
 * espacio de datos va siempre delante y el ambito solo se anade cuando aporta informacion.
 */
export function dataScopeLabel(item: DataScope): string {
  return item.scope === '/' ? item.tenant : `${item.tenant} · ${item.scope}`
}
