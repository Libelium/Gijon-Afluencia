# Keycloak — gestor de identidad de PID Gijón

Imagen de **Keycloak 25** con la configuración de identidad de la plataforma: el realm exportado,
los temas de login y de correo, y la extensión de segundo factor por correo electrónico.

Keycloak es el emisor de los tokens OIDC que consumen el backend, el frontal y los procesos de
integración: aquí se define quién puede autenticarse, con qué clientes y con qué aspecto.

| | |
| --- | --- |
| Base | `quay.io/keycloak/keycloak:25.0` |
| Realm | se importa desde `realm.json` en el primer arranque |
| Temas | `pidtheme` (login + correo) |
| Base de datos | PostgreSQL 16 (el `docker-compose.yml` levanta la suya) |
| Consola | http://localhost:8080 |
| Salud | http://localhost:9010/health (puerto 9000 dentro del contenedor) |

## Contenido

```
Dockerfile                       imagen de producción (4 stages)
Dockerfile_local                 imagen de desarrollo (start-dev, temas sin caché)
bootstrap-keycloak-backend.sh    entrypoint: resuelve placeholders y arranca con --import-realm
realm.json                       configuración del realm (clientes, roles, flujos, temas)
change-password-client.json      definición suelta del cliente de cambio de contraseña
pidtheme/                        tema de login y de correo (5 idiomas: es, en, ca, el, pt)
i18n_validity_check.py           comprueba que ningún idioma se quede sin traducir
docker-compose.yml               Keycloak + su PostgreSQL
```

El `Dockerfile` encadena cuatro stages: Maven compila la extensión de 2FA por correo,
`kc.sh build` genera la distribución optimizada con la extensión y las opciones de arranque,
`ubi-micro-build` extrae un `rootfs` mínimo del que solo se aprovecha `curl` (necesario para los
*healthchecks*, la imagen base de Keycloak no lo trae) y el último stage monta la imagen final.

## Configuración

Toda la parametrización es por variables de entorno. El entrypoint sustituye marcadores
`__KC_*__` en `realm.json` y en `pidtheme/**/theme.properties` antes de arrancar Keycloak.

```bash
cp .env.example .env
```

**Las credenciales de `.env.example` son de desarrollo y son públicas: cámbialas.** Dos variables
no tienen valor por defecto y el contenedor **se detiene sin arrancar** si faltan:

| Variable | Qué es | Cómo generarla |
| --- | --- | --- |
| `KC_LARAVEL_BACKEND_SECRET` | secreto del cliente confidencial `laravel-backend` | `openssl rand -base64 24` |
| `KC_REALM_MANAGEMENT_SECRET` | secreto del cliente `realm-management` | `openssl rand -base64 24` |

Es deliberado: el realm no lleva ningún secreto escrito, de modo que la imagen no puede arrancar
nunca con un valor adivinable a partir del código fuente. El valor de `KC_LARAVEL_BACKEND_SECRET`
debe coincidir con el configurado en el backend.

Otras variables de interés (todas documentadas en `.env.example`): `BACKEND_URL` (obligatoria),
`KC_DEFAULT_LOCALE`, `KC_REGISTRATION_ALLOWED` y los colores de marca
`KC_BRAND_PRIMARY` / `KC_BRAND_SECONDARY` / `KC_BRAND_INDIGO`.

### URLs de retorno OAuth

Los clientes de servicio (`laravel-backend`, `laravel-backend-client`, `vue-frontend`,
`dlm-client`) ya no llevan el comodín `"/*"` en `redirectUris`. Ese patrón es relativo al origen
de Keycloak, así que aceptaba una redirección a cualquier ruta que sirva Keycloak.

Por defecto se usa `KC_HOSTNAME`, que es el mismo valor que el backend envía como
`KEYCLOAK_REDIRECT_URI` al canjear el código de autorización. Si una instalación necesita más,
`KC_APP_REDIRECT_URIS` acepta una lista separada por comas (y `KC_APP_WEB_ORIGINS` los orígenes
CORS). **El contenedor no arranca si la lista queda vacía.**

Los clientes que solo usan *password grant* o intercambio de token (`queues-consumer-client`,
`pid-gijon-mcp-cli`, `change-password-client`) ya no tienen ninguna URL de retorno, porque no la
necesitan.

### Correo (segundo factor y reinicio de contraseña)

Ese canal transporta el código OTP y los enlaces de reinicio, así que el arranque lo exige
autenticado y cifrado. Si defines `KC_SMTP_HOST` tienes que definir también `KC_SMTP_USER` y
`KC_SMTP_PASSWORD`, y dejar activo `KC_SMTP_STARTTLS` (puerto 587) o `KC_SMTP_SSL` (puerto 465):
con los dos en `false` el contenedor se detiene.

Si no defines `KC_SMTP_HOST` no se configura correo. Es válido en desarrollo, pero entonces ni el
reinicio de contraseña ni el segundo factor por correo funcionan.

## Arranque

```bash
docker compose up -d --build
docker compose logs -f keycloak       # esperar "Import finished successfully"
```

La consola de administración queda en http://localhost:8080 con el usuario de
`KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD`.

El realm **solo se importa si no existe todavía** en la base de datos. Para volver a importarlo
desde cero hay que descartar el volumen de PostgreSQL:

```bash
docker compose down -v && docker compose up -d --build
```

Para iterar sobre los temas sin reconstruir en cada cambio, la imagen de desarrollo arranca en
modo `start-dev` con la caché de plantillas desactivada:

```bash
docker build -f Dockerfile_local -t pid-keycloak:dev .
```

## Marca

Los ficheros de `pidtheme/login/resources/img/` (`logo.png`, `favicon.ico`) son **marcadores de
posición transparentes**; hay que sustituirlos por el arte propio (ver el `README.md` de esa
carpeta). Como alternativa sin reconstruir la imagen, `KC_BRAND_LOGIN_IMAGE` admite una URL
absoluta, una ruta absoluta o el nombre de un fichero de esa carpeta.

Los textos visibles viven en `pidtheme/login/messages/` y `pidtheme/email/messages/`, con un
`messages_<idioma>.properties` por idioma.

## Verificación

```bash
# la imagen construye
docker build -t pid-keycloak:test .

# el entrypoint aborta si falta cualquiera de los dos secretos
docker run --rm -e BACKEND_URL=http://backend:80 pid-keycloak:test

# ningún idioma se ha quedado atrás tras tocar las traducciones
python3 i18n_validity_check.py
```

> Si el stage `ubi-micro-build` falla con `/bin/sh: no such file or directory`, es una capa de
> caché corrupta de BuildKit: repetir con `docker build --no-cache`.

## Notas de operación

- El nombre del realm y los `clientId` que trae `realm.json` se conservan **por compatibilidad**:
  el identificador del realm forma parte de la URL de todos los endpoints OIDC
  (`/realms/<realm>/…`) y tanto él como los `clientId` están configurados en el backend, en el
  frontal y en los procesos de integración, así que renombrarlos exige cambiarlos en todos a la
  vez. Es una decisión de coordinación, no técnica.
- El realm exportado **no incluye material criptográfico**: Keycloak genera sus propias claves RSA
  (firma y cifrado) y sus secretos HMAC/AES al importarlo, distintos en cada instalación.
- El realm exportado **no incluye usuarios**. Las cuentas se crean desde la consola de
  administración o desde el backend a través del cliente `realm-management`.
- Las URIs de redirección de los clientes apuntan a `localhost` y a
  `keycloak.pid.svc.cluster.local`; hay que ajustarlas al dominio real en *Clients → Valid
  redirect URIs* (o antes de importar, en `realm.json`).
- El correo saliente sale sin configurar (`smtp.pid.gijon.example`). Sin un SMTP válido no
  funcionan ni el restablecimiento de contraseña ni el segundo factor: ver `MFA_implementation.md`.

---

## Licencia

La configuración de este directorio —realm, tema y arranque— es desarrollo de Libelium anterior al
proyecto PID Gijón, licenciado al Ayuntamiento de Gijón bajo la [EUPL v1.2](../LICENSE). Se apoya
en Keycloak, software de terceros con licencia propia (Apache-2.0). La imagen que se despliega **se
construye aquí** a partir de la suya, añadiéndole la extensión de segundo factor por correo
(Apache-2.0 también): es obra derivada y se redistribuye conservando esas licencias y sus avisos.
Ver [`NOTICE.md`](../NOTICE.md).
