# Cómo contribuir

Gracias por trabajar sobre la Plataforma de Integración de Datos del Ayuntamiento de Gijón. Esta
página recoge lo mínimo para que un cambio entre sin fricción.

## Antes de nada: la licencia

El repositorio se distribuye bajo la **Licencia Pública de la Unión Europea (EUPL) v1.2**
([`LICENSE`](LICENSE)). Al enviar una contribución aceptas que se publique bajo esa misma licencia
y que la titularidad corresponde al Ayuntamiento de Gijón, según [`NOTICE.md`](NOTICE.md).

**No introduzcas dependencias con licencia incompatible.** La EUPL es compatible con MIT, BSD,
Apache-2.0, MPL-2.0, LGPL y las licencias listadas en su apéndice. Antes de añadir un paquete,
comprueba su licencia y actualiza el SBOM (más abajo). Las dependencias propietarias o de pago no
tienen cabida: la entrega debe poder reutilizarse por cualquier administración.

## Arrancar un componente

Cada servicio es autónomo y se levanta con Docker Compose desde su propia carpeta. Ninguno
necesita cuenta en un proveedor cloud ni registro privado. `pylibs/aether-pylib` es la excepción:
es una biblioteca, no un servicio, y la ejercitan las pruebas de quienes la consumen.

```sh
cd aether-link
cp app/.env.example app/.env      # y editar
docker compose up
```

Los puertos, la ubicación del fichero de entorno y las particularidades de cada uno están en su
`README.md`. El mapa de componentes está en el [`README.md`](README.md) de la raíz.

## Pruebas

Se ejecutan dentro del contenedor, así nadie depende de lo que tenga instalado en su máquina:

| Componente | Comando |
| --- | --- |
| `aether-link` | `docker compose run --rm --no-deps aether-link pytest ./app/tests/ -q` |
| `fiware-manager` | `docker compose run --rm --no-deps fiware-manager pytest ./app/tests/ -q` |
| `queues-consumer` | `docker compose run --rm --no-deps queues-consumer pytest ./app/tests/ -q` |
| `predictions` | `docker compose run --rm crowd pytest -q` (el servicio de Compose se llama `crowd`) |
| `backend` | `docker compose exec backend vendor/bin/phpunit` |
| `frontend` | `npm run typecheck && npm run build` |

Un cambio no se da por terminado hasta que la batería del componente que tocas pasa entera.

## Dependencias y reproducibilidad

Los proyectos Python usan `uv` y **todos llevan `uv.lock` versionado**. Si añades o subes una
dependencia:

```sh
# desde la carpeta del componente
docker compose run --rm --no-deps <servicio> uv lock
```

Las imágenes se construyen con `uv sync --locked`, de modo que **la construcción falla si el
`uv.lock` no concuerda con el `pyproject.toml`**. Es deliberado: sin eso, la cadena transitiva
cambia sin que nadie se entere y deja de poder auditarse.

En `backend` el equivalente es `composer.lock` y en `frontend`, `package-lock.json`; ambos van
versionados. Al añadir una dependencia al frontend, regenera además su inventario con
`npm run licenses` y comprueba que la licencia nueva es compatible: la EUPL no admite copyleft
fuerte incompatible, y hoy sus 123 paquetes instalados —105 en el árbol de producción— son todos
permisivos.

## Documentación que hay que mantener viva

Un cambio que altere cualquiera de estas cosas debe actualizarlas en el mismo commit:

- **[`CHANGELOG.md`](CHANGELOG.md)** — toda modificación reseñable, bajo la versión en curso.
- **[`openapi-gestion.yaml`](openapi-gestion.yaml)** — si tocas `backend/src/routes/api.php`.
- **[`openapi-ingesta.yaml`](openapi-ingesta.yaml)** — si tocas `fiware-manager/app/api/v1/routes/`.
- **[`postman/`](postman)** — se derivan de los dos OpenAPI anteriores.
- **[`sbom.json`](sbom.json)** — si añades, quitas o subes una dependencia de terceros.
- **[`NOTICE.md`](NOTICE.md)** — si entra o sale un componente de terceros desplegado.
- El `README.md` del componente, si cambia cómo se arranca, se configura o se prueba.

## Estilo

No hay linter ni formateador configurado en ningún componente. La norma es **seguir el estilo del
código de alrededor**: si un fichero usa una convención, respétala aunque no coincida con tu
preferencia. Los comentarios explican *por qué*, no *qué*: si el código no se entiende solo,
reescríbelo antes de comentarlo.

La documentación se escribe **en castellano**. Los nombres de identificadores, variables y rutas de
la API se dejan como están.

## Git

- Rama por cambio, partiendo de `main`.
- Mensajes de commit en imperativo y en castellano, con un prefijo de tipo:
  `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Un commit debe dejar el repositorio en un estado que arranque y pase las pruebas. Si el cambio es
  grande, divídelo en commits que cumplan eso por separado.
- No se versionan artefactos de construcción (`node_modules/`, `.venv/`, `vendor/`, `dist/`,
  cachés) ni ficheros `.env` con credenciales. Los `.gitignore` de cada componente ya lo cubren.

## Seguridad

Si encuentras una vulnerabilidad, **no abras una incidencia pública**. El procedimiento de aviso
está en [`SECURITY.md`](SECURITY.md). El tratamiento de secretos de un despliegue es otra cosa y
está en [`deploy/SECURITY.md`](deploy/SECURITY.md).
