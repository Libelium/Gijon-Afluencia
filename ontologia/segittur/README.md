# Ontología de referencia de turismo de SEGITTUR

Copia sin cambios de los ficheros oficiales publicados en
<https://ontologia.segittur.es/turismo/def/core/> (versión 1.2.0, emitida el 2025-08-25).

- `ontology.ttl`: la ontología en Turtle (272 clases, 188 propiedades).
- `kos/skos-*.ttl`: 61 tesauros SKOS con los valores controlados. Dos de los 63 que enlaza la
  ontología (`TravelUnit` y `TourismResourceService`) devolvían 404 en la fuente y no se incluyen.

**Licencia:** © SEGITTUR, Creative Commons Attribution-ShareAlike 4.0 International
(CC BY-SA 4.0). Los datos derivados (`frontend/src/features/ontology/data/segittur.json`) se
distribuyen bajo la misma licencia; ver `NOTICE.md`.

## Regenerar los datos de la vista

La pantalla Ontología lee un JSON generado a partir de estos ficheros (la imagen del frontend no
ve fuera de `frontend/`). Tras actualizar la ontología:

```bash
pip install rdflib
python3 frontend/scripts/segittur-to-json.py
```

La correspondencia entre los PIT de la plataforma y las clases de SEGITTUR está en
`frontend/src/features/ontology/lib/mapping.ts`; sus pruebas comprueban que todas las clases y
propiedades que usa existen en la versión cargada.
