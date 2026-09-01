/**
 * Utilidades de accesibilidad compartidas.
 *
 * Estan aqui, y no repetidas en cada vista, porque el criterio WCAG 2.1.1 (teclado) se incumple
 * siempre de la misma manera: un elemento que responde a `@click` y a nada mas. La respuesta es
 * tambien siempre la misma —hacerlo enfocable y atender Intro y espacio—, asi que conviene que
 * haya un unico sitio donde esa respuesta este escrita y probada.
 */

/** Teclas que activan un control segun la practica de la plataforma web. */
const ACTIVATION_KEYS = new Set(['Enter', ' ', 'Spacebar'])

/**
 * Convierte un manejador de activacion en un manejador de teclado.
 *
 * El espacio se intercepta (`preventDefault`) porque su comportamiento por defecto es desplazar
 * la pagina: sin eso, activar una fila con la barra espaciadora ademas mueve la vista.
 */
export function activateOnKey(handler: () => void): (event: KeyboardEvent) => void {
  return (event: KeyboardEvent) => {
    if (!ACTIVATION_KEYS.has(event.key)) return
    event.preventDefault()
    handler()
  }
}

export interface RowContext<T> {
  item: T
}

/**
 * Props para las filas de una `VDataTable` que actuan como enlace.
 *
 * Vuetify ofrece `@click:row`, pero deja la fila sin `tabindex` y sin manejador de teclado: con
 * el raton se abre el detalle y con el teclado no hay forma de llegar (hallazgo
 * GDTIS-PT01-ACC-004). Esto devuelve la fila al recorrido de tabulacion y le da la activacion
 * por Intro y espacio, sin tocar la semantica de tabla —no se le pone `role`, que romperia la
 * lectura por celdas de un lector de pantalla—.
 */
export function clickableRowProps<T>(
  open: (item: T) => void,
): (context: RowContext<T>) => Record<string, unknown> {
  return ({ item }: RowContext<T>) => ({
    class: 'cursor-pointer',
    tabindex: 0,
    onKeydown: activateOnKey(() => open(item)),
  })
}
