/** Zoom al que se acerca el mapa al elegir una entidad: el de calle, donde se distinguen sus vecinas. */
export const FOCUS_ZOOM = 17

/** Zoom al que llevar el mapa al elegir una entidad, o null si ya esta igual de cerca o mas. */
export function focusZoom(current: number): number | null {
  return current < FOCUS_ZOOM ? FOCUS_ZOOM : null
}

export interface LoadOutcome {
  /** Entidades que cumplen los filtros en el area visible. */
  count: number
  /** Es la primera carga de la vista. */
  first: boolean
  /** La carga la ha provocado un cambio de filtros, no un movimiento del mapa. */
  byFilter: boolean
  /** Hay algun filtro aplicado. */
  filtered: boolean
}

/**
 * Si hay que llevar el mapa a donde estan los datos. Solo cuando la vista sale vacia y nadie la ha
 * elegido: en la primera carga el centro es el configurado, no donde hay datos, y quien filtra busca
 * algo concreto. Si el usuario arrastra el mapa a una zona vacia lo ha hecho a proposito.
 */
export function shouldLocate({ count, first, byFilter, filtered }: LoadOutcome): boolean {
  if (count > 0) return false
  return (first && !filtered) || (byFilter && filtered)
}

/**
 * Lo que tarda como mucho el reagrupamiento animado de los marcadores. Pasado este tiempo sin que
 * avise de que ha terminado, se da por hecho.
 */
export const REGROUP_FALLBACK_MS = 600

/** Lo que se usa de un objeto de Leaflet que emite eventos. */
interface Evented {
  once(type: string, fn: () => void): unknown
  off(type: string, fn: () => void): unknown
}

/**
 * Llama a `done` una sola vez: con el primer `type` que emita `target` o, si no llega, pasados `ms`.
 * Hace falta porque markercluster solo anima el reagrupamiento cuando la zona de destino se solapa
 * con la que habia: al saltar lejos reagrupa sin animar y nunca emite `animationend`.
 */
export function onceOrAfter(target: Evented, type: string, ms: number, done: () => void): void {
  // Lo que llegue primero anula lo otro: el evento cancela el plazo y el plazo deja de escucharlo.
  const run = () => {
    clearTimeout(timer)
    target.off(type, run)
    done()
  }
  const timer = setTimeout(run, ms)
  target.once(type, run)
}
