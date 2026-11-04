import type { Entity } from '@/types'
import { placeEntities, type PlacedEntity } from './geometry'

/** Letras a partir de las que el buscador sugiere entidades: con una sola casi todo coincide. */
export const MIN_SUGGEST_CHARS = 2

/** Sugerencias que caben en el desplegable sin taparle el mapa a quien busca. */
export const MAX_SUGGESTIONS = 8

/**
 * Entidades que se piden para sacar las sugerencias. Son mas de las que se enseñan porque las que
 * no publican su ubicacion no se pueden señalar en el mapa y se descartan.
 */
export const SUGGEST_FETCH_SIZE = 50

/** Si el texto del buscador basta para sugerir entidades. */
export function canSuggest(text: string | null | undefined): boolean {
  return (text ?? '').trim().length >= MIN_SUGGEST_CHARS
}

/** Las primeras entidades con ubicacion, en el orden en que llegan, como sugerencias del buscador. */
export function suggestionsFrom(rows: Entity[]): PlacedEntity[] {
  return placeEntities(rows).placed.slice(0, MAX_SUGGESTIONS)
}
