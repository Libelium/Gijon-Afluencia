import { http } from '@/api/http'

/** El manual de la plataforma en PDF, que el backend sirve desde el almacenamiento. */
export async function fetchManual(): Promise<Blob> {
  const { data } = await http.get<Blob>('/documentation', { responseType: 'blob' })
  return data
}
