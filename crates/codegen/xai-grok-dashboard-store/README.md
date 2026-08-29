# Grok Dashboard Store

SQLite-backed persistent storage for the Grok Build agent dashboard.

## Overview

This crate provides a typed, safe interface to the dashboard workspace database. It manages:

- **Workspace membership** — which sessions belong to the dashboard
- **Layout persistence** — pinned sessions and custom ordering  
- **Grouping preferences** — how sessions are organized (by state or directory)
- **Schema evolution** — forward-compatible additive migrations

## Key Invariants

- **Single writer** — One `WorkspaceStore` instance per process
- **Path safety** — All session IDs are validated single path components  
- **Capacity limits** — Membership is capped at `WORKSPACE_CAPACITY`
- **Data preservation** — Corrupt or newer-schema files are never deleted

## Usage

```rust
use xai_grok_dashboard_store::WorkspaceStore;

// Open or create the store
let store = WorkspaceStore::open(&store_path)?;

// Add a session to the workspace
let member = NewMember {
    session_id: session_id,
    kind: MemberKind::TopLevel,
    cwd: current_dir,
    title: "My Session".to_string(),
    // ...
};
store.insert_member(member)?;
```

## Architecture

- **`store.rs`** — Main `WorkspaceStore` API
- **`schema.rs`** — Database schema and migrations  
- **`error.rs`** — Typed error handling
- **`types.rs`** — Core data types and validation

This crate owns all SQL for the dashboard feature. No other code should access the database directly.
