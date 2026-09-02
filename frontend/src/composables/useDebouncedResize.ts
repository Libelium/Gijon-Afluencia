import { onMounted, onScopeDispose, type Ref } from 'vue'
import { useDebounceFn } from './useDebounce'

function sizeKey(el: HTMLElement): string {
  return `${Math.round(el.clientWidth)}x${Math.round(el.clientHeight)}`
}

/**
 * Observa el tamaño de `target` y llama a `onResize` (rebotado `delay` ms) solo cuando cambia de
 * veras. Observar el contenedor cubre a la vez el plegado del menu lateral, el giro del movil y el
 * redimensionado de la ventana sin acoplarse a ninguno; el filtro por tamaño evita repetir el
 * trabajo cuando el navegador dispara el observador sin que las dimensiones hayan cambiado.
 *
 * Se monta con el componente y se desconecta al destruirse su ambito, sin necesidad de limpiar a
 * mano ni el observador ni el temporizador.
 */
export function useDebouncedResize(
  target: Ref<HTMLElement | null>,
  onResize: () => void,
  delay: number,
): void {
  let observer: ResizeObserver | undefined
  let lastSize = ''
  const run = useDebounceFn(onResize, delay)

  function handle() {
    const el = target.value
    if (!el) return
    const key = sizeKey(el)
    if (key === lastSize) return
    lastSize = key
    run()
  }

  onMounted(() => {
    const el = target.value
    if (!el || typeof ResizeObserver === 'undefined') return
    lastSize = sizeKey(el)
    observer = new ResizeObserver(handle)
    observer.observe(el)
  })

  onScopeDispose(() => observer?.disconnect())
}
