# Computer Hub Core

Core functionality for Grok Build's Computer Hub — a distributed tool execution system.

## Overview

Computer Hub enables Grok Build to execute tools across multiple machines and environments:

- **Tool registry** — Discover and manage available tools
- **Transport layer** — Communication between hub and clients  
- **Remote execution** — Run tools on remote machines
- **Workspace management** — Handle different execution contexts

## Key Components

- **`registry.rs`** — Tool registration and discovery
- **`transport.rs`** — Communication protocols and serialization  
- **`local.rs`** — Local tool execution
- **`workspace.rs`** — Workspace isolation and management

## Usage

```rust
use xai_computer_hub_core::*;

// Create a tool registry
let mut registry = ToolRegistry::new();

// Register tools
registry.register("bash", bash_tool)?;
registry.register("edit", edit_tool)?;

// Execute a tool call
let result = registry.execute(tool_call).await?;
```

## Transport Types

- **Local** — Direct in-process execution
- **IPC** — Inter-process communication  
- **Network** — TCP/WebSocket remote execution
- **SSH** — Secure remote execution

## Security

All tool execution is:
- **Sandboxed** — Limited filesystem and network access
- **Audited** — Comprehensive logging and monitoring
- **Authorized** — Permission checking before execution
