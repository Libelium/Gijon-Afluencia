import { beforeEach, describe, expect, it, vi } from 'vitest'
import { registeredScenarioEvents, type ScenarioEvent } from './eventSimulation'

const get = vi.hoisted(() => vi.fn())
const post = vi.hoisted(() => vi.fn())
const del = vi.hoisted(() => vi.fn())

vi.mock('@/api/http', () => ({ http: { get, post, delete: del } }))

const {
  appliesToZone,
  asPublished,
  deleteRegistryEvent,
  draftFromScenario,
  emptyDraft,
  listRegistry,
  registerEvent,
  toNewEvent,
  touchesLearnedDays,
} = await import('./predictionEvents')

const tz = 'Europe/Madrid'
const target = { tenant: 'demo', scope: '/' }
const ZONE = 'urn:ngsi-ld:Zone:plaza'
const OTHER = 'urn:ngsi-ld:Zone:muelle'

const row = (over: Record<string, unknown> = {}) => ({
  id: '0:abc',
  date: '2026-12-14',
  end_date: '2026-12-20',
  event_type: 'market',
  device_ids: [] as string[],
  notes: '',
  start_hour: 10,
  end_hour: 21,
  ...over,
})

beforeEach(() => {
  get.mockReset()
  post.mockReset()
  del.mockReset()
})

describe('llamadas al servidor', () => {
  it('lista el registro del tenant y el ámbito de la previsión', async () => {
    get.mockResolvedValue({ data: { rows: [row()], canEdit: true } })
    await expect(listRegistry(target)).resolves.toEqual({ rows: [row()], canEdit: true })
    expect(get).toHaveBeenCalledWith('/prediction-events', { params: target })
  })

  it('una respuesta sin filas no rompe nada', async () => {
    get.mockResolvedValue({ data: {} })
    await expect(listRegistry(target)).resolves.toEqual({ rows: [], canEdit: false })
  })

  it('registra con el destino dentro del cuerpo', async () => {
    post.mockResolvedValue({ data: row() })
    const event = toNewEvent(emptyDraft(tz, Date.parse('2026-12-14T12:00:00Z')), ZONE)
    await registerEvent(target, event)
    expect(post).toHaveBeenCalledWith('/prediction-events', { ...target, ...event })
  })

  it('borra por el id, que lleva dos puntos', async () => {
    del.mockResolvedValue({})
    await deleteRegistryEvent(target, '3:5f1c0a9e2b7d')
    expect(del).toHaveBeenCalledWith('/prediction-events/3%3A5f1c0a9e2b7d', { params: target })
  })
})

describe('eventos de la zona', () => {
  it('un evento sin zonas es de todas; con zonas, solo de esas', () => {
    expect(appliesToZone(row(), ZONE)).toBe(true)
    expect(appliesToZone(row({ device_ids: [ZONE, OTHER] }), ZONE)).toBe(true)
    expect(appliesToZone(row({ device_ids: [OTHER] }), ZONE)).toBe(false)
  })

  it('el simulador los lee como los publica la previsión, uno por fila con sus días', () => {
    const published = asPublished([row({ notes: 'Navidad' }), row({ id: '1:def', device_ids: [OTHER] })], ZONE)
    const [event, ...rest] = registeredScenarioEvents(published, tz)
    expect(rest).toEqual([])
    expect([event.start, event.hours, event.days, event.kind, event.notes, event.registered]).toEqual([
      '2026-12-14T09:00:00.000Z',
      11,
      7,
      'market',
      'Navidad',
      true,
    ])
  })
})

describe('formulario', () => {
  it('vacío propone hoy, en local, un día de mercado en esta zona', () => {
    // Las 23:30 UTC del 14 ya son el 15 en Madrid.
    expect(emptyDraft(tz, Date.parse('2026-12-14T23:30:00Z'))).toMatchObject({
      date: '2026-12-15',
      endDate: '2026-12-15',
      kind: 'market',
      startHour: 10,
      endHour: 21,
      onlyThisZone: true,
    })
  })

  it('desde un evento simulado toma sus días y sus horas locales', () => {
    const simulated: ScenarioEvent = {
      id: 4,
      kind: 'concert',
      weather: 'rain',
      intensity: 2,
      start: '2026-12-14T19:00:00.000Z', // 20:00 en Madrid
      hours: 3,
      days: 2,
    }
    expect(draftFromScenario(simulated, tz)).toMatchObject({
      date: '2026-12-14',
      endDate: '2026-12-15',
      kind: 'concert',
      startHour: 20,
      endHour: 23,
      fromScenario: 4,
    })
  })

  it('un evento que acaba pasada la medianoche se registra hasta las 24', () => {
    const late: ScenarioEvent = { id: 1, kind: 'festival', weather: 'clear', intensity: 1, start: '2026-12-14T21:00:00.000Z', hours: 4 }
    expect(draftFromScenario(late, tz).endHour).toBe(24)
  })

  it('lo que se envía: un día sin fecha final, sin notas vacías, y la zona o ninguna', () => {
    const draft = { ...emptyDraft(tz, Date.parse('2026-12-14T12:00:00Z')), notes: '  ' }
    expect(toNewEvent(draft, ZONE)).toEqual({
      date: '2026-12-14',
      end_date: null,
      event_type: 'market',
      device_ids: [ZONE],
      notes: null,
      start_hour: 10,
      end_hour: 21,
    })
    expect(toNewEvent({ ...draft, endDate: '2026-12-20', onlyThisZone: false, notes: ' Navidad ' }, ZONE)).toMatchObject({
      end_date: '2026-12-20',
      device_ids: [],
      notes: 'Navidad',
    })
  })

  it('hoy ya cuenta como aprendido; mañana no', () => {
    const now = Date.parse('2026-12-14T12:00:00Z')
    expect(touchesLearnedDays('2026-12-13', tz, now)).toBe(true)
    expect(touchesLearnedDays('2026-12-14', tz, now)).toBe(true)
    expect(touchesLearnedDays('2026-12-15', tz, now)).toBe(false)
  })
})
