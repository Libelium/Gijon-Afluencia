# Construcción y despliegue

PID-GIJÓN se construye a un **directorio de ficheros estáticos**. No hay servidor de aplicación, ni
proceso de Node en ejecución, ni base de datos propia: se publican HTML, JavaScript, CSS y el
favicon en cualquier servidor web o almacenamiento de objetos con servidor de contenido delante.

Los dos sistemas de los que sí depende —la **API REST** y el **proveedor de identidad OIDC**— son
externos y tienen que estar accesibles desde el navegador de la persona usuaria, no solo desde el
servidor que sirve la aplicación.

Hay dos formas de desplegarlo, y las dos están cubiertas aquí:

- **Copiar `dist/`** a un servidor web que ya se opera (secciones 1 y 5).
- **Ejecutar la imagen de contenedor** que trae el repositorio, con nginx ya configurado
  (sección 6). Es la vía recomendada: la configuración correcta del servidor viaja con el
  artefacto en lugar de tener que reproducirse en cada máquina.

---

## 1. Construir

```bash
npm ci                 # instalación reproducible desde package-lock.json
cp .env.example .env   # y rellenar con los valores del entorno destino
npm run build          # comprueba tipos y empaqueta en dist/
```

`npm run build` ejecuta `vue-tsc --noEmit && vite build`: si la comprobación de tipos falla, **no se
genera nada**. Es intencionado; un artefacto que no compila limpio no se publica. La construcción de
la imagen de contenedor hereda esa garantía, porque invoca el mismo script.

El resultado queda en `dist/`: `index.html`, los fragmentos con huella (`assets/*.[hash].js|css`) y
el favicon.

Requisitos de la máquina de construcción: **Node 20 o superior** y npm 10 o superior. Nada más.

### Verificar el artefacto antes de publicarlo

```bash
npm run preview        # sirve dist/ en http://localhost:20600
```

Y una comprobación que evita el incidente más común: **buscar en el paquete algo que no debiera
estar ahí**.

```bash
grep -ril "secret\|password\|apikey" dist/ || echo "sin coincidencias"
```

Y la trampa de verdad: las variables `VITE_*` se incrustan al empaquetar, así que si construyes con
un `.env` local apuntando a otro despliegue, **ese dominio, ese realm y ese identificador de cliente
acaban dentro del paquete**. Conviene comprobarlo sobre el artefacto que se va a publicar:

```bash
# Sustituye los valores por los de los OTROS entornos: no deben aparecer en este paquete.
# La hoja de estilo del tipo de iconos se excluye a proposito: trae cientos de nombres de
# icono de Material Design que no son referencia a nada.
grep -ril --exclude='*.css' -e 'otro-dominio.example' -e 'otro-realm' dist/ \
  && echo '  ↑ valor de otro entorno incrustado'
echo 'revision del paquete terminada'
```

Construye siempre con el `.env` del entorno destino: un paquete generado con la configuración de
otro entorno queda atado a él, aunque el código sea el mismo.

---

## 2. La configuración: dos momentos, dos mecanismos

Esto es lo primero que hay que entender del despliegue:

> Las variables `VITE_*` se **incrustan en el paquete** en el momento de empaquetar. No se leen en
> tiempo de ejecución.

Consecuencias prácticas:

1. **Un artefacto por entorno.** El `dist/` construido apuntando a preproducción no sirve para
   producción. Cambiar una URL exige **reconstruir**, no reiniciar ni editar un fichero.
2. **Todo lo que empieza por `VITE_` es público.** Viaja en el JavaScript que descarga cualquier
   visitante y se lee con abrir las herramientas del navegador. Solo entran ahí URL,
   identificadores públicos de cliente OIDC y parámetros de mapa. **Jamás una credencial, un
   secreto de cliente ni un token.**
3. El `client_id` de OIDC es público por diseño: la seguridad del flujo la da PKCE y la lista de URI
   de redirección registradas en el proveedor, no el secreto del cliente.

El punto 1 es un problema real en cuanto hay más de un entorno: obliga a construir una imagen por
entorno, y entonces «la imagen que se probó en preproducción» y «la que se despliega en producción»
son artefactos distintos. Es exactamente lo que no se quiere de un despliegue reproducible.

### El mecanismo de ejecución: `config.js`

Por eso la imagen incorpora una segunda vía. En cada arranque del contenedor,
[`deploy/entrypoint.sh`](../deploy/entrypoint.sh) escribe
`/usr/share/nginx/html/config.js` a partir de las variables de entorno del contenedor:

```js
/* Generado por deploy/entrypoint.sh en cada arranque del contenedor. No editar a mano. */
window.__APP_CONFIG__ = Object.freeze({
  "VITE_API_BASE_URL": "https://api.mi-dominio.es",
  "VITE_OIDC_URL": "https://auth.mi-dominio.es",
  "VITE_OIDC_REALM": "sensores",
  "VITE_OIDC_CLIENT_ID": "visor-publico"
});
```

Con eso, **una sola imagen sirve para todos los entornos**: se despliega la misma y cambian sus
variables. Las claves llevan el nombre `VITE_*` a propósito, para que leerlas desde la aplicación
sea un reemplazo directo de `import.meta.env`.

> **Estado actual: operativo.** El entrypoint genera `config.js`, nginx lo sirve sin caché y **la
> aplicación lo lee**. El acceso está centralizado en `src/lib/env.ts`, cuya función `env(clave)`
> consulta primero `window.__APP_CONFIG__` y cae en el valor incrustado al compilar cuando la
> clave no está definida. `index.html` carga `config.js` como script **clásico y antes del módulo**
> de la aplicación, porque el cliente OIDC y la instancia de axios se construyen al evaluarse su
> módulo, no dentro de una función: si la configuración no estuviera en `window` antes, se
> quedarían con el valor de compilación.
>
> En desarrollo hay un `public/config.js` con un objeto vacío, de modo que manda el fichero `.env`
> y no aparece un 404 en la consola. El contenedor lo sobrescribe en cada arranque.
>
> Por tanto **no hace falta pasar argumentos de construcción por entorno**: se construye la imagen
> una vez y se despliega en cualquier entorno cambiando sus variables. Los argumentos de la
> sección 6.2 siguen existiendo para poder generar un artefacto autocontenido si se quiere.

Reglas del fichero generado, que conviene conocer:

- **Solo se escriben las claves con valor.** Una clave ausente deja que la aplicación caiga en el
  valor incrustado al compilar, que puede ser el correcto.
- Se acepta el nombre **con prefijo** (`VITE_API_BASE_URL`) y el **corto** (`API_BASE_URL`). En el
  contenedor se recomienda el corto: el prefijo `VITE_` solo significa algo al compilar y en una
  variable de ejecución induce a error.
- Los valores se **escapan** antes de escribirse (`"`, `\`, `<` y saltos de línea), de forma que un
  valor mal puesto no pueda inyectar código en `config.js`.
- `config.js` **se sirve con `Cache-Control: no-store`**. Si se cacheara, un contenedor arrancado
  con otras variables seguiría entregando la configuración anterior desde el navegador.
- `config.js` **lo descarga cualquier visitante**, igual que las `VITE_*`. Rige la misma norma: ni
  credenciales, ni secretos de cliente, ni tokens.
- Si el sistema de ficheros está montado de solo lectura, el entrypoint **avisa por el registro y
  arranca igualmente** con la configuración incrustada, en lugar de dejar el contenedor caído.

---

## 3. Variables de entorno

Todas se describen una a una en el [README](../README.md#variables-de-entorno) y hay una plantilla
lista para copiar en [`.env.example`](../.env.example). Esta tabla es la referencia del despliegue:
qué nombre usar al compilar, qué nombre usar en el contenedor y qué pasa si falta.

| Al compilar (`.env`, `--build-arg`) | En el contenedor (`environment`) | Oblig. | Qué es |
| --- | --- | :---: | --- |
| `VITE_API_BASE_URL` | `API_BASE_URL` | **sí** | Raíz de la API REST, sin `/api/V1` (la aplicación lo añade). Ej.: `https://api.mi-dominio.es` |
| `VITE_OIDC_URL` | `OIDC_URL` | **sí** | Raíz del proveedor de identidad. Ej.: `https://auth.mi-dominio.es` |
| `VITE_OIDC_REALM` | `OIDC_REALM` | **sí** | Realm del proveedor |
| `VITE_OIDC_CLIENT_ID` | `OIDC_CLIENT_ID` | **sí** | Identificador del cliente público (no lleva secreto) |
| `VITE_OIDC_REDIRECT_URI` | `OIDC_REDIRECT_URI` | no | URI de retorno tras autenticarse. **Por defecto `<origen>/login`.** Solo se pone si hace falta otra |
| `VITE_MAP_TILES_URL` | `MAP_TILES_URL` | no | Plantilla de teselas. Por defecto OpenStreetMap, que no requiere clave |
| `VITE_MAP_TILES_ATTRIBUTION` | `MAP_TILES_ATTRIBUTION` | no | Texto de atribución del mapa. **Obligatorio por los términos de uso** si se cambia el proveedor de teselas |
| `VITE_MAP_DEFAULT_CENTER` | `MAP_DEFAULT_CENTER` | no | Centro inicial, `lat,lon`. Por defecto `43.5322,-5.6611` |
| `VITE_MAP_DEFAULT_ZOOM` | `MAP_DEFAULT_ZOOM` | no | Nivel de zoom inicial. Por defecto `13` |
| `VITE_REALTIME_URL` | `REALTIME_URL` | no | Servidor de datos en vivo. Si va vacío, la aplicación funciona sin actualización automática. **La credencial no va aquí**: se pide a la API una vez hay sesión |
| `VITE_DATA_SCOPE_PREFERENCE_KEY` | `DATA_SCOPE_PREFERENCE_KEY` | no | Clave de la preferencia de usuario que fija el ámbito de datos. Sin ella, el histórico de alarmas se degrada de forma explícita |
| `VITE_ALARM_ENTITY_TYPE` | `ALARM_ENTITY_TYPE` | no | Tipo de entidad NGSI-LD bajo el que la API publica el estado de una alarma |

Las dos últimas son **identificadores técnicos del sistema con el que se integra**, no nombres de
producto: son claves de datos ya existentes en ese despliegue y tienen que coincidir con las suyas.
Por eso se leen del entorno y no están escritas en el código. Véase
[`src/api/platform-contract.ts`](../src/api/platform-contract.ts).

Argumentos adicionales de la imagen, solo informativos (rellenan etiquetas OCI):
`APP_VERSION`, `VCS_REF`, `BUILD_DATE`.

Si falta una de las cuatro obligatorias, el síntoma es inequívoco: la aplicación carga en blanco y
la consola del navegador se llena de errores contra `undefined/api/V1` o del propio proveedor de
identidad.

---

## 4. Los dos requisitos externos imprescindibles

Aunque el artefacto y el servidor estén perfectos, **la aplicación no funciona si el origen desde el
que se sirve no está dado de alta en otros dos sistemas**. No es algo que se pueda arreglar desde
este repositorio, y es el origen de casi todos los problemas de una primera puesta en marcha.

Un «origen» es esquema + host + puerto: `https://sensores.mi-dominio.es`. Si la aplicación se sirve
desde dos dominios, o además desde `http://localhost:8080` en pruebas, **cada uno** hay que darlo de
alta por separado.

### 4.1 Origen permitido en el CORS de la API

La API tiene que aceptar peticiones desde el origen que sirve la aplicación, con la cabecera
`Authorization` entre las permitidas y las respuestas al `OPTIONS` previo bien resueltas.

> **La API de este proyecto no admite comodines en CORS.** No sirve `*`, ni
> `https://*.mi-dominio.es`: hay que registrar el **origen exacto**, uno por uno, incluidos los de
> desarrollo (`http://localhost:20600`) y los del contenedor local (`http://localhost:8080`).

Síntoma de que falta: la aplicación carga, pero **todas** las peticiones fallan y en la consola
aparece un error de CORS —no un 401—. Desde el punto de vista de la aplicación es un fallo de red
(`kind: 'network'`), porque el navegador nunca le entrega la respuesta.

### 4.2 URI de retorno válida en el cliente OIDC

El proveedor de identidad solo redirige a URI previamente registradas. La aplicación usa
**`<origen>/login`** como URI de retorno, y ese es el valor por defecto; si el despliegue necesita
otra, se fija con `VITE_OIDC_REDIRECT_URI` (`OIDC_REDIRECT_URI` en el contenedor) y **hay que
registrar exactamente esa**.

En el cliente de Keycloak, para cada origen desde el que se sirva la aplicación:

| Ajuste | Valor |
| --- | --- |
| Valid redirect URIs | `https://mi-dominio.es/*` (tiene que cubrir `/login`) |
| Valid post logout redirect URIs | `https://mi-dominio.es/*` |
| Web origins | `https://mi-dominio.es` |
| Client authentication | desactivada (cliente público) |
| Standard flow | activado; PKCE `S256` |

Si el origen no está registrado, el proveedor rechaza la redirección y la persona ve un error del
propio Keycloak, no de la aplicación: la traza no apunta a este repositorio y la búsqueda se pierde.

**Sirve siempre por HTTPS.** El flujo OIDC con PKCE lo exige en la práctica, y sin TLS los tokens
viajan en claro por la red. La única excepción razonable es `http://localhost` en desarrollo, que
los navegadores tratan como contexto seguro. Un despliegue municipal accesible por HTTP no es un
despliegue incompleto: es un despliegue que no se debe publicar.

### 4.3 Salida a las teselas del mapa

El navegador descarga las teselas directamente del proveedor configurado en `VITE_MAP_TILES_URL`.
En una red municipal cerrada hay que permitir ese destino, o servir las teselas desde dentro y
apuntar la variable al servidor interno —cambiando también
`VITE_MAP_TILES_ATTRIBUTION` y la sección «Atribuciones obligatorias» del
[`NOTICE.md`](../../NOTICE.md) de la raíz.

---

## 5. Servir `dist/` sin contenedor

### 5.1 La regla que no se puede olvidar: reescritura a `index.html`

Es una SPA con historial HTML5. Las rutas (`/entidades`, `/paneles/12`) **no existen como ficheros**.
Si el servidor no reescribe las peticiones de navegación a `index.html`, la aplicación funciona
mientras se navega por dentro y devuelve un 404 en cuanto alguien **recarga** una página o **entra
por un enlace directo**. Es el fallo más frecuente y el más desconcertante, porque «a mí me
funciona» es cierto.

### 5.2 nginx

La configuración completa y probada es la de la imagen,
[`deploy/nginx.conf`](../deploy/nginx.conf), y se puede reutilizar tal cual. En su versión mínima:

```nginx
server {
    listen 443 ssl http2;
    server_name mi-dominio.es;
    root /var/www/pid-gijon;
    index index.html;

    # Los ficheros con huella en el nombre son inmutables: se cachean para siempre.
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }

    # index.html NUNCA se cachea: es lo que apunta a la versión desplegada.
    location = /index.html {
        add_header Cache-Control "no-cache, must-revalidate" always;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    gzip on;
    gzip_types text/css text/javascript application/javascript image/svg+xml application/json;
}
```

Las dos reglas de caché son un par: si se cachea `index.html`, los navegadores seguirán pidiendo los
fragmentos de la versión anterior tras un despliegue y la aplicación se romperá a medias. Si no se
cachean los `assets/`, se paga la descarga completa en cada visita sin necesidad.

Dos detalles que se pasan por alto y salen caros:

- `try_files $uri =404` en `/assets/`. Sin él, un fragmento que falta devuelve `index.html` con tipo
  `text/html` y el navegador falla con un error de MIME que no menciona el fichero que falta.
- `add_header` **no acumula**: en cuanto un `location` declara una cabecera propia, descarta todas
  las que heredaba del bloque padre. Por eso en `deploy/nginx.conf` las cabeceras de seguridad están
  en [`deploy/security-headers.conf`](../deploy/security-headers.conf) y se incluyen en **cada**
  `location`.

### 5.3 Apache

```apache
<Directory /var/www/pid-gijon>
    Options -Indexes
    AllowOverride None
    Require all granted

    RewriteEngine On
    RewriteBase /
    RewriteRule ^index\.html$ - [L]
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule . /index.html [L]
</Directory>
```

### 5.4 Almacenamiento de objetos con servidor de contenido

Sube `dist/` al contenedor y configura:

- Documento índice: `index.html`.
- **Documento de error 404 y 403: `index.html`, con código de respuesta 200.** Es la forma que
  tienen estos servicios de hacer la reescritura de la sección 5.1.
- Caché: `index.html` sin caché; `assets/*` inmutable.
- Invalidar la caché del servidor de contenido para `/index.html` en cada despliegue.

### 5.5 Servir bajo un subdirectorio

Si la aplicación no cuelga de la raíz del dominio (por ejemplo `https://mi-dominio.es/sensores/`),
hay que declarar la base **al construir** y en el enrutador:

```bash
npm run build -- --base=/sensores/
```

Y en `src/router/index.ts`, `createWebHistory('/sensores/')`. Con la base mal puesta el paquete
carga desde rutas absolutas equivocadas y la página queda en blanco sin error visible.

---

## 6. Imagen de contenedor

El [`Dockerfile`](../Dockerfile) tiene dos etapas: una con `node:20-alpine` que instala con
`npm ci` y ejecuta `npm run build`, y otra con `nginx:alpine` que sirve `dist/`. La imagen final no
arrastra Node ni las dependencias de compilación.

Lo que trae ya resuelto:

- La reescritura a `index.html` de la sección 5.1 y el par de reglas de caché.
- gzip, y `Cache-Control: no-store` sobre `config.js`.
- Cabeceras de seguridad: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` y
  `Permissions-Policy`.
- La generación de `config.js` en el arranque (sección 2).
- **Ejecución sin privilegios**: el proceso corre como el usuario `nginx`, y por eso escucha en el
  **puerto 8080** —un usuario que no es root no puede abrir puertos por debajo de 1024—. El pid y
  los ficheros temporales van a `/var/cache/nginx`, que es suyo, y no a `/tmp`: con el bit sticky
  de `/tmp` no podría sobrescribir el `nginx.pid` que deja ahí la validación de la configuración al
  construir la imagen, y el contenedor no arrancaría.
- `HEALTHCHECK` contra `/healthz`, que responde `200 ok` y no ensucia el registro de accesos.
- Etiquetas OCI: `org.opencontainers.image.title`, `.description`, `.licenses` (`EUPL-1.2`),
  `.version`, `.revision` y `.created`.

### 6.1 Construir la imagen

```bash
docker build -t pid-gijon:0.1.0 .
```

Si `npm run build` falla —incluida la comprobación de tipos—, **la imagen no se construye**.

### 6.2 Construir con la configuración del entorno destino

Mientras la aplicación siga leyendo la configuración incrustada (sección 2), la imagen hay que
construirla con los valores del entorno al que se va a desplegar:

```bash
docker build -t pid-gijon:0.1.0 \
  --build-arg VITE_API_BASE_URL=https://api.mi-dominio.es \
  --build-arg VITE_OIDC_URL=https://auth.mi-dominio.es \
  --build-arg VITE_OIDC_REALM=sensores \
  --build-arg VITE_OIDC_CLIENT_ID=visor-publico \
  --build-arg APP_VERSION=0.1.0 \
  --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
  .
```

Y entonces **la etiqueta de la imagen tiene que decir a qué entorno pertenece**
(`pid-gijon:0.1.0-produccion`), porque no es intercambiable.

Un `.env` local **no** afecta a la construcción de la imagen: [`.dockerignore`](../.dockerignore) lo
excluye del contexto a propósito, para que una imagen no quede atada al entorno de quien la
construyó por descuido.

### 6.3 Ejecutar la imagen

```bash
docker run -d --name pid-gijon -p 8080:8080 \
  -e API_BASE_URL=https://api.mi-dominio.es \
  -e OIDC_URL=https://auth.mi-dominio.es \
  -e OIDC_REALM=sensores \
  -e OIDC_CLIENT_ID=visor-publico \
  --cap-drop ALL --security-opt no-new-privileges:true \
  pid-gijon:0.1.0
```

No necesita montajes ni capacidades adicionales: escucha en 8080 sin ser root, y escribe
únicamente `config.js` y su propio pid.

Comprobaciones inmediatas:

```bash
curl -fsS http://localhost:8080/healthz      # ok
curl -fsS http://localhost:8080/config.js    # las variables que se le pasaron
docker inspect --format '{{.State.Health.Status}}' pid-gijon   # healthy
```

El contenedor **no termina la conexión TLS ni redirige de HTTP a HTTPS**: eso es del proxy inverso o
del balanceador que va delante, que es también donde se ponen `Strict-Transport-Security` y la
`Content-Security-Policy` (sección 7), porque ambas dependen del dominio público.

Se puede ejecutar con la raíz de solo lectura, y entonces sí hace falta un montaje en memoria para
el pid y los temporales de nginx:

```bash
docker run -d --name pid-gijon -p 8080:8080 \
  --read-only --tmpfs /var/cache/nginx:mode=1777 \
  -e API_BASE_URL=https://api.mi-dominio.es \
  pid-gijon:0.1.0
```

Con la raíz de solo lectura el entrypoint no puede escribir `config.js`: **avisa por el registro y
arranca igualmente** con la configuración incrustada. Es decir, se renuncia a la configuración en
tiempo de ejecución; hay que elegir una cosa o la otra.

### 6.4 En local, con Compose

[`docker-compose.yml`](../docker-compose.yml) construye y levanta la imagen con las variables del
`.env` del directorio, el mismo que usa `npm run dev`:

```bash
cp .env.example .env       # y rellenar
docker compose up --build  # http://localhost:8080
```

Recuerda que `http://localhost:8080` es un origen más: si no está dado de alta según la sección 4,
la aplicación no pasará del inicio de sesión.

---

## 7. Cabeceras recomendadas

La imagen ya pone las cabeceras que no dependen del dominio. Las dos que sí dependen —**HSTS** y
**`Content-Security-Policy`**— las pone **quien opera el despliegue**, en el terminador TLS.

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data: https://*.tile.openstreetmap.org; connect-src 'self' https://api.mi-dominio.es https://auth.mi-dominio.es; frame-ancestors 'none'; base-uri 'self'" always;
```

Notas sobre la política de contenido, porque una CSP mal ajustada rompe la aplicación en silencio:

- `connect-src` tiene que incluir **la API y el proveedor de identidad**. Si falta uno, no hay datos
  o no hay inicio de sesión.
- `img-src` tiene que incluir **el proveedor de teselas** (y `data:` para los iconos del mapa). Si
  falta, el mapa sale gris.
- `style-src 'unsafe-inline'` hace falta hoy porque Vuetify inserta estilos en línea al aplicar el
  tema. Es la única concesión de la lista, y conviene revisarla cuando el framework permita
  prescindir de ella.
- `script-src 'self'` es compatible con `config.js`, porque es un fichero servido desde el mismo
  origen y no un script en línea. Si algún día se generara en línea dentro de `index.html`, esta
  directiva habría que relajarla: otra razón para mantenerlo en un fichero aparte.
- `X-Frame-Options: DENY` y `frame-ancestors 'none'` impiden empotrar la aplicación. Si hace falta
  publicar un panel dentro de otra web municipal, habrá que relajarlo **solo** para ese origen.

---

## 8. Comprobación tras desplegar

Recorrido corto que detecta el 95 % de los problemas de una puesta en marcha:

1. Abre la raíz: debe redirigir al proveedor de identidad y volver autenticado.
2. **Recarga estando en `/paneles`**: si sale un 404, falta la reescritura (5.1).
3. Entra por un **enlace directo** a un detalle: mismo criterio.
4. La consola del navegador debe estar limpia. Un error de CORS apunta a 4.1; uno del propio
   proveedor de identidad, a 4.2; uno de CSP, a la sección 7.
5. Abre el mapa: deben verse las teselas **y el texto de atribución**. Sin atribución, el despliegue
   incumple los términos de uso (véase la sección «Atribuciones obligatorias» del
   [`NOTICE.md`](../../NOTICE.md)).
6. Cambia a tema oscuro y recarga: debe mantenerse.
7. Deja la sesión abierta más de la vida del token —unos minutos— y vuelve a interactuar: debe
   renovarse sin expulsarte. Si te expulsa, revisa la configuración de sesión del cliente OIDC.
8. Repítelo en un móvil real, o a 390 px de ancho: sin desplazamiento horizontal de la página.
9. Cierra sesión: debe volver a `/login` y no dejar sesión activa al recargar.

Si el despliegue es la imagen de contenedor, además:

10. `docker inspect --format '{{.State.Health.Status}}' <nombre>` debe decir `healthy`.
11. `curl -s https://mi-dominio.es/config.js` debe mostrar los valores del entorno, y la respuesta
    llevar `Cache-Control: no-store`.
12. `docker logs <nombre>` no debe contener ningún `AVISO:` del entrypoint.
13. `curl -sI https://mi-dominio.es/` debe traer las cuatro cabeceras de seguridad y
    `Cache-Control: no-cache`; un fragmento de `/assets/` debe traer `immutable`.

---

## 9. Publicar una versión

1. Rama al día y las dos comprobaciones en verde: `npm run typecheck` y `npm run build`.
2. Sube la versión en `package.json` (versionado semántico).
3. Revisa [THIRD-PARTY-LICENSES.md](../THIRD-PARTY-LICENSES.md) si ha cambiado alguna dependencia, y
   [ASSETS.md](../ASSETS.md) si ha entrado algún recurso gráfico.
4. Etiqueta la revisión.
5. Construye con el `.env` del entorno destino y publica `dist/`, o construye la imagen con
   `APP_VERSION` y `VCS_REF` (sección 6.2).
6. Invalida la caché de `/index.html`.
7. Recorre la lista de la sección 8.

Guarda qué revisión está publicada en cada entorno. Mientras la configuración se incruste al
construir, «el artefacto de producción» y «el de preproducción» son ficheros distintos aunque
salgan del mismo `commit`: sin ese registro, un rollback es una adivinanza.

---

## 10. Dos detalles que conviene conocer

### 10.1 Toda la configuración se resuelve al arrancar, cartografía incluida

`src/lib/env.ts` expone `env(clave)`, que consulta `window.__APP_CONFIG__` y cae en el valor de
compilación; `index.html` carga `config.js` como script clásico antes del módulo, y
`public/config.js` mantiene un objeto vacío para desarrollo. **Ningún módulo de la aplicación lee
`import.meta.env.VITE_*` directamente**: pasan por `env()` la instancia de axios
(`src/api/http.ts`), el cliente OIDC (`src/auth/keycloak.ts`), los identificadores técnicos del
backend (`src/api/platform-contract.ts`) y la cartografía (`src/lib/mapConfig.ts`, del que tiran la
vista de mapa, `PointMap` y `EntityLocationMap`).

Consecuencia práctica: cambiar de proveedor de teselas **no exige reconstruir la imagen**, basta
cambiar `MAP_TILES_URL` en el contenedor. Y si se cambia, hay que cambiar en el mismo momento
`MAP_TILES_ATTRIBUTION` por el texto que exija el nuevo proveedor: la atribución es obligatoria por
sus términos de uso, y las dos variables viajan juntas por eso (sección 4 de
[`NOTICE.md`](../../NOTICE.md)).

### 10.2 La imagen se construye aquí, se publica fuera

El repositorio trae el `Dockerfile` y la configuración de nginx, así que la imagen se construye con
un solo comando (sección 6). Lo que no trae es la publicación en un registro de contenedores: eso
exige un registro y sus credenciales, y es una decisión de quien opera el servicio, no del código.
