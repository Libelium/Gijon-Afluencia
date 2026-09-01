import axios from 'axios'
import { http } from '@/api/http'
import { env } from '@/lib/env'
import type { CustomizationValues, CustomizationPreference } from '@/customization/preferences'

/**
 * Preferencias de organizacion. Son distintas de las de usuario (`api/user.ts`): estas valen para
 * todo el mundo de la organizacion, y solo las puede escribir quien tenga permiso sobre ella.
 */

export type OrganizationPreferences = Record<string, string | null>

export async function getPreferences(orgId: number): Promise<OrganizationPreferences> {
  const { data } = await http.get<OrganizationPreferences>(`/organizations/${orgId}/preferences`)
  return data
}

/** Una preferencia por peticion, igual que en las de usuario. Un valor invalido devuelve 422. */
export async function savePreference(
  orgId: number,
  name: CustomizationPreference,
  value: string,
): Promise<void> {
  await http.put(`/organizations/${orgId}/preferences/${name}`, { value })
}

export async function deletePreference(
  orgId: number,
  name: CustomizationPreference,
): Promise<void> {
  await http.delete(`/organizations/${orgId}/preferences/${name}`)
}

/**
 * Preferencias publicas de una organizacion, SIN sesion.
 *
 * Se usa en la pantalla de inicio de sesion, que se pinta antes de tener token: si se pidiera con
 * el cliente autenticado, el interceptor trataria el 401 como sesion caducada y forzaria un ciclo
 * de login. Por eso va con una instancia limpia de axios y sin cabecera Authorization.
 */
export async function getPublicPreferences(orgId: number): Promise<OrganizationPreferences> {
  const { data } = await axios.get<OrganizationPreferences>(
    `${env('VITE_API_BASE_URL')}/api/V1/publicOrganizations/${orgId}/preferences`,
    { timeout: 15_000 },
  )
  return data
}

/**
 * URL de la imagen de una preferencia, servida como imagen de verdad por el backend.
 *
 * Se devuelve la URL en lugar del data URI para que la pinte el navegador con su propia cache: el
 * mismo camino que usa el tema de Keycloak (`dynamicLogo.js`) para el logotipo del login.
 */
export function preferenceImageUrl(orgId: number, name: CustomizationPreference): string {
  return `${env('VITE_API_BASE_URL')}/api/V1/publicOrganizations/${orgId}/preferences/${name}/image`
}

/** Quedarse solo con lo que compone la personalizacion, descartando el resto de preferencias. */
export function pickCustomization(
  all: OrganizationPreferences,
  names: readonly CustomizationPreference[],
): CustomizationValues {
  const out: CustomizationValues = {}
  for (const name of names) {
    const value = all[name]
    if (typeof value === 'string' && value.trim() !== '') out[name] = value
  }
  return out
}
