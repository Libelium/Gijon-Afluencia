import { http } from '@/api/http'

/** Usuario de la organizacion tal y como lo devuelve `OrganizationUserController`. */
export interface OrganizationUser {
  id: number
  name: string
  email: string
  enabled: boolean
  status: 'active' | 'suspended' | 'blocked' | 'deleted'
  isOrganizationAdmin: boolean
  roles: string[]
  mfa: boolean
  lastActivity: string | null
  createdAt: string | null
}

export interface NewUser {
  name: string
  email: string
}

const base = (orgId: number) => `/organizations/${orgId}/users`

export async function listUsers(orgId: number): Promise<OrganizationUser[]> {
  const { data } = await http.get<OrganizationUser[]>(base(orgId))
  return data
}

/** `invitationSent` falso: la cuenta existe pero el correo para fijar la contrasena no salio. */
export async function createUser(
  orgId: number,
  user: NewUser,
): Promise<{ user: OrganizationUser; invitationSent: boolean }> {
  const { data } = await http.post<{ user: OrganizationUser; invitationSent: boolean }>(
    base(orgId),
    user,
  )
  return data
}

export async function setUserEnabled(
  orgId: number,
  userId: number,
  enabled: boolean,
): Promise<OrganizationUser> {
  const { data } = await http.put<OrganizationUser>(`${base(orgId)}/${userId}/enabled`, { enabled })
  return data
}

export async function sendPasswordEmail(orgId: number, userId: number): Promise<void> {
  await http.post(`${base(orgId)}/${userId}/password-email`)
}

export async function deleteUser(orgId: number, userId: number): Promise<void> {
  await http.delete(`${base(orgId)}/${userId}`)
}
