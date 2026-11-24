# Reporte de prueba — mole-mcp 0.1.0

Fecha: 2026-11-24. Entorno: Python 3.12.3, paquete `mcp` 1.30.0
(`mcp>=1.12,<2`), VM Linux sin token de GitHub configurado.

## 1. Smoke test stdio — OK 6/6

Comando: `.venv/bin/python tests/test_smoke.py`

- Lista de herramientas: las 9 esperadas
  (`mole_status`, `estacion_repo_tree`, `estacion_read_file`,
  `estacion_pipeline_summary`, `estacion_outreach_status`,
  `estacion_search_code`, `workspace_list_files`, `workspace_read_file`,
  `workspace_note`).
- `mole_status`: repo por defecto `gonor98/estacion-ia`, token no
  configurado (correcto), workspace `/home/hatch/workspace/goals`.
- `workspace_list_files`: 74 archivos `.md` listados.
- `workspace_note`: nota escrita y verificada en el archivo temporal.
- `estacion_pipeline_summary` sin token: error claro (ver §3), sin datos
  inventados.
- `estacion_read_file` contra repo público `gonor98/opus-magna-write`:
  ruta HTTP verificada (ver §3).

Resultado: `SMOKE TEST OK: 6/6 comprobaciones pasaron`.

## 2. Transporte streamable-http — OK

Servidor arrancado con `--transport streamable-http --port 8765`.
Cliente MCP (`streamablehttp_client`) hizo initialize, listó las 9
herramientas y llamó `mole_status` correctamente.

Nota: en esta VM el cliente HTTP necesita las variables de proxy
desactivadas para `127.0.0.1` (ya está en `NO_PROXY`); en el ThinkPad de
Gonzalo no aplica.

## 3. Límite de peticiones anónimas de GitHub (hallazgo)

Sin token, la API de GitHub devuelve **403 rate limit exceeded** para la
IP compartida de esta VM (cuota anónima 60/h agotada). El servidor
distingue este caso del error de autenticación y responde:

> GitHub devolvió 403 por límite de peticiones (rate limit) para esta IP
> sin autenticar. Configura GITHUB_TOKEN para subir el límite a 5.000
> peticiones/hora.

Con `GITHUB_TOKEN` (fine-grained PAT, Contents: Read, solo
`gonor98/estacion-ia`) el límite sube a 5.000/h y el repo privado es
accesible. **Sin token no se puede probar el pipeline real desde esta VM.**

## 4. Pendiente de verificar con token

- `estacion_pipeline_summary` y `estacion_outreach_status` contra el
  `pipeline.csv` real (128 filas esperadas).
- `estacion_repo_tree` y `estacion_read_file` contra `estacion-ia`.
- `scripts/sync_pipeline_to_datos.py` de extremo a extremo.

## 5. Publicación en GitHub — BLOQUEADA

`create_repository` vía el conector de GitHub falla con:

> `403 Resource not accessible by integration` en `POST /user/repos`

El token de la GitHub App de Muse no tiene permiso para crear
repositorios en la cuenta. El repo `gonor98/mole-mcp` **no existe aún**.
Para publicar: crear el repo vacío en github.com (público, sin README
ni licencia) y luego subir con `github push-files` (ver `README.md`).
Todo el código está listo y probado en `~/workspace/mole-mcp/`.
