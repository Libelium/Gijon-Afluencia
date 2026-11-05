import { DateTime } from 'luxon'
import { http } from '@/api/http'
import { toMillis } from '../../charts/chartOptions'
import { REGISTERED_DEFAULT_HOURS, type EventKind, type ScenarioEvent } from './eventSimulation'

/**
 * El registro de eventos del componente de prediccion: los dias de los que el modelo de afluencia
 * no aprende. Es un fichero por despliegue de prediccion (tenant y ambito), el mismo que lee ese
 * componente; el servidor lo lista y lo cambia en `/prediction-events`.
 */

/** Donde publica la prediccion: el tenant y el ambito de su entidad de prevision. */
export interface RegistryTarget {
  tenant: string
  scope: string
}

/** Una fila del registro tal y como la devuelve el servidor. */
export interface RegistryEvent {
  /** Posicion y huella de la fila: si alguien la cambia entretanto, el borrado se rechaza. */
  id: string
  date: string
  end_date: string
  event_type: string
  /** URN de las zonas a las que afecta; vacio, a todas. */
  device_ids: string[]
  notes: string
  start_hour: number | null
  end_hour: number | null
}

export interface RegistryList {
  rows: RegistryEvent[]
  /** Si quien mira puede registrar y borrar. */
  canEdit: boolean
}

export interface NewRegistryEvent {
  date: string
  end_date: string | null
  event_type: string
  device_ids: string[]
  notes: string | null
  start_hour: number | null
  end_hour: number | null
}

export async function listRegistry(target: RegistryTarget): Promise<RegistryList> {
  const { data } = await http.get<RegistryList>('/prediction-events', { params: target })
  return { rows: data?.rows ?? [], canEdit: !!data?.canEdit }
}

export async function registerEvent(target: RegistryTarget, event: NewRegistryEvent): Promise<RegistryEvent> {
  const { data } = await http.post<RegistryEvent>('/prediction-events', { ...target, ...event })
  return data
}

export async function deleteRegistryEvent(target: RegistryTarget, id: string): Promise<void> {
  await http.delete(`/prediction-events/${encodeURIComponent(id)}`, { params: target })
}

/** Si el evento afecta a la zona: lo dice su lista de zonas, o afecta a todas. */
export function appliesToZone(event: RegistryEvent, zoneUrn: string): boolean {
  return event.device_ids.length === 0 || event.device_ids.includes(zoneUrn)
}

/**
 * Los eventos de la zona en la forma de `registeredEvents`, la que publica la entidad de
 * prevision, para pasarlos por `registeredScenarioEvents`: asi lo registrado se ve en el simulador
 * al momento, sin esperar a que la prediccion vuelva a publicar.
 */
export function asPublished(events: RegistryEvent[], zoneUrn: string) {
  return events
    .filter((event) => appliesToZone(event, zoneUrn))
    .map((event) => ({
      date: event.date,
      endDate: event.end_date,
      type: event.event_type,
      startHour: event.start_hour,
      endHour: event.end_hour,
      notes: event.notes,
    }))
}

/** Lo que propone el formulario de registro. */
export interface RegistryDraft {
  date: string
  endDate: string
  kind: EventKind
  startHour: number
  endHour: number
  /** Solo la zona del panel, o todas. */
  onlyThisZone: boolean
  notes: string
  /** El evento simulado del que sale, para quitarlo del simulador cuando quede registrado. */
  fromScenario?: number
}

/** Un evento vacio: hoy, un dia de mercado, en esta zona. */
export function emptyDraft(timeZone: string, nowMs = Date.now()): RegistryDraft {
  const today = DateTime.fromMillis(nowMs, { zone: timeZone }).toISODate()!
  return {
    date: today,
    endDate: today,
    kind: 'market',
    startHour: REGISTERED_DEFAULT_HOURS.start,
    endHour: REGISTERED_DEFAULT_HOURS.end,
    onlyThisZone: true,
    notes: '',
  }
}

/** El formulario relleno con un evento simulado: sus dias y sus horas locales. */
export function draftFromScenario(event: ScenarioEvent, timeZone: string): RegistryDraft {
  const start = DateTime.fromMillis(toMillis(event.start), { zone: timeZone })
  const days = Math.max(1, event.days ?? 1)
  return {
    date: start.toISODate()!,
    endDate: start.plus({ days: days - 1 }).toISODate()!,
    kind: event.kind,
    startHour: start.hour,
    endHour: Math.min(24, start.hour + event.hours),
    onlyThisZone: true,
    notes: '',
    fromScenario: event.id,
  }
}

export function toNewEvent(draft: RegistryDraft, zoneUrn: string): NewRegistryEvent {
  return {
    date: draft.date,
    end_date: draft.endDate && draft.endDate !== draft.date ? draft.endDate : null,
    event_type: draft.kind,
    device_ids: draft.onlyThisZone ? [zoneUrn] : [],
    notes: draft.notes.trim() || null,
    start_hour: draft.startHour,
    end_hour: draft.endHour,
  }
}

/**
 * Si el evento empieza un dia que el modelo puede haber aprendido ya: hoy o antes, porque cada
 * ejecucion aprende hasta el ultimo dato, del mismo dia. Entonces la siguiente lo reentrena entero
 * para olvidarlo; un evento futuro no le cuesta eso.
 */
export function touchesLearnedDays(date: string, timeZone: string, nowMs = Date.now()): boolean {
  return date <= DateTime.fromMillis(nowMs, { zone: timeZone }).toISODate()!
}
