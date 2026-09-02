import { onScopeDispose } from 'vue'

export interface DebouncedFn<A extends unknown[]> {
  (...args: A): void
  /** Cancela una ejecucion pendiente, si la hay. */
  cancel(): void
}

/**
 * Envuelve `fn` en un rebote: cada llamada reinicia la espera de `delay` ms y solo se ejecuta
 * cuando pasan sin que llegue otra llamada. Sirve para no lanzar una peticion por cada pulsacion
 * de teclado ni por cada evento de redimension.
 *
 * Se cancela sola al destruirse el ambito reactivo donde se crea (el componente), asi que no hace
 * falta un `onBeforeUnmount` que limpie el temporizador. `cancel()` la detiene a mano cuando hay
 * que descartar una espera en vuelo (p. ej. al limpiar el filtro antes de que salte).
 */
export function useDebounceFn<A extends unknown[]>(
  fn: (...args: A) => void,
  delay: number,
): DebouncedFn<A> {
  let timer: ReturnType<typeof setTimeout> | undefined

  const cancel = () => {
    if (timer !== undefined) {
      clearTimeout(timer)
      timer = undefined
    }
  }

  const debounced = ((...args: A) => {
    cancel()
    timer = setTimeout(() => {
      timer = undefined
      fn(...args)
    }, delay)
  }) as DebouncedFn<A>

  debounced.cancel = cancel
  onScopeDispose(cancel)

  return debounced
}
