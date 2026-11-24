#!/usr/bin/env python3
"""mole-mcp — servidor MCP que conecta Muse con la Estación IA de Gonzalo.

Expone herramientas reales y verificables sobre:
- El repo privado gonor98/estacion-ia (vía API de GitHub): árbol de archivos,
  lectura de archivos, resumen de pipeline.csv, estado de outreach y búsqueda
  de código. Requiere GITHUB_TOKEN (fine-grained PAT, solo lectura, repo
  estacion-ia). Los repos públicos también funcionan sin token.
- El workspace local (solo lectura, salvo notas): listar/leer archivos bajo
  MOLE_WORKSPACE_ROOT y registrar notas en MOLE_NOTES_FILE.

Sin secretos en el código: el token solo se lee de la variable de entorno
GITHUB_TOKEN y nunca se imprime ni se guarda.

Uso (stdio, por defecto):
    python3 server/mole_mcp_server.py

Uso (HTTP, para clientes que no soportan stdio, p. ej. el puente de AI World):
    python3 server/mole_mcp_server.py --transport streamable-http --port 8765
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

__version__ = "0.1.0"

DEFAULT_OWNER = "gonor98"
DEFAULT_REPO = "estacion-ia"
DEFAULT_REF = "main"
DEFAULT_PIPELINE = "11-Ingresos-Gonzalo/datos/pipeline.csv"
GITHUB_API = "https://api.github.com"
MAX_FILE_CHARS = 200_000

mcp = FastMCP("mole-mcp")


# ---------------------------------------------------------------------------
# Utilidades de GitHub
# ---------------------------------------------------------------------------

def _gh_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"mole-mcp/{__version__}",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _gh_get(url: str):
    """GET a la API de GitHub. Devuelve el JSON decodificado o lanza RuntimeError."""
    req = urllib.request.Request(url, headers=_gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        if "rate limit exceeded" in body.lower():
            raise RuntimeError(
                "GitHub devolvió 403 por límite de peticiones (rate limit) para "
                "esta IP sin autenticar. Configura GITHUB_TOKEN para subir el "
                "límite a 5.000 peticiones/hora. Detalle: " + body
            ) from exc
        if exc.code == 404:
            raise RuntimeError(
                "GitHub devolvió 404. Si el repo es privado (estacion-ia lo es), "
                "configura GITHUB_TOKEN con un fine-grained PAT de solo lectura "
                "para ese repo. Detalle: " + body
            ) from exc
        if exc.code in (401, 403):
            raise RuntimeError(
                "GitHub rechazó la autenticación (401/403). Revisa GITHUB_TOKEN: "
                "debe ser un fine-grained PAT con permiso Contents: Read sobre "
                "gonor98/estacion-ia. Detalle: " + body
            ) from exc
        raise RuntimeError(f"GitHub API {exc.code} en {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No se pudo contactar api.github.com: {exc}") from exc


def _gh_file_text(owner: str, repo: str, path: str, ref: str) -> str:
    """Lee un archivo del repo vía Contents API y devuelve su texto."""
    url = (
        f"{GITHUB_API}/repos/{owner}/{repo}/contents/"
        f"{urllib.parse.quote(path)}?ref={urllib.parse.quote(ref)}"
    )
    data = _gh_get(url)
    if isinstance(data, list):
        raise RuntimeError(f"'{path}' es un directorio, no un archivo.")
    if data.get("encoding") != "base64" or "content" not in data:
        raise RuntimeError(f"La API no devolvió contenido base64 para '{path}'.")
    raw = base64.b64decode(data["content"]).decode("utf-8", "replace")
    if len(raw) > MAX_FILE_CHARS:
        return raw[:MAX_FILE_CHARS] + f"\n\n[... truncado: archivo de {len(raw)} caracteres ...]"
    return raw


def _pipeline_rows(ref: str, pipeline_path: str, owner: str, repo: str) -> list[dict]:
    text = _gh_file_text(owner, repo, pipeline_path, ref)
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise RuntimeError(f"'{pipeline_path}' no tiene encabezado CSV.")
    return [row for row in reader if any((v or "").strip() for v in row.values())]


def _count(rows: list[dict], field: str) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        key = (row.get(field) or "").strip() or "(vacío)"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


# ---------------------------------------------------------------------------
# Utilidades del workspace local
# ---------------------------------------------------------------------------

def _workspace_root() -> Path:
    root = Path(os.environ.get("MOLE_WORKSPACE_ROOT", "~/workspace/goals")).expanduser()
    return root.resolve()


def _safe_join(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    if target != root and root not in target.parents:
        raise RuntimeError(f"Ruta fuera del workspace permitido: {rel!r}")
    return target


# ---------------------------------------------------------------------------
# Herramientas MCP — estado del servidor
# ---------------------------------------------------------------------------

@mcp.tool()
def mole_status() -> str:
    """Estado del servidor mole-mcp: versión, repo por defecto, token configurado
    (solo sí/no, nunca el valor) y raíz del workspace local."""
    return json.dumps(
        {
            "server": "mole-mcp",
            "version": __version__,
            "default_repo": f"{DEFAULT_OWNER}/{DEFAULT_REPO}",
            "default_ref": DEFAULT_REF,
            "default_pipeline": DEFAULT_PIPELINE,
            "github_token_configured": bool(os.environ.get("GITHUB_TOKEN", "").strip()),
            "workspace_root": str(_workspace_root()),
            "notes_file": os.environ.get(
                "MOLE_NOTES_FILE", str(Path.home() / "workspace" / "mole-notes.md")
            ),
        },
        indent=2,
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Herramientas MCP — repo estacion-ia (GitHub)
# ---------------------------------------------------------------------------

@mcp.tool()
def estacion_repo_tree(path: str = "", ref: str = DEFAULT_REF,
                       owner: str = DEFAULT_OWNER, repo: str = DEFAULT_REPO) -> str:
    """Lista archivos y carpetas de un directorio del repo (por defecto la raíz
    de gonor98/estacion-ia en main). Devuelve nombre, tipo, tamaño y ruta."""
    url = (
        f"{GITHUB_API}/repos/{owner}/{repo}/contents/"
        f"{urllib.parse.quote(path)}?ref={urllib.parse.quote(ref)}"
    )
    data = _gh_get(url)
    if isinstance(data, dict):  # un archivo, no un directorio
        data = [data]
    entries = [
        {
            "name": item.get("name"),
            "type": item.get("type"),
            "size": item.get("size"),
            "path": item.get("path"),
        }
        for item in data
    ]
    return json.dumps(
        {"owner": owner, "repo": repo, "ref": ref, "path": path or "/",
         "entries": entries},
        indent=2, ensure_ascii=False,
    )


@mcp.tool()
def estacion_read_file(path: str, ref: str = DEFAULT_REF,
                       owner: str = DEFAULT_OWNER, repo: str = DEFAULT_REPO) -> str:
    """Lee el contenido de un archivo del repo (por defecto gonor98/estacion-ia,
    rama main). Archivos de más de 200.000 caracteres se truncan."""
    return _gh_file_text(owner, repo, path, ref)


@mcp.tool()
def estacion_pipeline_summary(ref: str = DEFAULT_REF,
                              pipeline_path: str = DEFAULT_PIPELINE,
                              owner: str = DEFAULT_OWNER,
                              repo: str = DEFAULT_REPO) -> str:
    """Resumen del pipeline de oportunidades (pipeline.csv): total de filas y
    conteos por estado y por canal. Columnas reales: fecha, canal, empresa,
    contacto, email, puesto_o_servicio, pais, pago_estimado, estado,
    fecha_contacto, respuesta, siguiente_paso, fuente, notas."""
    rows = _pipeline_rows(ref, pipeline_path, owner, repo)
    con_respuesta = sum(1 for r in rows if (r.get("respuesta") or "").strip())
    cerrados = sum(
        1 for r in rows
        if (r.get("estado") or "").strip().lower() in ("cerrado", "ganado", "oferta")
    )
    return json.dumps(
        {
            "repo": f"{owner}/{repo}",
            "ref": ref,
            "pipeline_path": pipeline_path,
            "total_filas": len(rows),
            "por_estado": _count(rows, "estado"),
            "por_canal": _count(rows, "canal"),
            "con_respuesta": con_respuesta,
            "cerrados_oferta_o_ganado": cerrados,
        },
        indent=2, ensure_ascii=False,
    )


@mcp.tool()
def estacion_outreach_status(ref: str = DEFAULT_REF) -> str:
    """Estado del outreach en una frase por métrica: cuántas oportunidades hay,
    cuántas por estado y canal, cuántas tienen respuesta y cuántas cerradas.
    Es el resumen ejecutivo de estacion_pipeline_summary."""
    rows = _pipeline_rows(ref, DEFAULT_PIPELINE, DEFAULT_OWNER, DEFAULT_REPO)
    por_estado = _count(rows, "estado")
    por_canal = _count(rows, "canal")
    con_respuesta = sum(1 for r in rows if (r.get("respuesta") or "").strip())
    enviados = por_estado.get("enviado", 0)
    lines = [
        f"Pipeline estacion-ia ({DEFAULT_PIPELINE}, ref {ref}): {len(rows)} oportunidades.",
        f"Por estado: {', '.join(f'{k} {v}' for k, v in por_estado.items())}.",
        f"Por canal: {', '.join(f'{k} {v}' for k, v in por_canal.items())}.",
        f"Enviados: {enviados}. Con respuesta registrada: {con_respuesta}.",
    ]
    return "\n".join(lines)


@mcp.tool()
def estacion_search_code(query: str, owner: str = DEFAULT_OWNER,
                         repo: str = DEFAULT_REPO) -> str:
    """Busca código en el repo con la API de búsqueda de GitHub.
    AVISO: la búsqueda de código de GitHub ha devuelto 0 resultados con
    incomplete_results=true para estacion-ia en el pasado; un resultado vacío
    NO prueba que el texto no exista en el repo."""
    url = (
        f"{GITHUB_API}/search/code?q="
        f"{urllib.parse.quote(query + f' repo:{owner}/{repo}')}"
    )
    data = _gh_get(url)
    items = [
        {"path": it.get("path"), "url": it.get("html_url")}
        for it in data.get("items", [])
    ]
    return json.dumps(
        {
            "query": query,
            "total_count": data.get("total_count"),
            "incomplete_results": data.get("incomplete_results"),
            "items": items,
        },
        indent=2, ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Herramientas MCP — workspace local
# ---------------------------------------------------------------------------

@mcp.tool()
def workspace_list_files(subdir: str = "", pattern: str = "*.md") -> str:
    """Lista archivos del workspace local bajo MOLE_WORKSPACE_ROOT
    (por defecto ~/workspace/goals) que coincidan con el patrón glob."""
    root = _workspace_root()
    base = _safe_join(root, subdir) if subdir else root
    if not base.is_dir():
        raise RuntimeError(f"No existe el directorio: {subdir or '.'}")
    files = sorted(
        str(p.relative_to(root)) for p in base.rglob(pattern) if p.is_file()
    )
    return json.dumps(
        {"workspace_root": str(root), "subdir": subdir or ".",
         "pattern": pattern, "files": files},
        indent=2, ensure_ascii=False,
    )


@mcp.tool()
def workspace_read_file(path: str) -> str:
    """Lee un archivo de texto del workspace local (bajo MOLE_WORKSPACE_ROOT).
    No permite salir de esa raíz. Máximo 200.000 caracteres."""
    root = _workspace_root()
    target = _safe_join(root, path)
    if not target.is_file():
        raise RuntimeError(f"No existe el archivo: {path!r}")
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_FILE_CHARS:
        return text[:MAX_FILE_CHARS] + f"\n\n[... truncado: archivo de {len(text)} caracteres ...]"
    return text


@mcp.tool()
def workspace_note(note: str, topic: str = "general") -> str:
    """Registra una nota con fecha y hora en el archivo de notas
    (MOLE_NOTES_FILE, por defecto ~/workspace/mole-notes.md). Es la única
    herramienta de escritura local; no modifica ningún otro archivo."""
    notes_file = Path(
        os.environ.get("MOLE_NOTES_FILE", str(Path.home() / "workspace" / "mole-notes.md"))
    ).expanduser()
    notes_file.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"- {stamp} [{topic}] {note.strip()}\n"
    with notes_file.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return f"Nota registrada en {notes_file}."


# ---------------------------------------------------------------------------
# Arranque
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="mole-mcp — servidor MCP de la Estación IA")
    parser.add_argument(
        "--transport", default="stdio",
        choices=["stdio", "streamable-http", "sse"],
        help="Transporte MCP (por defecto: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host para transporte HTTP/SSE")
    parser.add_argument("--port", type=int, default=8765, help="Puerto para transporte HTTP/SSE")
    args = parser.parse_args()

    if args.transport != "stdio":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
    print(f"mole-mcp {__version__} iniciando (transporte: {args.transport})",
          file=sys.stderr)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
