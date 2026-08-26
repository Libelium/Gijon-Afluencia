# predictions

Fusión de sensores **LIDAR + Smart Spot** y **predicción de afluencia** para el gemelo digital de
flujos de personas.

El repositorio cubre tres cosas: los **algoritmos** de fusión y clasificación (módulos autónomos,
ejecutables por separado), los **procesos ETL** de producción (`scripts/main.py` + `etl/`) y el
**modelo de predicción de aforo** (`scripts/train.py` / `scripts/predict.py`, XGBoost).

- Stack: **Python 3.10** · pandas · XGBoost · scikit-learn.
- Servicio de Compose: `crowd` (contenedor `crowd-predictions`). Una sola imagen; lo que cambia
  entre trabajos es el comando.

Las rutas de este documento son relativas al paquete: `etl/crowd/extract.py` significa
`crowd_predictions/etl/crowd/extract.py`. Sólo `scripts/` y `tests/` quedan fuera de él.

---

## Estructura

```
crowd_predictions/     el paquete instalable — todo lo importable vive aquí
  config/                backends de almacenamiento + settings.py (cada variable, tipada)
  helpers/               cliente de Aether Link, claves de almacenamiento, publicador, multi-tenant
  etl/crowd/             el ETL de fusión        etl/predict/   el ETL de predicción
  etl/ote/               el ETL de ingesta del crudo LIDAR
  train_pipeline.py      el entrenamiento (frío/caliente, selección de características)
  predict_pipeline.py    un ciclo de predicción por destino
  daily_pipeline.py      entrenar + predecir en una pasada: lo que invoca el CronJob
  anomaly_detection/     la vertical de anomalías (núcleo, almacenamiento, pipeline)
scripts/               puntos de entrada finos, los que invoca el contenedor
  run_daily.py           <- CronJob principal: entrena y predice
  run_ote.py             <- el otro CronJob: compacta e ingesta el archivo LIDAR
  main.py  train.py  predict.py  post_measures.py  run_anomalies.py
  run_ingest.py  compact_ote_archive.py  update_weather.py
tests/                 importa el paquete INSTALADO, igual que producción
pyproject.toml         única fuente de dependencias y de la configuración de pytest
```

## Módulos

- `zones_config.py` — las zonas del despliegue y los dispositivos instalados en cada una, leídas de
  `ote/zones/{tenant}/{scope}/zones.json` en el almacenamiento, **no de este fichero**. El código
  **filtra por este registro**, así que un `zones.json` que falte es un fallo duro y nunca un valor
  por defecto: un registro vacío se parece demasiado a una ejecución correcta que no publicó nada.
  El formato no admite aforo máximo ni porcentaje de ocupación: un aforo que nadie ha medido es un
  número que parece oficial y es inventado.
- `lidar_estimation.py` — recuento por zona según tres casos (`classify_zone_case`):
  - **mixto** (LIDAR + Smart Spot): manda el LIDAR cuando tiene lectura en la ventana. La señal de
    Smart Spot se reporta aparte como `smartspot_delta_pct` (diagnóstico: cuánto se desvía del
    LIDAR), nunca mezclada en la cifra de aforo.
  - **sólo LIDAR**: se confía en su recuento directo.
  - **sólo Smart Spot**: se corrige con el factor de calibración aprendido en las zonas mixtas
    (`confidence="estimated"`), o se deja sin corregir y marcado explícitamente
    (`confidence="estimated_uncalibrated"`) si todavía no hay zona mixta con datos.
  - **Corrección de cobertura del LIDAR, configurable por sensor**: cada LIDAR cubre un campo de
    visión real que depende del montaje. `zones_config.lidar_coverage_multiplier()` suma el FOV
    declarado de cada sensor de la zona (`fov_degrees` en `zones.json`) y corrige por `360 / suma`,
    con suelo 1.0. El valor por defecto son 360°, de modo que la corrección es neutra salvo que un
    sensor declare un arco menor.
- `crowd_prediction.py` — predicción por día de la semana: media histórica de las últimas N
  apariciones del mismo día, hora a hora. Incluye `backtest_weekday_prediction()` para medir
  MAE/MAPE contra un día ya conocido. Sirve de referencia contra la que se compara el modelo.
- `training_data.py` — de series de ocupación a tabla de entrenamiento: características de
  calendario cíclicas (seno/coseno de hora y día de la semana), `is_weekend`, `month`,
  `is_holiday`/`is_holiday_eve` (biblioteca `holidays`, región en
  `HOLIDAYS_COUNTRY`/`HOLIDAYS_SUBDIVISION`, que calcula sola las fiestas móviles cada año),
  `is_high_season`, `event_magnitude`, `precip_mm`, `lag_1d`/`lag_1w`, `rolling_mean_7d`/`28d` y
  `rolling_std_7d`/`28d`: las 17 de `FEATURE_COLUMNS`.
  Las de calendario se derivan en `CALENDAR_TIMEZONE`, no en UTC: los datos se guardan en UTC y una
  hora nocturna caería en el DÍA equivocado. Las de retardo y media móvil se buscan por marca de
  tiempo exacta, no por posición, porque las series tienen huecos. Las móviles devuelven `NaN` si no
  está presente al menos `ROLLING_MIN_COVERAGE` de los días de su ventana, en vez de promediar lo
  que haya y llamarlo media de 28 días.
  **Qué características se usan se decide en cada ejecución** (`select_feature_columns()`): una
  candidata sobrevive si es calculable el último día y aún deja `MIN_USABLE_TRAINING_DAYS` de filas,
  así que el escalón de 28 días entra solo el día que el histórico llega. Por debajo del de 7 días
  los puntos de entrada se niegan a entrenar y no publican nada.
- `weather.py` — precipitación y temperatura horarias vía Open-Meteo (gratuito, sin clave).
  `training_data.py` nunca llama a la red: lee una caché en el almacenamiento, que refresca el
  primer paso de `daily_pipeline.py`. Un fallo ahí no bloquea el entrenamiento ni la predicción.
  Sin `WEATHER_LAT`/`WEATHER_LON` el refresco no hace nada y `precip_mm` vale 0.0.
- `events_registry.py` — eventos puntuales (mercados, ferias, conciertos) registrados **a mano**,
  una fila CSV por evento (`date,event_type,device_ids,notes`): a diferencia de festivos, temporada
  o meteorología, un evento no se puede calcular, alguien tiene que saber que ocurre. Vive en el
  almacenamiento, bajo el mismo prefijo que el modelo. `device_ids` vacío = afecta a todas las zonas
  de ese día.
- `crowd_xgboost_model.py` — XGBoost (`count:poisson`, porque son recuentos) sobre la tabla
  anterior, un único modelo para todas las zonas (`zone_id` con codificación *one-hot*). Partición
  **temporal** (la reserva son los últimos días, nunca aleatoria) y `tune_hyperparameters()` con
  validación separada de la reserva final, para no inflar la métrica que se reporta. Siempre se
  compara contra la referencia de `crowd_prediction.py` sobre la misma reserva.
- `prediction_features.py` — construye filas de características para horas FUTURAS reutilizando
  `training_data.py` sin tocarlo.
- `fixtures.py` — genera eventos de Smart Spot y recuentos LIDAR sintéticos (residentes que repiten
  a diario + visitantes con un itinerario de una sola visita) para poder probar todo lo anterior sin
  sensores reales.
- `smartspot_transform.py` — convierte recuentos agregados en entidades `CrowdFlowObserved`. Sólo
  agregados, nunca detecciones por persona.
- `fake_measures.py` (CLI: `scripts/post_measures.py`) — herramienta de PRUEBA: publica medidas
  **ficticias** en el entorno al que apunten las variables, para validar la tubería a mano o llenar
  un entorno de histórico verosímil. Un único script para ambas fuentes (`--source lidar|smartspot`),
  con dos modos de generación (`--mode fixture|random`) y dos rutas de publicación (`--route
  iota|batch`).

  ```bash
  python scripts/post_measures.py --source lidar --dry-run   # construye y enseña, no publica
  python scripts/post_measures.py --source smartspot --mode random \
      --entities 6 --mean 120 --interval 15m \
      --from 2026-05-01T00:00:00Z --to 2026-05-31T23:45:00Z
  ```

## Detección de anomalías

Una **vertical separada** (`crowd_predictions/anomaly_detection/`): no está enganchada a los ETL de
fusión ni de predicción y no añade ninguna columna a lo que éstos publican. No sabe nada de zonas ni
de aforo —sólo identificadores de entidad, medidas y marcas de tiempo—, así que se puede apuntar a
cualquier modelo de datos. Responde al requisito de detección adaptativa que aprende la
estacionalidad sin umbrales manuales fijos.

`core.py` usa `sklearn.cluster.Birch`: su *Clustering Feature* por subgrupo es (N, LS, SS), de modo
que los centroides se actualizan a partir de un estadístico acumulado y nunca releyendo el
histórico. Se configura con `ANOMALY_CONFIG`, una entrada por modelo de datos.

## ETL (extraer → transformar → cargar)

`scripts/main.py` + `etl/` + `config/` + `helpers/`: CSV → almacenamiento (S3 o MinIO) → trabajo
`platform.data.importation_job` en la cola de la plataforma. Es la ruta fiable; el POST directo al IoT
Agent pierde datos bajo carga.

- `etl/base_etl.py` — el contrato `BaseETL` (init_etl/extract/transform/load), para que un ETL nuevo
  se enganche igual.
- `etl/crowd/extract.py` — **segregado por `ENABLE_SMARTSPOT`/`ENABLE_LIDAR`**, para que un
  despliegue con Smart Spot solamente funcione sin tocar código. `DATA_SOURCE=synthetic|real`
  (por defecto `real`) elige de dónde vienen AMBAS señales, siempre del mismo lado.
- `etl/crowd/transform.py` — ejecuta `lidar_estimation.estimate_zone_totals()` y exporta un CSV por
  zona (entidad `CrowdFlowZone`).
- `etl/crowd/load.py` y `helpers/uploader.py` — publican los CSV.
- `config/` — abstracción de almacenamiento: `s3_storage.py` (boto3, `STORAGE_TYPE=s3`) y
  `local_storage.py` (MinIO, `STORAGE_TYPE=local`, para instalaciones sin AWS).
- `config/settings.py` — **todas las variables de entorno**, tipadas con `pydantic-settings` y
  agrupadas por dominio. ⚠️ Cada accesor construye una instancia nueva y **nada se cachea, a
  propósito**: `helpers/fiware_targets.py` aísla los destinos mutando temporalmente `os.environ`, y
  un `FIWARE_TENANT` cacheado haría que todos los destinos leyeran el del primero.
- `etl/predict/` — el mismo contrato para `scripts/predict.py`: exporta **un CSV por ZONA**
  (`urn:ngsi-ld:CrowdFlowPrediction:<zone_id>_pred`, identificador estable que se actualiza en cada
  ejecución) con tantas filas como horas de horizonte.

## Ejecución

Una imagen para todos los puntos de entrada, un comando distinto por trabajo:

- `python scripts/run_daily.py` — el ciclo DIARIO: entrena y después predice, por destino. Que falle
  el entrenamiento NO impide la predicción (lee el modelo del almacenamiento, así que el de ayer
  sigue publicando), pero la ejecución termina en rojo para que nadie lea «publicado» como «sano».
  No es horario: el arranque en caliente añade árboles en cada pasada.
- `python scripts/main.py` — fusión LIDAR + Smart Spot.
- `python scripts/train.py` — entrenamiento XGBoost. Sube el modelo y sus dos ficheros hermanos
  (`.columns.json`, las columnas exactas de entrenamiento, y `.metrics.json`) bajo
  `<MODELS_PREFIX>/<FIWARE_TENANT>/<FIWARE_SCOPE>/`, segregado para que dos despliegues sobre el
  mismo bucket no se pisen el modelo.
  **Frío o caliente no se configura: lo decide el estado del almacenamiento**
  (`helpers/warm_start.py`). Sin modelo, entrena el histórico completo con `tune_hyperparameters()`;
  con modelo y sus dos hermanos, arranca en caliente añadiendo `N_ESTIMATORS_INCREMENT` árboles.
  Vuelve a un reentrenamiento completo en nueve casos: las columnas ya no coinciden, el último
  completo es más viejo que `FULL_RETRAIN_AFTER_DAYS`, la meteorología pasó de no configurada a
  configurada (o al revés), cambió el registro de eventos, `CALENDAR_TIMEZONE` difiere del anotado,
  se alcanzó `MAX_ESTIMATORS`, el MAE del último día empeora más de `INCREMENTAL_MAE_TOLERANCE`, el
  fichero hermano no trae hiperparámetros, o `FORCE_FULL_RETRAIN=true`. Y en dos casos no entrena
  nada: sin datos nuevos desde la última ejecución, y con un histórico por debajo del suelo de 7 días.
- `python scripts/predict.py` — predice `PREDICTION_HORIZON_HOURS` (24 por defecto) con el modelo
  que subió `train.py` y publica el resultado como entidades.
- `python scripts/run_ote.py` — compacta e ingesta el archivo crudo del LIDAR que deja
  `fiware-manager`.

`FIWARE_TARGETS=tenant_a:/,tenant_b:/` ejecuta el ciclo completo una vez por pareja tenant/scope
(`helpers/fiware_targets.py`): cada destino tiene su modelo, su directorio de salida y su mensaje de
cola, y un destino que falla no aborta el resto. Un tenant VACÍO se rechaza en vez de aceptarse: la
cola admitiría el trabajo, la plataforma no crearía ninguna entidad y la ejecución parecería correcta.
⚠️ Aplica a `train.py`, `predict.py` y `run_daily.py`; **`main.py` NO itera destinos**.

`predict.py` ancla el inicio de la ventana justo después del último dato REAL disponible, no al
reloj: si el histórico termina unos días antes de «hoy», anclar a «ahora» dejaba `lag_1d`/`lag_1w`
sin encontrar nada y se descartaban todas las predicciones en silencio. Se puede forzar un instante
concreto con `PREDICTION_START`.

**Un horizonte de más de ~24 h exige predicción RECURSIVA** (`prediction_features.predict_recursive()`,
que usa `PredictTransform`): predice hora a hora y realimenta cada predicción como si fuera
histórico real, para poder calcular los retardos de la hora siguiente. Probado de extremo a extremo
hasta 168 h. Cada fila lleva `horizon_step` (`horizonStep` en la entidad exportada): 1 = calculada
sobre datos reales; valores mayores dependen de predicciones propias y acumulan error. Volver a
ejecutar más adelante reemplaza esas horas por una versión con `horizon_step` menor, así que las
predicciones se refinan solas conforme se acerca la fecha.

> ⚠️ **Cuidado al tocar `add_rolling_features()`** (`training_data.py`): filtra los huecos con
> `pd.notna()`, no con `v is not None`. Al mezclar series reales (ocupación `int`) con los huecos
> futuros de `prediction_features.py` (ocupación `None`), pandas convierte la columna a `float64` y
> el `None` pasa a ser `NaN` — y `NaN is not None` es `True`, así que se colaría en
> `statistics.pstdev()` y reventaría en cuanto el horizonte pasara de 24 h.

### Despliegue

La imagen se construye desde este directorio y los dos trabajos periódicos —`run_daily.py` y
`run_ote.py`— se programan como CronJobs de Kubernetes. **El chart de [`../deploy`](../deploy) no
los incluye todavía**: hoy este módulo se construye y se ejecuta aparte del núcleo de la plataforma,
con la que se comunica sólo por sus interfaces públicas (la API de `aether-link` y las entidades del
context broker).

No hay nada que montar en el contenedor: el histórico se lee en vivo de la plataforma, por zona
(`CrowdFlowZone`), así que no hacen falta ni PVC ni contenedor de inicio, y las predicciones no se
degradan porque una exportación envejezca.

## Uso

La biblioteca es el paquete `crowd_predictions` y se INSTALA; `scripts/` sólo tiene los puntos de
entrada. `-e` (editable) para que editar un fichero no obligue a reinstalar, y `[test]` trae pytest;
`pyproject.toml` es la única fuente de dependencias.

```bash
pip install -e ".[test]"

pytest                                          # la suite completa
pytest tests/test_training_data.py -k lag -v    # un fichero o un subconjunto

cp .env.example .env             # y rellenar el almacenamiento y la conexión a la plataforma
python scripts/main.py           # genera predictions_per_zone/*.csv y los publica
python scripts/train.py          # entrena contra el histórico y sube el modelo
python scripts/predict.py        # genera predictions_forecast/*.csv y los publica

# Contenedor: una imagen, un servicio de Compose; lo que cambia es el comando.
docker compose up -d
docker exec -it crowd-predictions python scripts/main.py
docker exec -it crowd-predictions pytest
docker compose down
```

---

## Licencia y titularidad

Este módulo se ha desarrollado **específicamente para el proyecto PID Gijón** y es de
**titularidad del Ayuntamiento de Gijón**. Se distribuye, como el resto del repositorio, bajo la
[EUPL v1.2](../LICENSE). Ver [`NOTICE.md`](../NOTICE.md).
