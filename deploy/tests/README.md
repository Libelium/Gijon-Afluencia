# PID Gijón — batería de verificación de la plataforma

Responde a una sola pregunta después de desplegar: **¿funciona de verdad la plataforma y, si no,
qué está roto exactamente y cómo se arregla?**

La batería comprueba el despliegue de fuera hacia dentro, igual que llegan a él las personas
usuarias y los dispositivos, e imprime un informe donde cada fallo viene con un consejo concreto de
reparación (el comando de kubectl que ejecutar, la sección de la documentación que seguir).

```bash
./tests/run-tests.sh <nombre-del-entorno>
```

Esa es toda la interfaz. La configuración sale de `environments/<nombre>/tests.env`, que
`scripts/generate-env.sh` genera por ti: con los argumentos por defecto no hay nada que configurar.

## Qué se comprueba

Las comprobaciones se ejecutan en orden de dependencia; cuando una falla, las que dependen de ella
se *saltan como bloqueadas* en lugar de fallar con errores secundarios confusos. **Arregla el
primer fallo, vuelve a lanzarlas y repite.**

| Etapa | Comprobaciones | Necesita |
|-------|----------------|----------|
| Requisitos previos | tests.env cargado, clúster accesible | — |
| Cargas del clúster | Pods de PostgreSQL / MongoDB / RabbitMQ / MinIO listos (solo los charts incluidos que hayas desplegado), todos los deployments de pid-gijon-core listos, sin patologías `ImagePullBackOff`/`CrashLoopBackOff`/`Pending`, valores de post-instalación de Keycloak aplicados (sin marcadores `REPLACE_AFTER_KEYCLOAK_SETUP`) | kubectl |
| Endpoints públicos | `/api/hchk` de web-back, realm `pid-gijon` de Keycloak, `/hchk` de fiware-manager, interfaz web — todo por HTTPS público, desde fuera del clúster | red |
| Autenticación | Inicio de sesión de administración por `/api/V1/login` (cadena web-back → Keycloak) | red |
| Ciclo de vida de un dispositivo | Resolver el dispositivo de `TEST_DEVICE_SERIAL` → enviar medidas por HTTP → la entidad refleja el dato (tubería de orion-ld) → ida y vuelta de un comando (`getCmd=1`) | red |
| Persistencia del dato | Las medidas aterrizan en el almacén de series temporales y se pueden recuperar por la API pública de series (carrot → RabbitMQ → consumidores → TimescaleDB) | red |
| Airflow *(opcional)* | Despliega una copia de usar y tirar del DAG `custom_iota_post` (`kubectl cp` al dag-processor y a los workers: Airflow 3 no tiene API de subida), crea sus Variables, lanza una ejecución, confirma que el IoT Agent aprovisionó la entidad en Orion-LD y luego borra el DAG y las Variables | red + kubectl |

La etapa de Airflow se ejecuta **solo cuando `AIRFLOW_URL` está definido** en `tests.env` (Airflow
es un complemento aparte, no forma parte del instalador base). Despliega y retira un DAG
desechable, así que nunca toca los DAG de producción sincronizados por git. Se configura con los
ajustes `TESTS_AIRFLOW_*` de `config.env` (como mínimo, la URL del api-server, unas credenciales de
administración, y la apikey y el tenant del IoT Agent con los que hace el POST el DAG).

Las etapas del flujo de dispositivo están adaptadas de la batería de pruebas de integración de la
plataforma. **La ingesta por LoRaWAN y MQTT no se cubre, a propósito**: depende de componentes
ajenos a este instalador.

**Alcance: la plataforma, no la infraestructura.** La batería verifica el *despliegue* de
pid-gijon: sus cargas de trabajo, sus endpoints públicos y su camino de datos. **No** comprueba
cómo se encamina el tráfico hacia dentro del clúster (Ingress frente a Gateway API frente a un
balanceador de nube, registros DNS, terminación TLS, el controlador de gateway): eso es
infraestructura que aportas tú, y cambia en cada plataforma. Las comprobaciones de endpoints
públicos confirman el resultado final con independencia de *cómo* esté cableado: si un nombre de
host no responde, lo dicen y señalan el enrutado o el DNS que hay que revisar, sin dar por supuesto
ningún controlador concreto.

## Ejemplo de informe

```
  Endpoints públicos
   ✗ API de la plataforma accesible (web-back /api/hchk)
       https://api.example.com/api/hchk → 404 (ninguna ruta casó)
       ↳ Algo respondió en este nombre de host, pero ninguna ruta casó con la
         petición, así que nunca llegó al servicio. Tu ingress o enrutador no
         tiene una regla para este host → servicio, o el nombre DNS público
         apunta al balanceador equivocado. (Son asuntos de infraestructura,
         no forman parte del despliegue de pid-gijon.)

  Autenticación
   — Inicio de sesión de administración por /api/V1/login
       (bloqueada: falló el requisito «API de la plataforma accesible (web-back /api/hchk)»)
```

## Acotar una ejecución

```bash
./tests/run-tests.sh prod                       # todo
./tests/run-tests.sh prod -m "not kubernetes"   # solo las comprobaciones de API (sin kubectl)
./tests/run-tests.sh prod -m kubernetes         # solo las del clúster
./tests/run-tests.sh prod -v --tb=short         # depurar un problema de la propia batería
```

Los argumentos adicionales se pasan a pytest tal cual. El código de salida es distinto de cero
cuando falla cualquier comprobación, así que el lanzador encaja en una tubería de CI sin cambios.

## Configuración (`environments/<nombre>/tests.env`)

Lo genera `scripts/generate-env.sh` (vuelve a ejecutarlo en entornos creados antes de que existiera
la batería). Todo lo que se puede deducir de `config.env` viene ya relleno. El fichero contiene la
contraseña de administración: está excluido de git, guárdalo a buen recaudo.

| Variable | Por defecto (generado) | Significado |
|----------|------------------------|-------------|
| `API_URL`, `FIWARE_MANAGER`, `KEYCLOAK_URL`, `FRONTEND_URL` | a partir de tus `DOMAIN_*` | Endpoints públicos bajo prueba. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | usuario de administración sembrado; **contraseña vacía** | Inicio de sesión en la plataforma. El usuario es por defecto el administrador sembrado del realm (`admin@example.com`; se cambia con `TESTS_ADMIN_USERNAME` en `config.env`). La contraseña no la genera este instalador: rellénala. |
| `DATA_API_KEY` | vacío | Clave de API del dispositivo (parámetro `k=`). Vacío → **se descubre sola** (ver más abajo); ponla a mano solo si el descubrimiento no puede llegar al IoT Agent. |
| `DEVICE_TYPE` | `one_fiware` | Tipo del dispositivo bajo prueba. |
| `TEST_DEVICE_SERIAL` | vacío | **Serial de un dispositivo ya aprovisionado** contra el que verificar el camino del dato. La API de gestión no expone el alta de dispositivos, así que la batería no puede crearse uno desechable. Vacío → se saltan las etapas 5 y 6. La batería **solo lee**: es seguro apuntarla a un dispositivo real. |
| `TENANT` | vacío | Tenant de las series temporales. Vacío → usa el que la plataforma asigne al dispositivo de prueba (en instalaciones estándar: `libelium`). |
| `REQUIRE_DATA_PATH` | `true` | Con `true`, un `DATA_API_KEY` sin resolver **hace fallar** las comprobaciones del camino de datos en lugar de saltarlas, de modo que una ejecución en verde significa de verdad que se verificó el camino IoT. Ponlo en `false` para hacerlas opcionales. |
| `PROPAGATION_ATTEMPTS` / `PROPAGATION_INTERVAL_SECONDS` | `8` / `2.5` | Presupuesto de sondeo de las comprobaciones con consistencia eventual (actualización de la entidad, persistencia de series). Súbelo si la plataforma va lenta bajo carga. |
| `TLS_VERIFY` | `false` | Ponlo en `true` cuando sirvas un certificado de confianza. |
| `KUBE_CONTEXT` | vacío (el contexto actual) | Contexto de kubectl para las comprobaciones del clúster **y** para el descubrimiento de `DATA_API_KEY`. |
| `CHECK_POSTGRES` / `CHECK_MONGODB` / `CHECK_RABBITMQ` / `CHECK_MINIO` | a partir de tus `EXTERNAL_*` / `STORAGE_TYPE` | Saltarse las comprobaciones de carga de los servicios que ejecutes por fuera. |

## Cómo obtener DATA_API_KEY y TENANT

Estos dos ajustes son los únicos valores propios de la instalación que necesitan las comprobaciones
del camino de datos y, **en un despliegue estándar, no hace falta definir ninguno**: déjalos en
blanco y la batería los resuelve sola.

- **`TENANT`** — la batería usa el tenant que la plataforma asigna al dispositivo de prueba que
  crea (en instalaciones estándar: `libelium`). Define `TENANT` solo si quieres forzar otro.
- **`DATA_API_KEY`** — el parámetro `k=` con el que un dispositivo empuja datos. Es la clave de API
  del *grupo de servicio* del IoT Agent bajo el que está aprovisionado el dispositivo. La batería
  la resuelve en este orden:
  1. un `DATA_API_KEY` explícito en `tests.env` (no hace falta acceso al clúster);
  2. la respuesta de la API de dispositivos, si expone la clave;
  3. la **API de administración del IoT Agent**, consultada por el dispositivo desechable que la
     batería acaba de aprovisionar — necesita acceso al clúster con `kubectl` (el mismo que usan
     las comprobaciones del clúster).

### Leerla a mano (instalaciones no estándar)

Si el descubrimiento automático falla —sin acceso a `kubectl`, el IoT Agent corre en otro sitio, o
tu tipo de dispositivo se aprovisiona de otra forma—, lee la clave directamente. Una plataforma
puede definir varios grupos de servicio para el mismo tipo de entidad, así que la única fuente
inequívoca es un dispositivo realmente aprovisionado.

1. Crea un dispositivo de tu `DEVICE_TYPE` en la interfaz o la API de la plataforma (o reutiliza uno
   real), y anota su **serial** y su **tenant** (el `tenant` de la entidad principal del
   dispositivo, por ejemplo `libelium`).
2. Pídele ese dispositivo al IoT Agent: su `apikey` es tu `DATA_API_KEY`.

   ```bash
   # Se ejecuta desde dentro del clúster (el puerto de administración 4041 no es público).
   POD=$(kubectl get pods -n pid-gijon \
     -l "$(kubectl get deploy iot-agent-json -n pid-gijon \
            -o go-template='{{range $k,$v := .spec.selector.matchLabels}}{{$k}}={{$v}},{{end}}')" \
     -o jsonpath='{.items[0].metadata.name}')

   kubectl exec -n pid-gijon "$POD" -- node -e '
     const http=require("http");
     const [id,svc]=process.argv.slice(1);
     http.get({host:"localhost",port:4041,path:"/iot/devices/"+encodeURIComponent(id),
       headers:{"fiware-service":svc,"fiware-servicepath":"/"}},r=>{
       let b="";r.on("data",c=>b+=c);r.on("end",()=>console.log(JSON.parse(b).apikey));
     });' "<serial-del-dispositivo>" "<tenant>"
   ```

3. Pon el valor impreso en `environments/<nombre>/tests.env`:

   ```
   DATA_API_KEY=<la clave>
   TENANT=<el tenant>      # solo si no se resuelve correctamente sola
   ```

Para listar en su lugar todos los grupos de servicio (útil al elegir por tipo de entidad), llama a
`GET /iot/services` con la cabecera `fiware-service: <tenant>` de la misma manera.

## Requisitos

- Python ≥ 3.10 (en la primera ejecución se crea automáticamente un entorno virtual con `pytest` y
  `requests` en `tests/.venv`; se usa `uv` cuando está disponible).
- `kubectl` con acceso al clúster — solo para las comprobaciones a nivel de clúster; las de API se
  ejecutan desde cualquier sitio con acceso de red a los nombres de host públicos.

## Estructura

```
tests/
  run-tests.sh             punto de entrada: prepara las dependencias de Python, carga tests.env y lanza pytest
  conftest.py              registra el resultado de cada comprobación e imprime el informe final
  helpers/
    report.py              CheckFailure con consejo + renderizado del informe + dependencias
    config.py              ajustes leídos de tests.env
    kube.py                envoltorio de kubectl (comprobaciones de solo lectura, descubrimiento de DATA_API_KEY, exec/cp)
    api.py                 cliente de la API de la plataforma (adaptado de sus pruebas de integración)
    airflow.py             cliente REST de Airflow 3 + utilidades de despliegue de DAG (etapa opcional)
    session.py             token y dispositivo compartidos entre etapas
  assets/
    dag_custom_iota_post.py.tpl   DAG desechable que la etapa de Airflow genera y despliega
  test_00_prerequisites.py … test_07_airflow.py   las comprobaciones, en orden
```
