# Registro de cambios

Todos los cambios reseñables de la plataforma se anotan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado es
[semántico](https://semver.org/lang/es/). Cada componente lleva además su propia versión en su
manifiesto (`pyproject.toml`, `composer.json`); la versión de esta página es la del conjunto.

## [2.0.0] — 2026-09-04

Se añade el motor de evaluación de alarmas, que la API publicaba sin que nadie lo ejecutase. Por lo
demás la plataforma se reduce: queda solo la superficie que la entrega usa de verdad. Y queda
instalable de principio a fin en un clúster real, con la identidad resuelta por completo en Keycloak.

Verificado con las tres suites del repositorio —83 pruebas de backend, 161 de la interfaz y las de
los cinco paquetes Python (205 de `aether-pylib`, 131 de `aether-link`, 53 de `fiware-manager`, 612
de `queues-consumer` y 566 de `predictions`)— y sobre el entorno demo, donde la batería de
verificación del despliegue deja en verde el camino completo de ingesta: envío por HTTP, IoT Agent,
Orion-LD, colas, persistencia en TimescaleDB, lectura por la API de series y actualización de la
base de tiempo real.

### Seguridad

- **Cerrados los hallazgos de la auditoría de tercera parte sobre PT01.4.** En el backend, control
  de acceso: una referencia directa a objeto dejaba leer las credenciales IoT de otra organización
  en `FiwareTenantScopeController`, se añade `PanelPolicy`, se autorizan los healthchecks y el
  secreto de la pasarela se compara con `hash_equals`. En `queues-consumer` se endurecen los
  endpoints internos: desaparece `/test-connection`, `/publish` exige token y lista blanca,
  `/stream` valida su entrada y el CORS pasa a lista blanca. El paquete de anomalías se sella con
  HMAC en lugar de viajar como `pickle`, la descompresión gzip lleva tope y la ingesta OTE falla
  cerrada, el `CREATE SCHEMA` de Timescale valida el *tenant*, el analizador de KML usa `defusedxml`
  y las imágenes Python dejan de ejecutar como root. Se endurecen también el realm de Keycloak, el
  entorno local de Compose y los charts. La clave `k` del *command-proxy* se documenta como lo que
  es: la autenticación del dispositivo.
- **Los dashboards públicos exigen un indicador de publicación explícito.** Las rutas
  `public/dashboards/{slug}` y `public/timeseries/{slug}` quedaban fuera de la autenticación y no
  comprobaban ningún campo que marcase el cuadro como publicado: bastaba conocer o adivinar el slug
  para leer el de cualquier organización. Se añade la columna `is_published`, por omisión falsa, se
  comprueba antes de servir —con 404, nunca 403, para no confirmar que el slug existe— y los slugs
  se emiten con suficiente entropía en lugar de derivarse del nombre.
- **La autorización del acceso público a series compara identificadores exactos.** La comprobación
  usaba `str_contains`, una coincidencia de subcadena sin anclar, evadible con un URN que
  contuviese al autorizado como fragmento; y una petición sin entidades explícitas no se comprobaba
  en absoluto. Ahora la comparación es exacta y una petición sin entidades se rechaza.
- **La deserialización de mensajes de cola resuelve la clase contra una lista blanca en código.**
  El módulo y la clase a instanciar venían dentro del propio mensaje, de modo que quien pudiera
  encolar elegía qué se importaba.
- **Los clientes públicos del realm dejan de admitir la concesión directa de contraseña.** Con ella
  bastaba con enviar usuario y contraseña y un identificador de cliente —visible en el propio
  frontend, sin secreto— para obtener un token por HTTP, saltándose el flujo de navegador y con él el
  segundo factor. Se desactiva en los cinco clientes públicos que la traían (`pid-gijon-client`,
  `vue-frontend`, `laravel-backend-client`, `queues-consumer-client` y `admin-cli`); ninguno la
  usaba. El acceso máquina a máquina sigue disponible por el cliente confidencial `laravel-backend`,
  que sí exige secreto y la conserva a propósito.
- **El realm de Keycloak deja de admitir el flujo implícito** en el cliente público, que entrega el
  token en el fragmento de la URL, y declara PKCE `S256`.
- **La imagen del backend ejecuta como usuario sin privilegios.** Había un `USER root` posterior al
  `USER www-data`, y rige el último. El `USER` final es ahora el uid numérico, para que el
  `runAsNonRoot` de Kubernetes pueda comprobarlo sin resolver `/etc/passwd`, y Apache abre el puerto
  con la capacidad justa (`cap_net_bind_service`) en lugar de con privilegios.
- **El secreto del usuario MQTT se deriva en lugar de cifrarse de forma reversible**, y el material
  criptográfico deja de venir en un seeder versionado. Una migración retira las columnas heredadas.
- **El cierre de sesión revoca el token** en el proveedor de identidad y en el almacén local, y
  responde con error si la revocación no se produce, en lugar de devolver éxito sin revocar nada.
- **Las conexiones AMQPS validan el certificado del intermediario** en los dos clientes del
  servicio, con autoridad de certificación declarada por entorno.
- **Los tokens de credencial verificable se validan** contra emisor, audiencia y algoritmo
  esperados, que se declaran aparte de la URL base del verificador.
- **`TrustProxies` declara los proxies de confianza** y la dirección de origen que se registra en
  los intentos de acceso se resuelve a través de ellos, en lugar de leerse en crudo de las
  cabeceras `X-Forwarded-*`, que cualquiera puede falsear.
- **Los recursos admisibles del guard de Keycloak se declaran explícitamente.**
- **Condición de carrera entre organizaciones en los proxies del núcleo FIWARE.** Los proxies del
  broker, del IoT Agent y de la API temporal son únicos por proceso y guardaban el *tenant* en su
  propio estado para leerlo al construir la cabecera; al dejar de estar serializados los
  manejadores, dos peticiones concurrentes de organizaciones distintas podían pisarse ese estado.
  El *tenant* pasa a ser local a cada llamada.

### Añadido

- **Personalización de la interfaz por organización**: colores de marca, logotipos y pie de página.
  Se piden tres colores y se derivan de ellos las variantes de tema claro y oscuro con el contraste
  garantizado, en lugar de pedir seis a mano, porque un color pensado para fondo claro rara vez
  cumple sobre fondo oscuro —el rojo corporativo de Gijón da 7,99:1 sobre blanco y 2,20:1 sobre la
  superficie oscura—; cada campo muestra el contraste obtenido en ambos temas. Los valores viven en
  las preferencias de organización que el backend ya validaba, así que no hay servicio nuevo, y se
  aplican en tiempo de ejecución sobre el tema de Vuetify: la misma imagen de contenedor sirve a
  cualquier organización. Se añade también el tema de Keycloak con los colores y el logotipo de
  Gijón, parametrizado con variables `KC_BRAND_*`.
- **Formulario de alta de alarmas** en la interfaz web.
- **Integración continua en GitHub Actions**, en cada `push` a `main` y en cada solicitud de
  incorporación: tipado, linter y Vitest de la interfaz; `pytest` de los cinco paquetes Python, cada
  uno con su versión de intérprete; y PHPUnit del backend sobre PostgreSQL con PostGIS y las tres
  conexiones de base de datos que la aplicación declara.
- **Red de pruebas donde no la había**: Vitest en la interfaz y pruebas de caracterización sobre los
  controladores de mayor complejidad del backend.
- **Motor de evaluación de alarmas** en el consumidor de colas: la API de gestión publicaba el alta
  de alarmas, sus condiciones y sus acciones, pero no existía el proceso que las evaluara, de modo
  que una alarma configurada nunca se disparaba. Se incorpora la evaluación de umbrales —con sus
  ocho operadores, sus restricciones temporales y la composición lógica de condiciones—, la
  detección de inactividad como tarea periódica, y la ejecución de acciones por Telegram, SMS y
  WhatsApp. Los canales de correo, notificación móvil, aviso HTTP y comando a dispositivo se pueden
  configurar desde la API pero todavía no se ejecutan.
- **Segmentación de red por componente** en el chart, con denegación por defecto y los saltos
  permitidos declarados por componente. Viene desactivada, porque activarla sin revisar el flujo
  del despliegue corta tráfico legítimo.
- **`GET /alive` en la capa de abstracción**, una sonda de proceso vivo sin dependencias, separada
  de `/hchk`, que ahora informa del estado real de los tres almacenes.
- **La autoridad de certificación del intermediario de mensajes es configurable** de punta a punta:
  variable, valores del chart, plantilla de entorno y generador, con el certificado montado desde
  un secreto opcional.

### Corregido

- **Cinco fallos que impedían instalar o actualizar en un clúster real.** `k3s-bootstrap.sh` no
  podía instalar los CRDs de Gateway API: el `apply` en cliente guarda el manifiesto en la anotación
  `last-applied-configuration` y el de `HTTPRoute` pasa de 256 KiB, así que moría a medias; ahora
  aplica en servidor. El chart de RabbitMQ no fijaba versión y el operador instalaba la 4.x, que
  rechaza las colas transitorias no exclusivas de Celery: se instalaba en verde y las colas quedaban
  sin consumidor, sin persistir nada y sin error visible. Keycloak pasa a estrategia `Recreate`
  —con `RollingUpdate` conviven dos pods, no forman clúster de Infinispan y el nuevo muere en
  bucle— y gana una `startupProbe`, sin la cual la sonda de vida lo mata durante un arranque lento.
  La plantilla del pod incorpora la anotación `checksum/config`, sin la cual un `helm upgrade` que
  solo cambiase configuración o secretos terminaba en verde dejando los pods con los valores
  viejos. Y
  `BACKEND_URL` pasa a ser la URL pública: no la usa el servidor, acaba en `window.BACKEND_URL` y la
  lee el navegador para descargar el logotipo de cada organización, de modo que con un nombre
  interno del clúster no resolvía nunca.
- **La construcción del backend caía por tres de sus noventa y ocho paquetes.** `composer.json`
  fijaba `preferred-install` a `dist`, lo que desactiva el respaldo a instalación desde fuente; con
  GitHub devolviendo 400 en su endpoint de archivo, esos tres bastaban para tumbar la imagen.
- **Reparado el empaquetado de `aether-link` y `fiware-manager`**, el `import` de `HTTPException` y
  los manejadores duplicados de `aether-link`, y se fija `laravel/framework` a la v10.50.3.
- **Reparadas las suites que no corrían**: la del backend, la de `queues-consumer`, que estaba
  bloqueada, y el fallo por zona horaria de `aether-pylib`.
- **`.gitignore`: los patrones de las carpetas de trabajo se anclan a la raíz.** Sin la barra
  inicial, `customization/` coincidía a cualquier profundidad e ignoraba en silencio el código de
  `frontend/src/customization`.
- **El nombre de un comando con guion bajo se registraba truncado.** `get_command_name` partía la
  clave del atributo por el primer `_`, de modo que `w_ota_status` daba `w`: el comando entraba en
  `entity_commands` con un nombre que no era el suyo y la API rechazaba después su envío con «You
  cannot send any of». Ahora se retira el sufijo `_info` o `_status` exacto, que es lo único con lo
  que se invoca la función.
- **La batería de verificación del despliegue resolvía siempre el mismo dispositivo.** Consultaba la
  paginación con un campo `filters` que ese endpoint no conoce —filtra con `search`— y pedía una
  sola fila ordenada por número de serie, así que devolvía el primero de la lista fuera cual fuera
  el configurado en `TEST_DEVICE_SERIAL`. Y la comprobación de persistencia partía sus medidas de la
  hora actual, con lo que una de ellas caía en el mismo segundo que los envíos sin `TimeInstant` de
  la etapa anterior y la sobrescribía, porque la serie se identifica por instante, entidad y
  atributo.


- **Las respuestas de validación devuelven el mapa de errores.** El manejador de excepciones
  reescribía el cuerpo de todas ellas dejando solo el mensaje y el código, así que un 422 no decía
  qué campo había fallado.
- **La comprobación de salud de la capa de abstracción vuelve a comprobar algo.** Su cuerpo estaba
  comentado y devolvía conformidad de forma incondicional, de modo que el orquestador daba por sano
  un servicio que podía no estarlo. Las comprobaciones se lanzan en paralelo con un presupuesto de
  tiempo acotado y las conexiones a base de datos llevan tiempo máximo de conexión.
- **Los manejadores que hablan con servicios síncronos dejan de bloquear el bucle de eventos.**
  Diecisiete de ellos se declaraban asíncronos sin serlo, con lo que una llamada lenta a un
  servicio externo congelaba el resto de las peticiones del proceso.
- **La clase base de las peticiones de la API abandona el espacio de nombres del marco**, donde era
  una copia literal de la clase de Laravel que ninguna actualización podía sobrescribir sin riesgo.
- **La configuración se lee siempre a través de la capa de configuración.** Treinta y tres lecturas
  directas del entorno quedaban fuera de ella y devolvían un valor vacío cuando la configuración
  está en caché, que es el modo recomendado en producción; entre ellas, el enlace del correo de
  restablecimiento de contraseña.
- **La biblioteca compartida declara la versión de Python que de verdad necesita**, y su fichero de
  bloqueo se ha regenerado en consecuencia.
- **Restos del recorte del repositorio**: un modelo inexistente que se importaba desde la capa de
  acceso a datos e impedía cargar el motor de alarmas.

### Accesibilidad

- **Cerrada la mayor parte de los hallazgos de accesibilidad de PT01.4**: enlace para saltar
  al contenido, manejo por teclado y alternativa textual en mapas y gráficas, `scope` y atributos
  ARIA en tablas y diálogos, y corrección de contrastes. Los mensajes de error llevan `role="alert"`
  y los de éxito `role="status"`. Se incorporan además las reglas de accesibilidad al linter, de
  modo que la comprobación queda automatizada.

### Cambiado

- **Reducidas complejidad y duplicación**, sin cambios de comportamiento: en el backend,
  `PreferenceValidator` por estrategia, el `switch` de `ResourceLimitsHelper` parametrizado,
  `ServiceProvisioningHelper` unificado, el objeto de valor `EntityFetchFilters` y el `join`
  deduplicado de `EntityRepository`; en Python, tabla de despacho en `realtime_sync_job`, clase base
  `BaseCrowdEntityLoad`, objeto de parámetros en el *backtest* de XGBoost y `MintakaDataSource`
  dividido en cliente HTTP y filtro de periodo; en la interfaz, los composables `useDebounce`,
  `usePaginatedList` y `useDebouncedResize`, un único módulo de análisis de series y `dashboards.ts`
  separado por capas.
- **Los README dejan de llevar el estado interno de pruebas.** La guía de despliegue y el README del
  módulo de predicción describían hasta dónde se había probado cada cosa, algo que no forma parte de
  la descripción de la plataforma. Las dos indicaciones operativas que iban dentro se conservan
  donde corresponde.

### Endurecido tras la revisión

Una verificación independiente de los cambios anteriores dejó anotados veintiún puntos, y estos son
los que tenían consecuencia:

- **El acceso público a series temporales ya no acepta el ámbito que mande el cliente.** Se resuelve
  a partir de las entidades del propio dashboard y se fuerza, porque con un enlace público
  válido se podía pedir un identificador autorizado en cualquier organización, y el error de esquema
  de la base servía para sondear qué existía.
- **El cierre de sesión comprueba que el refresh token pertenece a quien lo presenta.** Antes
  se usaba tal cual llegaba, de modo que quien obtuviera el de otra persona podía cerrarle la sesión.
- **La API restringe de qué cliente puede venir un token.** La clave pública es la del *realm*
  completo, así que sin esa lista valía cualquier token emitido en él. Es configurable por entorno y,
  vacía, conserva el comportamiento anterior para no romper instalaciones existentes.
- **La comprobación de salud de la capa de abstracción dejó de dar por caídos dos de sus almacenes.**
  Dos de los cuatro respaldos posibles respondían siempre que no estaban sanos, así que al restituir
  la sonda el servicio no llegaba nunca a estar listo con cualquiera de los dos configurado.
- **Los dashboards publicados se distinguen de los que solo tienen enlace**, también en el
  listado y en las respuestas de lectura, y la migración declara que la reemisión de enlaces no se
  puede revertir.
- **Segmentación de red coherente con el flujo real**: se retira el permiso de entrada que ningún
  componente usaba, se permite el sondeo de las sondas del orquestador y el corte del recogido de
  métricas deja de poder ocurrir en silencio.
- **El certificado del intermediario de mensajes se declara de punta a punta** y el arranque falla de
  forma explícita si se pide cifrado sin autoridad de certificación disponible.
- **Los proxies de confianza se declaran también en el despliegue**, donde faltaban: sin eso regía la
  lista por omisión y cualquier carga de las redes privadas podía falsear la dirección de origen.
- **Retirado código muerto** con configuración de cifrado que nadie ejecutaba, y **añadidas las
  pruebas** del cierre de sesión y de la restricción por cliente, que no existían.

### Eliminado

Nada se retira sin comprobar antes que no tiene consumidor, ni en el backend, ni en el frontend, ni en
los servicios Python que comparten base de datos.

- **Los restos del módulo de incidencias públicas**, que la reducción de la plataforma ya había
  desmontado en parte: quedaban un servicio, un seeder, su configuración, una tabla y tres
  plantillas de correo. 
- **El canal push de las alarmas**, que dependía de Firebase y APNS, servicios de terceros que esta
  entrega no despliega ni configura, junto con el cliente móvil del realm de Keycloak y su tema.
  Quedan los tres canales con destino propio: correo, HTTP y comando de entidad.
- **`POST /V1/login` y `POST /V1/refresh-token`.** La API de gestión ya no participa en la sesión:
  el acceso y la renovación se hacen contra Keycloak con flujo de código y PKCE `S256`, que es lo
  que el frontend ya hacía. `POST /V1/logout` se mantiene, porque revoca la sesión en el proveedor.
- **El flujo de contraseñas y, con él, el envío de correo de la API.** Las credenciales las gestiona
  Keycloak, que ya mandaba su propio correo de establecer contraseña. **El correo de alarmas de los
  consumidores y el SMTP de Keycloak son independientes y no se tocan.**
- **Los espacios de trabajo.** No tenían ninguna ruta, pero sí dos enganches vivos: dejan de ser
  titulares de permiso —ahora el único titular es el usuario— y `queues-consumer` deja de
  sincronizar su contexto al crear una entidad.
- **Las sondas**, el único de estos módulos con un efecto vivo: el aprovisionamiento en el IoT Agent
  recorría sus tipos además de los de dispositivo, y ahora recorre solo estos últimos.
- **El anclaje en blockchain y las credenciales verificables**, dos piezas que nadie llegó a unir:
  un endpoint de hash en Aether Link, el cableado de Polygon del chart —que configuraba una
  funcionalidad inexistente en el código— y la configuración `VC_*`, huérfana desde antes.
- **Los informes, las carpetas y la pantalla de inicio configurable**, sin una sola ruta que los
  expusiera ni trabajo que los generase. La entrega redirige la raíz a `/entidades`.
- **Las etiquetas de los dashboards**, cuyo catálogo solo alimentaba un filtro del listado que
  ningún frontend usa.
- **Las imágenes de dashboard y de panel**: seis operaciones de subida y descarga sin
  consumidor. La edición del panel se mantiene.
- **Las descargas, la exportación de datos y la de gráficas**, la tabla genérica de ficheros y los
  permisos de *reseller*. Ninguno tenía ruta ni nada que los escribiera.
- **Las notificaciones en la aplicación**: sus cinco operaciones y el aviso que el trabajo de
  importación de CSV de `queues-consumer` escribía al terminar, que era lo único que las alimentaba.
- **Los módulos sin superficie ni consumidor**: marketplace de IA, ficheros de dispositivo, eventos
  de tráfico, simulaciones WRF, `Bootstrap`, `Parking` y `PasswordReset`.
- **Los ayudantes y las tablas huérfanas que quedaban**: `FiwareProvisioningHelper`, sin ningún
  llamante desde la retirada de las sondas, `UserHelper` y `PermissionRepository`; tres tablas sin
  modelo ni lector y dos preferencias que se quedaron sin uso al caer la pantalla de inicio.

### Nota de compatibilidad

- **Retiradas las tablas huérfanas que quedaban y aplanado el historial de migraciones.** Ya no se
  crean `access_attempts` (con la relación `User::lastLogin` y los campos `ip`, `last_login_date` y
  `last_login_time` del recurso de usuario), `html_blocks`, `contracts`,
  `organization_has_contracts`, `contract_default_resource_limits`, `device_user`,
  `device_organization` ni `user_notifications`; esta última exigió quitar antes el aviso que
  escribía el trabajo de importación de CSV en `queues-consumer`. Además se han colapsado las
  migraciones que creaban una columna para borrarla poco después: `users` ya no nace con `password`,
  `remember_token`, `support_password`, `created_by` ni `level`; `log_lines` sin `channel`, `level`
  ni `context`; `mqtt_users` sin `password_encrypted` ni `password_salt`; `custom_datamodels` sin
  `send_type` ni `device_type_id`; `http_connector` sin `authorization`; y las columnas `up` de
  `alarms` y `payload_config` de `mqtt_connector` nacen ya con su nombre definitivo.

**Las tablas retiradas ya no se dropean: directamente no se crean.** En lugar de acumular
migraciones de baja, se han eliminado las migraciones que creaban esas cuarenta tablas y las que las
modificaban después. Una instalación nueva nunca las llega a crear.

La sonda de proceso vivo de la capa de abstracción **debe apuntar a `/alive`**, no a `/hchk`: esta
última informa ahora del estado de sus dependencias, y usarla como sonda de vida reinicia el
contenedor cada vez que uno de los almacenes deja de responder.

---

## [1.0.0] — Entrega inicial

Primera versión de la Plataforma de Integración de Datos ajustada al alcance del proyecto: ingesta
de sensores LIDAR y Smart Spot, análisis de afluencia, entidades, series temporales, cuadros de
mando, alarmas y preferencias.

### Añadido

- **Interfaz web** ([`frontend`](frontend)): visualizador de datos de sensores urbanos con cuadros de
  mando, análisis y mapa. Aplicación Vue 3 servida por nginx, con la configuración resuelta en
  arranque, de modo que la misma imagen vale para cualquier entorno. Se despliega como un componente
  más del chart. Es de titularidad municipal, igual que el módulo de predicción.

- **Documentación de la API** en formato OpenAPI 3, generada a partir de las rutas reales del
  servicio: [`openapi-gestion.yaml`](openapi-gestion.yaml) para la API de gestión (124 rutas, 164
  operaciones) y [`openapi-ingesta.yaml`](openapi-ingesta.yaml) para la de ingesta (4 rutas, 5
  operaciones).
- **Colecciones Postman** listas para importar, derivadas de las especificaciones anteriores, en
  [`postman/`](postman).
- **Inventario de componentes de terceros (SBOM)** en formato CycloneDX 1.5
  ([`sbom.json`](sbom.json)): 424 componentes con su versión, identificador `purl` y licencia
  declarada, incluidas las imágenes de infraestructura que despliega la plataforma.
- **Ficheros de bloqueo de dependencias**: `uv.lock` en los seis proyectos Python y `package-lock.json` en la interfaz web, de modo que cada
  construcción es reproducible y la cadena de dependencias queda auditable.
- **Guía de contribución** ([`CONTRIBUTING.md`](CONTRIBUTING.md)) y este registro de cambios, como
  documentación viva del proyecto.

### Cambiado

- **El análisis de afluencia se ejecuta para todas las organizaciones del despliegue**: los cinco
  procesos de `queues-consumer` que lo calculan recorren el conjunto completo de organizaciones.
- **Toda la documentación del repositorio está en castellano**: 43 documentos, incluidas la guía de
  despliegue, la referencia de infraestructura, secretos, Gateway API y pasarela API, y la
  documentación funcional de los procesos ETL de afluencia y del consumidor de colas.
- **Las tareas, las colas y el *exchange* de RabbitMQ viven bajo el espacio de nombres
  `platform.*`**, igual que las variables de entorno que se derivan del nombre de cola, de forma
  coherente en `backend`, `predictions`, `queues-consumer` y el chart de despliegue.
- **Licencia y autoría declaradas de forma uniforme**: los nueve manifiestos del repositorio
  (`composer.json`, los dos `package.json` y los seis `pyproject.toml`) indican `EUPL-1.2` y nombran en
  `authors` a quien escribió cada componente, en coherencia con el reparto del
  [`NOTICE.md`](NOTICE.md). La titularidad de la entrega la establecen [`LICENSE`](LICENSE) y ese
  mismo documento.
- **Construcción reproducible** de las imágenes Python: se instalan desde el fichero de bloqueo
  (`uv sync --locked`), que pasa a ser obligatorio en la construcción.


### Corregido

- **Consolidación de la superficie de la API de gestión**: todas las rutas publicadas resuelven
  contra un controlador existente, incluidas las variantes `create` y `edit` que `Route::resource`
  genera para formularios HTML y que una API no utiliza.
- **Documentación de despliegue al día** con la configuración real del servicio de ingesta: los
  secretos y las variables de entorno documentados coinciden con los que el servicio necesita.
