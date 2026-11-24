# Conectar mole-mcp a Claude Code

Claude Code es un cliente MCP: puede lanzar este servidor por stdio y usar
sus herramientas en cada sesión. Hay dos rutas: comando `claude mcp add`
(la más rápida) o el plugin incluido en este repo.

## 0. Requisitos previos

- Python 3.10+ en la máquina donde corre Claude Code (el ThinkPad de Gonzalo).
- Clonar este repo en el ThinkPad, por ejemplo en `C:\Users\jdavi\mole-mcp`
  (o donde prefieras; ajusta las rutas de abajo).
- Instalar la dependencia: `pip install -r requirements.txt`
  (o `python -m venv .venv` y luego instalar dentro del venv).
- **Token de GitHub (obligatorio para estacion-ia, que es privado):**
  1. Ve a https://github.com/settings/personal-access-tokens/new
  2. Tipo: **Fine-grained personal access token**.
  3. Repositorio: solo `gonor98/estacion-ia`.
  4. Permisos: **Contents: Read** (solo lectura). Nada más.
  5. Expiración: 90 días (renuébalo cuando caduque).
  6. Guárdalo como variable de entorno `GITHUB_TOKEN` en tu sesión.
     Nunca lo pegues en el chat, en un archivo del repo ni en un `.env`
     que se suba a GitHub.

## 1. Ruta rápida: `claude mcp add`

Desde una terminal en el ThinkPad, con el repo clonado:

```bash
claude mcp add mole-mcp -- python3 C:\Users\jdavi\mole-mcp\server\mole_mcp_server.py \
  -e GITHUB_TOKEN=%GITHUB_TOKEN% \
  -e MOLE_WORKSPACE_ROOT=%USERPROFILE%\workspace\goals
```

En macOS/Linux la misma idea con rutas Unix:

```bash
claude mcp add mole-mcp -- python3 ~/mole-mcp/server/mole_mcp_server.py \
  -e GITHUB_TOKEN=$GITHUB_TOKEN
```

Verifica dentro de Claude Code con `/mcp`: debe aparecer `mole-mcp` con
sus 9 herramientas. Prueba con: *"usa mole_status y dime si el token está
configurado"*.

## 2. Ruta por proyecto: `.mcp.json`

Crea `.mcp.json` en la raíz del proyecto donde trabajes (por ejemplo en
`estacion-ia/.mcp.json` — ojo: ese archivo vive en tu copia local; no lo
subas al repo si contiene rutas de tu máquina):

```json
{
  "mcpServers": {
    "mole-mcp": {
      "command": "python3",
      "args": ["C:/Users/jdavi/mole-mcp/server/mole_mcp_server.py"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "MOLE_WORKSPACE_ROOT": "C:/Users/jdavi/workspace/goals"
      }
    }
  }
}
```

Claude Code lo detecta al abrir ese proyecto.

## 3. Ruta plugin (incluye la skill)

Este repo trae un manifiesto de plugin (`.claude-plugin/plugin.json`) y una
skill (`skills/mole-mcp/SKILL.md`) que documenta las herramientas y sus reglas.

```bash
# Copia el repo como plugin local de Claude Code:
cp -r mole-mcp ~/.claude/plugins/mole-mcp
```

Luego en Claude Code: `/plugin` y activa `mole-mcp`. La skill queda
disponible para que Claude sepa qué herramientas existen y con qué reglas
(p. ej. que el pipeline vive en `11-Ingresos-Gonzalo/datos/pipeline.csv`).

## 4. Qué puede hacer Claude Code con él

- `mole_status`: comprobar que el servidor y el token están bien.
- `estacion_repo_tree` / `estacion_read_file`: leer cualquier archivo de
  estacion-ia (CLAUDE.md de cada negocio, planes, datos) sin salir de la sesión.
- `estacion_pipeline_summary` / `estacion_outreach_status`: saber cuántas
  oportunidades hay, por estado y canal, antes de preparar un lote de correos.
- `workspace_list_files` / `workspace_read_file`: consultar los archivos de
  trabajo de Mole (tandas de correos, mockups, guiones).
- `workspace_note`: dejar notas con fecha para Mole.

## 5. Solución de problemas

| Síntoma | Causa probable |
|---|---|
| `mole-mcp` no aparece en `/mcp` | La ruta a `mole_mcp_server.py` está mal o `python3` no está en el PATH |
| Herramientas de GitHub devuelven 404 | Falta `GITHUB_TOKEN` o el PAT no tiene acceso a `gonor98/estacion-ia` |
| 401/403 de GitHub | Token caducado o sin permiso Contents: Read |
| `workspace_*` no encuentra archivos | `MOLE_WORKSPACE_ROOT` apunta a otra ruta; revisa `mole_status` |
