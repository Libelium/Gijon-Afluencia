import type { AccessLevel, OrganizationUser } from '../api/users'

/** Niveles que se pueden asignar, de menos a mas. */
export const ACCESS_LEVELS: AccessLevel[] = ['read', 'edit']

/** Clave de texto del acceso de un usuario, incluido el de quien administra y el de «sin acceso». */
export function accessKey(user: Pick<OrganizationUser, 'isOrganizationAdmin' | 'accessLevel'>): string {
  if (user.isOrganizationAdmin) return 'users.access.admin'
  return user.accessLevel ? `users.access.${user.accessLevel}` : 'users.access.none'
}
