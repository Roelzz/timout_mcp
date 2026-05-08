# MCP_Timeout_MCS

A FastMCP server exposing six tools that sleep for fixed durations (5s, 10s, 30s, 60s, 90s, 120s). Use it to probe the timeout threshold Microsoft Copilot Studio enforces on MCP tool calls.

## 1. Deploy on Coolify

1. **New service → Application → Public Repository** (or connect Git source). Pick the **Nixpacks** build pack — it auto-detects `pyproject.toml` + `uv`.
2. **Start command**: `uv run main.py`
3. **Exposed port**: `8765`
4. **Domain**: assign a domain in Coolify and let Coolify's built-in proxy (Traefik) handle SSL, **or** front the service with Nginx Proxy Manager and terminate TLS there. Streamable-HTTP needs HTTP/1.1 keep-alive — long-poll responses must not be buffered or capped at 60s by the proxy. In NPM: enable *Websockets Support* and set *Custom Nginx Configuration* `proxy_read_timeout 180s; proxy_send_timeout 180s; proxy_buffering off;`.
5. Deploy. Confirm `https://timeoutmcp.test.roelschenk.com/mcp` responds (a `GET` returns 405 / Method Not Allowed — that's fine, the endpoint exists).

## 2. Register in Copilot Studio (MCP path — preferred)

1. Open your agent in Copilot Studio → **Tools** → **+ Add a tool** → **Model Context Protocol**.
2. **MCP server URL**: `https://timeoutmcp.test.roelschenk.com/mcp`
3. **Authentication**: None.
4. Save. The six `delay_*` tools should appear in the tool picker. Enable each one.
5. In the agent's instructions add a line like: *"When the user says 'test 30 seconds', call the delay_30s tool."* — this gives the orchestrator an explicit hook so you can reliably trigger each probe.

## 3. Register as Custom Connector in Power Platform (alternative path)

Use this if you want to call the delays as connector actions instead of MCP tools (e.g. inside a topic via *Call an action*).

1. **make.powerautomate.com** → **Data → Custom connectors** → **+ New custom connector** → **Import an OpenAPI file**.
2. Upload `swagger.yaml`. Name it `MCP Timeout MCS`.
3. On the **General** tab, set **Host** to your deployed domain (no scheme, no path). Scheme stays HTTPS.
4. **Security** tab: **No authentication**.
5. **Definition** tab: confirm all six operations imported (`delay_5s` … `delay_120s`).
6. **Create connector**.
7. Add to a Copilot Studio agent: open the agent → **Actions** → **+ Add an action** → **Connector** → pick *MCP Timeout MCS* → choose the operation. Repeat for each delay you want to test.

> Note: this path expects plain REST endpoints at `/delay_5s`, `/delay_10s`, etc. The current `main.py` only serves the FastMCP `/mcp` endpoint, so the connector path will not work until you add a REST shim (e.g. a Starlette/FastAPI layer alongside FastMCP). The swagger is included so you can wire that up later or repurpose it.

## 4. Test order

Run probes from short to long. The shape of the failure tells you which timeout you hit.

1. `delay_5s` → must succeed. If this fails, your deploy or proxy is broken, not MCS.
2. `delay_10s` → must succeed.
3. `delay_30s` → typically succeeds on MCP and connector paths.
4. `delay_60s` → first interesting boundary. Many Power Platform connector defaults sit near here.
5. `delay_90s` → past most connector defaults; MCP streamable-HTTP usually still passes.
6. `delay_120s` → upper probe.

**Success looks like**: a chat reply containing `Survived Ns — 2026-05-08T12:34:56.789012+00:00`. Compute round-trip time as `now - timestamp` to confirm the server actually slept (a fast reply with the right text means a cached response, not a real probe).

**Timeout looks like**:
- *MCP path*: agent replies with a generic "I ran into an error" or "the tool didn't respond in time". In the **Activity map** / conversation transcript, the tool-call node shows a red error with a `timeout` / `cancelled` reason. The server-side log still records the call starting; if you see your own `Survived Ns` log line on the server but MCS reports an error, the client (MCS) timed out, not the server.
- *Connector path*: the action returns a 504 / 408, or Power Platform shows *"The request has timed out."* in the action result.

**What to record per probe**: which path (MCP vs connector), delay value, success/timeout, MCS-side error message verbatim, and whether the server logged the completion. That set lets you pinpoint *which* layer enforced the cutoff.

## 5. Local dev

```bash
uv sync
uv run main.py
```

The server binds `0.0.0.0:8765` and exposes the MCP endpoint at `/mcp`.

**Reachable on this machine at**:

| URL                                       | Use case                                        |
| ----------------------------------------- | ----------------------------------------------- |
| `http://localhost:8765/mcp`               | curl / MCP Inspector / Claude Desktop on the dev box |
| `http://127.0.0.1:8765/mcp`               | same as above                                   |
| `http://192.168.68.122:8765/mcp`          | other devices on the LAN, **including NPM**     |

> The LAN IP `192.168.68.122` is the current address of `en0` on this Mac. It can change after a DHCP lease renewal — pin it in your router or rerun `ipconfig getifaddr en0` if probes start failing.

Quick liveness check:

```bash
curl -i -X POST http://localhost:8765/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

A `200` (or `202` with an SSE stream) plus a JSON-RPC body listing the six `delay_*` tools means the server is healthy.

### 5a. Exposing the local dev server through NPM

Use this to point `https://timeoutmcp.test.roelschenk.com` at your laptop instead of the Coolify deploy, so MCS can hit the live code while you iterate.

In **Nginx Proxy Manager → Proxy Hosts → Add Proxy Host**:

| Field                          | Value                              |
| ------------------------------ | ---------------------------------- |
| Domain Names                   | `timeoutmcp.test.roelschenk.com`   |
| Scheme                         | `http`                             |
| Forward Hostname / IP          | `192.168.68.122`                   |
| Forward Port                   | `8765`                             |
| Cache Assets                   | off                                |
| Block Common Exploits          | off (it can interfere with SSE)    |
| Websockets Support             | **on**                             |
| SSL → Request a new SSL cert   | on, Force SSL on                   |

Then in **Advanced → Custom Nginx Configuration** paste:

```nginx
proxy_http_version 1.1;
proxy_set_header Connection "";
proxy_buffering off;
proxy_read_timeout 180s;
proxy_send_timeout 180s;
chunked_transfer_encoding on;
```

Without `proxy_buffering off` and a `proxy_read_timeout` ≥ 180s, NPM itself will cut off the longer probes (`delay_90s`, `delay_120s`) before the server responds — and you'd be measuring NPM, not MCS.

Verify end-to-end after starting the server locally:

```bash
curl -i -X POST https://timeoutmcp.test.roelschenk.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Same response as the localhost check above means the path `MCS → internet → NPM → 192.168.68.122:8765 → FastMCP` is clean and you can register the same URL in Copilot Studio (section 2).
