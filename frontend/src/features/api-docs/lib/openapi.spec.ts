import { describe, expect, it } from 'vitest'
import {
  filterOperations,
  groupByTag,
  listOperations,
  resolveRef,
  schemaTree,
  schemaType,
  UNTAGGED,
  type OpenApiSpec,
} from './openapi'
import { escapeHtml, renderMarkdown } from './markdown'

const spec: OpenApiSpec = {
  tags: [{ name: 'Alarmas', description: 'Avisos' }, { name: 'Entidades' }],
  paths: {
    '/V1/alarms/{id}': {
      parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'integer' } }],
      get: { tags: ['Alarmas'], summary: 'Ver alarma', responses: { '200': { description: 'OK' } } },
      put: {
        tags: ['Alarmas'],
        summary: 'Actualizar alarma',
        parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'string' }, description: 'propio' }],
        requestBody: {
          required: true,
          content: { 'application/json': { schema: { $ref: '#/components/schemas/Alarm' } } },
        },
        responses: { '204': { description: 'Sin contenido' } },
      },
    },
    '/hchk': { get: { summary: 'Salud', responses: {} } },
  },
  components: {
    schemas: {
      Alarm: {
        type: 'object',
        required: ['name'],
        properties: {
          name: { type: 'string', description: 'Nombre' },
          tags: { type: 'array', items: { type: 'string' } },
          parent: { $ref: '#/components/schemas/Alarm' },
          when: { anyOf: [{ type: 'string', format: 'date-time' }, { type: 'null' }] },
        },
      },
    },
  },
}

describe('resolveRef', () => {
  it('sigue un puntero local', () => {
    expect(resolveRef(spec, '#/components/schemas/Alarm')?.type).toBe('object')
  })

  it('devuelve null para un puntero roto o externo', () => {
    expect(resolveRef(spec, '#/components/schemas/Nada')).toBeNull()
    expect(resolveRef(spec, 'otro.yaml#/x')).toBeNull()
  })
})

describe('schemaType', () => {
  it('describe arrays, uniones y referencias', () => {
    expect(schemaType(spec, { type: 'array', items: { type: 'integer' } })).toBe('array<integer>')
    expect(schemaType(spec, { anyOf: [{ type: 'string' }, { type: 'null' }] })).toBe('string | null')
    expect(schemaType(spec, { $ref: '#/components/schemas/Alarm' })).toBe('Alarm')
    expect(schemaType(spec, { type: 'string', format: 'date-time' })).toBe('string (date-time)')
  })
})

describe('schemaTree', () => {
  it('lista propiedades con tipo y obligatoriedad y corta el ciclo', () => {
    const tree = schemaTree(spec, { $ref: '#/components/schemas/Alarm' })
    expect(tree.map((n) => n.name)).toEqual(['name', 'tags', 'parent', 'when'])
    expect(tree[0]).toMatchObject({ required: true, type: 'string', description: 'Nombre' })
    const parent = tree.find((n) => n.name === 'parent')!
    expect(parent.children).toEqual([])
    expect(parent.truncated).toBe(true)
  })

  it('corta por profundidad', () => {
    const deep: OpenApiSpec = {
      components: {
        schemas: {
          A: { type: 'object', properties: { b: { type: 'object', properties: { c: { type: 'object', properties: { d: { type: 'string' } } } } } } },
        },
      },
    }
    const tree = schemaTree(deep, { $ref: '#/components/schemas/A' }, 2)
    expect(tree[0].children[0].truncated).toBe(true)
    expect(tree[0].children[0].children).toEqual([])
  })
})

describe('listOperations', () => {
  const ops = listOperations(spec)

  it('extrae cada metodo de cada ruta', () => {
    expect(ops.map((o) => `${o.method} ${o.path}`)).toEqual([
      'get /V1/alarms/{id}',
      'put /V1/alarms/{id}',
      'get /hchk',
    ])
  })

  it('el parametro de la operacion sustituye al del path', () => {
    const put = ops.find((o) => o.method === 'put')!
    expect(put.parameters).toHaveLength(1)
    expect(put.parameters[0]).toMatchObject({ type: 'string', description: 'propio' })
    expect(put.requestBodyRequired).toBe(true)
    expect(put.requestBody?.$ref).toBe('#/components/schemas/Alarm')
  })

  it('sin etiqueta va al grupo por defecto', () => {
    expect(ops[2].tag).toBe(UNTAGGED)
  })
})

describe('filterOperations y groupByTag', () => {
  const ops = listOperations(spec)

  it('busca sin tildes ni mayusculas y con todos los terminos', () => {
    expect(filterOperations(ops, 'ALARMA actualizar').map((o) => o.method)).toEqual(['put'])
    expect(filterOperations(ops, 'salud')).toHaveLength(1)
    expect(filterOperations(ops, '  ')).toHaveLength(3)
  })

  it('agrupa en el orden declarado y omite las etiquetas vacias', () => {
    const groups = groupByTag(spec, ops)
    expect(groups.map((g) => g.name)).toEqual(['Alarmas', UNTAGGED])
    expect(groups[0].operations).toHaveLength(2)
  })
})

describe('renderMarkdown', () => {
  it('escapa el HTML del origen', () => {
    expect(renderMarkdown('<script>x</script>')).toBe('<p>&lt;script&gt;x&lt;/script&gt;</p>')
    expect(escapeHtml(`"'&`)).toBe('&quot;&#39;&amp;')
  })

  it('da formato a negrita, cursiva, codigo y listas', () => {
    expect(renderMarkdown('Es **clave** y *util*: `a**b**`')).toBe(
      '<p>Es <strong>clave</strong> y <em>util</em>: <code>a**b**</code></p>',
    )
    expect(renderMarkdown('1. uno\n2. dos\n\n- a\n- b')).toBe(
      '<ol><li>uno</li><li>dos</li></ol><ul><li>a</li><li>b</li></ul>',
    )
  })
})

describe('especificaciones reales', () => {
  it('gestion e ingesta se leen enteras y cada esquema del cuerpo se resuelve', async () => {
    for (const load of [() => import('../specs/gestion.json'), () => import('../specs/ingesta.json')]) {
      const real = (await load()).default as unknown as OpenApiSpec
      const ops = listOperations(real)
      const declared = Object.values(real.paths ?? {}).reduce(
        (n, item) => n + Object.keys(item).filter((k) => k !== 'parameters').length,
        0,
      )
      expect(ops.length).toBe(declared)
      expect(groupByTag(real, ops).reduce((n, g) => n + g.operations.length, 0)).toBe(ops.length)
      for (const op of ops) if (op.requestBody) expect(() => schemaTree(real, op.requestBody)).not.toThrow()
    }
  })
})
