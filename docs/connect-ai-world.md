# Conectar mole-mcp a AI World (Cerebro-IA)

AI World es el panel de la Estación IA (`Cerebro-IA/mundo-ia.html` en
estacion-ia). Es una **página estática**: no puede hablar el protocolo MCP
por sí misma. La conexión se hace con un puente, no con una integración
directa. Hay dos puentes, de menor a mayor trabajo.

## Puente 1 (recomendado): sincronizar el pipeline a JSON

El panel ya carga datos desde `/publico/datos.json`. Este repo incluye
`scripts/sync_pipeline_to_datos.py`, que lee `pipeline.csv` de GitHub y
escribe un JSON pequeño con los totales:

```bash
GITHUB_TOKEN=... python3 scripts/sync_pipeline_to_datos.py \
  --out Cerebro-IA/publico/datos-pipeline.json
```

El JSON resultante tiene esta forma:

```json
{
  "fuente": "gonor98/estacion-ia@main:11-Ingresos-Gonzalo/datos/pipeline.csv",
  "total_filas": 128,
  "por_estado": {"enviado": 88, "identificado": 38, "cotizado": 2},
  "por_canal": {"taller-ia": 40, "speaker": 29, "obc": 23, "web": 13},
  "con_respuesta": 0
}
```

En `mundo-ia.html` se carga con un `fetch()` normal:

```js
fetch('/publico/datos-pipeline.json')
  .then(r => r.json())
  .then(d => {
    // pinta d.total_filas, d.por_estado, d.por_canal donde hoy van los contadores
  });
```

Para mantenerlo fresco, ejecuta el script con una tarea programada (cron en
el ThinkPad o GitHub Actions en estacion-ia) cada hora o cada vez que cambie
`pipeline.csv`. El token que usa el script es el mismo fine-grained PAT de
solo lectura del servidor MCP.

## Puente 2: servidor MCP en modo HTTP

Si algún día un componente del panel necesita preguntar en vivo (no solo
totales), arranca el servidor en modo HTTP en la máquina donde corre el panel:

```bash
python3 server/mole_mcp_server.py --transport streamable-http --port 8765
```

Y desde el backend que sirva el panel (no desde el navegador directamente,
porque MCP sobre HTTP requiere cabeceras de sesión) se hacen peticiones
`POST /mcp` con el protocolo MCP (initialize → tools/list → tools/call).
Este puente es experimental: el Puente 1 cubre el caso real del panel
(mostrar el estado del pipeline).

## Qué NO es

- No es una integración embebida en `mundo-ia.html`: el HTML no cambia.
- No modifica `Cerebro-IA/` ni escribe en estacion-ia: el script solo lee
  de GitHub y escribe el JSON donde tú le indiques.
- No conecta con Hermes ni OpenClaw: eso va por el protocolo MCP genérico,
  ver `docs/connect-hermes-openclaw.md`.
