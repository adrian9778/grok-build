# Message Delivery Core

Source-typed message delivery values and operation authorization for Grok Build.

## Overview

This crate provides the core primitives for secure message delivery between components:

- **Typed envelopes** — Structured message containers with source identity
- **Operation authorization** — Permission checking for message operations  
- **Principal tracking** — Who or what originated each message

## Key Types

- **`DeliveryEnvelope`** — A message with source identity and payload
- **`Principal`** — Represents the source (human, agent, system)
- **`Operation`** — Actions that can be performed on messages
- **`AuthorizedOperation`** — An operation with permission context

## Usage

```rust
use xai_message_delivery_core::*;

// Create an envelope from an agent source
let envelope = DeliveryEnvelope::new(
    AgentSource::new("agent-123"),
    payload
);

// Check if an operation is allowed
let op = Operation::Deliver;
if authorize_operation(&envelope, op).is_ok() {
    // Proceed with delivery
}
```

## Security Model

All operations are authorized based on:
- **Source identity** — Human vs agent vs system
- **Operation type** — Read, write, administer
- **Principal permissions** — What the source is allowed to do

This enables fine-grained audit trails and prevents unauthorized message manipulation.
