# 5. Secretos

> **Nunca subas a git valores secretos reales.** Trata el fichero de valores de ejemplo como una
> plantilla: rellena los secretos en el momento del despliegue desde una fuente segura, o usa la
> estrategia `external` que se describe más abajo.

La estrategia se elige con `secretsStrategy.type`.

## Estrategia `values` (por defecto)

Pones los valores secretos en el mapa `secrets:` de cada componente; el chart genera un `Secret` de
Kubernetes por componente (`<nombre-del-servicio>-secret`) y lo monta en el Deployment mediante
`envFrom`.

```yaml
secretsStrategy:
  type: values

components:
  keycloak:
    secrets:
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: "..."          # se aporta en el despliegue
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: "..." # fuerte y única
      KC_LARAVEL_BACKEND_SECRET: "..."   # openssl rand -base64 24
      KC_REALM_MANAGEMENT_SECRET: "..."  # openssl rand -base64 24
```

Buenas prácticas con esta estrategia:
- Mantén los secretos en un fichero aparte que pases con un `-f secrets.yaml` adicional y que esté
  **excluido de git**, o inyéctalos desde el almacén de secretos de tu CI/CD.
- O pasa cada valor con `--set` desde un gestor de secretos en el momento de instalar.

## Estrategia `external`

Los Secrets los creas tú (External Secrets Operator, Sealed Secrets, SOPS, Vault…); el chart **no**
genera ningún Secret y en su lugar referencia los tuyos por nombre. Los mapas `secrets:` de cada
componente se ignoran.

```yaml
secretsStrategy:
  type: external
  externalSecrets:
    webBack: external-web-back
    keycloak: external-keycloak
    cbConsumer: external-cb-consumer
    # ... una entrada por cada componente que actives
```

Cada Secret referenciado debe contener las mismas claves que pondrías en el mapa `secrets:` de ese
componente (ver la lista por componente más abajo). El Secret tiene que existir en el namespace de
la release **antes** de que arranquen los pods.

## Claves de secreto necesarias por componente

Solo necesitan secretos los componentes que actives. Las claves marcadas como **(post-instalación)**
se obtienen durante [06-post-install.md](06-post-install.md).

| Componente | Claves del Secret |
|------------|-------------------|
| `keycloak` | `KC_DB_USERNAME`, `KC_DB_PASSWORD`, `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD`, `KC_LARAVEL_BACKEND_SECRET`, `KC_REALM_MANAGEMENT_SECRET` — las dos últimas son los secretos de cliente que sustituye la importación del realm, y el entrypoint aborta si faltan (`k3s-deploy.sh` genera ambas; véase [06-post-install.md](06-post-install.md)) |
| `webBack` | `DB_PASSWORD`, `DB_REALTIME_USERNAME`, `DB_REALTIME_PASSWORD`, `APP_KEY`, `FILE_ENCRYPTION_KEY`, `GENERIC_ENCRYPTION_KEY`, `KEYCLOAK_REALM`, `KEYCLOAK_ENCRYPTION_ALGORITHM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET` *(post-instalación)*, `KEYCLOAK_PUBLIC_KEY` *(post-instalación)*, `KC_ADMIN_*`, `KC_IMPERSONATION_*`, `ENCRYPTION_ENTITIES_KEY`, `API_GATEWAY_SECRET`, claves del almacenamiento de objetos |
| `fiwareManager` | `MONGO_DB_USERNAME`, `MONGO_DB_PASSWORD`, `OTE_WEBHOOK_TOKEN` (secreto compartido del webhook LIDAR: vacío = endpoint público sin autenticar), claves del almacenamiento de objetos |
| `orionLd` | `ORIONLD_MONGO_USER`, `ORIONLD_MONGO_PASSWORD` |
| `iotAgentJson` | `IOTA_MONGO_USER`, `IOTA_MONGO_PASSWORD` (`IOTA_MQTT_USERNAME` / `IOTA_MQTT_PASSWORD` si usas MQTT) |
| `aetherLink` | `PLATFORM_TS_DB_USER`, `PLATFORM_TS_DB_PASS` |
| `cbConsumer`, `genericConsumer` | `DB_USERNAME`/`DB_PASSWORD`, `TS_DB_USERNAME`/`TS_DB_PASSWORD`, `DB_REALTIME_USERNAME`/`DB_REALTIME_PASSWORD`, `RABBITMQ_USER`/`RABBITMQ_PASSWORD`, `KEYCLOAK_USER`/`KEYCLOAK_PASSWORD`, claves del almacenamiento de objetos |
| `carrot` | `RABBITMQ_USER`, `RABBITMQ_PASSWORD` |

Las integraciones opcionales añaden sus propias claves solo cuando activas el `config`
correspondiente (todas vienen comentadas): por ejemplo, los secretos de notificación de
`genericConsumer` (`TELEGRAM_BOT_TOKEN`, `WHATSAPP_ACCESS_TOKEN`, `SMS_API_KEY`,
`SMS_API_SECRET`) y los extras de `webBack` (`STATUSCAKE_API_KEY`,
`OPENWEATHERMAP_API_KEY`, `SMS_AWS_KEY`, `SMS_AWS_SECRET`).

## Cambia todos los valores por defecto antes de producción

**En este repositorio no hay ninguna credencial**: toda credencial es un marcador, y el generador
de entornos crea valores aleatorios en la instalación. Aun así, revisa que ni la contraseña de
administrador de Keycloak ni el secreto de suplantación se queden en un valor de ejemplo. Antes de
pasar a producción, pon valores fuertes y únicos al menos en:

- `keycloak`: `KEYCLOAK_ADMIN_PASSWORD`, `KC_DB_PASSWORD`.
- `webBack`: `APP_KEY`, `FILE_ENCRYPTION_KEY`, `GENERIC_ENCRYPTION_KEY`, `KC_IMPERSONATION_*` y
  todas las contraseñas de base de datos.
- Todas las contraseñas de las bases de datos, de MongoDB y de RabbitMQ.

Los marcadores `# TODO: change this default password` de los ficheros de valores señalan los campos
sensibles.
