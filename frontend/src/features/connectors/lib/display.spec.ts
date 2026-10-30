import { describe, expect, it } from 'vitest'
import {
  clientCertificateErrors,
  connectorStatus,
  formatTopic,
  hostError,
  parseTopic,
  portError,
  topicError,
  topicVariables,
} from './display'

describe('parseTopic / formatTopic', () => {
  it('separa el texto fijo de las variables', () => {
    expect(parseTopic('pid/{tenant}/datos/{urn}')).toEqual([
      { type: 'static', value: 'pid/' },
      { type: 'variable', value: 'tenant' },
      { type: 'static', value: '/datos/' },
      { type: 'variable', value: 'urn' },
    ])
  })

  it('un topic fijo es una sola parte', () => {
    expect(parseTopic('gijon/pid/aforos')).toEqual([{ type: 'static', value: 'gijon/pid/aforos' }])
  })

  it('ida y vuelta conserva el texto', () => {
    const text = '{tenant}/medidas/{measure}'
    expect(formatTopic(parseTopic(text))).toBe(text)
  })

  it('sin partes no hay topic', () => {
    expect(formatTopic(null)).toBe('')
  })
})

describe('topicError', () => {
  it('los formatos de foto periodica solo admiten {id}', () => {
    expect(topicVariables('occupancy_readings')).toEqual(['id'])
    expect(topicError('gijon/pid/aforos', 'occupancy_readings')).toBeUndefined()
    expect(topicError('gijon/pid/aforos/{id}', 'occupancy_readings')).toBeUndefined()
    expect(topicError('gijon/{tenant}', 'flow_readings')).toBeDefined()
  })

  it('{id} no existe en los formatos por notificacion', () => {
    expect(topicError('pid/{id}', 'key_value')).toBeDefined()
  })

  it('measure solo existe en el formato original', () => {
    expect(topicError('pid/{measure}', 'legacy')).toBeUndefined()
    expect(topicError('pid/{measure}', 'key_value')).toBeDefined()
  })

  it('rechaza vacio y comodines de suscripcion', () => {
    expect(topicError('  ', 'key_value')).toBeDefined()
    expect(topicError('pid/#', 'key_value')).toBeDefined()
    expect(topicError('pid/+/x', 'key_value')).toBeDefined()
  })
})

describe('hostError / portError', () => {
  it('acepta host o IP y rechaza URL', () => {
    expect(hostError('mqtt.ejemplo.es')).toBeUndefined()
    expect(hostError('10.0.0.1')).toBeUndefined()
    expect(hostError('mqtt://mqtt.ejemplo.es')).toBeDefined()
    expect(hostError('user@mqtt.ejemplo.es')).toBeDefined()
    expect(hostError('')).toBeDefined()
  })

  it('el puerto va de 1 a 65535', () => {
    expect(portError(8883)).toBeUndefined()
    expect(portError('1883')).toBeUndefined()
    expect(portError(0)).toBeDefined()
    expect(portError(70000)).toBeDefined()
    expect(portError('abc')).toBeDefined()
  })
})

describe('clientCertificateErrors', () => {
  const CERT = '-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----'
  const KEY = '-----BEGIN RSA PRIVATE KEY-----\nBBB\n-----END RSA PRIVATE KEY-----'

  it('sin certificado ni clave no hay nada que validar', () => {
    expect(clientCertificateErrors('', '', false, true)).toEqual({})
  })

  it('certificado y clave en PEM son validos', () => {
    expect(clientCertificateErrors(CERT, KEY, false, true)).toEqual({})
    expect(clientCertificateErrors(CERT, '-----BEGIN PRIVATE KEY-----', false, true)).toEqual({})
  })

  it('al editar, la clave vacia conserva la guardada', () => {
    expect(clientCertificateErrors(CERT, '', true, true)).toEqual({})
    expect(clientCertificateErrors(CERT, '', false, true).key).toBeDefined()
  })

  it('rechaza contenido que no es PEM y la clave sin certificado', () => {
    expect(clientCertificateErrors('hola', KEY, false, true).certificate).toBeDefined()
    expect(clientCertificateErrors(CERT, 'hola', false, true).key).toBeDefined()
    expect(clientCertificateErrors('', KEY, false, true).certificate).toBeDefined()
  })

  it('necesita la conexion cifrada', () => {
    expect(clientCertificateErrors(CERT, KEY, false, false).certificate).toBeDefined()
  })
})

describe('connectorStatus', () => {
  it('activo sin fallos', () => {
    expect(connectorStatus({ status: 'active', retries: 0 }).key).toBe('active')
  })

  it('activo con fallos seguidos se marca con errores', () => {
    expect(connectorStatus({ status: 'active', retries: 3 }).key).toBe('failing')
    expect(connectorStatus({ status: 'error' }).key).toBe('failing')
  })

  it('desactivado', () => {
    expect(connectorStatus({ status: 'inactive', retries: 0 }).key).toBe('inactive')
  })
})
