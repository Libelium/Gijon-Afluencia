# Conector MQTT: puesta en marcha

Lista para poner en marcha el envío a un broker MQTT nuevo: los datos que hay que pedir, cómo
configurarlos y cómo comprobar que llegan. El funcionamiento del conector está en [`mqtt.md`](mqtt.md).

## 1. Datos del broker

| Dato | Dónde va en el conector |
|---|---|
| Host y puerto (8883 con TLS, 1883 sin él) | Servidor y Puerto (y el host, en `MQTT_ALLOWED_DESTINATIONS`) |
| TLS | Conexión cifrada. El certificado del servidor se valida siempre |
| CA del servidor en PEM, si no la firma una CA pública | Certificado de la CA |
| Usuario y contraseña | Usuario y Contraseña, si el broker los usa |
| Certificado y clave de cliente en PEM, si el broker identifica por certificado (TLS mutuo, como AWS IoT) | Certificado de cliente y Clave privada del cliente |
| Topics | Topic de cada conector |

Los ficheros se cargan desde el formulario. **Nunca en el repositorio**, ni en las skills.

Hay que confirmar con quien gestiona el broker:

- [ ] **Permisos de publicación en los topics exactos.** Una política que dé permiso sobre
  `<raíz>/aforos/#` (o `…/aforos/*` en AWS IoT) permite publicar *bajo* `…/aforos/`, no en
  `…/aforos` a secas: hay que publicar en un subtopic, fijo (`…/aforos/<algo>`) o con `{id}`
  (`…/aforos/{id}`, un mensaje por zona). Si falta el permiso, el conector registra el error con el
  motivo que da el broker (`Not authorized`).
- [ ] **Identificador de cliente.** Si el broker admite cualquiera, deja el campo vacío: el conector
  genera uno único en cada conexión (`pid-gijon-c<conector>-<aleatorio>`). Un identificador fijo
  solo si el broker lo exige, porque dos envíos simultáneos con el mismo identificador se
  desconectan entre sí.
- [ ] **Lectura para verificar** (opcional): permisos de suscripción para comprobar los envíos desde
  nuestro lado; si no, que quien gestiona el broker confirme la recepción.
- [ ] El host tiene que resolver a una IP pública: el conector rechaza a propósito los que resuelven
  a una dirección interna.

## 2. Supuestos que hay que confirmar

Están implementados así. Si la respuesta es otra, el cambio está localizado en el builder indicado
(`app/jobs/out_connectors/out_connector/payload/`).

| Pregunta | Implementado | Fichero |
|---|---|---|
| ¿Cada cuánto se envía? | Cada 15 min (aforos y desplazamientos) y cada 24 h (activos) | `tasks/out_connectors.py` y variables de entorno |
| ¿Un mensaje con todo o uno por elemento? | Topic fijo: uno con todo. Con `{id}`: uno por zona, sensor de origen o dispositivo | `snapshot_base.py`, `mqtt.py` |
| Formato de `fechaLectura` | ISO 8601 en UTC: `2026-10-26T10:00:00Z` | `snapshot_base.py` |
| ¿Los valores van como texto (`""`) o como número? | Número | `snapshot_base.py` |
| `idPuntoInteres`, `idOrigen`, `idDestino` | Último tramo del URN (`playa`, `smsp001`) | `occupancy_readings.py`, `flow_readings.py` |
| `total(%)` | % del flujo sobre todo lo que salió de su origen en la ventana | `flow_readings.py` |
| ¿Se envían también los flujos de un sensor consigo mismo? | No | `flow_readings.py` |
| `nombreSensor` / `idSensor` frente a `nombre` | Sensor = entidad principal; activo = dispositivo | `device_inventory.py` |
| `modelo` / `familia` | `device_types.name` / `device_types.category` | `device_inventory.py` |
| `groupings` (`grupo`, `valor`) | **Sin definir**: se envía `[]` | `device_inventory.py` |
| ¿Se reenvía la misma lectura si no ha cambiado? | Sí: cada foto lleva el último valor, aunque sea el mismo. El receptor puede descartar duplicados por `fechaLectura` | — |

## 3. Configuración

En el `generic-consumer`, que es el que ejecuta celery beat (en el chart, `values.yaml`):

```yaml
MQTT_ALLOWED_DESTINATIONS: "<host del broker>"
OUT_CONNECTOR_REQUEST_TIMEOUT: "10"
OUT_CONNECTOR_READINGS_INTERVAL: "900"
OUT_CONNECTOR_INVENTORY_INTERVAL: "86400"
QUEUE_TASK_CONFIG_PLATFORM_OUT_CONNECTOR_GENERIC_TIMEOUT: "30"
```

- [ ] Rellenar `MQTT_ALLOWED_DESTINATIONS` con el host del broker.
- [ ] Migraciones del backend (se aplican solas al arrancar `web-back`):
  `2026_10_26_000000_change_ssl_cert_to_text_in_mqtt_connector_table` (`sslCert` pasa a `text`) y
  `2026_10_29_000000_add_client_certificate_to_mqtt_connector_table` (`clientCert` y `clientKey`).
- [ ] Desplegar backend, frontend y queues-consumer (skill `desplegar-pre`). La imagen del
  queues-consumer necesita reconstruirse: añade `paho-mqtt`.

## 4. Alta de los conectores

Uno por formato. Desde la interfaz, en **Integraciones → Conectores → Nuevo conector**: ahí se
configura el servidor, el formato, el topic y las entidades, y desde el detalle se activa, se
desactiva, se borra y se ven los errores. Por API, con un token de un usuario que tenga
`out_connectors.update`:

| Conector | `payload_type` | Topic (ejemplo) | Se asocian |
|---|---|---|---|
| Activos | `device_inventory` | `<raíz>/activos/{id}` | Dispositivos, o entidades (se toman sus dispositivos) |
| Aforos | `occupancy_readings` | `<raíz>/aforos/{id}` | Entidades `CrowdFlowZone` |
| Desplazamientos | `flow_readings` | `<raíz>/desplazamientos/{id}` | Entidades de los sensores (las que son origen o destino de los flujos) |

```bash
# Crear (repetir para cada conector cambiando name, payload_type y topic)
curl -X POST "$API/api/V1/connectors/out/mqtt" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "name": "Aforos",
    "ipAddress": "<host>", "port": 8883,
    "username": null, "password": null, "clientId": null,
    "ssl": true, "sslCert": "<CA en PEM o null>",
    "clientCert": "<certificado de cliente en PEM o null>",
    "clientKey": "<clave privada del cliente en PEM o null>",
    "payload_type": "occupancy_readings",
    "topicTemplate": [{"type": "static", "value": "<raíz>/aforos/"}, {"type": "variable", "value": "id"}]
  }'

# Asociar (el id es el del out_connector que devuelve el alta)
curl -X PUT "$API/api/V1/connectors/out/<id>/models" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"entities": [<ids>], "devices": [<ids>]}'
```

- [ ] Sacar los ids de las zonas, sensores y dispositivos (skill `acceso-servicios`, tabla
  `entities` y `devices`).
- [ ] Comprobar que la base de tiempo real tiene `occupancy` de las zonas y los flujos
  `CrowdFlowEventETL` con `origin`, `destination`, `count` y `startDate`. Si no aparecen, revisar la
  ETL de fusión y la de flujos (skill `diagnostico-plataforma`).

## 5. Prueba contra el broker

- [ ] Suscribirse a los topics desde fuera, con un cliente que tenga permiso de lectura (MQTT
  Explorer o `mosquitto_sub -h <host> -p <puerto> -t '<raíz>/#' -v`, con `--cafile`, `--cert` y
  `--key` si hay TLS mutuo).
- [ ] Lanzar un envío a mano sin esperar a celery beat, desde el pod `generic-consumer`:

  ```bash
  python -c "import sys; sys.path.insert(0, 'app'); \
  from tasks.out_connectors import snapshot_connector_job; snapshot_connector_job.delay(<id>)"
  ```

- [ ] Comprobar el resultado en el detalle del conector (estado, último envío y errores) o en la base
  de datos:
  - `out_connectors`: `last_connection` actualizado, `retries = 0`, `status = 'active'`.
  - Si ha fallado: `SELECT * FROM log_lines WHERE resource_type = 'out_connectors' ORDER BY id DESC`.
- [ ] Validar el JSON recibido con quien lo consume, sobre todo `total(%)`, las fechas y los ids.

## 6. Pendiente fuera del conector

- [ ] Pruebas de backend (`phpunit`) específicas del conector: alta, edición, borrado, asociación y
  permisos.
- [ ] Definir `groupings` y completarlo en `device_inventory.py`.
- [ ] Si hay conectores existentes en `legacy`, comprobar que siguen enviando tras el despliegue.
