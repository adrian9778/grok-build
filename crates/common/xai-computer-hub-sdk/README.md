# Computer Hub SDK

SDK for building Computer Hub integrations and external tool providers.

## Overview

This SDK enables developers to:

- **Build custom tools** — Create new tools for the Computer Hub ecosystem
- **Implement transports** — Add new communication protocols  
- **Create providers** — Bridge external systems into Computer Hub
- **Extend capabilities** — Add domain-specific functionality

## Key Traits

- **`Tool`** — Core tool execution interface
- **`Transport`** — Communication protocol implementation
- **`Provider`** — External system integration
- **`Registry`** — Tool discovery and management

## Building a Custom Tool

```rust
use xai_computer_hub_sdk::*;

struct MyTool;

#[async_trait]
impl Tool for MyTool {
    async fn execute(&self, args: Value) -> Result<Value> {
        // Your tool implementation
        Ok(json!({"result": "success"}))
    }
    
    fn schema(&self) -> ToolSchema {
        ToolSchema::new("my_tool")
            .description("Does something useful")
            .parameter("input", Type::String)
    }
}
```

## Custom Transport

```rust
struct MyTransport;

#[async_trait]
impl Transport for MyTransport {
    async fn send(&self, message: Message) -> Result<Response> {
        // Your transport implementation
    }
}
```

## Integration Patterns

- **MCP Server** — Expose tools via Model Context Protocol
- **HTTP API** — REST endpoints for external tools
- **CLI Bridge** — Wrap command-line tools
- **Service Mesh** — Microservice integration

## Testing

The SDK includes test utilities:

```rust
use xai_computer_hub_sdk::test::*;

let harness = TestHarness::new();
harness.register_tool(MyTool);
let result = harness.call("my_tool", args).await?;
```
