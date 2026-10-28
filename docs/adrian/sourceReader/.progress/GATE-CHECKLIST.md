# 收尾门禁清单（起点快照 = `.progress/baseline-verify.txt`；A 组编辑器仍在改，数字会变动）

| 篇 | 裸行号 | 失效路径 | 搬家待标注 | 符号待判读 |
|---|---|---|---|---|
| 01-简单框架-系统骨架.md | 7 | 0 | 0 | 0 |
| 02-简单例子-全路径走读.md | 1 | 0 | 0 | 3 |
| 03-详细逐步说明-主链路拆解.md | 1 | 0 | 0 | 3 |
| 04-核心模块与类关系.md | 40 | 0 | 0 | 3 |
| 05-API与接口设计.md | 119 | 0 | 0 | 1 |
| 06-配置与数据流.md | 0 | 0 | 0 | 3 |
| 08-TUI交互循环与渲染.md | 6 | 0 | 0 | 0 |
| 09-Agent会话与模型循环.md | 35 | 0 | 0 | 0 |
| 10-工具协议与扩展体系.md | 13 | 0 | 0 | 1 |
| 11-Workspace权限沙箱与Git.md | 2 | 0 | 2 | 2 |
| 12-认证网络遥测与更新.md | 12 | 0 | 0 | 0 |
| 14-构建测试第三方与许可证.md | 8 | 1 | 0 | 0 |
| 15-跨模块完整运行链与场景.md | 5 | 0 | 1 | 2 |
| 16-术语表与源码查找手册.md | 0 | 0 | 2 | 1 |
| README.md | 0 | 0 | 1 | 0 |
| 可靠性与通用技术实现说明书.md | 0 | 0 | 0 | 4 |
| tui-guide.md | 3 | 0 | 0 | 0 |
| **合计** | **252** | **1** | **6** | **23** |

## 失效 / 搬家（逐条）

- ↦ 搬家 crates/codegen/xai-grok-workspace/src/permission/policy.rs  ->  多候选(3): crates/codegen/xai-grok-cloud-config/src/managed_config/policy.rs, crates/codegen/xai-grok-permission-rules/src/policy.rs, crates/codegen/xai-grok-sandbox/src/command/policy.rs
- ↦ 搬家 crates/codegen/xai-grok-workspace/src/permission/gate_preflight.rs  ->  crates/codegen/xai-grok-permission-rules/src/gate_preflight.rs
- ✗ 失效路径 third_party/ffmpeg/local/lib
- ↦ 搬家 xai-grok-workspace/src/sandbox/lib.rs  ->  crates/codegen/xai-grok-workspace/src/sandbox/mod.rs
- ↦ 搬家 crates/codegen/xai-grok-workspace/src/permission/gate_preflight.rs  ->  crates/codegen/xai-grok-permission-rules/src/gate_preflight.rs
- ↦ 搬家 xai-grok-workspace/src/permission/gate_preflight.rs  ->  crates/codegen/xai-grok-permission-rules/src/gate_preflight.rs
- ↦ 搬家 xai-grok-shell/src/agent.rs  ->  多候选(5): crates/codegen/xai-grok-agent/src/agent.rs, crates/codegen/xai-grok-pager/src/app/agent.rs, crates/codegen/xai-grok-pager/src/scrollback/blocks/agent.rs, crates/codegen/xai-grok-pager/src/views/agent.rs

## 符号待判读（每条要给结论：改对，或在同一行写清为何非错）

- ? 符号待判读 crates/codegen/xai-grok-pager/src/app/agent.rs · AcpUpdateTracker  [在他处: crates/codegen/xai-grok-pager/src/acp/tracker.rs]
- ? 符号待判读 crates/codegen/xai-grok-shell/src/config/mod.rs · ProfileName  [在他处: crates/codegen/xai-grok-sandbox/src/lib.rs]
- ? 符号待判读 crates/codegen/xai-acp-lib/src/message.rs · AcpAgentTx  [在他处: crates/codegen/xai-acp-lib/src/common.rs]
- ? 符号待判读 crates/codegen/xai-grok-shell/src/session/acp_session_impl/types.rs · PromptTurnOk  [在他处: crates/codegen/xai-grok-shell/src/session/commands.rs]
- ? 符号待判读 crates/codegen/xai-grok-pager/src/app/agent_view/mod.rs · Action  [在他处: crates/codegen/xai-grok-pager/tests/settings_e2e.rs]
- ? 符号待判读 crates/codegen/xai-grok-pager/src/actions/defaults.rs · ActionId  [在他处: crates/codegen/xai-grok-pager/src/actions/mod.rs]
- ? 符号待判读 crates/common/xai-computer-hub-sdk/src/harness.rs · ToolServerHandler  [在他处: crates/codegen/xai-grok-workspace/src/hub.rs]
- ? 符号待判读 crates/codegen/xai-grok-workspace-types/src/rpc/mod.rs · RpcEnvelope  [在他处: crates/codegen/xai-grok-workspace-types/src/rpc/envelope.rs]
- ? 符号待判读 xai-grok-workspace/src/handle.rs · WorkspaceOps  [在他处: crates/codegen/xai-grok-workspace/src/workspace_ops.rs]
- ? 符号待判读 crates/common/xai-tool-runtime/src/tool.rs · ToolDispatch  [在他处: crates/common/xai-computer-hub-core/src/inner.rs]
- ? 符号待判读 xai-grok-sampler/src/handle.rs · SamplerCommand  [在他处: crates/codegen/xai-grok-sampler/src/commands.rs]
- ? 符号待判读 crates/codegen/xai-grok-config/src/paths.rs · paths  [在他处: crates/codegen/xai-fast-worktree/src/bin/worktree_lifecycle_bench.rs]
- ? 符号待判读 xai-grok-memory/src/storage.rs · MemoryMode  [在他处: crates/codegen/xai-grok-telemetry/src/process/memory_telemetry.rs]
- ? 符号待判读 crates/codegen/xai-grok-tools/src/types/tool_index.rs · split_identifier  [在他处: crates/codegen/xai-grok-shell/src/session/tool_index.rs]
- ? 符号待判读 crates/codegen/xai-grok-workspace-types/src/rpc/mod.rs · WorkspaceOp  [在他处: crates/codegen/xai-grok-workspace/src/workspace_ops.rs]
- ? 符号待判读 crates/codegen/xai-grok-sandbox/src/child_net.rs · child_net  [在他处: crates/codegen/xai-grok-sandbox/src/lib.rs]
- ? 符号待判读 xai-grok-shell/src/session/acp_session_impl/sampler_turn.rs · SamplingEvent  [在他处: crates/codegen/xai-grok-sampler/src/events.rs]
- ? 符号待判读 xai-grok-shell/src/session/handle.rs · SessionCommand  [在他处: crates/codegen/xai-grok-shell/src/agent/handlers/session.rs]
- ? 符号待判读 xai-grok-pager/src/app/event_loop.rs · JoinSet<TaskResult>  [全库无]
- ? 符号待判读 xai-grok-pager/src/app/effects/mod.rs · Effect::CancelTurn  [在他处: crates/codegen/xai-grok-pager/src/app/actions.rs]
- ? 符号待判读 xai-chat-state/src/handle.rs · ChatStateCommand  [在他处: crates/codegen/xai-chat-state/src/commands.rs]
- ? 符号待判读 xai-grok-workspace/src/permission/manager/mod.rs · PermissionCommand  [在他处: crates/codegen/xai-grok-workspace/src/permission/types.rs]
- ? 符号待判读 xai-grok-shell/src/session/handle.rs · SessionCommand  [在他处: crates/codegen/xai-grok-shell/src/agent/handlers/session.rs]

## 起点逐条结论（已回源码核实，写文档时直接照此改）

| 篇 | 报出的 token | 结论 | 依据 |
|---|---|---|---|
| 11 | `crates/codegen/xai-grok-workspace/src/permission/policy.rs` | **真搬家**，目的地是 `xai-grok-permission-rules/src/policy.rs`（校验器的另两个候选 `cloud-config/src/managed_config/policy.rs`、`sandbox/src/command/policy.rs` 是同名的**不同**策略文件，别选错） | `UPDATE-SPEC.md` §4.2 走掉的清单 |
| 11 / 16 | `…/workspace/src/permission/gate_preflight.rs`（3 种写法：全路径、workspace 相对、裸 crate 名） | **真搬家** → `crates/codegen/xai-grok-permission-rules/src/gate_preflight.rs`；三种写法都要改 | `ls` 实证目的地存在、源文件已无 |
| 14 | `third_party/ffmpeg/local/lib` | **不是文档错误**（文档已用 ⚠️ 标为上游同步残留），但要按 §4.7 补强的证据改写成「**死配置**」：`rsmpeg`/`rusty_ffmpeg` 在根与全部成员 `Cargo.toml` 里**零命中** ⇒ 消费方已不在依赖图，不只是目录没同步 | `grep -rn "rsmpeg\|rusty_ffmpeg" Cargo.toml crates/*/*/Cargo.toml` = 空；`ls third_party/` 只有 4 个 crate |
| 15 | `xai-grok-workspace/src/sandbox/lib.rs`（第 620 行） | 该行位于「旧文档写法 → 当前源码」对照表的**左列** ⇒ 说明性引用，不是失效路径。**两种收尾法任选**：①在同一行补「旧文档」三字（校验器按行判否定词）；②保持不动并在本清单留结论。右列 `crates/codegen/xai-grok-sandbox/src/lib.rs` 已核实为 `SandboxManager` 定义处（快照 `:172`），**不要改** | `grep -n "struct SandboxManager"` |
| README | `xai-grok-shell/src/agent.rs`（第 6 行的记法示例） | 该文件已目录化 → `xai-grok-shell/src/agent/mod.rs`。示例本身在讲记法，**换成一个现存路径**即可，免得读者照抄一个不存在的锚点 | `ls crates/codegen/xai-grok-shell/src/agent/`（`mod.rs` 在） |
