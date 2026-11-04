import { t } from '@/i18n'
import type { ConnectorRow, PayloadType, TopicPart } from '../types'

/** Formatos que se envian cada cierto tiempo con todas las lecturas en un mensaje. */
export const SNAPSHOT_PAYLOAD_TYPES: PayloadType[] = [
  'occupancy_readings',
  'flow_readings',
  'device_inventory',
]

const PAYLOAD_TYPES: PayloadType[] = [...SNAPSHOT_PAYLOAD_TYPES, 'normalized', 'key_value', 'legacy']

export function isSnapshot(type?: string): boolean {
  return SNAPSHOT_PAYLOAD_TYPES.includes(type as PayloadType)
}

export function isPayloadType(type?: string): type is PayloadType {
  return PAYLOAD_TYPES.includes(type as PayloadType)
}

export function payloadTypeLabel(type?: string): string {
  return isPayloadType(type) ? t(`connectors.payload.${type}`) : (type || '—')
}

export function payloadTypeOptions(): Array<{ value: PayloadType; title: string; subtitle: string }> {
  return PAYLOAD_TYPES.map((value) => ({
    value,
    title: t(`connectors.payload.${value}`),
    subtitle: t(`connectors.payload.${value}Hint`),
  }))
}

/**
 * Variables de topic que el servidor sabe sustituir con cada formato. Mismo criterio que la
 * validacion del backend: una foto lleva muchas entidades, y con {id} se envia un mensaje por
 * cada una (zona, sensor de origen o dispositivo) a su propio subtopic.
 */
export function topicVariables(type?: string): string[] {
  if (isSnapshot(type)) return ['id']
  if (type === 'legacy') return ['urn', 'tenant', 'scope', 'measure']
  return ['urn', 'tenant', 'scope']
}

/** «planta/{tenant}/datos» → partes fijas y variables, como las guarda el servidor. */
export function parseTopic(text: string): TopicPart[] {
  const parts: TopicPart[] = []
  const pattern = /\{(\w+)\}/g
  let last = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) parts.push({ type: 'static', value: text.slice(last, match.index) })
    parts.push({ type: 'variable', value: match[1] })
    last = match.index + match[0].length
  }
  if (last < text.length) parts.push({ type: 'static', value: text.slice(last) })

  return parts
}

export function formatTopic(parts?: TopicPart[] | null): string {
  return (parts ?? [])
    .map((part) => (part.type === 'variable' ? `{${part.value}}` : part.value))
    .join('')
}

/** Mensaje de error del topic, o undefined si es valido para ese formato. */
export function topicError(text: string, type?: string): string | undefined {
  if (!text.trim()) return t('connectors.form.topicRequired')
  if (/[#+]/.test(text)) return t('connectors.form.topicWildcard')

  const allowed = topicVariables(type)
  const used = parseTopic(text).filter((part) => part.type === 'variable')
  const unknown = used.find((part) => !allowed.includes(part.value))
  if (!unknown) return undefined

  return t('connectors.form.topicVariables', { variables: allowed.map((v) => `{${v}}`).join(', ') })
}

/** Solo host o IP: ni esquema, ni ruta, ni credenciales, igual que valida el servidor. */
export function hostError(host: string): string | undefined {
  const value = host.trim()
  if (!value) return t('connectors.form.hostRequired')
  if (!/^[A-Za-z0-9.\-:[\]]+$/.test(value)) return t('connectors.form.hostInvalid')
  return undefined
}

const PEM_CERTIFICATE = /-----BEGIN CERTIFICATE-----/
const PEM_PRIVATE_KEY = /-----BEGIN ([A-Z]+ )?PRIVATE KEY-----/

export interface ClientCertificateErrors {
  certificate?: string
  key?: string
}

/**
 * Certificado y clave del cliente van juntos. Al editar, la clave guardada no se devuelve:
 * vacia con `hasStoredKey` significa conservarla, igual que decide el servidor.
 */
export function clientCertificateErrors(
  certificate: string,
  key: string,
  hasStoredKey: boolean,
  tls: boolean,
): ClientCertificateErrors {
  const cert = certificate.trim()
  const pem = key.trim()
  const errors: ClientCertificateErrors = {}

  if (!cert && !pem) return errors
  if (!tls) errors.certificate = t('connectors.form.clientCertNeedsTls')
  else if (!cert) errors.certificate = t('connectors.form.clientCertMissing')
  else if (!PEM_CERTIFICATE.test(cert)) errors.certificate = t('connectors.form.clientCertInvalid')

  if (pem && !PEM_PRIVATE_KEY.test(pem)) errors.key = t('connectors.form.clientKeyInvalid')
  else if (cert && !pem && !hasStoredKey) errors.key = t('connectors.form.clientKeyMissing')

  return errors
}

export function portError(port: unknown): string | undefined {
  const value = Number(port)
  return Number.isInteger(value) && value >= 1 && value <= 65535
    ? undefined
    : t('connectors.form.portInvalid')
}

export interface ConnectorStatusView {
  key: 'active' | 'failing' | 'inactive'
  label: string
  hint: string
  icon: string
  color?: 'success' | 'warning'
}

/**
 * Estado del conector en un solo dato. Un conector activo con fallos seguidos sigue enviando
 * (reintenta en cada envio), pero conviene verlo: si los fallos continuan, el servidor lo
 * desactiva solo.
 */
export function connectorStatus(row: Pick<ConnectorRow, 'status' | 'retries'>): ConnectorStatusView {
  if (row.status === 'active' && !(Number(row.retries) > 0)) {
    return {
      key: 'active',
      label: t('connectors.state.active'),
      hint: t('connectors.state.activeHint'),
      icon: 'mdi-check-circle-outline',
      color: 'success',
    }
  }
  if (row.status === 'active' || row.status === 'error') {
    return {
      key: 'failing',
      label: t('connectors.state.failing'),
      hint: t('connectors.state.failingHint', { count: Number(row.retries) || 0 }),
      icon: 'mdi-alert-outline',
      color: 'warning',
    }
  }
  return {
    key: 'inactive',
    label: t('connectors.state.inactive'),
    hint: t('connectors.state.inactiveHint'),
    icon: 'mdi-pause-circle-outline',
  }
}
