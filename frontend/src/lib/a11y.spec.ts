import { describe, expect, it, vi } from 'vitest'
import { activateOnKey, clickableRowProps } from './a11y'

const keydown = (key: string) => new KeyboardEvent('keydown', { key, cancelable: true })

describe('activateOnKey', () => {
  it('activa con Intro y con espacio, que son las teclas de la plataforma', () => {
    const handler = vi.fn()
    const onKeydown = activateOnKey(handler)
    onKeydown(keydown('Enter'))
    onKeydown(keydown(' '))
    expect(handler).toHaveBeenCalledTimes(2)
  })

  it('ignora cualquier otra tecla: tabular o escribir no debe abrir nada', () => {
    const handler = vi.fn()
    const onKeydown = activateOnKey(handler)
    for (const key of ['Tab', 'a', 'Escape', 'ArrowDown']) onKeydown(keydown(key))
    expect(handler).not.toHaveBeenCalled()
  })

  it('detiene el espacio para que no desplace la pagina al activar', () => {
    const event = keydown(' ')
    activateOnKey(() => {})(event)
    expect(event.defaultPrevented).toBe(true)
  })

  it('no detiene las teclas que no le competen', () => {
    const event = keydown('Tab')
    activateOnKey(() => {})(event)
    expect(event.defaultPrevented).toBe(false)
  })
})

/** GDTIS-PT01-ACC-004: la fila pulsable necesita equivalente de teclado (WCAG 2.1.1). */
describe('clickableRowProps', () => {
  const item = { id: 7 }

  it('devuelve la fila al recorrido de tabulacion', () => {
    const props = clickableRowProps(() => {})({ item })
    expect(props.tabindex).toBe(0)
  })

  it('conserva el cursor de mano, que es lo que anuncia que la fila es pulsable', () => {
    expect(clickableRowProps(() => {})({ item }).class).toBe('cursor-pointer')
  })

  it('activar con teclado abre EL MISMO elemento que abriria el raton', () => {
    const open = vi.fn()
    const props = clickableRowProps<{ id: number }>(open)({ item })
    ;(props.onKeydown as (event: KeyboardEvent) => void)(keydown('Enter'))
    expect(open).toHaveBeenCalledWith(item)
  })

  it('no pone `role`: cambiarlo romperia la lectura por celdas de la tabla', () => {
    expect(clickableRowProps(() => {})({ item }).role).toBeUndefined()
  })
})
