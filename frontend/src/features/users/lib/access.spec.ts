import { describe, expect, it } from 'vitest'
import { accessKey } from './access'

describe('accessKey', () => {
  it('quien administra tiene acceso total, tenga o no nivel', () => {
    expect(accessKey({ isOrganizationAdmin: true, accessLevel: null })).toBe('users.access.admin')
  })

  it('cada nivel y la ausencia de nivel tienen su texto', () => {
    expect(accessKey({ isOrganizationAdmin: false, accessLevel: 'read' })).toBe('users.access.read')
    expect(accessKey({ isOrganizationAdmin: false, accessLevel: 'edit' })).toBe('users.access.edit')
    expect(accessKey({ isOrganizationAdmin: false, accessLevel: null })).toBe('users.access.none')
  })
})
