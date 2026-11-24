# Conectar mole-mcp a Hermes y OpenClaw (genérico, por protocolo MCP)

> **Honestidad primero:** en el repo `gonor98/estacion-ia` **no existe
> ninguna configuración de Hermes ni de OpenClaw** (búsqueda verificada:
> 0 resultados). No hay integración nativa que descubrir ni reutilizar.
> Lo que sigue es la conexión **estándar por protocolo MCP**: cualquier
> cliente MCP puede lanzar este servidor por stdio, igual que Claude Code.
> Adapta las rutas a tu máquina; nada de lo de abajo ha sido probado contra
> una instalación concreta de Hermes/OpenClaw porque no hay una a la vista
> desde aquí.

## Cómo funciona MCP aquí

El servidor `mole_mcp_server.py` habla MCP por stdio: el cliente lo lanza
como subproceso, le envía JSON-RPC por stdin y lee respuestas por stdout.
Cualquier agente que soporte `mcpServers` con `command` + `args` + `env`
puede usarlo sin cambiar una línea del servidor.

## OpenClaw

OpenClaw lee servidores MCP de su archivo de configuración
(`~/.openclaw/openclaw.json` o el `clawdbot.json` según la versión).
Añade:

```json
{
  "mcpServers": {
    "mole-mcp": {
      "command": "python3",
      "args": ["/ruta/a/mole-mcp/server/mole_mcp_server.py"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "MOLE_WORKSPACE_ROOT": "/ruta/a/workspace/goals"
      }
    }
  }
}
```

Reinicia OpenClaw y verifica que lista las herramientas (`mole_status`,
`estacion_pipeline_summary`, etc.). Si tu versión de OpenClaw usa otro
nombre de archivo de config, busca la clave `mcpServers` en su documentación.

## Hermes

Hermes, como modelo/agente, no trae un cliente MCP propio: se conecta a
través del *host* que lo ejecuta (por ejemplo, un harness MCP, Claude
Desktop, o un script que haga de puente). Opciones:

1. **Si tu host Hermes soporta MCP:** añade el mismo bloque `mcpServers`
   de arriba en la config del host.
2. **Si solo acepta herramientas por HTTP:** arranca el servidor en modo
   HTTP (`--transport streamable-http --port 8765`) y pon delante un
   adaptador MCP→REST de tu host, o usa el script
   `scripts/sync_pipeline_to_datos.py` para exponer los datos como JSON.
3. **Si Hermes corre como agente autónomo con shell:** puede lanzar el
   servidor por stdio directamente con el mismo comando.

## Variables de entorno (comunes a todos los clientes)

| Variable | Obligatoria | Valor |
|---|---|---|
| `GITHUB_TOKEN` | Sí (para estacion-ia) | Fine-grained PAT, Contents: Read, solo `gonor98/estacion-ia` |
| `MOLE_WORKSPACE_ROOT` | No | Ruta del workspace local (defecto `~/workspace/goals`) |
| `MOLE_NOTES_FILE` | No | Archivo de notas (defecto `~/workspace/mole-notes.md`) |

## Límites conocidos

- Las herramientas de GitHub son de **solo lectura**. Ningún cliente puede
  escribir en estacion-ia a través de este servidor.
- La única escritura es `workspace_note`, y solo añade líneas al archivo de
  notas local.
- La búsqueda de código (`estacion_search_code`) depende de la API de GitHub
  y ha devuelto vacíos con `incomplete_results=true` para este repo: un
  resultado vacío no prueba ausencia.
- El token nunca debe ir en un archivo de configuración que se suba a GitHub.
  Usa variables de entorno del sistema o el almacén de secretos de tu host.
