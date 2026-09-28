# 08-TUI交互循环与渲染.md 同步证据

## 主题：SignalStreams 抽取 + HeadlessSignals + WidthShrink/reflow + forget_transmitted_inline_media + dashboard row 重构 + minimal reprint

### 1. SignalStreams（xai-grok-pager/src/signal_streams.rs，新文件 81 行）
- `pub struct SignalStreams`（unix: `signal_streams.rs:4`）：字段 `interrupt`/`terminate`/`hangup`（均 `Option<tokio::signal::unix::Signal>`）
- `install()`（`:12`）：从 `SignalKind` claim 三个信号流；错误只 warn 不 fatal
- `next_code(&mut self) -> i32`（`:28`）：`select!` 三个流，返回 130(SIGINT)/143(SIGTERM)/129(SIGHUP)
- windows 版（`:34`）：字段 `ctrl_c: Option<tokio::signal::windows::CtrlC>`；`install()`（`:40`）、`next_code()`（`:48`）
- 注释：「The signals the 130/143/129 exit-code map covers, claimed from construction for as long as this lives: without a live stream a signal takes its default action and kills the process.」
- `app/signal_handler.rs` 重构：`spawn_async_signal_task` 使用 `SignalStreams::install()` + `streams.next_code().await`

### 2. HeadlessSignals（headless/signals.rs，新文件 157 行）
- `pub(super) struct HeadlessSignals`（`:37`）：字段 `handoff: Arc<SignalHandoff>`
- `install() -> Result<HeadlessSignals, SignalSetupError>`（`:42`，async）
- `defer_exit(&self) -> DeferredExit<'_>`（`:52`）
- `DeferredExit`（`:63`）：`signalled()`（`:69`）、`release(self) -> Option<i32>`（`:80`）
- `headless.rs::run_single_turn` 在入口安装 `HeadlessSignals::install().await?`，loop 中 `deferred_exit.signalled()` 在 biased select 第一位

### 3. WidthShrink（xai-ratatui-inline/src/terminal.rs:34）
- `pub enum WidthShrink { Truncates (#[default]), Rewraps }`
- 注释：「How the host terminal treats rows already on screen when its width shrinks.」
- `width_shrink` 字段加到 `Terminal` 结构体（`:170`）
- `reflowed_cursor_offset(&self, new_width: u16) -> u16`（`:1257`）：Truncates 直接返回 `rows_above`；Rewraps 累加每行溢出宽度

### 4. forget_transmitted_inline_media（agent_view/media.rs:372）
- `pub(crate) fn forget_transmitted_inline_media(&mut self)`
- 清空 `inline_media_ids`、`inline_media_iterm_emitted`、`last_placed_ids`，递归 `subagent_views`
- 注释：「Forget which Kitty images the terminal holds, so the next frame re-transmits them. Call after a full screen clear: Ghostty drops image data on ESC[2J.」
- `event_loop.rs:630` 在 `force` clear 后调用

### 5. minimal reprint
- `xai-grok-pager/src/minimal/reprint.rs`（新文件 132 行）：`REPRINT_DEBOUNCE = Duration::from_millis(120)`（`:11`）、`observe_minimal_layout`（`:111`）、`record_minimal_rows_printed`（`:118`）、`mark_minimal_history_printed`（`:124`）
- `xai-grok-pager-minimal/src/reprint.rs`（新文件 124 行）：`REPRINT_MAX_ROWS: u16 = 4000`（`:31`）、`maybe_reprint(app, terminal)`（`:34`）
- 注释：「Reprints the session history at the terminal's new width after a resize. A reflowing terminal re-wraps printed rows and splits committed text mid-word.」

### 6. Dashboard row 重构
- `DashboardRowId`（`views/dashboard/state.rs:26`）：当前三变体 `TopLevel(AgentId)`、`Roster{session_id}`、`Workspace{session_id}`——**`Subagent` 变体已移除**
- `DashboardRow`（`row.rs`）：移除字段 `indent`、`parent_label`、`is_more_placeholder`、`more_count`
- `build_rows` 函数移除，替换为 `build_rows_with_roster`（`:84`）和 `build_rows_with_workspace`（`:116`）
- `MAX_VISIBLE_SUBAGENTS` 常量移除
- `subagent_catalog_pane.rs` 整文件删除（513 行）
- `dispatch/dashboard.rs::rearm_session_overlay` 不再选 Subagent 行，直接 `DashboardRowId::TopLevel(id)`
- `dispatch/router.rs` 移除 `Action::ViewCatalogEntry` 分支

### 7. plan.rs Ctrl+C 取消空草稿
- `agent_view/plan.rs::ctrl_c_cancels_empty_draft(&self, key) -> bool`（新增）
- 条件：`key!('c', CONTROL).matches(key) && self.prompt.text().is_empty()`
- 在 commenting 和 casual_plan_commenting 两处使用
