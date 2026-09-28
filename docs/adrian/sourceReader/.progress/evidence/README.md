# README.md 同步更新证据

## 变更范围
- base: cb8e30bd (SOURCE_REV=84745de9)
- target: 0e2bfffb (SOURCE_REV=036a5d83)
- 184 源文件变更 (5462+/4762-)

## 关键主题（影响 README 同步说明）
1. **WinGet 安装检测与升级提示** — `xai-grok-update/src/winget.rs`（新文件，100 行）；`auto_update.rs` 引入 `WINGET`/`UPGRADE_COMMAND`，`check_update_status` 对 WinGet 安装强制 stable channel，`print_update_status` 打印 `winget upgrade` 提示；`reinstall_hint` 加 WinGet 分支；`is_stable_channel` 从 `auto_update.rs` 移至 `version.rs` 并 pub。
2. **Team capability hydration** — `xai-grok-login/src/model.rs` `GrokAuth` 新增 `can_administer_team: Option<bool>` 字段；`manager.rs` 新增 `hydrate_can_administer_team`；`manager/enrichment.rs` 新增 `hydrate_can_administer_team` 函数 + 日志卸载 `log_offloaded`；`xai-grok-pager` 新增 `Effect::HydrateTeamCapability`、`TaskResult::TeamCapabilityHydrated`、`AuthIdentity` 结构体、`app_view` 新增 `is_team_principal`/`can_administer_team` 字段、`needs_team_capability_hydration`、`coding_data_sharing_lock` 替代 `is_team_non_admin`；`extensions/auth.rs` 新增 `x.ai/auth/hydrate_team_capability` 方法；`effects/helpers.rs` 新增 `send_hydrate_team_capability`。
3. **Memory capture 捕获取消回合** — `memory_capture.rs`：`is_successful_query_loop` 重命名为 `is_capturable_turn_result`，现在匹配 `Completed` + `Cancelled`；`enqueue_v2_completed_turn` 重命名为 `enqueue_v2_turn_capture`；新增 `is_capturable_front`；`run_loop.rs` 和 `cancel.rs` 调用更新；`commands.rs` `FlushMemory` 注释更新；`SessionActor::handle_prompt` 新增 `record_turn_start`。
4. **信号处理重构** — `xai-grok-pager/src/signal_streams.rs`（新文件，81 行）`SignalStreams` 结构体统一 unix/windows 信号；`app/signal_handler.rs` 重构使用 `SignalStreams`；`headless/signals.rs`（新文件）`HeadlessSignals` + `deferred_exit`；`headless.rs` `run_single_turn` 安装 `HeadlessSignals`。
5. **Dashboard row 重构** — `views/dashboard/row.rs` 移除 `indent`/`parent_label`/`is_more_placeholder`/`more_count` 字段、`MAX_VISIBLE_SUBAGENTS` 常量、`build_rows` 函数；`DashboardRowId::Subagent` 变体移除；`subagent_catalog_pane.rs` 整文件删除（513 行）；`dispatch/dashboard.rs` `rearm_session_overlay` 不再选 Subagent 行；`dispatch/router.rs` 移除 `Action::ViewCatalogEntry`。
6. **终端 resize 与 reprint** — `xai-ratatui-inline/src/terminal.rs` 新增 `WidthShrink` 枚举、`reflowed_cursor_offset` 方法；`xai-grok-pager-minimal/src/reprint.rs`（新文件，124 行）+ `xai-grok-pager/src/minimal/reprint.rs`（新文件，132 行）`maybe_reprint` + `REPRINT_MAX_ROWS` + `REPRINT_DEBOUNCE`。
7. **工具集与截断配置** — `xai-grok-workspace/src/session/tool_config.rs` 新增 `resolve_session_toolset_for_host`（生产路径，按 `WorkspaceHostKind` 截断 poll 上限：sandbox=5k，其他=40k）、`truncation_config_for_host`；`resolve_session_toolset` 改为 `#[cfg(test)]`；`handle.rs` 切换至 `resolve_session_toolset_for_host`。
8. **GetTerminalCommandOutputTool 参数化** — `xai-grok-tools/src/registry/types.rs` 改用 `register_with_params::<GetTerminalCommandOutputTool, TerminalCommandOutputParams>()`；`task_output/terminal_command.rs` +303 行。
9. **bundle entry/get 移除** — `extensions/bundle.rs` 移除 `EntryGetRequest`/`EntryGetResult`/`get_entry`/`get_entry_at`/`validate_entry_name` 和 `x.ai/bundle/entry/get` 方法。
10. **fast-worktree 重构** — `xai-fast-worktree/src/worktree/execute.rs` -428 行、`worktree/mod.rs` -473 行（大量代码删除/重组）；新增 `offline_clean_tests.rs`（239 行）。
11. **Kitty 图像重传** — `agent_view/media.rs` 新增 `forget_transmitted_inline_media`；`event_loop.rs` 在 `force` clear 后调用；`agent_view/paste.rs` 新增对应测试。
12. **plan.rs Ctrl+C 取消空草稿** — `agent_view/plan.rs` 新增 `ctrl_c_cancels_empty_draft`。
13. **PersistenceMsg::UsageTurn 加 ack** — `persistence.rs` `UsageTurn` 新增 `respond_to: oneshot::Sender<io::Result<()>>`。
14. **Cargo.lock** — `rmcp` 3.2.0→3.4.0、`hashbrown` 引入 0.17.0 + `foldhash`。
15. **CHANGELOG** — `sports_search` 和 `long reasoning reminder` 从 1.0.41 changelog 移除。

## 未影响 README 规模数据
- Workspace members 数不变（102）
- rust-toolchain 不变（1.94.0）
- ratatui/tokio/agent-client-protocol 版本不变
