import { onBeforeUnmount, ref, watch } from 'vue'

// Se guarda en el navegador, no como preferencia de cuenta: «cada cuánto refresca esta pantalla»
// es un ajuste por dispositivo (una pantalla fija y un portátil quieren cadencias distintas).
const STORAGE_KEY = 'iris360-dashboard-auto-refresh'

/** Minutos entre refrescos. `0` es «desactivado» y es el valor por defecto que exige WCAG 2.2.2. */
export const AUTO_REFRESH_INTERVALS = [0, 1, 5, 10] as const
export type AutoRefreshMinutes = (typeof AUTO_REFRESH_INTERVALS)[number]

function readStored(): AutoRefreshMinutes {
  try {
    const raw = Number(localStorage.getItem(STORAGE_KEY))
    if ((AUTO_REFRESH_INTERVALS as readonly number[]).includes(raw)) {
      return raw as AutoRefreshMinutes
    }
  } catch {
    // Sin localStorage (modo privado, almacenamiento bloqueado): queda desactivado.
  }
  return 0
}

function writeStored(minutes: AutoRefreshMinutes): void {
  try {
    localStorage.setItem(STORAGE_KEY, String(minutes))
  } catch {
    // Sin persistencia el valor sigue vivo en memoria durante la sesión; no es un error.
  }
}

/**
 * Refresco automático de un panel, opt-in y pausable (WCAG 2.2.2 «Pause, Stop, Hide»): arranca
 * desactivado, el usuario elige la cadencia y puede volver a «Desactivado», que es a la vez parar
 * y controlar la frecuencia. Nunca refresca con la pestaña oculta —ahorra peticiones— ni cuando
 * `paused()` lo indica (una carga en curso, para no solapar; un rango fijo, que no cambia).
 */
export function useAutoRefresh(onTick: () => void, paused: () => boolean) {
  const minutes = ref<AutoRefreshMinutes>(readStored())
  let timer: ReturnType<typeof setInterval> | undefined

  function stop(): void {
    if (timer !== undefined) {
      clearInterval(timer)
      timer = undefined
    }
  }

  function start(): void {
    stop()
    if (minutes.value === 0) return
    timer = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return
      if (paused()) return
      onTick()
    }, minutes.value * 60_000)
  }

  watch(minutes, (value) => {
    writeStored(value)
    start()
  })

  start()
  onBeforeUnmount(stop)

  return { minutes }
}
