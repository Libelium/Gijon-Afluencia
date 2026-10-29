/** Formatos de mensaje que entiende el conector MQTT del queues-consumer. */
export type PayloadType =
  | 'occupancy_readings'
  | 'flow_readings'
  | 'device_inventory'
  | 'normalized'
  | 'key_value'
  | 'legacy'

export type ConnectorStatus = 'active' | 'inactive' | 'error'

/** Una parte del topic: texto fijo o una variable que el servidor sustituye al enviar. */
export interface TopicPart {
  type: 'static' | 'variable'
  value: string
}

export interface ConnectorRow {
  id: number
  name: string
  type: string
  status: ConnectorStatus | string
  last_connection?: string | null
  /** Fallos seguidos desde el ultimo envio correcto. */
  retries?: number
}

export interface LinkedEntity {
  id: number
  urn: string
}

export interface MqttSettings {
  ipAddress: string
  port: number
  username?: string | null
  has_password: boolean
  clientId?: string | null
  ssl: boolean
  sslCert?: string | null
  /** Certificado de cliente (PEM). Su clave privada nunca se devuelve. */
  clientCert?: string | null
  has_client_key?: boolean
  topicTemplate: TopicPart[]
  payload_type: PayloadType | string
  payload_config?: unknown
}

export interface ConnectorDetail extends ConnectorRow {
  use_readable_names: boolean
  connector: MqttSettings | null
  entities?: LinkedEntity[]
  created_at?: string
  updated_at?: string
}

/** Lo que se envia al dar de alta o editar. Sin contrasena, el servidor conserva la actual. */
export interface MqttConnectorInput {
  name: string
  use_readable_names: boolean
  ipAddress: string
  port: number
  username: string | null
  password?: string
  clientId: string | null
  ssl: boolean
  sslCert: string | null
  clientCert: string | null
  /** Sin ella, al editar el servidor conserva la clave que ya tenia. */
  clientKey?: string
  topicTemplate: TopicPart[]
  payload_type: PayloadType
  payload_config?: unknown
}
