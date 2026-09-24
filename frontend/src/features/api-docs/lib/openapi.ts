/**
 * Lectura de una especificacion OpenAPI 3 para la vista «API».
 *
 * Solo cubre lo que la vista pinta: operaciones agrupadas por etiqueta, parametros, cuerpo y
 * respuestas. Los `$ref` se resuelven contra el propio documento y el arbol de un esquema se
 * corta por profundidad y por ciclos, porque un esquema recursivo no tiene fin.
 */

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json }
export type JsonObject = { [key: string]: Json }

export interface OpenApiSpec {
  openapi?: string
  info?: { title?: string; version?: string; description?: string }
  servers?: { url: string; description?: string }[]
  tags?: { name: string; description?: string }[]
  paths?: Record<string, JsonObject>
  components?: JsonObject
  security?: Json
}

export const HTTP_METHODS = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'] as const
export type HttpMethod = (typeof HTTP_METHODS)[number]

export interface Parameter {
  name: string
  in: string
  required: boolean
  type: string
  description: string
}

export interface ResponseInfo {
  code: string
  description: string
}

export interface Operation {
  id: string
  method: HttpMethod
  path: string
  summary: string
  description: string
  tag: string
  parameters: Parameter[]
  requestBody: JsonObject | null
  requestBodyRequired: boolean
  responses: ResponseInfo[]
}

export interface TagGroup {
  name: string
  description: string
  operations: Operation[]
}

export interface SchemaNode {
  name: string
  type: string
  required: boolean
  description: string
  children: SchemaNode[]
  /** Se corto por profundidad o porque el esquema se referencia a si mismo. */
  truncated: boolean
}

export const UNTAGGED = 'Sin etiqueta'

function isObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function str(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

/** Sigue un `$ref` local (`#/components/schemas/X`). Un puntero externo o roto devuelve null. */
export function resolveRef(spec: OpenApiSpec, ref: string): JsonObject | null {
  if (!ref.startsWith('#/')) return null
  let node: unknown = spec
  for (const raw of ref.slice(2).split('/')) {
    const key = raw.replace(/~1/g, '/').replace(/~0/g, '~')
    if (!isObject(node)) return null
    node = node[key]
  }
  return isObject(node) ? node : null
}

/** Devuelve el objeto apuntado si es un `$ref`, o el propio objeto. */
export function deref(spec: OpenApiSpec, value: unknown): JsonObject | null {
  if (!isObject(value)) return null
  const ref = value.$ref
  return typeof ref === 'string' ? resolveRef(spec, ref) : value
}

/** Tipo legible de un esquema: `string`, `array<integer>`, `A | B`, el nombre de un `$ref`... */
export function schemaType(spec: OpenApiSpec, raw: unknown, depth = 0): string {
  if (!isObject(raw)) return '—'
  if (typeof raw.$ref === 'string') return raw.$ref.split('/').pop() || 'object'
  if (depth > 4) return '…'
  for (const key of ['anyOf', 'oneOf'] as const) {
    const options = raw[key]
    if (Array.isArray(options)) {
      return options.map((one) => schemaType(spec, one, depth + 1)).join(' | ')
    }
  }
  if (Array.isArray(raw.allOf)) return raw.allOf.map((one) => schemaType(spec, one, depth + 1)).join(' & ')
  const type = Array.isArray(raw.type) ? raw.type.join(' | ') : str(raw.type)
  if (type === 'array') return `array<${schemaType(spec, raw.items, depth + 1)}>`
  const format = str(raw.format)
  if (type) return format ? `${type} (${format})` : type
  if (isObject(raw.properties)) return 'object'
  return 'any'
}

/**
 * Arbol de propiedades de un esquema. `seen` guarda los `$ref` del camino actual (no de todo el
 * arbol): la misma referencia en dos ramas hermanas se pinta dos veces, un ciclo no.
 */
export function schemaTree(
  spec: OpenApiSpec,
  raw: unknown,
  maxDepth = 4,
  depth = 0,
  seen: ReadonlySet<string> = new Set(),
): SchemaNode[] {
  if (!isObject(raw)) return []

  if (typeof raw.$ref === 'string') {
    if (seen.has(raw.$ref)) return []
    const target = resolveRef(spec, raw.$ref)
    return target ? schemaTree(spec, target, maxDepth, depth, new Set([...seen, raw.$ref])) : []
  }

  if (Array.isArray(raw.allOf)) {
    return raw.allOf.flatMap((one) => schemaTree(spec, one, maxDepth, depth, seen))
  }

  if (str(raw.type) === 'array' || (raw.items && !raw.properties)) {
    return schemaTree(spec, raw.items, maxDepth, depth, seen)
  }

  const properties = raw.properties
  if (!isObject(properties)) return []
  const required = new Set(Array.isArray(raw.required) ? raw.required.map(String) : [])

  return Object.entries(properties).map(([name, child]) => {
    const ref = isObject(child) && typeof child.$ref === 'string' ? child.$ref : null
    const cyclic = ref !== null && seen.has(ref)
    const tooDeep = depth + 1 >= maxDepth
    const resolved = deref(spec, child)
    const nested = cyclic || tooDeep ? [] : schemaTree(spec, child, maxDepth, depth + 1, seen)
    const hasOwnChildren =
      !!resolved &&
      (isObject(resolved.properties) ||
        (isObject(resolved.items) && (isObject(resolved.items.properties) || !!resolved.items.$ref)))
    return {
      name,
      type: schemaType(spec, child),
      required: required.has(name),
      description: str(resolved?.description) || str(isObject(child) ? child.description : ''),
      children: nested,
      truncated: (cyclic || tooDeep) && hasOwnChildren,
    }
  })
}

function parameterFrom(spec: OpenApiSpec, raw: unknown): Parameter | null {
  const param = deref(spec, raw)
  if (!param) return null
  return {
    name: str(param.name),
    in: str(param.in),
    required: param.required === true,
    type: schemaType(spec, param.schema),
    description: str(param.description),
  }
}

/** Esquema del primer tipo de contenido declarado; JSON primero, que es el habitual. */
function bodySchema(spec: OpenApiSpec, raw: unknown): { schema: JsonObject | null; required: boolean } {
  const body = deref(spec, raw)
  if (!body || !isObject(body.content)) return { schema: null, required: false }
  const content = body.content
  const media = content['application/json'] ?? Object.values(content)[0]
  const schema = isObject(media) && isObject(media.schema) ? media.schema : null
  return { schema, required: body.required === true }
}

/** Todas las operaciones del documento, en el orden en que aparecen. */
export function listOperations(spec: OpenApiSpec): Operation[] {
  const operations: Operation[] = []
  for (const [path, item] of Object.entries(spec.paths ?? {})) {
    if (!isObject(item)) continue
    const shared = Array.isArray(item.parameters) ? item.parameters : []
    for (const method of HTTP_METHODS) {
      const op = item[method]
      if (!isObject(op)) continue
      const own = Array.isArray(op.parameters) ? op.parameters : []
      // Un parametro de la operacion sustituye al del path con el mismo nombre y ubicacion.
      const byKey = new Map<string, Parameter>()
      for (const raw of [...shared, ...own]) {
        const param = parameterFrom(spec, raw)
        if (param) byKey.set(`${param.in}:${param.name}`, param)
      }
      const { schema, required } = bodySchema(spec, op.requestBody)
      const tags = Array.isArray(op.tags) ? op.tags.map(String) : []
      operations.push({
        id: str(op.operationId) || `${method}-${path}`,
        method,
        path,
        summary: str(op.summary),
        description: str(op.description),
        tag: tags[0] || UNTAGGED,
        parameters: [...byKey.values()],
        requestBody: schema,
        requestBodyRequired: required,
        responses: Object.entries(isObject(op.responses) ? op.responses : {}).map(([code, raw]) => ({
          code,
          description: str(deref(spec, raw)?.description),
        })),
      })
    }
  }
  return operations
}

/** Filtro de la busqueda: ruta, resumen, metodo o etiqueta, sin distinguir mayusculas ni tildes. */
export function normalize(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

export function filterOperations(operations: Operation[], query: string): Operation[] {
  const terms = normalize(query).split(/\s+/).filter(Boolean)
  if (!terms.length) return operations
  return operations.filter((op) => {
    const haystack = normalize(`${op.method} ${op.path} ${op.summary} ${op.tag} ${op.description}`)
    return terms.every((term) => haystack.includes(term))
  })
}

/** Agrupa por etiqueta respetando el orden de `tags` del documento; las no declaradas, al final. */
export function groupByTag(spec: OpenApiSpec, operations: Operation[]): TagGroup[] {
  const declared = spec.tags ?? []
  const groups = new Map<string, TagGroup>()
  for (const tag of declared) {
    groups.set(tag.name, { name: tag.name, description: tag.description ?? '', operations: [] })
  }
  for (const op of operations) {
    if (!groups.has(op.tag)) groups.set(op.tag, { name: op.tag, description: '', operations: [] })
    groups.get(op.tag)!.operations.push(op)
  }
  return [...groups.values()].filter((group) => group.operations.length > 0)
}
