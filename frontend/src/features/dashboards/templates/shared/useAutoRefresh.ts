import { onBeforeUnmount, ref, watch } from 'vue'

// Se guarda en el navegador, no como preferencia de cuenta: «si esta pantalla se refresca sola»
// es un ajuste por dispositivo (una pantalla fija y un portátil quieren cosas distintas).
const STORAGE_KEY = 'iris360-dashboard-auto-refresh'

/** Cadencia fija del modo automático. No hay push: se sondea cada minuto. */
export const AUTO_REFRESH_INTERVAL_MS = 60_000

function readStored(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'on'
  } catch {
    // Sin localStorage (modo privado, almacenamiento bloqueado): queda desactivado.
    return false
  }
}

function writeStored(enabled: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? 'on' : 'off')
  } catch {
    // Sin persistencia el valor sigue vivo en memoria durante la sesión; no es un error.
  }
}

/**
 * Refresco automático de un panel, opt-in y pausable (WCAG 2.2.2 «Pause, Stop, Hide»): arranca
 * desactivado y el usuario lo activa; «Desactivado» es a la vez parar el refresco. Mientras está
 * activo vuelve a pedir los datos cada minuto, nunca con la pestaña oculta —ahorra peticiones— ni
 * cuando `paused()` lo indica (una carga en curso, para no solapar; un rango fijo, que no cambia).
 */
export function useAutoRefresh(onTick: () => void, paused: () => boolean) {
  const enabled = ref<boolean>(readStored())
  let timer: ReturnType<typeof setInterval> | undefined

  function stop(): void {
    if (timer !== undefined) {
      clearInterval(timer)
      timer = undefined
    }
  }

  function start(): void {
    stop()
    if (!enabled.value) return
    timer = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return
      if (paused()) return
      onTick()
    }, AUTO_REFRESH_INTERVAL_MS)
  }

  watch(enabled, (value) => {
    writeStored(value)
    start()
  })

  start()
  onBeforeUnmount(stop)

  return { enabled }
}
