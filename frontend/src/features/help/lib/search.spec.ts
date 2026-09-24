import { describe, expect, it } from 'vitest'
import { FAQ, SECTIONS, type HelpSection } from './content'
import { filterFaq, filterSections, sectionText } from './search'

const sample: HelpSection[] = [
  { id: 'a', title: 'Alarmas', icon: '', paragraphs: ['Avisos por correo electrónico'] },
  {
    id: 'b',
    title: 'Paneles',
    icon: '',
    paragraphs: ['Gráficas'],
    items: [{ term: 'Zona LIDAR Predicción', text: 'Proyección del aforo' }],
  },
]

describe('filterSections', () => {
  it('sin busqueda devuelve todas', () => {
    expect(filterSections(sample, '  ')).toHaveLength(2)
  })

  it('ignora tildes y mayusculas y busca tambien en los terminos de la lista', () => {
    expect(filterSections(sample, 'PREDICCION').map((s) => s.id)).toEqual(['b'])
    expect(filterSections(sample, 'electronico correo').map((s) => s.id)).toEqual(['a'])
  })

  it('exige todos los terminos', () => {
    expect(filterSections(sample, 'alarmas prediccion')).toEqual([])
  })
})

describe('filterFaq', () => {
  it('busca en pregunta y respuesta', () => {
    expect(filterFaq(FAQ, 'codigo verificacion').length).toBeGreaterThan(0)
    expect(filterFaq(FAQ, 'zzzz')).toEqual([])
  })
})

describe('contenido', () => {
  it('cada seccion tiene un id unico y texto buscable', () => {
    const ids = SECTIONS.map((s) => s.id)
    expect(new Set(ids).size).toBe(ids.length)
    for (const section of SECTIONS) expect(sectionText(section).length).toBeGreaterThan(20)
  })
})
