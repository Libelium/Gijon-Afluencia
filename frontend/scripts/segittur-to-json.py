#!/usr/bin/env python3
"""
Genera los datos de la vista de ontologia a partir de los ficheros oficiales de SEGITTUR.

Entrada : ontologia/segittur/ontology.ttl y ontologia/segittur/kos/skos-*.ttl (raiz del repo).
Salida  : frontend/src/features/ontology/data/segittur.json

La imagen del frontend se construye solo con `frontend/` como contexto, asi que la vista no
puede leer los TTL en tiempo de compilacion: se versiona el JSON generado. Hay que volver a
ejecutar este script cuando SEGITTUR publique una version nueva de la ontologia.

Requiere rdflib (`pip install rdflib`). Uso, desde la raiz del repositorio:
    python3 frontend/scripts/segittur-to-json.py
"""
from __future__ import annotations

import json
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DC, DCTERMS, OWL, RDF, RDFS, SKOS, XSD

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ontologia" / "segittur"
OUT = ROOT / "frontend" / "src" / "features" / "ontology" / "data" / "segittur.json"

NS = "https://ontologia.segittur.es/turismo/def/core#"


def local(uri) -> str:
    s = str(uri)
    return s[len(NS):] if s.startswith(NS) else s.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def text(g: Graph, s, p, lang: str) -> str:
    """Literal en el idioma pedido; si no hay, el primero sin idioma."""
    fallback = ""
    for o in g.objects(s, p):
        if isinstance(o, Literal):
            if o.language == lang:
                return str(o).strip()
            if not o.language and not fallback:
                fallback = str(o).strip()
    return fallback


def classes_of(g: Graph, node) -> list[str]:
    """Dominio o rango: una clase, o la union de varias (owl:unionOf sobre un nodo en blanco)."""
    if isinstance(node, URIRef):
        return [local(node)] if str(node).startswith(NS) else [local(node)]
    if isinstance(node, BNode):
        union = g.value(node, OWL.unionOf)
        if union is not None:
            return [c for item in Collection(g, union) for c in classes_of(g, item)]
    return []


def main() -> None:
    g = Graph()
    g.parse(SRC / "ontology.ttl", format="turtle")
    onto = URIRef(NS)

    classes = {}
    for s in g.subjects(RDF.type, OWL.Class):
        if not (isinstance(s, URIRef) and str(s).startswith(NS)):
            continue
        name = local(s)
        classes[name] = {
            "id": name,
            "uri": str(s),
            "label": text(g, s, RDFS.label, "es") or name,
            "labelEn": text(g, s, RDFS.label, "en"),
            "comment": text(g, s, RDFS.comment, "es"),
            "parents": sorted(
                local(o) for o in g.objects(s, RDFS.subClassOf)
                if isinstance(o, URIRef) and str(o).startswith(NS)
            ),
            "properties": [],
        }

    properties = []
    for kind, rdf_type in (("datatype", OWL.DatatypeProperty), ("object", OWL.ObjectProperty)):
        for s in g.subjects(RDF.type, rdf_type):
            if not (isinstance(s, URIRef) and str(s).startswith(NS)):
                continue
            domain = [c for d in g.objects(s, RDFS.domain) for c in classes_of(g, d)]
            rng = [c for r in g.objects(s, RDFS.range) for c in classes_of(g, r)]
            prop = {
                "id": local(s),
                "uri": str(s),
                "kind": kind,
                "label": text(g, s, RDFS.label, "es") or local(s),
                "comment": text(g, s, RDFS.comment, "es"),
                "domain": sorted(set(domain)),
                "range": sorted(set(rng)),
            }
            properties.append(prop)
            for c in prop["domain"]:
                if c in classes:
                    classes[c]["properties"].append(prop["id"])

    for c in classes.values():
        c["properties"].sort()

    schemes = []
    for path in sorted((SRC / "kos").glob("skos-*.ttl")):
        k = Graph()
        k.parse(path, format="turtle")
        for scheme in k.subjects(RDF.type, SKOS.ConceptScheme):
            label = (text(k, scheme, SKOS.prefLabel, "es") or text(k, scheme, RDFS.label, "es")
                     or path.stem.replace("skos-", ""))
            concepts = sorted(
                (
                    {
                        "uri": str(c),
                        "label": text(k, c, SKOS.prefLabel, "es") or local(c),
                    }
                    for c in k.subjects(RDF.type, SKOS.Concept)
                ),
                key=lambda c: c["label"].lower(),
            )
            schemes.append({
                "id": path.stem.replace("skos-", ""),
                "uri": str(scheme),
                "label": label,
                "concepts": concepts,
            })
    schemes.sort(key=lambda s: s["label"].lower())

    data = {
        "meta": {
            "title": text(g, onto, DCTERMS.title, "es") or text(g, onto, RDFS.label, "es")
                     or "Ontología de turismo de SEGITTUR",
            "description": text(g, onto, DCTERMS.description, "es"),
            "version": str(g.value(onto, OWL.versionInfo) or "")
                       or local(g.value(onto, OWL.versionIRI) or ""),
            "versionIri": str(g.value(onto, OWL.versionIRI) or ""),
            "issued": str(g.value(onto, DCTERMS.issued) or g.value(onto, DCTERMS.modified) or ""),
            "rights": text(g, onto, DC.rights, "es") or str(g.value(onto, DC.rights) or ""),
            "namespace": NS,
            "source": "https://ontologia.segittur.es/turismo/def/core/",
        },
        "classes": sorted(classes.values(), key=lambda c: c["label"].lower()),
        "properties": sorted(properties, key=lambda p: p["label"].lower()),
        "schemes": schemes,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(classes)} clases, {len(properties)} propiedades, "
          f"{len(schemes)} tesauros, {sum(len(s['concepts']) for s in schemes)} conceptos")


if __name__ == "__main__":
    main()
