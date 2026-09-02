import { ref, type Ref } from 'vue'
import { errorMessage } from '@/api/http'
import type { Paginated } from '@/types'

export interface PaginatedListOptions<T> {
  /**
   * Se llama tras cada respuesta aceptada, con las filas recien cargadas y un `isCurrent()` que
   * dice si la carga sigue siendo la vigente. Sirve para encadenar una peticion secundaria
   * (p. ej. la marca de ultimo dato) sin escribir estado de una carga que ya quedo atras.
   */
  onLoaded?: (rows: T[], isCurrent: () => boolean) => void
  /**
   * Valor inicial de `loading`. Por defecto `true`, para que la primera carga muestre el
   * esqueleto sin un parpadeo de estado vacio. Se pone en `false` cuando la vista arranca vacia
   * y solo carga mas tarde (p. ej. en `onMounted`).
   */
  initialLoading?: boolean
}

export interface PaginatedList<T> {
  rows: Ref<T[]>
  /** Total declarado por el servidor, no el numero de filas de esta pagina. */
  total: Ref<number>
  /** Verdadero mientras hay una carga en vuelo. Arranca en `true`: la primera carga es inmediata. */
  loading: Ref<boolean>
  error: Ref<string | null>
  /** Lanza `fetcher`. Reentrante: una respuesta lenta anterior no pisa a una posterior. */
  load: () => Promise<void>
}

/**
 * Estado y carga de un listado paginado desde servidor. Recoge el patron que repetian las vistas
 * de listado: `rows` / `total` / `loading` / `error`, mas una carga con guarda de secuencia para
 * que una respuesta lenta de una consulta anterior no sobrescriba la actual.
 *
 * La vista conserva sus propios refs de pagina, tamano y filtros y decide cuando llamar a `load`
 * (por lo general desde un `watch` sobre esos refs); `fetcher` los lee en el momento de cada
 * llamada, asi que siempre pide con los valores vigentes.
 */
export function usePaginatedList<T>(
  fetcher: () => Promise<Paginated<T>>,
  options: PaginatedListOptions<T> = {},
): PaginatedList<T> {
  const rows = ref<T[]>([]) as Ref<T[]>
  const total = ref(0)
  const loading = ref(options.initialLoading ?? true)
  const error = ref<string | null>(null)

  // Cada carga lleva su numero: una respuesta lenta de una consulta anterior no debe pisar la actual.
  let sequence = 0

  async function load() {
    const current = ++sequence
    loading.value = true
    error.value = null
    try {
      const result = await fetcher()
      if (current !== sequence) return
      rows.value = result.rows
      total.value = result.count
      options.onLoaded?.(result.rows, () => current === sequence)
    } catch (e) {
      if (current !== sequence) return
      rows.value = []
      total.value = 0
      error.value = errorMessage(e)
    } finally {
      if (current === sequence) loading.value = false
    }
  }

  return { rows, total, loading, error, load }
}
