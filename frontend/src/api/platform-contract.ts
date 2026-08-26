import { env } from '@/lib/env'

/**
 * Identificadores tecnicos que espera el backend con el que se integra esta aplicacion.
 * No son nombres de producto ni de marca: son claves de datos ya existentes en ese sistema,
 * y por eso se leen de la configuracion en lugar de estar escritas aqui. Si faltan, la
 * funcionalidad que depende de ellas se degrada de forma explicita, nunca en silencio.
 */

/** Clave de la preferencia de usuario que fija el ambito de datos. La necesita el historico de alarmas. */
export const DATA_SCOPE_PREFERENCE_KEY = env('VITE_DATA_SCOPE_PREFERENCE_KEY')

/** Tipo de entidad NGSI-LD bajo el que el backend publica el estado de una alarma. */
export const ALARM_ENTITY_TYPE = env('VITE_ALARM_ENTITY_TYPE')

export function alarmStateUrn(alarmId: number | string): string | null {
  if (!ALARM_ENTITY_TYPE) return null
  return `urn:ngsi-ld:${ALARM_ENTITY_TYPE}:${alarmId}`
}

export function missingContractKeys(): string[] {
  const missing: string[] = []
  if (!DATA_SCOPE_PREFERENCE_KEY) missing.push('VITE_DATA_SCOPE_PREFERENCE_KEY')
  if (!ALARM_ENTITY_TYPE) missing.push('VITE_ALARM_ENTITY_TYPE')
  return missing
}
