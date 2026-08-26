# Arquitectura

PID-GIJÓN es una **aplicación de página única (SPA)** escrita en Vue 3 con TypeScript, compuesta
con Vuetify 3 y empaquetada con Vite. No tiene servidor propio: se construye a un directorio de
ficheros estáticos y consume una **API REST** y un **proveedor de identidad OIDC**, ambos
externos.

```
   navegador
   ┌──────────────────────────────────────────┐
   │  PID-GIJÓN (ficheros estáticos)          │
   │                                          │
   │  vistas ── stores ── capa api ── axios ──┼──► API REST   /api/V1
   │                │                         │
   │                └──── cliente OIDC ───────┼──► Keycloak (OpenID Connect)
   └──────────────────────────────────────────┘
                                              └──► teselas de mapa (OpenStreetMap)
```

---

## 1. Estructura de carpetas

```
pid-gijon/
├── index.html                 punto de entrada; título e icono
├── vite.config.ts             alias @ → src, plugin de Vue y de Vuetify, puerto 20600
├── tsconfig.json              strict, noUnusedLocals, paths
├── env.d.ts                   tipos de las variables VITE_*
├── .env.example               plantilla de configuración (documentada en el README)
├── public/
│   └── favicon.svg            único recurso gráfico (véase ASSETS.md)
├── docs/                      esta documentación
└── src/
    ├── main.ts                arranque: pinia → vuetify → auth → sesión → router → mount
    ├── App.vue                aplica el tema; no contiene interfaz
    ├── brand.ts               nombre y título del producto, en un solo sitio
    ├── api/
    │   ├── http.ts            instancia axios, token, refresco, ApiError
    │   ├── user.ts            usuario y preferencias
    │   └── platform-contract.ts  identificadores técnicos del backend, leídos del entorno
    ├── auth/
    │   └── keycloak.ts        cliente OIDC: init, token, refresco, logout
    ├── components/
    │   ├── StateBlock.vue     cargando / error / vacío / contenido
    │   └── PageHeader.vue     título, subtítulo, volver, acciones
    ├── features/
    │   └── <feature>/
    │       ├── routes.ts      rutas de la funcionalidad
    │       ├── i18n.ts        fragmento de textos de la funcionalidad
    │       ├── api/           llamadas HTTP propias de la funcionalidad
    │       ├── components/    componentes que solo usa esta funcionalidad
    │       └── views/         pantallas
    ├── i18n/
    │   ├── es.ts              textos comunes
    │   └── index.ts           fusiona los fragmentos y expone t()
    ├── layouts/
    │   ├── AppShell.vue       menú lateral, barra superior, contenedor
    │   └── BlankLayout.vue    lienzo sin cromo (inicio de sesión)
    ├── lib/
    │   └── format.ts          fechas, números y medidas
    ├── plugins/
    │   └── vuetify.ts         tema y defaults (véase design-system.md)
    ├── router/
    │   └── index.ts           compone las rutas de las funcionalidades
    ├── stores/
    │   ├── session.ts         usuario, preferencias, huso horario
    │   └── ui.ts              tema y estado del menú
    ├── types/
    │   └── index.ts           tipos del dominio, compartidos
    └── views/
        ├── LoginView.vue
        ├── ForbiddenView.vue
        └── NotFoundView.vue
```

Las funcionalidades actuales son `entities`, `map`, `dashboards`, `alarms` y `preferences`.

### Qué va en el núcleo y qué va en una funcionalidad

| Va en `src/` (núcleo) | Va en `src/features/<x>/` |
| --- | --- |
| Tipos usados por más de una funcionalidad | Tipos que solo entiende esa funcionalidad |
| Cliente HTTP, autenticación, tema, formato | Llamadas concretas a la API de esa funcionalidad |
| Componentes reutilizados por todas las pantallas | Componentes de esa funcionalidad, aunque parezcan genéricos |
| Textos comunes (`common.*`, `app.*`) | Textos con el prefijo de la funcionalidad |

Regla de decisión: **un componente sube al núcleo cuando lo pide la tercera funcionalidad**, no la
segunda. Duplicar una tarjeta pequeña es más barato que un componente compartido con seis props
booleanas.

---

## 2. Por qué un monolito

La aplicación es un único proyecto, un único `package.json` y un único build. No hay
micro-frontends, no hay federación de módulos, no hay un paquete por funcionalidad.

Las razones, por orden de peso:

1. **Es lo que se entrega y lo que hay que mantener.** El destinatario es un ayuntamiento, y el
   código se publica como software libre. Un desarrollador que llega debe poder clonar, `npm
   install`, `npm run dev` y tener la aplicación entera funcionando. Cada capa de orquestación
   añadida es una barrera de entrada permanente.
2. **El tamaño no lo justifica.** Cinco funcionalidades, una API, un proveedor de identidad. Un
   monolito modular cubre esto sin coste: la separación por carpetas ya da límites claros.
3. **El despliegue es un directorio estático.** Un `dist/` que se sirve desde cualquier servidor
   web o almacenamiento de objetos. Con micro-frontends serían N artefactos, N pipelines y un
   contrato de versiones entre ellos.
4. **Un solo grafo de tipos.** `vue-tsc --noEmit` comprueba la aplicación completa en una pasada,
   incluidas las plantillas. Con paquetes separados esa garantía se pierde en las fronteras.
5. **Una sola instancia de las bibliotecas.** Vue, Vuetify y el tema existen una vez. Es lo que
   permite que un cambio de paleta se aplique a todas las pantallas.

Lo que sí se conserva de una arquitectura modular: **una funcionalidad se puede borrar quitando su
carpeta y sus dos líneas de registro**. Nada del núcleo importa desde `features/`, y una
funcionalidad no importa de otra. Si aparece esa necesidad, lo compartido sube al núcleo.

División de carga en tiempo de ejecución: cada vista se registra con `component: () =>
import('./views/…')`, así que Vite genera un fragmento por pantalla y el arranque solo descarga el
cascarón, no las cinco funcionalidades.

---

## 3. Cómo se agregan las rutas

Cada funcionalidad exporta un array de `RouteRecordRaw` en su `routes.ts`:

```ts
// src/features/alarms/routes.ts
const routes: RouteRecordRaw[] = [
  { path: '/alarmas', name: 'alarms-list', component: () => import('./views/AlarmsListView.vue'), meta: { title: 'Alarmas' } },
  { path: '/alarmas/:id', name: 'alarm-detail', component: () => import('./views/AlarmDetailView.vue'), props: true, meta: { title: 'Alarma' } },
]
export default routes
```

Y `src/router/index.ts` los inserta como hijos del layout autenticado:

```ts
children: [
  { path: '', redirect: '/entidades' },
  ...entityRoutes, ...mapRoutes, ...dashboardRoutes, ...alarmRoutes, ...preferenceRoutes,
  { path: '/sin-acceso', … }, { path: '/:pathMatch(.*)*', … },
]
```

Convenciones:

- **Las URL están en español** (`/entidades`, `/mapa`, `/paneles`, `/alarmas`, `/preferencias`):
  las ve el ciudadano. Los `name` están en inglés, como el código.
- `meta.title` es el nombre de la sección; `router.afterEach` lo compone con el nombre del
  producto mediante `pageTitle()` de `src/brand.ts` y lo escribe en `document.title`.
- `meta.public: true` marca las rutas que no exigen sesión. Solo la de inicio de sesión lo lleva.
- El detalle recibe el identificador como prop (`props: true`), no leyendo `useRoute()` dentro de
  la vista: la vista queda comprobable con un valor cualquiera.

El guardia es deliberadamente corto, porque la sesión ya está resuelta antes de montar
(sección 5):

```ts
router.beforeEach((to) => {
  if (to.meta.public) return true
  if (!isAuthenticated()) { void login(); return false }
  return true
})
```

**Añadir una funcionalidad** = crear la carpeta con su `routes.ts` y su `i18n.ts`, y añadir dos
importaciones y dos líneas en `router/index.ts` y en `i18n/index.ts`. Nada más del núcleo se toca.

---

## 4. Cómo se agregan los textos (i18n)

Los textos de interfaz están **siempre en español** y viven en un diccionario plano de claves con
punto. El núcleo aporta `src/i18n/es.ts` (`app.*`, `common.*`, `error.*`, `login.*`) y cada
funcionalidad aporta su fragmento en `features/<x>/i18n.ts`, con sus claves prefijadas por el
nombre de la funcionalidad. `src/i18n/index.ts` los fusiona:

```ts
const messages: Record<string, string> = { ...base, ...entities, ...map, ...dashboards, ...alarms, ...preferences }

export function t(key: string, params?: Record<string, string | number>): string { … }
```

Por qué así y no con un único fichero de textos: **para que dos funcionalidades no compitan por el
mismo fichero**. Un fichero central de traducciones es el punto de conflicto garantizado en cuanto
hay más de una persona trabajando, y además obliga a abrirlo para entender una pantalla. Con el
fragmento al lado de las vistas, el texto se lee donde se usa.

- `t()` interpola con `{parámetro}`.
- Si falta una clave, devuelve la clave y avisa por consola **solo en desarrollo**: la pantalla no
  se rompe, pero el hueco es visible mientras se programa.
- `locale` (`'es-ES'`) es el que consumen `Intl` y Luxon en `src/lib/format.ts`.

El módulo es un envoltorio mínimo a propósito: `t()` es la única superficie que ven las vistas, así
que sustituirlo por `vue-i18n` el día que haya un segundo idioma no obliga a tocarlas.

---

## 5. Autenticación (OIDC)

El proveedor de identidad es **Keycloak**, consumido con `keycloak-js` mediante **Authorization
Code Flow con PKCE (`S256`)**. Todo está encapsulado en `src/auth/keycloak.ts`; ningún componente
manipula tokens.

### El arranque resuelve la sesión antes de montar

```ts
// src/main.ts
const isPublic = PUBLIC_PATHS.some((p) => window.location.pathname.startsWith(p))
await initAuth(isPublic)
if (isAuthenticated()) await useSessionStore().load()
app.use(router); await router.isReady(); app.mount('#app')
```

El orden importa. Si se monta antes de resolver la sesión, la primera petición de la primera vista
sale **sin cabecera `Authorization`**, recibe un 401 y el usuario ve un error en una pantalla que
en realidad sí tenía permiso. Montar después cuesta unos milisegundos de pantalla en blanco y
elimina esa clase de fallo por completo.

Las rutas públicas se inician con `onLoad: 'check-sso'` (mira si ya hay sesión, sin redirigir); el
resto con `'login-required'` (redirige al proveedor).

### Por qué se inicializa siempre el cliente

Es la decisión menos obvia del módulo y la más importante:

> Se inicializa **siempre** el cliente OIDC. Reconstruir la sesión leyendo el token guardado en
> `localStorage` deja la instancia sin inicializar, incapaz de refrescar, y el primer 401 expulsa
> al usuario.

Desarrollado: el atajo tentador es guardar el token, leerlo al arrancar y saltarse `init()` porque
«ya hay sesión». El problema es que un token de acceso es un objeto de vida corta —minutos— y
quien lo renueva es el cliente OIDC, que para renovar necesita su estado interno: el token de
refresco, el descubrimiento del proveedor, el verificador PKCE y los temporizadores. Sin `init()`
ese estado no existe. El resultado es una aplicación que parece funcionar durante unos minutos y
luego, en la primera renovación, empieza a devolver 401 en cada petición y termina cerrando la
sesión en medio de una tarea. Peor aún: el fallo no aparece en desarrollo, donde se recarga cada
poco, sino en producción, en la sesión larga de una persona que está trabajando.

Además, `init()` es lo único que puede detectar que la sesión **ya se cerró en el proveedor** —en
otra pestaña, o por caducidad del lado del servidor—. Un token guardado no lo sabe: sigue
pareciendo válido hasta que expira.

Coste: una llamada al proveedor en el arranque. Beneficio: la sesión siempre es real, y siempre
renovable.

### Renovación

Dos mecanismos que se complementan:

- **Preventivo**: un temporizador cada 60 s llama a `updateToken(70)`, que renueva si al token le
  quedan menos de 70 segundos. Así, en uso normal, el token nunca llega a caducar.
- **Reactivo**: si una petición recibe un 401, el interceptor de respuesta fuerza un refresco y
  **reintenta la petición una sola vez** (`config._retried`). Si el refresco falla, se cierra la
  sesión.

El refresco reactivo está **compartido**: `refreshToken()` guarda la promesa en vuelo, de modo que
N peticiones que reciben 401 a la vez esperan al mismo refresco en lugar de disparar N. Sin esto,
una pantalla con seis paneles produce seis renovaciones simultáneas y el proveedor invalida unas
con otras.

`logout()` limpia el temporizador y redirige a `/login`.

### Autorización

La aplicación **no decide permisos**: los decide la API. Un `403` se traduce en el mensaje
«No tienes permiso para realizar esta acción» y, cuando afecta a una pantalla completa, en la vista
`/sin-acceso`. Ocultar un botón en el cliente es cortesía, no seguridad: la comprobación que cuenta
está en el servidor.

---

## 6. Gestión de errores

Un único camino, con tres piezas.

### 6.1 La capa api propaga; nunca devuelve `null`

```ts
export async function getPreferences(userId: number): Promise<UserPreferences> {
  const { data } = await http.get<UserPreferences>(`/user/${userId}/preferences`)
  return data
}
```

Devolver `null` en el fallo haría **indistinguible «no hay datos» de «ha fallado»**, y esa
ambigüedad acaba siempre en una pantalla que muestra «No hay resultados» cuando lo que ha pasado es
que el servidor está caído. La capa api devuelve el dato o lanza.

### 6.2 `ApiError` clasifica el fallo

El interceptor de `src/api/http.ts` convierte cualquier fallo de axios en un `ApiError` con un
`kind`:

| `kind` | Origen | Mensaje por defecto |
| --- | --- | --- |
| `network` | sin respuesta | No se ha podido contactar con el servidor. Revisa tu conexión. |
| `auth` | 401 | Tu sesión ha caducado. Vuelve a iniciar sesión. |
| `forbidden` | 403 | No tienes permiso para realizar esta acción. |
| `notFound` | 404 | No se ha encontrado el recurso solicitado. |
| `validation` | 400, 422 | Los datos enviados no son válidos. |
| `server` | ≥ 500 | El servidor ha devuelto un error. Inténtalo de nuevo en unos minutos. |
| `unknown` | resto | Se ha producido un error inesperado. |

Si la respuesta trae un `message` o un `error` legible, ese texto gana al mensaje por defecto: el
servidor sabe más del fallo concreto que el cliente. `errorMessage(e)` devuelve siempre una cadena
mostrable, incluso si lo que llegó al `catch` no era un `ApiError`.

### 6.3 La vista traduce el error a estado

```ts
async function load() {
  loading.value = true; error.value = null
  try { rows.value = await listSomething(query) }
  catch (e) { error.value = errorMessage(e) }
  finally { loading.value = false }
}
```

Y el error se pinta con `StateBlock`, que además ofrece **reintentar** emitiendo `retry`. La vista
no inspecciona códigos HTTP ni compone mensajes: eso ya está resuelto.

Consecuencias de este reparto:

- Ningún `alert()`, ningún `console.error` como forma de informar al usuario.
- Un fallo de red y un fallo de permisos se distinguen sin que la vista sepa nada de HTTP.
- El 401 no llega a la vista: lo absorbe el interceptor (refresco + reintento, o cierre de sesión).

---

## 7. Estado

Dos stores de Pinia, y ninguno más de momento:

- **`useSessionStore()`** — usuario autenticado, sus preferencias, su huso horario (`timeZone`, con
  `Europe/Madrid` de reserva) y `displayName`. Se carga una vez en el arranque con `GET /user`, que
  ya devuelve las preferencias resueltas: no hace falta una segunda llamada.
- **`useUiStore()`** — tema (`light` | `dark`), menú colapsado (`rail`) y visible (`drawer`).
  Persiste tema y `rail` en `localStorage` con las claves `pidgijon.theme` y `pidgijon.nav.rail`.

Lo que **no** se pone en un store: los datos de una pantalla. Viven en la vista, con su `loading` y
su `error` al lado, y se vuelven a pedir al entrar. Una caché global de entidades y series
temporales exigiría invalidación, y la invalidación mal hecha es peor que una petición de más. Un
store solo se justifica cuando el estado sobrevive a la navegación y lo comparten pantallas
distintas.

---

## 8. Configuración y contrato con el despliegue

Toda la configuración entra por **variables de entorno `VITE_*`**, tipadas en `env.d.ts` y
documentadas en `.env.example` y en el README. Se resuelven **en tiempo de compilación**: cada
despliegue construye con su `.env`. Nada de secretos: solo URL, identificadores públicos de cliente
OIDC y parámetros de mapa.

Aparte están los **identificadores técnicos del backend**, en
[`src/api/platform-contract.ts`](../src/api/platform-contract.ts): la clave de la preferencia que
fija el ámbito de datos y el tipo de entidad NGSI-LD bajo el que se publica el estado de una
alarma. No son nombres de producto, son claves de datos existentes en el sistema con el que se
integra, y por eso se leen del entorno en lugar de estar escritas en el código. Si faltan,
`missingContractKeys()` lo dice y la funcionalidad que dependa de ellas **se degrada de forma
explícita, nunca en silencio**.

Esta indirección tiene una segunda ventaja: el repositorio publicado no queda atado a los
identificadores de un despliegue concreto.

---

## 9. Calidad

| Comprobación | Orden | Qué garantiza |
| --- | --- | --- |
| Tipos | `npm run typecheck` | `vue-tsc` en modo estricto, plantillas incluidas |
| Build | `npm run build` | Comprueba tipos y luego empaqueta |

Las comprobaciones obligatorias antes de abrir un cambio están en
[CONTRIBUTING.md](../CONTRIBUTING.md).
