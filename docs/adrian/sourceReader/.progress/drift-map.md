# 本轮重核清单（自动生成）

> 生成方式：`.progress/make_drift_map.py`；数据源 = `git diff --name-status 0e2bfffb..HEAD` ∩「本篇正文引用过的 `.rs` 路径」。
> 状态码：A=新增 M=修改 R=改名（→ 指向新路径）D=已删除。
> 用法：编辑某篇时，先按本表逐文件回源码核对该篇中依赖它的结论；本表没列到不代表内容没错，只代表本轮该文件没动。

共 20 篇，命中 266 个本轮变更文件（去重前，按篇计）。


## 00-阅读指南与文档地图.md｜命中 9 个本轮变更文件
- **crates/codegen/xai-grok-pager**（6）
  - `M` `crates/codegen/xai-grok-pager/src/app/actions.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/router.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/helpers.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/tests.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/event_loop.rs`
- **crates/codegen/xai-grok-shell**（2）
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`

## 01-简单框架-系统骨架.md｜命中 17 个本轮变更文件
- **crates/codegen/xai-grok-pager**（7）
  - `M` `crates/codegen/xai-grok-pager/src/acp/spawn.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/actions.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/router.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/helpers.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/event_loop.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/mod.rs`
- **crates/codegen/xai-grok-shell**（7）
  - `M` `crates/codegen/xai-grok-shell/src/agent/app.rs`
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/leader/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_calls.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/commands.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`
- **crates/codegen/xai-grok-sampler**（1）
  - `M` `crates/codegen/xai-grok-sampler/src/events.rs`
- **crates/codegen/xai-grok-workspace**（1）
  - `M` `crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs`

## 02-简单例子-全路径走读.md｜命中 31 个本轮变更文件
- **crates/codegen/xai-grok-shell**（14）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/acp_agent.rs`
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/config/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/run_loop.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/sampler_turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/sampling_events.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/spawn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_calls.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_dispatch.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/updates.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/commands.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/mod.rs`
- **crates/codegen/xai-grok-pager**（12）
  - `M` `crates/codegen/xai-grok-pager/src/acp/tracker.rs`
  - `M` `crates/codegen/xai-grok-pager/src/actions/defaults.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/acp_handler/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/actions.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/agent.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/agent_view/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/prompt.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/queue.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/router.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/task_result.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/event_loop.rs`
- **crates/codegen/xai-grok-workspace**（2）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs`
- **crates/codegen/xai-grok-sampler**（1）
  - `M` `crates/codegen/xai-grok-sampler/src/events.rs`
- **crates/codegen/xai-grok-sandbox**（1）
  - `M` `crates/codegen/xai-grok-sandbox/src/lib.rs`
- **crates/codegen/xai-grok-tools**（1）
  - `M` `crates/codegen/xai-grok-tools/src/registry/types.rs`

## 03-详细逐步说明-主链路拆解.md｜命中 33 个本轮变更文件
- **crates/codegen/xai-grok-shell**（15）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/acp_agent.rs`
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/config/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/hook_dispatch.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/run_loop.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/sampler_turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/sampling_events.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/spawn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_calls.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_dispatch.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/updates.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/commands.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/mod.rs`
- **crates/codegen/xai-grok-pager**（13）
  - `M` `crates/codegen/xai-grok-pager/src/acp/tracker.rs`
  - `M` `crates/codegen/xai-grok-pager/src/actions/defaults.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/acp_handler/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/actions.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/agent.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/agent_view/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/prompt.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/queue.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/router.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/task_result.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/helpers.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/event_loop.rs`
- **crates/codegen/xai-grok-workspace**（2）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs`
- **crates/codegen/xai-grok-sampler**（1）
  - `M` `crates/codegen/xai-grok-sampler/src/events.rs`
- **crates/codegen/xai-grok-sandbox**（1）
  - `M` `crates/codegen/xai-grok-sandbox/src/lib.rs`
- **crates/codegen/xai-grok-tools**（1）
  - `M` `crates/codegen/xai-grok-tools/src/registry/types.rs`

## 04-核心模块与类关系.md｜命中 13 个本轮变更文件
- **crates/codegen/xai-grok-shell**（5）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/acp_agent.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/run_loop.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/commands.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/handle.rs`
- **crates/codegen/xai-grok-tools**（2）
  - `M` `crates/codegen/xai-grok-tools/src/registry/types.rs`
  - `M` `crates/codegen/xai-grok-tools/src/types/resources.rs`
- **crates/codegen/xai-grok-workspace**（2）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs`
- **crates/common/xai-computer-hub-sdk**（2）
  - `M` `crates/common/xai-computer-hub-sdk/src/harness.rs`
  - `M` `crates/common/xai-computer-hub-sdk/src/server.rs`
- **crates/codegen/xai-grok-pager**（1）
  - `M` `crates/codegen/xai-grok-pager/src/app/actions.rs`
- **crates/codegen/xai-grok-sampler**（1）
  - `M` `crates/codegen/xai-grok-sampler/src/events.rs`

## 05-API与接口设计.md｜命中 14 个本轮变更文件
- **crates/codegen/xai-grok-shell**（3）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/session_setup.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/spawn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/commands.rs`
- **crates/codegen/xai-grok-tools**（2）
  - `M` `crates/codegen/xai-grok-tools/src/registry/types.rs`
  - `M` `crates/codegen/xai-grok-tools/src/types/resources.rs`
- **crates/codegen/xai-grok-workspace**（2）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/hub_server.rs`
- **crates/codegen/xai-acp-lib**（1）
  - `M` `crates/codegen/xai-acp-lib/src/lib.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`
- **crates/codegen/xai-grok-pager**（1）
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/helpers.rs`
- **crates/codegen/xai-grok-sampler**（1）
  - `M` `crates/codegen/xai-grok-sampler/src/events.rs`
- **crates/common/xai-computer-hub-sdk**（1）
  - `M` `crates/common/xai-computer-hub-sdk/src/server.rs`
- **crates/common/xai-tool-protocol**（1）
  - `M` `crates/common/xai-tool-protocol/src/lib.rs`
- **crates/common/xai-tool-runtime**（1）
  - `M` `crates/common/xai-tool-runtime/src/render.rs`

## 06-配置与数据流.md｜命中 13 个本轮变更文件
- **crates/codegen/xai-grok-shell**（6）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/acp_agent.rs`
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_calls.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/persistence.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/storage/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/util/config/campaigns.rs`
- **crates/codegen/xai-grok-config**（2）
  - `M` `crates/codegen/xai-grok-config/src/config_layers.rs`
  - `M` `crates/codegen/xai-grok-config/src/lib.rs`
- **crates/codegen/xai-grok-workspace**（2）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs`
- **crates/codegen/xai-grok-login**（1）
  - `M` `crates/codegen/xai-grok-login/src/storage.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`
- **crates/codegen/xai-grok-sandbox**（1）
  - `M` `crates/codegen/xai-grok-sandbox/src/paths.rs`

## 07-程序入口与运行模式.md｜命中 3 个本轮变更文件
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`
- **crates/codegen/xai-grok-pager**（1）
  - `M` `crates/codegen/xai-grok-pager/src/app/mod.rs`
- **crates/codegen/xai-grok-sandbox**（1）
  - `M` `crates/codegen/xai-grok-sandbox/src/paths.rs`

## 08-TUI交互循环与渲染.md｜命中 3 个本轮变更文件
- **crates/codegen/xai-grok-pager**（3）
  - `M` `crates/codegen/xai-grok-pager/src/app/actions.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/router.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/event_loop.rs`

## 09-Agent会话与模型循环.md｜命中 13 个本轮变更文件
- **crates/codegen/xai-grok-shell**（9）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/run_loop.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/sampler_turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/spawn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_calls.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/commands.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/compaction.rs`
- **crates/codegen/xai-grok-agent**（1）
  - `M` `crates/codegen/xai-grok-agent/src/builder.rs`
- **crates/codegen/xai-grok-sampler**（1）
  - `M` `crates/codegen/xai-grok-sampler/src/events.rs`
- **crates/codegen/xai-grok-workspace**（1）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
- **crates/common/xai-tool-types**（1）
  - `M` `crates/common/xai-tool-types/src/task.rs`

## 10-工具协议与扩展体系.md｜命中 19 个本轮变更文件
- **crates/codegen/xai-grok-mcp**（4）
  - `M` `crates/codegen/xai-grok-mcp/src/credentials.rs`
  - `M` `crates/codegen/xai-grok-mcp/src/elicitation.rs`
  - `M` `crates/codegen/xai-grok-mcp/src/lib.rs`
  - `M` `crates/codegen/xai-grok-mcp/src/servers.rs`
- **crates/codegen/xai-grok-tools**（4）
  - `M` `crates/codegen/xai-grok-tools/src/lib.rs`
  - `M` `crates/codegen/xai-grok-tools/src/registry/types.rs`
  - `M` `crates/codegen/xai-grok-tools/src/types/template_renderer.rs`
  - `M` `crates/codegen/xai-grok-tools/src/types/tool_metadata.rs`
- **crates/codegen/xai-grok-shell**（3）
  - `M` `crates/codegen/xai-grok-shell/src/extensions/skills.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_calls.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_dispatch.rs`
- **crates/codegen/xai-grok-workspace**（2）
  - `M` `crates/codegen/xai-grok-workspace/src/permission/types.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/session/tool_config.rs`
- **crates/codegen/xai-grok-agent**（1）
  - `M` `crates/codegen/xai-grok-agent/src/builder.rs`
- **crates/codegen/xai-grok-workspace-types**（1）
  - `M` `crates/codegen/xai-grok-workspace-types/src/lib.rs`
- **crates/common/xai-computer-hub-mcp-adapter**（1）
  - `M` `crates/common/xai-computer-hub-mcp-adapter/src/bridge.rs`
- **crates/common/xai-tool-protocol**（1）
  - `M` `crates/common/xai-tool-protocol/src/bot_relay.rs`
- **crates/common/xai-tool-runtime**（1）
  - `M` `crates/common/xai-tool-runtime/src/context.rs`
- **crates/common/xai-tool-types**（1）
  - `M` `crates/common/xai-tool-types/src/task.rs`

## 11-Workspace权限沙箱与Git.md｜命中 6 个本轮变更文件
- **crates/codegen/xai-grok-workspace**（5）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/hub_gate.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/state.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/types.rs`
- **crates/codegen/xai-grok-sandbox**（1）
  - `M` `crates/codegen/xai-grok-sandbox/src/lib.rs`

## 12-认证网络遥测与更新.md｜命中 11 个本轮变更文件
- **crates/codegen/xai-grok-shell**（5）
  - `M` `crates/codegen/xai-grok-shell/src/agent/feedback_client.rs`
  - `M` `crates/codegen/xai-grok-shell/src/agent/session_registry_client.rs`
  - `M` `crates/codegen/xai-grok-shell/src/remote/client.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/sampler_turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/session_setup.rs`
- **crates/codegen/xai-grok-login**（2）
  - `M` `crates/codegen/xai-grok-login/src/lib.rs`
  - `M` `crates/codegen/xai-grok-login/src/manager.rs`
- **crates/codegen/xai-grok-update**（2）
  - `M` `crates/codegen/xai-grok-update/src/auto_update.rs`
  - `M` `crates/codegen/xai-grok-update/src/lib.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`
- **crates/codegen/xai-grok-telemetry**（1）
  - `M` `crates/codegen/xai-grok-telemetry/src/lib.rs`

## 13-持久化记忆与会话恢复.md｜命中 12 个本轮变更文件
- **crates/codegen/xai-grok-shell**（5）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/session_setup.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/rewind.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/persistence.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/storage/jsonl/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/storage/mod.rs`
- **crates/codegen/xai-grok-memory**（2）
  - `M` `crates/codegen/xai-grok-memory/src/lib.rs`
  - `M` `crates/codegen/xai-grok-memory/src/v2.rs`
- **crates/codegen/xai-grok-pager**（2）
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/helpers.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/mod.rs`
- **crates/codegen/xai-grok-config-types**（1）
  - `M` `crates/codegen/xai-grok-config-types/src/memory.rs`
- **crates/codegen/xai-grok-login**（1）
  - `M` `crates/codegen/xai-grok-login/src/manager.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`

## 14-构建测试第三方与许可证.md｜命中 2 个本轮变更文件
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/build.rs`
- **crates/codegen/xai-grok-test-support**（1）
  - `M` `crates/codegen/xai-grok-test-support/src/lib.rs`

## 15-跨模块完整运行链与场景.md｜命中 20 个本轮变更文件
- **crates/codegen/xai-grok-shell**（8）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/acp_agent.rs`
  - `M` `crates/codegen/xai-grok-shell/src/extensions/notification.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/sampler_turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/spawn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/commands.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/compaction.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/handle.rs`
- **crates/codegen/xai-grok-pager**（6）
  - `M` `crates/codegen/xai-grok-pager/src/app/actions.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/app_view.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/router.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/helpers.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/event_loop.rs`
- **crates/codegen/xai-grok-workspace**（2）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`
- **crates/codegen/xai-grok-sampler**（1）
  - `M` `crates/codegen/xai-grok-sampler/src/events.rs`
- **crates/codegen/xai-grok-sandbox**（1）
  - `M` `crates/codegen/xai-grok-sandbox/src/lib.rs`
- **crates/codegen/xai-grok-tools**（1）
  - `M` `crates/codegen/xai-grok-tools/src/implementations/grok_build/read_file/mod.rs`

## 16-术语表与源码查找手册.md｜命中 31 个本轮变更文件
- **crates/codegen/xai-grok-shell**（12）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/run_loop.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/sampler_turn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/spawn.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_calls.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/tool_dispatch.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn_end.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/commands.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/handle.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/persistence.rs`
- **crates/codegen/xai-grok-pager**（5）
  - `M` `crates/codegen/xai-grok-pager/src/app/actions.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/dispatch/router.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/mod.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/event_loop.rs`
  - `M` `crates/codegen/xai-grok-pager/src/scrollback/blocks/session_event.rs`
- **crates/codegen/xai-grok-workspace**（4）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/hub_server.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/types.rs`
- **crates/codegen/xai-grok-tools**（2）
  - `M` `crates/codegen/xai-grok-tools/src/lib.rs`
  - `M` `crates/codegen/xai-grok-tools/src/registry/types.rs`
- **crates/codegen/xai-grok-config**（1）
  - `M` `crates/codegen/xai-grok-config/src/lib.rs`
- **crates/codegen/xai-grok-login**（1）
  - `M` `crates/codegen/xai-grok-login/src/manager.rs`
- **crates/codegen/xai-grok-mcp**（1）
  - `M` `crates/codegen/xai-grok-mcp/src/servers.rs`
- **crates/codegen/xai-grok-memory**（1）
  - `M` `crates/codegen/xai-grok-memory/src/lib.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`
- **crates/codegen/xai-grok-sampler**（1）
  - `M` `crates/codegen/xai-grok-sampler/src/events.rs`
- **crates/codegen/xai-grok-sandbox**（1）
  - `M` `crates/codegen/xai-grok-sandbox/src/lib.rs`
- **crates/codegen/xai-grok-update**（1）
  - `M` `crates/codegen/xai-grok-update/src/auto_update.rs`

## README.md｜命中 1 个本轮变更文件
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`

## 可靠性与通用技术实现说明书.md｜命中 10 个本轮变更文件
- **crates/codegen/xai-grok-shell**（2）
  - `M` `crates/codegen/xai-grok-shell/src/agent/mvp_agent/mod.rs`
  - `M` `crates/codegen/xai-grok-shell/src/session/handle.rs`
- **crates/codegen/xai-grok-workspace**（2）
  - `M` `crates/codegen/xai-grok-workspace/src/handle.rs`
  - `M` `crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`
- **crates/codegen/xai-grok-pager**（1）
  - `M` `crates/codegen/xai-grok-pager/src/app/effects/mod.rs`
- **crates/codegen/xai-grok-sampler**（1）
  - `M` `crates/codegen/xai-grok-sampler/src/events.rs`
- **crates/codegen/xai-grok-sandbox**（1）
  - `M` `crates/codegen/xai-grok-sandbox/src/lib.rs`
- **crates/codegen/xai-grok-test-support**（1）
  - `M` `crates/codegen/xai-grok-test-support/src/sandbox.rs`
- **crates/codegen/xai-grok-tools**（1）
  - `M` `crates/codegen/xai-grok-tools/src/registry/types.rs`

## tui-guide.md｜命中 5 个本轮变更文件
- **crates/codegen/xai-grok-pager**（3）
  - `M` `crates/codegen/xai-grok-pager/src/app/app_view.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/event_loop.rs`
  - `M` `crates/codegen/xai-grok-pager/src/app/mod.rs`
- **crates/codegen/xai-grok-pager-bin**（1）
  - `M` `crates/codegen/xai-grok-pager-bin/src/main.rs`
- **crates/codegen/xai-tty-utils**（1）
  - `A` `crates/codegen/xai-tty-utils/src/display_char.rs`
