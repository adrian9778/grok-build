# Computer Hub MCP Adapter

Model Context Protocol (MCP) adapter for Computer Hub integration.

## Overview

This adapter bridges Computer Hub's distributed tool execution system with the Model Context Protocol (MCP), enabling:

- **MCP server exposure** — Expose Computer Hub tools as MCP servers
- **Protocol translation** — Convert between MCP and Computer Hub protocols
- **Client integration** — Connect MCP clients to Computer Hub tools
- **Tool discovery** — Automatic tool registration and schema export

## Key Features

- **Bidirectional bridge** — Both MCP server and client modes
- **Schema mapping** — Automatic tool schema conversion
- **Auth forwarding** — Pass through authentication context
- **Error translation** — Consistent error handling across protocols

## Usage

### As MCP Server

```rust
use xai_computer_hub_mcp_adapter::*;

// Wrap a Computer Hub registry as an MCP server
let hub_registry = create_hub_registry().await?;
let mcp_server = McpAdapter::new(hub_registry);

// Serve over stdio (for use with Grok Build)
mcp_server.serve_stdio().await?;
```

### As MCP Client

```rust
// Connect to an external MCP server through Computer Hub
let transport = McpTransport::connect("mcp://server").await?;
let hub_client = ComputerHubClient::new(transport);

// Tools now available in Computer Hub registry
let tools = hub_client.list_tools().await?;
```

## Configuration

Configure via `config.toml`:

```toml
[mcp_servers]
[mcp_servers.my-hub]
type = "computer-hub"
endpoint = "tcp://hub.example.com:8080"
auth_token = "..."
```

## Tool Schema Mapping

MCP tool schemas are automatically converted:

| MCP Type | Computer Hub Type |
|----------|-------------------|
| `string` | `Value::String` |
| `number` | `Value::Number` |
| `boolean` | `Value::Bool` |
| `object` | `Value::Object` |
| `array` | `Value::Array` |

## Error Handling

All MCP errors are translated to Computer Hub error types:

- `McpError::ToolNotFound` → `HubError::UnknownTool`
- `McpError::InvalidArgs` → `HubError::InvalidArguments`  
- `McpError::Timeout` → `HubError::ExecutionTimeout`
