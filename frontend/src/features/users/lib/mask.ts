/**
 * Ofuscado de datos personales para mostrar en pantalla (capturas, proyecciones, puestos
 * compartidos). Es solo presentacion: quien administra la organizacion tiene derecho a los datos
 * y el servidor los envia completos.
 *
 * Se conserva la primera letra de cada parte y la longitud aproximada no se revela: siempre tres
 * puntos, de modo que "Ana" y "Anastasia" no se distinguen por el tamano del hueco.
 */

const DOTS = '•••'

function maskWord(word: string): string {
  const first = Array.from(word)[0]
  return first ? `${first}${DOTS}` : ''
}

/** "Maria Lopez Garcia" -> "M••• L••• G•••". */
export function maskName(name: string | null | undefined): string {
  if (!name) return '—'
  return name.trim().split(/\s+/).filter(Boolean).map(maskWord).join(' ') || '—'
}

/**
 * "maria.lopez@gijon.es" -> "m•••@g•••.es". Se deja el dominio de primer nivel, que no
 * identifica a nadie y ayuda a distinguir cuentas internas de externas.
 */
export function maskEmail(email: string | null | undefined): string {
  if (!email) return '—'
  const at = email.lastIndexOf('@')
  if (at <= 0) return maskWord(email)

  const local = email.slice(0, at)
  const domain = email.slice(at + 1)
  const dot = domain.lastIndexOf('.')
  const host = dot > 0 ? domain.slice(0, dot) : domain
  const tld = dot > 0 ? domain.slice(dot) : ''

  return `${maskWord(local)}@${maskWord(host)}${tld}`
}

/** Iniciales para el avatar: tambien delatan a la persona, asi que se ocultan con el resto. */
export function initialsOf(name: string | null | undefined, masked: boolean): string {
  if (masked || !name) return '•'
  const parts = name.trim().split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '•'
}
