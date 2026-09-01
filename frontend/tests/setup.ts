/**
 * Arranque comun de las pruebas.
 *
 * jsdom no implementa ni `ResizeObserver` ni `matchMedia`, y Vuetify consulta los dos al montar
 * cualquier componente (el primero para el tamano del contenedor, el segundo para el modo de
 * pantalla y la preferencia de tema del sistema). Sin estos sustitutos, montar un componente
 * falla antes de llegar a la asercion.
 */

class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver

if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
}

// El navegador aplica `visibility` de verdad; jsdom no. Da igual para lo que se comprueba aqui,
// pero Vuetify emite avisos si falta.
if (typeof window !== 'undefined' && !window.visualViewport) {
  Object.defineProperty(window, 'visualViewport', {
    value: { width: 1280, height: 800, addEventListener: () => {}, removeEventListener: () => {} },
    writable: true,
  })
}

/**
 * jsdom no dibuja: `canvas.getContext` lanza «Not implemented» salvo que se instale el paquete
 * nativo `canvas`, y sin contexto no se puede ni MONTAR un grafico de ECharts. Como aqui nunca
 * se comprueban pixeles —las pruebas de graficos miran atributos del DOM y datos—, basta con un
 * contexto que acepte todas las ordenes de dibujo sin hacer nada y que sepa medir texto.
 *
 * Se implementa con un proxy para no tener que enumerar las mas de sesenta operaciones de la
 * API de lienzo: cualquier metodo desconocido es una funcion vacia, y las propiedades de estilo
 * (`fillStyle`, `lineWidth`…) se guardan y se devuelven como en un objeto normal.
 */
const AVERAGE_GLYPH_WIDTH = 6

function createContext2dStub(canvas: HTMLCanvasElement): CanvasRenderingContext2D {
  const state: Record<string, unknown> = { canvas }
  const noop = () => {}
  const gradient = { addColorStop: noop }

  return new Proxy(state, {
    get(target, property: string) {
      if (property in target) return target[property]
      if (property === 'measureText') {
        return (text: string) => ({ width: String(text).length * AVERAGE_GLYPH_WIDTH })
      }
      if (property === 'createLinearGradient' || property === 'createRadialGradient') {
        return () => gradient
      }
      if (property === 'createPattern') return () => null
      if (property === 'getImageData') {
        return (_x: number, _y: number, w = 1, h = 1) => ({
          data: new Uint8ClampedArray(Math.max(1, w * h) * 4),
          width: w,
          height: h,
        })
      }
      return noop
    },
    set(target, property: string, value) {
      target[property] = value
      return true
    },
  }) as unknown as CanvasRenderingContext2D
}

if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = function getContext(this: HTMLCanvasElement) {
    return createContext2dStub(this)
  } as unknown as typeof HTMLCanvasElement.prototype.getContext
}

/**
 * jsdom no hace maquetacion, asi que TODO elemento mide 0x0 y ECharts avisa de que no puede
 * calcular el tamano del lienzo. Se le da una medida plausible para que el grafico se construya
 * de verdad y la prueba compruebe algo. Ninguna asercion depende de estas cifras.
 */
const VIEWPORT = { clientWidth: 800, clientHeight: 400, offsetWidth: 800, offsetHeight: 400 }

for (const [property, value] of Object.entries(VIEWPORT)) {
  Object.defineProperty(HTMLElement.prototype, property, {
    configurable: true,
    get: () => value,
  })
}

// jsdom no desplaza la vista y no implementa `scrollIntoView`. Lo llama, por ejemplo, el enlace
// de salto al contenido despues de mover el foco, que es lo que si se comprueba.
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}
