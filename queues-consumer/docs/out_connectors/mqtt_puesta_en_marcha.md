# Conector MQTT: puesta en marcha

Lista para el día en que haya acceso al broker y estén cerradas las preguntas pendientes. El código
ya está hecho y probado con el broker simulado; lo que queda es configurar, confirmar supuestos y
probar contra el broker real. El funcionamiento del conector está en [`mqtt.md`](mqtt.md).

## 1. Datos del broker

- [ ] Host y puerto.
- [ ] TLS: ¿sí o no? Si el certificado no lo firma una CA pública, hace falta su CA en PEM (va en
  `sslCert`).
- [ ] Usuario y contraseña.
- [ ] `clientId`: ¿lo imponen ellos? Si se deja vacío, se genera `pid-<aleatorio>` en cada envío.
- [ ] ¿Exigen QoS 1 o `retain`? Ahora se publica con QoS 0 y sin `retain`.
- [ ] ¿El host resuelve a una IP pública? Si resuelve a una IP privada (VPN, red interna), el
  conector lo rechaza a propósito. En ese caso hay que decidir cómo permitirlo sin abrir la puerta
  a cualquier host interno.

## 2. Supuestos que hay que confirmar

Están implementados así. Si la respuesta es otra, el cambio está localizado en el builder indicado
(`app/jobs/out_connectors/out_connector/payload/`).

| Pregunta | Implementado | Fichero |
|---|---|---|
| ¿Un mensaje por envío con todas las lecturas? | Sí, cada 15 min (aforos y desplazamientos) y cada 24 h (activos) | `tasks/out_connectors.py` y variables de entorno |
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
OUT_CONNECTOR_READINGS_INTERVAL: "900"
OUT_CONNECTOR_INVENTORY_INTERVAL: "86400"
QUEUE_TASK_CONFIG_PLATFORM_OUT_CONNECTOR_GENERIC_TIMEOUT: "30"
```

- [ ] Rellenar `MQTT_ALLOWED_DESTINATIONS`.
- [ ] Ejecutar la migración del backend `2026_10_26_000000_change_ssl_cert_to_text_in_mqtt_connector_table`
  (`sslCert` pasa a `text`).
- [ ] Desplegar backend y queues-consumer (skill `desplegar-pre`). La imagen del queues-consumer
  necesita reconstruirse: añade `paho-mqtt`.

## 4. Alta de los tres conectores

Uno por topic. Con un token de un usuario que tenga `out_connectors.update`:

| Conector | `payload_type` | Topic | Se asocian |
|---|---|---|---|
| Activos | `device_inventory` | `gijon/pid/aero-people/activos` | Dispositivos (Smart Spot y LIDAR) |
| Aforos | `occupancy_readings` | `gijon/pid/aero-people/aforos` | Entidades `CrowdFlowZone` |
| Desplazamientos | `flow_readings` | `gijon/pid/aero-people/desplazamientos` | Entidades de los sensores (las que son origen o destino de los flujos) |

```bash
# Crear (repetir para los tres cambiando name, payload_type y topic)
curl -X POST "$API/api/V1/connectors/out/mqtt" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "name": "Aforos",
    "ipAddress": "<host>", "port": 8883,
    "username": "<usuario>", "password": "<contraseña>",
    "ssl": true, "sslCert": null, "clientId": null,
    "payload_type": "occupancy_readings",
    "topicTemplate": [{"type": "static", "value": "gijon/pid/aero-people/aforos"}]
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

- [ ] Suscribirse a los tres topics desde fuera: `mosquitto_sub -h <host> -p <puerto> -u <usuario>
  -P <contraseña> -t 'gijon/pid/aero-people/#' -v` (con `--cafile` si hay TLS).
- [ ] Lanzar un envío a mano sin esperar a celery beat, desde el pod `generic-consumer`:

  ```bash
  python -c "import sys; sys.path.insert(0, 'app'); \
  from tasks.out_connectors import snapshot_connector_job; snapshot_connector_job.delay(<id>)"
  ```

- [ ] Comprobar el resultado:
  - `out_connectors`: `last_connection` actualizado, `retries = 0`, `status = 'active'`.
  - Si ha fallado: `SELECT * FROM logs WHERE resource_type = 'out_connectors' ORDER BY id DESC`.
- [ ] Validar el JSON recibido con quien lo consume, sobre todo `total(%)`, las fechas y los ids.

## 6. Pendiente fuera del conector

- [ ] `CHANGELOG.md`, `openapi-gestion.yaml` y `postman/` (rutas `connectors/out`).
- [ ] Pruebas de backend (`phpunit`): alta, edición, borrado, asociación y permisos.
- [ ] Definir `groupings` y completarlo en `device_inventory.py`.
- [ ] Si hay conectores existentes en `legacy`, comprobar que siguen enviando tras el despliegue.
