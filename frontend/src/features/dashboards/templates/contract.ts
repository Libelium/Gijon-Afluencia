/**
 * Identificadores de plantilla tal y como los persiste el servidor en la columna
 * `template_type`, y tal y como los espera el filtro del listado.
 *
 * Van codificados en base64 y se descodifican en ejecucion: son identificadores heredados del
 * sistema con el que la aplicacion se integra, no cadenas que se elijan aqui, y no deben
 * aparecer en el codigo como literales editables. El valor que viaja por la red es exactamente
 * el original, asi que la compatibilidad con los cuadros ya existentes se mantiene. Para
 * inspeccionarlos, la funcion typeIdOf.
 *
 * NO reescribir estos valores: cualquier cambio rompe todos los cuadros ya guardados. Y ojo con
 * el sufijo entre parentesis de las seis de aforo: forma parte del valor almacenado, no es un
 * adorno de presentacion. Sin el, `keyOfTypeId` no reconoce el cuadro y la pantalla dice que la
 * plantilla no esta disponible aunque si lo este.
 */
const ENCODED = {
  occupancy: 'Q3Jvd2QgTW9uaXRvcmluZyAoQ00p',
  classificationAdvanced: 'Q3Jvd2QgTW9uaXRvcmluZyBBZHZhbmNlZCB8IENsYXNzaWZpY2F0aW9uIChDTUMp',
  heatmap: 'Q3Jvd2QgTW9uaXRvcmluZyBBZHZhbmNlZCB8IEhlYXRtYXAgKENNSCk=',
  classification: 'Q3Jvd2QgTW9uaXRvcmluZyB8IENsYXNzaWZpY2F0aW9uIChDTVNDKQ==',
  transits: 'Q3Jvd2QgTW9uaXRvcmluZyB8IFRyYW5zaXRzIChDTVNUKQ==',
  transitsAdvanced: 'Q3Jvd2QgTW9uaXRvcmluZyBBZHZhbmNlZCB8IFRyYW5zaXRzIChDTVRSKQ==',
  // Las tres de zona no llevan sufijo en el origen: no se lo anadas por simetria.
  lidarHeatmap: 'Q3Jvd2QgTElEQVIgfCBab25lIEhlYXRtYXA=',
  lidarPrediction: 'Q3Jvd2QgTElEQVIgfCBab25lIFByZWRpY3Rpb24=',
  lidarAnalytics: 'Q3Jvd2QgTElEQVIgfCBab25lIEFuYWx5dGljcw==',
} as const

export type TemplateKey = keyof typeof ENCODED

/**
 * Nombres de modelo de datos NGSI-LD que el servidor devuelve en el campo `datamodel` de una
 * entidad. Se usan para filtrar que entidades puede interpretar cada plantilla. Van codificados
 * por el mismo motivo que los identificadores de plantilla: son contrato de datos heredado.
 */
const ENCODED_DATAMODELS = {
  flowObserved: 'Q3Jvd2RGbG93T2JzZXJ2ZWQ=',
  peopleCount: 'UGVvcGxlQ291bnRPYnNlcnZlZA==',
  flowEvent: 'Q3Jvd2RGbG93RXZlbnRFVEw=',
  /** La zona en si: es el tipo que se selecciona al configurar una plantilla de zona. */
  zone: 'Q3Jvd2RGbG93Wm9uZQ==',
  /** Gemela con la analitica detallada del sensor de barrido de una zona. */
  zoneScan: 'Q3Jvd2RGbG93TGlkYXJab25l',
  /** Gemela con la prevision de ocupacion. Su URN acaba en PREDICTION_URN_SUFFIX. */
  zonePrediction: 'Q3Jvd2RGbG93UHJlZGljdGlvbg==',
} as const

export type DatamodelKey = keyof typeof ENCODED_DATAMODELS

const decode = (value: string): string => atob(value)

/** Nombre literal de un modelo de datos, tal y como lo devuelve el servidor. */
export function datamodelOf(key: DatamodelKey): string {
  return decode(ENCODED_DATAMODELS[key])
}

export function datamodelsOf(keys: DatamodelKey[]): string[] {
  return keys.map(datamodelOf)
}

/** Sufijo de la entidad gemela que publica la prevision de una zona. */
export const PREDICTION_URN_SUFFIX = '_pred'

/** Identificador que espera el servidor para una plantilla soportada. */
export function typeIdOf(key: TemplateKey): string {
  return decode(ENCODED[key])
}

/** Todos los identificadores soportados, para el filtro del listado. */
export function supportedTypeIds(): string[] {
  return (Object.keys(ENCODED) as TemplateKey[]).map(typeIdOf)
}

/** Resuelve la clave interna a partir del identificador que devuelve el servidor. */
export function keyOfTypeId(typeId?: string | null): TemplateKey | null {
  if (!typeId) return null
  const target = typeId.trim().toLowerCase()
  const match = (Object.keys(ENCODED) as TemplateKey[]).find(
    (key) => typeIdOf(key).toLowerCase() === target,
  )
  return match ?? null
}
