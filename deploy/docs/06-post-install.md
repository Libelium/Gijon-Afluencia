# 6. Post-instalación (configuración manual, una sola vez)

Hay una cosa que debe configurarse una vez, a mano, antes de que la plataforma quede plenamente
operativa. **No** está automatizada en el chart a propósito, para que este siga siendo declarativo
y libre de scripts específicos de la plataforma.

Hazlo entre las fases `core` y `webback` del [README.md](../README.md) de despliegue: después de
la instalación base (con web-back desactivado) y antes de activar web-back. Una vez obtenidas la
clave pública RS256 del realm y el secreto de cliente de `laravel-backend`, ponlas en
`environments/<nombre>/pid-gijon-core.values.yaml` (los campos `KEYCLOAK_PUBLIC_KEY` y
`KEYCLOAK_CLIENT_SECRET`, que el generador dejó como `REPLACE_AFTER_KEYCLOAK_SETUP`) y vuelve a
ejecutar `helm upgrade`.

---

## 6.1 Realm y clientes de Keycloak

El backend y los consumidores se autentican contra un realm de Keycloak —**`pid-gijon`** por
defecto, `KEYCLOAK_REALM` en `config.env`— que contiene un conjunto concreto de clientes. La imagen
de `keycloak/` importa ese realm en el primer arranque desde su `realm.json`, así que en una
instalación normal el realm y todos los clientes de abajo ya existen: comprueba la instancia en
marcha antes de crear nada a mano, y asegúrate de que `KEYCLOAK_REALM` coincide con el campo
`realm` de ese fichero.

> **Hay que aportar dos secretos de cliente en el arranque.** La exportación del realm trae los
> marcadores `__KC_LARAVEL_BACKEND_SECRET__` y `__KC_REALM_MANAGEMENT_SECRET__` en lugar de valores
> reales, y el entrypoint de la imagen aborta si falta cualquiera de las dos variables de entorno.
> `k3s-deploy.sh` genera ambas una vez por entorno en
> `environments/<nombre>/keycloak-secrets.env` (añadiéndolas a `SECRETS.env`) y se las pasa al
> chart. Si instalas a mano, ponlas tú en `components.keycloak.secrets`. Ese mismo componente
> necesita además `BACKEND_URL` en su `config`.

### a) Abrir la consola de administración de Keycloak

```bash
kubectl port-forward -n pid-gijon svc/keycloak 8080:8080
# abre http://localhost:8080  (entra con KEYCLOAK_ADMIN / KEYCLOAK_ADMIN_PASSWORD)
```

También puedes automatizarlo con `kcadm.sh` dentro del pod:

```bash
KC_POD=$(kubectl get pod -n pid-gijon -l service=pid-gijon-keycloak -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n pid-gijon "$KC_POD" -- /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master \
  --user "$KEYCLOAK_ADMIN" --password "$KEYCLOAK_ADMIN_PASSWORD"
```

### b) Comprobar que existen el realm y los clientes

Realm: **`pid-gijon`**. Clientes que usa la plataforma:

| Cliente | Tipo | Lo usa |
|---------|------|--------|
| `pid-gijon-client` | público | Interfaz web / inicio de sesión interactivo. |
| `laravel-backend` | confidencial | `web-back` (tiene secreto de cliente) y el token de administración de la batería de verificación. |
| `queues-consumer-client` | público | `cb-consumer`, `generic-consumer`. |
| `change-password-client` | confidencial | Flujo de cambio de contraseña por administración, usado por `web-back`. |

Configura las **URIs de redirección válidas** de cada cliente con tus nombres de host públicos, por
ejemplo `https://app.example.com/*`, `https://api.example.com/*`, `https://kc.example.com/*`.

> Los roles y mapeadores concretos de cada cliente forman parte de la definición del realm de la
> plataforma. Si tu imagen de Keycloak trae una exportación del realm, importarla es el camino
> soportado; si no, crea los clientes de arriba según la especificación del realm.

### c) Copiar dos valores a los secretos de `web-back`

1. **Clave pública RS256 del realm** — Realm settings → Keys → `RS256` → *Public key*. Ponla en
   `webBack.secrets.KEYCLOAK_PUBLIC_KEY`.
2. **Secreto de cliente de `laravel-backend`** — Clients → `laravel-backend` → Credentials →
   *Client secret*. Ponlo en `webBack.secrets.KEYCLOAK_CLIENT_SECRET`. Cuando el realm viene de la
   importación de la imagen, este valor es exactamente el `KC_LARAVEL_BACKEND_SECRET` de
   `environments/<nombre>/keycloak-secrets.env` —el que la instalación sustituyó en el realm—, así
   que puedes copiarlo de ahí en vez de leerlo en la consola.

Estos dos valores alimentan la validación de JWT en el backend; por eso web-back se activa solo
después de este paso.

---

## Listo

Vuelve al [README.md](../README.md) de despliegue y ejecuta la fase `webback`. Cuando termine de
desplegarse, la API de la plataforma, la identidad y la tubería de datos quedan operativas. Confírmalo con la batería de verificación:
`./tests/run-tests.sh <nombre-del-entorno>`.
