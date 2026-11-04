import { http } from '@/api/http'
import type { LogLine, PageQuery, Paginated } from '@/types'
import type { ConnectorDetail, ConnectorRow, MqttConnectorInput } from '../types'

export type ConnectorsQuery = Pick<PageQuery, 'page' | 'paginationSize' | 'search'>

/** El servidor exige orderBy y orderDirection: se pide por id, los mas recientes primero. */
export async function listConnectors(query: ConnectorsQuery): Promise<Paginated<ConnectorRow>> {
  const { data } = await http.post<Paginated<ConnectorRow>>('/connectors/out/paginate', {
    page: query.page,
    paginationSize: query.paginationSize,
    search: query.search?.trim() || null,
    orderBy: 'id',
    orderDirection: 1,
  })

  return {
    count: Number(data?.count) || 0,
    rows: Array.isArray(data?.rows) ? data.rows : [],
  }
}

export async function getConnector(id: number): Promise<ConnectorDetail> {
  const { data } = await http.get<ConnectorDetail>(`/connectors/out/${id}`)
  return data
}

export async function createConnector(input: MqttConnectorInput): Promise<ConnectorDetail> {
  const { data } = await http.post<ConnectorDetail>('/connectors/out/mqtt', input)
  return data
}

export async function updateConnector(id: number, input: MqttConnectorInput): Promise<ConnectorDetail> {
  const { data } = await http.put<ConnectorDetail>(`/connectors/out/mqtt/${id}`, input)
  return data
}

/** Sustituye las entidades asociadas: las que no van en la lista dejan de enviarse. */
export async function linkEntities(id: number, entityIds: number[]): Promise<void> {
  await http.put(`/connectors/out/${id}/models`, { entities: entityIds })
}

/** Borra el conector con su configuracion y credenciales; deja de enviar en el acto. */
export async function deleteConnector(id: number): Promise<void> {
  await http.delete(`/connectors/out/${id}`)
}

/** Activar pone a cero los fallos acumulados: el conector vuelve a empezar. */
export async function setConnectorStatus(
  id: number,
  status: 'active' | 'inactive',
): Promise<ConnectorDetail> {
  const { data } = await http.patch<ConnectorDetail>(`/connectors/out/${id}/status`, { status })
  return data
}

export async function listConnectorErrors(
  id: number,
  page: number,
  paginationSize = 10,
): Promise<Paginated<LogLine>> {
  const { data } = await http.post<Paginated<LogLine>>('/logs/paginate', {
    resource_type: 'out_connectors',
    resource_id: [id],
    level: 'ERROR',
    page,
    paginationSize,
    orderBy: 'id',
    // 0 se traduce en orden descendente: la primera pagina trae los errores mas recientes.
    orderDirection: 0,
  })

  return {
    count: Number(data?.count) || 0,
    rows: Array.isArray(data?.rows) ? data.rows : [],
  }
}
