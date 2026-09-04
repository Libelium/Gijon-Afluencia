import { env } from './env'

/**
 * Datos que aporta el organismo titular de la instalacion, no el producto.
 *
 * La via de contacto para cuestiones de accesibilidad es contenido obligatorio de la
 * declaracion (Real Decreto 1112/2018), pero depende de quien despliega: se lee del entorno
 * igual que el resto de la configuracion, y la declaracion avisa si esta sin rellenar.
 */
export const accessibilityContact = (): string => env('VITE_ACCESSIBILITY_CONTACT')
