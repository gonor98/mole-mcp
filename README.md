# mole-mcp

Servidor [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) que
conecta **Muse** con el ecosistema de Gonzalo Acuña Nava: su **Estación IA**
(repo `gonor98/estacion-ia`), su workspace de trabajo y su panel **AI World**.

Lo que hace, en una frase: cualquier cliente MCP (Claude Code, Claude
Desktop, OpenClaw, un host de Hermes) puede preguntar por el pipeline de
oportunidades, leer archivos de la Estación IA y registrar notas, sin
contraseñas ni accesos raros.

## Herramientas que expone

| Herramienta | Qué hace |
|---|---|
| `mole_status` | Estado del servidor: versión, repo, si hay token, workspace |
| `estacion_repo_tree` | Lista archivos/carpetas de `estacion-ia` (o cualquier repo) |
| `estacion_read_file` | Lee un archivo del repo (rama `main` por defecto) |
| `estacion_pipeline_summary` | Totales de `pipeline.csv` por estado y por canal |
| `estacion_outreach_status` | Resumen ejecutivo del outreach en texto plano |
| `estacion_search_code` | Busca código en el repo (ver aviso abajo) |
| `workspace_list_files` | Lista archivos del workspace local |
| `workspace_read_file` | Lee un archivo del workspace local |
| `workspace_note` | Registra una nota con fecha (única escritura local) |

El pipeline vive en `11-Ingresos-Gonzalo/datos/pipeline.csv`. Sus columnas
reales son: fecha, canal, empresa, contacto, email, puesto_o_servicio,
pais, pago_estimado, estado, fecha_contacto, respuesta, siguiente_paso,
fuente, notas.

## Instalación

```bash
git clone https://github.com/gonor98/mole-mcp.git
cd mole-mcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Requisitos: Python 3.10+ y el paquete `mcp` 1.x (`mcp>=1.12,<2`).

## Configuración

El repo `gonor98/estacion-ia` es **privado**. Las herramientas de GitHub
necesitan un token; sin él devuelven un error claro, no datos inventados.

1. Crea un fine-grained PAT en
   https://github.com/settings/personal-access-tokens/new
   - Repositorio: solo `gonor98/estacion-ia`
   - Permiso: **Contents: Read** (solo lectura)
   - Expiración: 90 días
2. Expórtalo como variable de entorno (nunca lo subas al repo ni lo pegues
   en el chat):

```bash
export GITHUB_TOKEN=<tu-fine-grained-pat>
```

Opcionales:

```bash
export MOLE_WORKSPACE_ROOT=~/workspace/goals   # raíz de lectura local
export MOLE_NOTES_FILE=~/workspace/mole-notes.md  # archivo de notas
```

## Uso

Stdio (por defecto, lo que usan Claude Code, Claude Desktop y OpenClaw):

```bash
python3 server/mole_mcp_server.py
```

HTTP (para puentes como el de AI World, ver `docs/connect-ai-world.md`):

```bash
python3 server/mole_mcp_server.py --transport streamable-http --port 8765
```

## Conectar clientes

- **Claude Code** (ThinkPad de Gonzalo): `docs/connect-claude-code.md`
  (comando `claude mcp add`, `.mcp.json` o el plugin incluido).
- **AI World (Cerebro-IA)**: `docs/connect-ai-world.md` (puente por JSON
  con `scripts/sync_pipeline_to_datos.py`, y modo HTTP experimental).
- **Hermes / OpenClaw**: `docs/connect-hermes-openclaw.md` (configuración
  MCP genérica por protocolo).

El repo incluye además un manifiesto de plugin para Claude Code
(`.claude-plugin/plugin.json`) y una skill (`skills/mole-mcp/SKILL.md`).

## Probarlo

```bash
.venv/bin/python tests/test_smoke.py
```

El test arranca el servidor por stdio, lista las 9 herramientas, ejerce
las locales, comprueba que el repo privado sin token da un error claro y
verifica la ruta HTTP de GitHub contra un repo público. Resultado esperado:
`SMOKE TEST OK: 6/6 comprobaciones pasaron`.

## Seguridad

- **Nunca** hay secretos en este repo: ni tokens, ni contraseñas, ni API
  keys, ni archivos `.env` (ver `.gitignore` y `.env.example`).
- El token solo se lee de la variable de entorno `GITHUB_TOKEN` y nunca se
  imprime ni se guarda.
- Las herramientas de GitHub son de **solo lectura**: ningún cliente puede
  escribir en `estacion-ia` a través de este servidor.
- La única escritura es `workspace_note`, que solo añade líneas al archivo
  de notas local. Las lecturas locales no pueden salir de
  `MOLE_WORKSPACE_ROOT`.

## Avisos honestos

- La búsqueda de código de GitHub (`estacion_search_code`) ha devuelto 0
  resultados con `incomplete_results=true` para `estacion-ia` en el pasado.
  Un resultado vacío **no prueba** que el texto no exista en el repo.
- En `estacion-ia` **no existe configuración de Hermes ni de OpenClaw**
  (verificado: 0 resultados). Las instrucciones de conexión para esos
  agentes son la configuración MCP estándar, no una integración probada.
- AI World es una página estática (`mundo-ia.html`): no habla MCP. La
  conexión real es el script de sincronización a JSON.

## Licencia

MIT. Hecho por Mole (Muse) para Gonzalo Acuña Nava.
