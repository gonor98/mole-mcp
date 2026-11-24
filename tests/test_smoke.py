"""Smoke test del servidor mole-mcp: arranca el servidor por stdio, lista sus
herramientas y ejerce las que no necesitan token, más la ruta de error clara
de las que sí lo necesitan. También prueba una herramienta de GitHub contra
un repo PÚBLICO (gonor98/opus-magna-write) para verificar el código HTTP
sin token.

Uso:
    .venv/bin/python tests/test_smoke.py
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent.parent / "server" / "mole_mcp_server.py"


async def main() -> int:
    # Notas de prueba en un archivo temporal, para no tocar el real.
    tmp_notes = Path(tempfile.gettempdir()) / "mole-mcp-smoke-notes.md"
    if tmp_notes.exists():
        tmp_notes.unlink()

    env = dict(os.environ)
    env.pop("GITHUB_TOKEN", None)  # prueba sin token, como un usuario nuevo
    env["MOLE_NOTES_FILE"] = str(tmp_notes)

    params = StdioServerParameters(
        command=sys.executable, args=[str(SERVER)], env=env
    )
    failures = []

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Lista de herramientas
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("Herramientas:", json.dumps(names, ensure_ascii=False))
            expected = {
                "mole_status", "estacion_repo_tree", "estacion_read_file",
                "estacion_pipeline_summary", "estacion_outreach_status",
                "estacion_search_code", "workspace_list_files",
                "workspace_read_file", "workspace_note",
            }
            if set(names) != expected:
                failures.append(f"herramientas inesperadas: faltan {expected - set(names)}, sobran {set(names) - expected}")

            # 2. mole_status: token no configurado
            res = await session.call_tool("mole_status", {})
            status = json.loads(res.content[0].text)
            print("mole_status:", json.dumps(status, ensure_ascii=False))
            if status["github_token_configured"] is not False:
                failures.append("mole_status debería decir token no configurado")
            if status["default_repo"] != "gonor98/estacion-ia":
                failures.append("default_repo incorrecto")

            # 3. workspace_list_files sobre el workspace real (solo lectura)
            res = await session.call_tool(
                "workspace_list_files", {"subdir": "", "pattern": "*.md"}
            )
            listing = json.loads(res.content[0].text)
            print(f"workspace_list_files: {len(listing['files'])} archivos .md")
            if not listing["files"]:
                failures.append("workspace_list_files no devolvió archivos")

            # 4. workspace_note escribe y se puede leer de vuelta
            res = await session.call_tool(
                "workspace_note", {"note": "nota de prueba smoke test", "topic": "test"}
            )
            print("workspace_note:", res.content[0].text)
            if "nota de prueba smoke test" not in tmp_notes.read_text(encoding="utf-8"):
                failures.append("workspace_note no escribió la nota")

            # 5. Repo privado sin token -> error claro, no datos inventados
            res = await session.call_tool("estacion_pipeline_summary", {})
            text = res.content[0].text
            print("pipeline sin token:", text[:200])
            if "GITHUB_TOKEN" not in text:
                failures.append("pipeline sin token debería mencionar GITHUB_TOKEN")

            # 6. Repo PÚBLICO sin token -> la ruta HTTP de GitHub funciona.
            # En esta VM la IP compartida puede estar sin cuota anónima (60/h):
            # se acepta el contenido del archivo o un error claro de rate limit.
            res = await session.call_tool(
                "estacion_read_file",
                {"owner": "gonor98", "repo": "opus-magna-write",
                 "path": "package.json", "ref": "main"},
            )
            text = res.content[0].text
            print("read público (primeros 200):", text[:200])
            if "tanstack" not in text.lower() and "name" not in text \
                    and "rate limit" not in text.lower():
                failures.append(
                    "lectura de repo público: ni package.json ni error de rate limit"
                )

    tmp_notes.unlink(missing_ok=True)

    if failures:
        print("\nFALLOS:")
        for failure in failures:
            print(" -", failure)
        return 1
    print("\nSMOKE TEST OK: 6/6 comprobaciones pasaron")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
