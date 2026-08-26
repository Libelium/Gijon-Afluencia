import { http } from '@/api/http'
import type { UserPreferences } from '@/types'

export async function getPreferences(userId: number): Promise<UserPreferences> {
  const { data } = await http.get<UserPreferences>(`/user/${userId}/preferences`)
  return data
}

/** El backend acepta una sola preferencia por peticion y valida el valor (puede devolver 422). */
export async function savePreference(userId: number, name: string, value: string): Promise<void> {
  await http.put(`/user/${userId}/preferences/${name}`, { value })
}
