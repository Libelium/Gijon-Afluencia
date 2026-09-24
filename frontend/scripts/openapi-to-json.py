#!/usr/bin/env python3
"""
Convierte las especificaciones OpenAPI de la raiz del repositorio a JSON para la vista «API».

El contexto de construccion de la imagen del frontend es solo `frontend/`, asi que los YAML de la
raiz no llegan al build: se generan aqui copias JSON que viajan con el codigo. Reejecutar tras
tocar `openapi-gestion.yaml` u `openapi-ingesta.yaml`:

    python3 frontend/scripts/openapi-to-json.py
"""
import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "src" / "features" / "api-docs" / "specs"

SPECS = {
    "openapi-gestion.yaml": "gestion.json",
    "openapi-ingesta.yaml": "ingesta.json",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for source, target in SPECS.items():
        with open(ROOT / source, encoding="utf-8") as fh:
            spec = yaml.safe_load(fh)
        with open(OUT / target, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(f"{source} -> {(OUT / target).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
