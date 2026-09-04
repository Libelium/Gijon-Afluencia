# aether-pylib

Librería Python compartida (paquete de import: `aether_pylib`) con los modelos de datos
que intercambian los servicios de la plataforma cuando hablan con el context broker, el IoT
Agent y el almacén de series temporales. Son modelos **Pydantic v2**: definen el contrato de
las peticiones y respuestas para que cada servicio no lo reimplemente por su cuenta.

- `context_broker/` — modelos NGSI-LD / NGSI-v2: alta, modificación y borrado de entidades,
  y suscripciones.
- `iota/` — modelos del IoT Agent: payload de aprovisionamiento y borrado de dispositivos.
- `time_series/` — modelos de series temporales: petición y respuesta de consulta, opciones,
  ámbito temporal (`TimeScope`) y borrado de series.

No es un servicio ejecutable: no tiene Docker ni `.env`. Se consume como dependencia.

## Requisitos

Python >= 3.10: los modelos usan uniones PEP 604 (`str | float | int | bool` en
`time_series/time_series_options.py`), que Pydantic evalúa en tiempo de ejecución y no están
disponibles en 3.9. Dependencias de ejecución: `pydantic`, `pandas`, `isodate`. Para las
pruebas, el grupo `test`: `pytest` y `freezegun`.

## Uso

Se instala como dependencia local (editable) desde el proyecto que la consume. Por ejemplo,
`aether-link` la declara así en su `pyproject.toml`:

```toml
[tool.uv.sources]
aether-pylib = { path = "../pylibs/aether-pylib", editable = true }
```

Al ser editable, cualquier cambio hecho aquí lo recoge el servicio sin reconstruir la imagen.

Instalación manual, si se quiere trabajar sobre la librería aislada:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

**El nombre del paquete de import es `aether_pylib`** y no debe cambiarse: es el que
usan los `import` del resto del código.

```python
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
```

## Pruebas

```bash
pip install pytest
python3 -m pytest tests/
```

## Versionado

La versión está en `pyproject.toml` (`[project] version`). Al publicar un cambio que afecte
al contrato de los modelos, súbela y ajusta el pin en los servicios que la consumen.

---

## Licencia

Desarrollo de Libelium anterior al proyecto PID Gijón, licenciado al Ayuntamiento de Gijón bajo la
[EUPL v1.2](../../LICENSE). La titularidad y las licencias de los componentes de terceros están en
[`NOTICE.md`](../../NOTICE.md).
