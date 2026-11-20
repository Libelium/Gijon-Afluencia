/**
 * CSV para abrir con doble clic en una hoja de calculo en castellano: `;` entre columnas, coma
 * decimal y sin separador de miles. Con la coma como separador, o con el punto decimal, Excel
 * en espanol lo mete todo en una columna o lee los decimales como miles.
 */

export type CsvCell = string | number | null | undefined

const SEPARATOR = ';'
// Sin la marca de orden de bytes, Excel lee el UTF-8 como Windows-1252 y estropea las tildes.
const BOM = '﻿'

function cell(value: CsvCell): string {
  if (value === null || value === undefined) return ''
  const text =
    typeof value === 'number' ? (Number.isFinite(value) ? String(value).replace('.', ',') : '') : value
  return /[;"\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function toCsv(columns: string[], rows: CsvCell[][]): string {
  return BOM + [columns, ...rows].map((row) => row.map(cell).join(SEPARATOR)).join('\r\n')
}

/** Nombre de fichero a partir de un titulo: sin tildes, espacios ni caracteres que den guerra. */
export function csvFileName(title: string, date = new Date()): string {
  const slug = title
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase()
  return `${slug || 'datos'}_${date.toISOString().slice(0, 10)}.csv`
}

export function downloadCsv(fileName: string, columns: string[], rows: CsvCell[][]): void {
  const url = URL.createObjectURL(new Blob([toCsv(columns, rows)], { type: 'text/csv;charset=utf-8' }))
  const link = Object.assign(document.createElement('a'), { href: url, download: fileName })
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
