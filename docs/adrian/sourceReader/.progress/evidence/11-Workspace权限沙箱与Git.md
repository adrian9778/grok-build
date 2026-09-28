# 11-Workspace权限沙箱与Git.md 同步证据

## 主题：resolve_session_toolset_for_host + truncation_config_for_host + handle.rs 切换

### 1. resolve_session_toolset_for_host（tool_config.rs:61）
- 签名与 `resolve_session_toolset` 相同，额外接受 `host_kind: WorkspaceHostKind`
- 调 `truncation_config_for_host(host_kind)` 获取 `TruncationConfig`，传给 `resolve_session_toolset_rebuild`
- `resolve_session_toolset` 降为 `#[cfg(test)]`，注释：「Test helper: same as resolve_session_toolset_for_host with a default truncation config.」

### 2. truncation_config_for_host（tool_config.rs:100）
- `pub(crate) fn truncation_config_for_host(host_kind: WorkspaceHostKind) -> TruncationConfig`
- Sandbox → `per_tool_max_output_bytes.insert("get_command_or_subagent_output", 5_000)`
- Daemon → 默认 `TruncationConfig`（40k）

### 3. handle.rs 切换
- `use crate::session::tool_config::resolve_session_toolset_for_host`（替换 `resolve_session_toolset`）
- `create_session`（`:836-855`）：调用 `resolve_session_toolset_for_host`，传入 `self.shared.host_kind`
- rebuild 路径（`:1021-1024`）：调用 `truncation_config_for_host(self.shared.host_kind)`

### 4. fast-worktree 重构
- `api.rs`：`remove_worktree_inner` 新增 `registry_home` 参数，`remove_worktree_in` 新函数
- `execute.rs`：-428 行（Grove/daemon 逻辑大幅简化）
- `worktree/mod.rs`：-473 行
- `offline_clean_tests.rs`：+239 行（新增测试）
- doc 11 未直接引用 fast-worktree 内部细节，不需要更新
