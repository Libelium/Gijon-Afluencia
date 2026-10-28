# Conector de salida MQTT

Publica en un broker MQTT externo los datos de las entidades y dispositivos asociados al conector.
Los conectores se crean, se editan y se asocian desde la API de gestión, bajo `connectors/out`.

## Dos formas de enviar

| | Por notificación | Foto periódica |
|---|---|---|
| Formatos | `normalized`, `key_value`, `legacy` | `occupancy_readings`, `flow_readings`, `device_inventory` |
| Cuándo se envía | Cada vez que llega una notificación de una entidad asociada | Cada `OUT_CONNECTOR_READINGS_INTERVAL` segundos (el inventario, cada `OUT_CONNECTOR_INVENTORY_INTERVAL`) |
| Quién lo dispara | El observer `check_connectors` de `EntitySync` | Celery beat: `platform.out-connector.snapshot_all` |
| De dónde lee | La propia notificación | La base de tiempo real: el último valor de cada atributo |
| Mensajes | Uno por notificación (`legacy`: uno por atributo) | Uno por envío, con todas las lecturas |
| Topic | Fijo, o con variables `urn`, `tenant`, `scope` (`legacy`: también `measure`) | Solo fijo |

Todos los trabajos van a la cola `platform.out-connector.generic`. Si una foto no tiene nada que
enviar, no se publica ningún mensaje y la salud del conector no cambia.

## Formatos de foto periódica

En todos, las fechas van en ISO 8601 en UTC (`2026-10-26T10:00:00Z`). Los números se envían como
números.

### `occupancy_readings`: aforos

Se asocian al conector las **zonas** (`CrowdFlowZone`). Se envía su último `occupancy`.

```json
{"lecturas": [{"dpa": {
  "fechaLectura": "2026-10-26T10:00:00Z",
  "idPuntoInteres": "playa",
  "descripcionPuntoInteres": "Playa",
  "total": 120
}}]}
```

| Campo | Origen |
|---|---|
| `fechaLectura` | Instante del último `occupancy` |
| `idPuntoInteres` | Último tramo del URN de la zona |
| `descripcionPuntoInteres` | Propiedad `name` de la zona; si no la tiene, su id |
| `total` | `occupancy` |

### `flow_readings`: desplazamientos

Se asocian al conector los **sensores**. Se envían los flujos (`CrowdFlowEventETL`, que publica la
ETL de flujos) que salen de ellos o llegan a ellos, solo los de la **última ventana**: la `startDate`
más reciente.

```json
{"lecturas": [{"dpa": {
  "fechaLectura": "2026-10-26T10:00:00Z",
  "idOrigen": "smsp001",
  "descripcionOrigen": "Playa",
  "idDestino": "smsp002",
  "descripcionDestino": "Puerto",
  "total(%)": 75.0
}}]}
```

| Campo | Origen |
|---|---|
| `fechaLectura` | `startDate` de la ventana |
| `idOrigen` / `idDestino` | Último tramo del URN de cada sensor |
| `descripcionOrigen` / `descripcionDestino` | Propiedad `name` de cada sensor; si no la tiene, su id |
| `total(%)` | `count` del flujo × 100 / suma de `count` de **todos** los flujos que salieron de ese origen en la ventana, estén o no asociados. Dos decimales |

Las entidades con origen igual a destino son el agregado por sensor de la ETL, no un desplazamiento,
y no se envían.

### `device_inventory`: activos

Se asocian al conector los **dispositivos**, o entidades (y entonces se toman sus dispositivos).

```json
{"devices": [{
  "general": {
    "nombreSensor": "Sensor playa",
    "idSensor": "urn:ngsi-ld:Device:smsp005",
    "coordenadas": {"lat": 43.54, "lon": -5.66},
    "nombre": "Activo playa",
    "modelo": "Smart Spot",
    "familia": "Afluencia",
    "descripcion": "Entrada norte",
    "numeroSerie": "SER-5"
  },
  "groupings": []
}]}
```

| Campo | Origen |
|---|---|
| `nombreSensor` | Propiedad `name` de la entidad principal del dispositivo |
| `idSensor` | URN de la entidad principal |
| `coordenadas` | `location` de la entidad principal en tiempo real; `null` si no tiene |
| `nombre`, `descripcion`, `numeroSerie` | `devices.name`, `devices.description`, `devices.serial` |
| `modelo`, `familia` | `device_types.name`, `device_types.category` |
| `groupings` | Vacío: falta definir qué es un agrupamiento |

## Seguridad y salud

- Solo se publica en los hosts de `MQTT_ALLOWED_DESTINATIONS` (o en subdominios suyos). Se rechazan
  los que resuelven a una dirección privada o de bucle local. Con la lista vacía no se envía nada.
- Tras `NUM_MAX_RETRIES` fallos seguidos, si no ha habido ningún envío correcto en
  `CONNECTOR_DEACTIVATION_WINDOW_SECONDS`, el conector pasa a `inactive`. Los errores quedan en la
  tabla `log_lines` con `resource_type = 'out_connectors'`.
- La contraseña del broker no sale nunca por la API: esta solo devuelve `has_password`.
