/** Unico punto donde vive la identidad del producto. Ningun componente escribe el nombre en linea. */
export const brand = {
  name: 'PID Gijón',
  shortName: 'PID',
  documentTitle: 'PID Gijón',
  tagline: 'Visualizador de datos de sensores urbanos',
} as const

export function pageTitle(section?: string): string {
  return section ? `${section} · ${brand.name}` : brand.name
}
