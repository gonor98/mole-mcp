---
name: mole-mcp
description: Conecta con la Estación IA de Gonzalo vía el servidor MCP mole-mcp. Úsala cuando necesites leer el repo gonor98/estacion-ia (archivos, pipeline.csv, estado de outreach), consultar archivos del workspace local o registrar notas. Requiere GITHUB_TOKEN configurado.
---

# mole-mcp — skill de la Estación IA

El servidor MCP `mole-mcp` expone la Estación IA como herramientas. Antes de
usarlo, verifica que el servidor esté configurado (ver `docs/connect-claude-code.md`).

## Herramientas disponibles

| Herramienta | Para qué sirve |
|---|---|
| `mole_status` | Estado del servidor: versión, repo, si hay token, raíz del workspace |
| `estacion_repo_tree` | Listar archivos/carpetas de estacion-ia (raíz o subdirectorio) |
| `estacion_read_file` | Leer un archivo de estacion-ia (rama main por defecto) |
| `estacion_pipeline_summary` | Totales del pipeline.csv por estado y por canal |
| `estacion_outreach_status` | Resumen ejecutivo del outreach en texto plano |
| `estacion_search_code` | Buscar código en el repo (aviso: la búsqueda de GitHub ha fallado antes para este repo; un vacío no prueba ausencia) |
| `workspace_list_files` | Listar archivos del workspace local (por defecto `~/workspace/goals`) |
| `workspace_read_file` | Leer un archivo del workspace local |
| `workspace_note` | Registrar una nota con fecha en `~/workspace/mole-notes.md` |

## Reglas

- El repo `gonor98/estacion-ia` es **privado**: sin `GITHUB_TOKEN` las
  herramientas de GitHub devuelven un error claro, no datos inventados.
- `workspace_note` es la única escritura local. Nunca escribas en el repo
  desde estas herramientas: son de solo lectura.
- Nunca pidas ni muestres el valor de `GITHUB_TOKEN`, contraseñas, API keys
  ni contenido de `.env`.
- El pipeline vive en `11-Ingresos-Gonzalo/datos/pipeline.csv`. Sus columnas
  reales son: fecha, canal, empresa, contacto, email, puesto_o_servicio,
  pais, pago_estimado, estado, fecha_contacto, respuesta, siguiente_paso,
  fuente, notas.
- Hermes y OpenClaw **no tienen configuración en estacion-ia** (verificado:
  0 resultados). No inventes integraciones con ellos; usa la configuración
  MCP genérica de `docs/connect-hermes-openclaw.md`.
