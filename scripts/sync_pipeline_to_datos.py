#!/usr/bin/env python3
"""Sincroniza el resumen del pipeline de estacion-ia a un JSON que el panel
AI World (Cerebro-IA/mundo-ia.html) puede cargar.

El panel es una página estática: no puede hablar MCP por sí mismo. Este
script es el puente: lee pipeline.csv vía la API de GitHub (mismo token que
el servidor MCP) y escribe un JSON pequeño con totales por estado y canal.

Uso:
    GITHUB_TOKEN=... python3 scripts/sync_pipeline_to_datos.py \
        --out Cerebro-IA/publico/datos-pipeline.json

El archivo resultante se puede cargar desde mundo-ia.html con fetch() o
copiarse a la carpeta que sirve el panel en producción.
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OWNER = "gonor98"
REPO = "estacion-ia"
REF = "main"
PIPELINE_PATH = "11-Ingresos-Gonzalo/datos/pipeline.csv"


def fetch_pipeline_text(token: str) -> str:
    url = (
        f"https://api.github.com/repos/{OWNER}/{REPO}/contents/"
        f"{urllib.parse.quote(PIPELINE_PATH)}?ref={REF}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "mole-mcp-sync/0.1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"GitHub API {exc.code}: estacion-ia es privado; configura "
            "GITHUB_TOKEN con un fine-grained PAT de solo lectura."
        ) from exc
    return base64.b64decode(data["content"]).decode("utf-8", "replace")


def summarize(text: str) -> dict:
    rows = [r for r in csv.DictReader(io.StringIO(text))
            if any((v or "").strip() for v in r.values())]

    def count(field: str) -> dict:
        out: dict[str, int] = {}
        for row in rows:
            key = (row.get(field) or "").strip() or "(vacío)"
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    return {
        "fuente": f"{OWNER}/{REPO}@{REF}:{PIPELINE_PATH}",
        "total_filas": len(rows),
        "por_estado": count("estado"),
        "por_canal": count("canal"),
        "con_respuesta": sum(1 for r in rows if (r.get("respuesta") or "").strip()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza pipeline.csv a JSON para AI World")
    parser.add_argument("--out", required=True, help="Ruta del JSON de salida")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    summary = summarize(fetch_pipeline_text(token))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK: {summary['total_filas']} filas -> {out}")


if __name__ == "__main__":
    main()
