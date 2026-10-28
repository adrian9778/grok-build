# Grok Build TUI 专题（函数级）

> 范围：Grok Build 的终端交互界面（TUI）——从进程入口、事件循环、输入解析、渲染管线、主题外观，到核心控件与自研 ratatui 组件。
>
> 快照：工作树 `HEAD = 7d70d52c`（`SOURCE_REV = 036a5d83…`），采集于 2026-10-14，并于同日按 HEAD 刷新第 1 章（§1.1/1.4/1.5/1.6/1.8）与第 5 章（§5.1/5.2/5.5/5.7/5.10）。2026-10-28 复核：当前 `HEAD = 42f4d7d3`，本文覆盖的六个 crate 与 `7d70d52c` **逐字节相同**，故上述快照仍然精确有效，见下一条。
>
> **刷新记录（2026-10-14，`9607d2c5` → `7d70d52c`）**：上游并入 3 个提交后，`xai-grok-pager-render` 的 `render/`、`theme/`、`input/`、`terminal/` 与两个 `xai-ratatui-*` 的**核心文件未变**；漂移集中在 pager 应用层（`main.rs` / `app/mod.rs` / `app/event_loop.rs` / `app/app_view.rs` / `app/voice_state.rs`(新) / `agent_view/*` / `views/*`）。本次已回同步：§1.1（新增 `run_update_blocking`/`is_opted_out_of_updates`）、§1.4（新增 `voice_state` 模块与 `resolve_voice_mode_enabled_as`）、§1.5（**select! 五个自限定时器上移到 ACP 之上**）、§1.6（voice 状态类型迁出至 `app/voice_state.rs` + 新增 `logout_pending`/`distribution`/`voice_*` 字段）、§1.8（调用链补行号与退出更新路径）、§3.3（`is_unsafe_display_char` 已搬到 `xai-tty-utils/src/display_char.rs`）、§4.7（`appearance/*` 行号 + `persist_respect_manual_folds_to` + `load_keep_text_selection` 返回类型变更）、§5.1/5.2（`load_failed`/`workspace_dashboard_enabled` + `model_notice` 渲染接入）、§5.5（计划注释关闭按钮 + `delete_plan_comment_by_id`）、§5.7（`is_awaiting_user_answer`）、§5.10（`AgentViewLayout.model_notice` + `prompt_widget` 方法更名 + 新增 `model_notice_banner.rs`/`modal_list.rs`/`skills_tab.rs`）。
>
> **刷新记录（2026-10-28，`7d70d52c` → `42f4d7d3`，`SOURCE_REV = 559751fd`）**：本文全部行号快照**无需改写**，理由是被覆盖的六个 crate 在两个提交之间逐字节相同：`git rev-parse <commit>:crates/codegen/<crate>` 取树哈希逐一比对，`xai-grok-pager` / `xai-grok-pager-bin` / `xai-grok-pager-render` / `xai-ratatui-textarea` / `xai-ratatui-inline` / `xai-tty-utils` **六个全部 IDENTICAL**，且 `7d70d52c` 确为 `42f4d7d3` 的祖先（`git merge-base --is-ancestor` 通过）、`git log 7d70d52c..HEAD -- <这六个路径>` 零提交。也就是说这一轮全库文档同步里唯一没有漂移的就是本文所讲的 TUI 运行时。
>
> 该结论另有独立一手实测支撑（口径与局限一并写明）：把「`SYM`（约?第 N 行）」与「- `SYM` … 约第 N 行。」两种**锚点无歧义**的形状交给脚本回源比对，**574 条形状可归因**，其中 **357 条在归属文件里定位到该符号的定义行、336 条与文中数字完全相等**；剩 **21 条逐条手工判定后全部是本机判据的伪告警**，没有一条是文档错误——成因三类：①文中是**区间**（如「约第 74–137 行」「45–55」「104–165」「391–479」），脚本拿单个成员的定义行去比区间起点；②同名重载（`app_view.rs` 三处 `pub fn new`，取到 36 那条而不是文中 1341）；③小节的文件写在**正文段落**而非标题里（§4.2 的 `struct Theme` 实为 `theme/tokyonight.rs` 第 46 行、`Theme::terminal_default()` 实为 `theme/terminal_default.rs` 第 28 行，两处数字都对，只是脚本沿用了 §4.1 的 `theme/mod.rs`）。
>
> **仍未逐条复测的部分**：919 个「第 N」记号里，其余 345 个属于上述两种形状之外（散文中的多个并列名各带一个数、字段级引用、`文件.rs 第 N 行` 的内联跨文件引用），未被脚本归因、也就**没有逐条一手复测**。它们同样受「六个 crate 逐字节相同」这条保护——漂移在物理上不可能发生；但「数字从一开始就写错」这类错误不受该保护，本轮未穷尽。按本文既有索引约定，这类情况用 `grep -n 'fn 函数名' 文件` 即可自证。：源码位置一律以「`文件路径` + `函数名`」为主锚点，文中括号里的「约第 N 行」只是**阅读时的快照**，随上游同步会漂移，**请以函数名为准**（`grep -n 'fn 函数名' 文件` 即可重新定位）。
>
> **索引约定**：源码位置一律以「`文件路径` + `函数名`」为主锚点，文中括号里的「约第 N 行」只是**阅读时的快照**，随上游同步会漂移，**请以函数名为准**（`grep -n 'fn 函数名' 文件` 即可重新定位）。
>
> 说明：本文由对当前源码的逐文件通读汇总而成，覆盖**架构上重要的函数/方法/结构体**；琐碎的 getter/setter/纯样板做了合并概括。`xai-grok-pager` 全 crate 约 53.6 万行（含测试），本文只聚焦 TUI 运行时本身，不含 agent 业务逻辑（dispatch 的具体动作、slash 命令实现、会话管理等另见对应专题）。

---

## 目录

- [0. 架构总览](#0-架构总览)
- [1. 入口、主循环与 App 状态机](#1-入口主循环与-app-状态机)
- [2. 输入系统](#2-输入系统)
- [3. 渲染管线](#3-渲染管线)
- [4. 主题与外观](#4-主题与外观)
- [5. 核心控件与视图](#5-核心控件与视图)
- [6. 横切主题与设计要点](#6-横切主题与设计要点)
- [附录 A：关键文件索引](#附录-a关键文件索引)
- [附录 B：建议阅读顺序](#附录-b建议阅读顺序)

---

## 0. 架构总览

### 0.1 crate 地图

TUI 不是单个 crate，而是一条**从可执行外壳到自研渲染原语**的分层家族（均在 `crates/codegen/` 下）：

| crate                        | 角色                                                                                        | 规模（src 行数）   |
| ---------------------------- | ----------------------------------------------------------------------------------------- | ------------ |
| `xai-grok-pager-bin`         | 进程外壳/组合根。CLI 解析、子命令分流、tokio runtime、IoC 装配                                                | 3,855        |
| `xai-grok-pager`             | **TUI 应用本体**：`app::run` 装配、事件循环、`AppView` 根状态机、各视图（`app/agent_view`、`views`、`scrollback`） | 536,256（含测试） |
| `xai-grok-pager-render`      | **表现原语层**：绘制入口与写线程、输入解析、换行、滚动条、语法高亮、主题、终端探测、overlay                                       | 42,882       |
| `xai-ratatui-textarea`       | 自研多行输入控件（缓冲区 + 编辑命令 + 元素 + 撤销 + 渲染）                                                       | 13,333       |
| `xai-ratatui-inline`         | 自研「内联视口」终端（TUI 只占屏幕底部，上方是原生 scrollback）                                                   | 3,477        |
| `xai-grok-pager-diff`        | diff hunk 构造                                                                              | 1,445        |
| `xai-grok-pager-minimal`     | `--minimal` 滚动原生渲染模式（经函数指针缝注入，避免 cargo 循环依赖）                                              | 7,230        |
| `xai-grok-pager-pty-harness` | PTY 端到端测试夹具                                                                               | —            |

关键设计：**`xai-grok-pager-bin` 之所以独立存在**，是因为 `xai-grok-pager-minimal` 依赖 `xai-grok-pager`，而 pager 库不能再反向依赖 minimal（cargo 循环）。于是由二进制 crate 同时链接两者，并在启动时安装 minimal 模式的 IoC 钩子。**发行产物名仍叫 `xai-grok-pager`**（`[[bin]] name = "xai-grok-pager"`）。

### 0.2 依赖与版本（工作区统一）

| 依赖                                        | 版本                                                                                | 用途                                                                                   |
| ----------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `ratatui`                                 | **0.29**（features: `crossterm`, `unstable-widget-ref`, `unstable-backend-writer`） | 核心 TUI 框架                                                                            |
| `ratatui-core`                            | 0.1                                                                               | 无 backend 的纯 widget 层                                                                |
| `crossterm`                               | **0.28**（`event-stream`, `bracketed-paste`）                                       | 终端事件/后端                                                                              |
| `tui-scrollbar`                           | 0.2                                                                               | 平滑 Unicode 滚动条                                                                       |
| `textwrap`                                | 0.16                                                                              | 词感知换行                                                                                |
| `unicode-width` / `unicode-segmentation`  | 0.2 / —                                                                           | 显示宽度与字素簇                                                                             |
| `unicode-bidi` / `unicode-bidi-mirroring` | —                                                                                 | 双向文本（可选）                                                                             |
| `vte`                                     | 0.15.0                                                                            | PTY 字节流 → 样式行的终端模拟                                                                   |
| `syntect`                                 | 5.3（default-onig）                                                                 | 语法高亮                                                                                 |
| `anstyle` / `anstyle-parse`               | 1.0 / 0.2                                                                         | markdown 样式桥 / 行切分 VTE                                                               |
| `agent-client-protocol`                   | 0.10.4（unstable）                                                                  | ACP（agent 通信协议）                                                                      |
| `tokio`                                   | 1（full）                                                                           | 异步运行时                                                                                |
| `dark-light`                              | 2                                                                                 | 系统深浅色探测                                                                              |
| `xai-grok-cloud-config`                   | workspace（**新增**）                                                                 | managed config / deployment key / 版本策略；原 `xai-grok-shell::managed_config` 已迁至此 crate |

> `xai-grok-pager-bin` 版本 `1.0.41 → 1.0.45`；新增 `stock` feature（`--no-default-features` 构建时显式开启上游 crate 默认特性）；`xai-grok-shell` / `xai-grok-update` 由 `workspace = true` 改为 `path` + `default-features = false`。

### 0.3 分层与数据流

```
┌──────────────────────────────────────────────────────────────────────┐
│ 进程外壳  xai-grok-pager-bin::main → async_main → app::run            │
├──────────────────────────────────────────────────────────────────────┤
│ 事件循环  app::event_loop::run   （biased tokio::select! 大循环）      │
│   ├── 输入 arm  → drain_and_process → AppView::handle_input           │
│   ├── ACP arm   → acp_handler::handle                                │
│   ├── 任务 arm  → tasks.join_next() → dispatch(TaskComplete)          │
│   └── 定时 arm  → app.tick() + schedule_tick                         │
├──────────────────────────────────────────────────────────────────────┤
│ 状态机    AppView（唯一可变状态容器）                                  │
│   ├── ActiveView::Welcome → 欢迎页/认证/会话选择                       │
│   └── ActiveView::Agent(id) → AgentView（会话主界面）                  │
│          ├── scrollback（消息流）  ├── prompt（输入框）                │
│          └── 各种 overlay（行查看器/块查看器/权限卡/模态…）             │
├──────────────────────────────────────────────────────────────────────┤
│ 渲染原语  xai-grok-pager-render（draw/wrapping/theme/input/…）        │
│ 自研控件  xai-ratatui-textarea · xai-ratatui-inline                   │
└──────────────────────────────────────────────────────────────────────┘
```

**单向数据流**（贯穿全系统的铁律）：

```
终端事件 ──► AppView::handle_input* ──► InputOutcome{Action|Effect 候选}
                                            │
                                            ▼
                       dispatch::dispatch(action)  ──► 同步改 AppView 状态
                                            │
                                            └──► Vec<Effect>
                                                     │
                                                     ▼
                              effects::execute(effect) ──► JoinSet::spawn(TaskResult)
                                                     │
                                                     ▼
                              主循环 tasks.join_next() ──► dispatch(TaskComplete)
```

即：**输入不直接产生副作用**，只产出 `Action`/`Effect`；副作用统一由异步任务执行、结果经 `TaskComplete` 回流。这让 dispatch 层可测（sans-IO）。

### 0.4 三种屏幕模式

`enum ScreenMode { Fullscreen, Inline, Minimal }`（`app/mod.rs`）：

- **Fullscreen**：`EnterAlternateScreen` 全屏 alt-screen，默认模式。
- **Inline**：用 `xai-ratatui-inline` 的内联视口，TUI 只占底部若干行，上方是终端原生 scrollback（可用终端自身滚动回看）。
- **Minimal**：由 `xai-grok-pager-minimal` 提供的滚动原生模式，进一步降低重绘开销。

模式是**进程级状态**（`CURRENT_SCREEN_MODE` 原子 + `minimal_mode_active()`），以便 panic hook、信号路径、post-loop teardown 在**没有 `AppView`** 时也能正确拆机。

### 0.5 全景：启动 → 循环 → 拆机

```
main() → async_main() → app::run()
   ├─ 读配置 / 预取 remote settings
   ├─ session_startup::materialize_startup()      // 决定 Load/New/Fork
   ├─ screen_mode_relaunch::resolve_screen_mode()
   ├─ render::draw::spawn_writer_thread()         // 独立写线程
   ├─ init_terminal()                             // raw mode / alt-screen / mouse / kitty / panic hook
   ├─ bounded_connect() → acp::connect | connect_via_leader
   └─ event_loop::run(...)                        // ★主循环
          └─ 循环直到 break
   └─ restore_terminal() → 退出摘要/更新/relaunch
```

---

## 1. 入口、主循环与 App 状态机

覆盖文件：`xai-grok-pager-bin/src/{main,agent_command}.rs`、`xai-grok-pager/src/{lib,startup}.rs`、`xai-grok-pager/src/app/{mod,event_loop,app_view,reader_thread,terminal_restore,event_loop_stall}.rs`。

### 1.1 `crates/codegen/xai-grok-pager-bin/src/main.rs`

进程外壳。**不是** TUI 逻辑本身，而是「解析 CLI → 分流子命令 → 仅交互路径才进 TUI」。

- `main()` — 进程主入口。先 `set_full_version`、处理 mermaid/voice 的**子进程再入**（`maybe_run_render_subprocess` / `maybe_run_capture_subprocess` 命中即 exit）；`PagerArgs::parse_cli()` 后先做 `--version`/`--doctor` 早期分流；随后装 jemalloc 钩子、Sentry、crash handler、`raise_fd_limit()`；再建 multi-thread runtime（worker 数由 `cli_worker_threads()` 决定，上限 8），用 `run_and_shutdown(runtime, async_main(args), RUNTIME_SHUTDOWN_GRACE)` 跑主 future。约第 2036 行。
- `async_main(mut args: PagerArgs) -> Result<()>` — 异步分发中枢。按 `args.command` 大 match 分流到 `run_agent_command`/`run_headless`/`run_leader`/`run_agent_server`/各 `*_cmd::run`；**无 command 的交互路径**在末尾构造 `bg_update_rx`（后台自动更新检查）后调用 **`xai_grok_pager::app::run(args, bg_update_rx).await`**。约第 2133 行；TUI 调用点在约第 2528 行。
- `run_agent_command(...) -> Result<()>` — `grok agent ...` 子命令实现：`spawn_signal_flush()` 起信号处理 → 构造 `AgentRuntime` → 按 `AgentCmd` 再分流（`Stdio`→`agent_command::run_stdio`、`Headless`、`Serve`、`Leader`）。约第 1227 行。
- `run_and_shutdown<F>(runtime, fut, grace) -> F::Output` — `block_on(fut)` 后 `shutdown_timeout(grace)`，防不可取消的 blocking task 卡死退出。约第 1870 行。
- `configure_process_env(mut args) -> Result<PagerArgs>` — 进 TUI 前把 CLI 选项写入进程环境（`GROK_COMPACTION_MODE`、`GROK_CHAT_MODE`、leader socket、debug log…）。约第 1749 行。
- `cli_worker_threads()` / `worker_threads_from` / `resolve_worker_override` / `default_worker_threads` — 解析 `GROK_WORKER_THREADS`，越界 clamp、非法忽略；默认 `min(cores, 8)`。约第 1840/1846/1849 行。
- `flag_dashboard_at_startup_if_requested(args)` — `grok dashboard` → 设 `GROK_OPEN_DASHBOARD_AT_STARTUP=1` 并清 command。约第 1730 行。
- `finish_update_on_exit(adopted, update_config) -> bool` — TUI 以 `quit_for_update` 退出后等待/兜底执行更新安装。约第 2549 行。
- `run_update_blocking(update_config: &UpdateConfig) -> bool` — **新增**：Ctrl+U quit-for-update 的阻塞式安装封装（`finish_update_on_exit` 的兜底调用抽成此函数）。约第 2609 行。
- `is_opted_out_of_updates(no_auto_update_flag: bool) -> bool` — **新增**：`--no-auto-update` / `GROK_DISABLE_AUTOUPDATER` 的单一 opt-out 判据（`should_check_for_updates` 委托它）。约第 2626 行。
- `raise_fd_limit()` — 把 fd 软限提到硬限（macOS 8192 / 其他 65536），避免大量会话触发 `EMFILE`。约第 1701 行。
- `dispatch_version_if_requested` / `dispatch_doctor_if_requested` / `write_version` / `version_text` — 早期 `--version`/`doctor` 分流，避免起 runtime。约第 2013/2026 行。
- 合并样板：`process_identity`、`command_needs_pre_sandbox_policy_heal`、`apply_headless_args_to_config`、`apply_agent_endpoint_args`、`init_tracing_simple`、`should_check_for_updates`、`crash_dir_for`、`jemalloc_*` 系列钩子等（约第 53–2010 行散布）。

### 1.2 `crates/codegen/xai-grok-pager-bin/src/agent_command.rs`

`grok agent stdio` 的信号 + stdio 生命周期封装。

- `spawn_signal_flush() -> AgentSignals` — 装 `SignalStreams` 并 spawn 监听：收到信号（除非 `defer_exit` 置位）立即 `shutdown_and_flush_telemetry(code)`；随后给优雅收尾 `STDIO_SHUTDOWN_TIMEOUT`（30s），超时或再收一次信号则强退。约第 29 行。
- `run_stdio(runtime, agent_config, signals) -> Result<()>` — 置 `defer_exit=true`，用 `tokio::select!`（biased）在信号 oneshot 与 `runtime.run_stdio` 间竞争。约第 61 行。
- `struct AgentSignals` — 持 `defer_exit: Arc<AtomicBool>`、`received`（oneshot）、`cancel`（`CancellationToken`）、`_listener`（`AbortOnDropHandle`）；`Drop` 里 `cancel.cancel()`。约第 16 行。

### 1.3 `crates/codegen/xai-grok-pager/src/lib.rs`

TUI 库根，只做模块声明与 re-export，无运行逻辑。关键点：

- `pub mod app;`（第 15 行）— 本专题核心模块树。
- `pub use xai_grok_pager_render::{ appearance, clipboard, glyphs, host, input, link_opener, modal_window_state, prompt_images, render, search, syntax, terminal, theme, util }`（第 65 行）— **把 render crate 的整套表现原语再导出**，使 `xai-grok-pager` 内可写 `crate::render::…`/`crate::theme::…` 直达。
- `pub use xai_grok_pager_render::key;`（第 64 行）— 快捷键类型再导出。
- `#![deny(clippy::indexing_slicing)]`（第 11 行）— 全局禁用索引切片，逼所有下标走安全 API（配合渲染层的 `SafeBuf`）。

### 1.4 `crates/codegen/xai-grok-pager/src/app/mod.rs`

`app` 模块门面 + **进程级启动编排**。`run()` 是「main 之后、主循环之前」的全部装配。

核心类型：

- `pub(crate) enum ScreenMode { Fullscreen, Inline, Minimal }`（约第 386 行）+ `to_u8`/`from_u8`（第 396/403 行，供无参 teardown 记录）+ `is_fullscreen`/`is_minimal`/`meta_label`（第 410/414/420 行）。
- `pub(crate) struct ExitInfo { session_id, minimal, summary }` 与 `ExitSummary { title, last_prompt, last_response }`（第 466/476 行）— 退出后打印「Resume this session with…」所需。
- `pub(crate) struct TerminalInit { terminal, screen_mode, startup_typeahead }`（第 1492 行）— `init_terminal` 返回，含「raw mode 后、事件循环前」捕获的 type-ahead 按键。
- `enum CursorStylePolicy { Inherit, ForceBlinking, ForceSteady }`（第 1475 行）+ `cursor_style_policy`（第 1484 行）— `[ui].cursor_blink` 三态映射。
- `pub struct LeaderMode<'p> { use_leader, policy_disable_reason, disabled_by_confinement }`（第 541 行）。
- `pub(crate) mod voice_state;`（第 50 行，**新增**）— 语音（口述）状态机的新宿主模块（原在 `app_view.rs`，见 §1.6）；模块 re-export 新增 `CancelMeta`（第 58 行）。

关键函数：

- `pub async fn run(args: PagerArgs, bg_update_rx) -> anyhow::Result<bool>` — **TUI 总编排**：读配置 → 预取 remote settings（`EARLY_PREFETCH_WAIT`）→ `session_startup::materialize_startup` → 解析 screen mode → `spawn_writer_thread` → `init_terminal` → `apply_screen_mode_globals` → `bounded_connect`（leader 失败回退 embedded）→ 组 `TerminalState` → **`event_loop::run(...)`** → `restore_terminal` → 处理 `RunResult`。返回 `Ok(true)` 表示需为更新退出。约第 707 行；调用 `event_loop::run` 约第 1187 行。
- `async fn bounded_connect(cancel, timeout, connect_ui_timeout_env, target, attempt, timer, connect) -> Result<AcpConnection, ConnectFailure>` — 有界连接：`tokio::select!`（biased）在 cancel / 连接完成 / 分片 sleep 间竞争；支持 launch-profile 升级后**延长预算**；超时把 phase snapshot 打包成 `StartupFailure`。约第 620 行。
- `fn init_terminal(mode, minimal_live_rows, clear_main_screen, frame_tx, writer_sync, cursor_blink) -> io::Result<TerminalInit>` — **终端初始化核心**：`enable_raw_mode` → 清屏/`EnterAlternateScreen`（fullscreen）→ `EnableMouseCapture`/`EnableFocusChange`/`EnableBracketedPaste`/光标样式 → `set_panic_hook()` + `signal_handler::install(mode)` → kitty keyboard 协商 push → 多次 `capture_startup_typeahead` 抓 type-ahead → 按模式构造 `PagerTerminal`（inline/minimal 探测 `Viewport::Inline`，失败降级 `Viewport::Fixed`）。失败时 `.inspect_err` 跑 teardown 序列。约第 1503 行。
- `fn apply_screen_mode_globals(screen_mode)` — 把模式写进 `CURRENT_SCREEN_MODE`/`MINIMAL_MODE_ACTIVE` 等进程级原子，并同步 `image`/`modal_window`/`scrollbar`/`theme::cache` 的 minimal 开关。约第 431 行。
- `fn engage_startup_theme(screen_mode)` / `fn finish_theme_after_probe(requested_minimal, effective_mode)` — 两阶段启动主题握手：阶段 1 在 `init_terminal`（读 `apply_cursor_color`）前解析初始主题；阶段 2 处理「`--minimal` 被探测降级为 Inline」时补解析常规主题。约第 442/454 行。
- `fn seed_remote_ui_caches(remote_settings)` — 用 remote settings 播种 auto-mode / prompt-suggestions / campaigns 缓存。约第 484 行。
- `pub fn resolve_leader_mode(...) -> LeaderMode` / `pub fn resolve_use_leader(...) -> (bool, Option<&'static str>)` — leader 决策与优先级（`--no-leader` > `--leader` > 资格 > config > remote > 默认 off），`requested_confinement` 可否决。约第 499/551 行。
- `pub(crate) fn push_gboom_keyboard_flags(writer)` / `pop_gboom_keyboard_flags(writer)` / `pop_gboom_keyboard_flags_inline()` — `/gboom` 游戏额外 kitty 键盘层（需 WASD release）的 push/pop；inline 变体供 teardown/panic 路径。约第 116/126/133 行。
- `pub(crate) fn set_current_screen_mode(mode)` / `current_screen_mode()` / `minimal_mode_active()`（第 166/170/179 行）— 无参可读的进程级状态。
- `pub(crate) fn resolve_dock_enabled` / `resolve_terminal_theme_enabled` / `resolve_voice_mode_enabled` / `resolve_voice_mode_live`（第 214/240/283/320 行）— feature 开关的「pin/env/config/remote/默认」优先级解析；`resolve_voice_mode_enabled` 现叠一层 distribution 能力门（`Distribution::allows(Capability::Voice)`），实现委托给**新增**的私有函数 `resolve_voice_mode_enabled_as(distribution, requirement, config, remote, is_api_key) -> bool`（第 297 行）。
- `fn print_exit_resume_hint(info, max_width, w)` / `fn print_relaunch_failure_hint(...)` — 终端恢复后的纯文本收尾。约第 1283/1308 行。
- `pub(crate) fn set_terminal_title(title)` / `fn terminal_title_string(title)` — 设置窗口标题；后者剥离控制字符防 OSC 注入并截断到 80 列。约第 1706/1715 行。

### 1.5 `crates/codegen/xai-grok-pager/src/app/event_loop.rs`（主循环）

**全系统最热的文件**：一个 `biased` `tokio::select!` 大循环，轮询终端输入、ACP 消息、后台任务完成、渲染定时器、信号、配置热重载。

> 本节是**逐函数清单**（签名、字段、行位、单条语义）。若要的是「为什么这么切」——同步 dispatch / 异步 effects 的可单测契约、27 臂 `biased` 序的防饥饿论证、写队列背压闭环与失败路径——读[第 8 篇《TUI 交互循环与渲染》](../sourceReader/08-TUI交互循环与渲染.md)。本节引用的 `Presenter` 方法组、`drain_and_process`、`process_effects` 与 select 臂顺序已在 `HEAD = 42f4d7d3` 复核过（`WriterProgress` 490 / `struct Presenter` 500 / `impl` 516 / `drain_and_process` 3200 / `process_effects` 3952 五处行位当时均命中），其余「约第 N 行」仍是 `7d70d52c` 快照。

核心类型：

- `pub(crate) struct TimedInputEvent { event: Event, arrived_at: Instant }`（约第 41 行）— 带到达时间戳的终端事件，用于卡顿测量。
- `pub(crate) struct TerminalState { is_control_mode, screen_mode, relaunched_into_minimal, relaunched_into_fullscreen, initial_theme, startup_typeahead }`（第 214 行）。
- `pub(crate) struct RunResult { exit_info, quit_for_update, trust_quit_error, relaunch }`（第 228 行）— 交给 `mod::run` 决定退出/更新/relaunch。
- `struct Presenter { dirty, force_full_repaint, in_flight_target, writer_stalled_since, last_written_observed, blocked_reported, last_draw_at, draw_scheduled_at }`（第 500 行）— **绘制节奏与背压控制器**。
- `enum WriterProgress { Flowing, Stalled, Recovered }`（第 490 行）。
- `struct DrainResult { needs_draw, should_quit, resize_only, force_repaint, handled }`（第 3140 行）。
- `struct RoutedInputEvent { event, arrived_at, paste_provenance, is_startup_replay }`（第 3154 行）。

主循环与分发：

- `pub(crate) async fn run(terminal, connection, pending_startup, tracing_handle, config_watcher, args, session_cwd, remote_settings, term_state, materialized, bg_update_rx, writer_event_rx, reader_thread) -> anyhow::Result<RunResult>` — **主入口**。构造 `AppView::new`、灌入 remote settings/CLI/auth 状态、`ReaderThread::spawn` 起 stdin 读线程、建 `JoinSet<TaskResult>` 任务集、`SessionLoadBarrier`、progress 通道；处理启动动作（`materialize` → `LoadSession`/`NewSession`/`NewWorktreeSession`/fork）、initial prompt、dashboard 启动钩子；然后进 `loop { ... tokio::select! { ... } }`，循环顶做 load-barrier drain、workspace sync、`run_pending_suspends`、`run_pending_mode_switch`、voice 冷启动、gboom 键盘层同步；循环尾 `present_if_dirty` + `schedule_tick`。循环顶另调 `app.voice_expire_outstanding_clip(Instant::now())`（约第 1974 行，**新增**，清理超时的语音剪辑）。约第 1034 行；主循环 `loop {` 约第 1868 行，`tokio::select!` 约第 2126 行。
- `Presenter` 方法组（约第 516–652 行）：
  - `acknowledge(sequence) -> bool`（第 530 行）— writer 事件序号覆盖 in-flight target 时清门闩。
  - `observe_writer_progress(queued, written, now) -> WriterProgress`（第 542 行）— 每轮读 writer 队列水位；积压且零写入推进则起/续 stall episode。
  - `blocked_report_deadline()`（第 566 行）/ `mark_blocked_reported()`（第 574 行）— 超 `WRITER_BLOCKED_WARN_AFTER`(5s) 上报一次「终端不再读 pty」。
  - `try_present(written, queued_before, draw, queued_after) -> bool`（第 579 行）— 只有脏且上一帧已被覆盖才真正 draw。
  - `request(force_full_repaint)` / `request_throttled(now, min_draw_interval) -> bool`（第 601/606 行）— 标脏并（可选）限速，防 ACP 洪流饿死输入。
  - `present_if_dirty(app, terminal)`（第 620 行）/ `request_presentation(app, terminal, force)`（第 642 行）。
- `async fn drain_and_process(first, input_rx, app, tasks, progress_tx, csi_filter, x10_filter, xt_filter, live_input_started_at) -> DrainResult` — **输入批处理核心**。先 `drain_immediate` 抓同批事件，按 `live_input_started_at` 切分 startup/live；`xt_filter`/paste 探测/`coalesce_live_keys`/`merge_paste_fragments` 归一；然后逐事件走闭包 `handle_one`：FocusGained/FocusLost 特判、voice chord 特判、否则 **`app.handle_input_at_with_paste_provenance`** → 按 `InputOutcome`（Action / ActionThenForward / ActionPair / Changed / ArmPending / Unchanged）派发。约第 3200 行；`handle_one` 约第 3245 行。
- `pub(crate) fn dispatch_then_forward(action, event, arrived_at, paste_provenance, app) -> Vec<Effect>` — 先 `dispatch::dispatch(action)`，再把同一事件重喂给（已变化的）视图；若仍在 Welcome 则落到 welcome composer。约第 3924 行。
- `fn process_effects(effs, tasks, app, progress_tx) -> bool` — **Effect → 异步任务**执行器：算 `session_flags_for_effects`，逐个 `effects::take_coalesced_interjects` + `effects::execute`，回填 auth abort/url-poll handle；返回 `true` 表示应退出。约第 3952 行。
- `fn finish_run(app) -> RunResult`（第 3110 行）/ `finish_run_with_stall_flush(app, stall_rollup)`（第 3101 行）— 退出漏斗：`abandon_startup` + 构造 `ExitInfo`（fullscreen 才有摘要），并 flush 未落盘的 stall window。
- `pub(crate) fn schedule_tick(tick_at, app, interval)` — 按 `app.tick_demand()`（None/Fast/Slow）决定是否及以何间隔安排下一动画 tick。约第 3068 行。
- `fn after_task_complete_dispatch(...)` — `TaskComplete` 后统一 bookkeeping：重排 tick、清 resize debounce、按 `billing_poll_wanted`/`has_access` 开关轮询定时器、请求绘制。约第 3042 行。
- `fn normalize_input_event(timed, live_input_started_at) -> RoutedInputEvent`（第 3163 行）— 标 `is_startup_replay`；Linux 上把「无修饰中键 Down」转成 `Event::Paste`（X11 PRIMARY）。`fn normalize_startup_event`（第 168 行）类似。
- `fn suspend_for_child(screen_mode, terminal, input_paused, reader_parked, input_rx, run_child) -> io::Result<Option<(u16,u16)>>`（第 398 行）— **tty 让渡**：`park_input_reader` 停读线程 → `writer_sync.wait_drained` → pop kitty/mouse/paste/focus → `disable_raw_mode` → `run_child()` → 反向恢复 → 清残留事件。
- `fn run_pending_suspends(...) -> anyhow::Result<()>`（第 762 行）— 消费 `app.pending_editor`/`app.pending_pager_path`，经 `suspend_for_child` 拉起 `$EDITOR`/`$PAGER`（ansi 时给 less 加 `-R +G`），超时则 requeue + `defer_suspend_retry` + 上报。`fn run_pending_mode_switch(...) -> bool`（第 912 行）— 消费 `app.pending_screen_mode_switch`，调 `mode_switch::transition_terminal`，失败走 `NeedsExecFallback`（设 `app.relaunch` 并返回 true 让循环退出）。
- 卡顿检测接线：`fn emit_event_loop_stall(window)`（第 3091 行）→ `session_ctx::log_event(event_loop_stall_event(window))`；`fn flush_pending_stall(stall_rollup)`（第 3096 行）。循环内 `stall_rollup.observe(...)`（输入 arm，约第 2341 行）与 `take_if_elapsed`（循环尾，约第 2944 行）。
- 启动 type-ahead：`pub(super) fn capture_startup_typeahead(poll_timeout) -> Vec<TimedInputEvent>`（第 178 行）、`normalize_startup_submissions`（第 93 行）、`replay_startup_typeahead`（第 194 行）、`filter_startup_typeahead`（第 80 行）、`is_typeahead_event`/`is_startup_submission_enter`（第 56/74 行）。
- 输入合并：`coalesce_rapid_keys`/`coalesce_rapid_keys_since`（第 3591/3600 行）、`coalesce_live_keys`（第 3610 行，处理无 bracketed paste 的终端粘贴）、`merge_paste_fragments`（第 3726 行）、`detect_paste`（第 3452 行）、`collect_remaining_paste`（第 3471 行）、`should_extend_for_paste`（第 3445 行）。
- voice chord：`voice_chord_action`（第 3545 行）、`voice_chord_claims_event`（第 3569 行）、`is_voice_chord`（第 3578 行）、`active_feedback_modal_open`（第 3539 行）。**voice arm 现调 `crate::voice::handle_tagged_voice_event(&mut app, ev)`**（第 2911 行；定义在 `voice/handle.rs`），事件类型改为 `TaggedVoiceEvent`（带会话戳，`voice_rx` 类型相应变为 `Receiver<TaggedVoiceEvent>`，约第 1649 行）。
- `pub(crate) fn load_initial_ui_config() -> UiConfig` — 进程级只读一次 `[ui]`（`OnceLock`）。约第 2963 行。

**`select!` 各 arm（`biased` 顺序即优先级，约第 2126–2943 行）**：

1. `connection_cancel.cancelled()` — leader 断开
2. `quit_notify.notified()` — 信号优雅退出，dispatch `Action::Quit`
3. `writer_event_rx.recv()` — writer ack/失败，`presenter.acknowledge`
4. `writer_blocked_report` — 上报 blocked
5. **自限定时器组（已上移到 ACP 之上）**：`scroll_tick`（门控 `if input_rx.is_empty()`，第 2192 行）/ `deferred_draw`（2200）/ `animation_tick`（2205）/ `resize_debounce`（门控，2244）/ `status_line_refresh`（2250）
6. ACP `msg` — `acp_handler::handle` + 立即 drain 一批（`if input_rx.is_empty()` 门控防饿死，第 2276 行）
7. `tasks.join_next()` — `TaskResult` → `dispatch` + `after_task_complete_dispatch`
8. `progress_rx.recv()` — restore 进度
9. `bg_update_rx` — 后台更新
10. `input_rx.recv()` — **终端输入 → `drain_and_process`** ★输入主路径
11. `stall_flush` / `suspend_retry` / `billing_poll` / `gate_poll` / `subscription_watch` / `dashboard_poll` / `recap_poll` / `load_barrier_tick` — 慢轮询
12. `config_watcher.changed()` — 热重载
13. `appearance_watcher.changed()` — 系统主题
14. `leader_status_rx` — 重连：re-init + 逐 agent reload
15. `reconnect_reinit`
16. `voice_rx` — **故意放最后**，防饿死

> **biased 优先级是显式设计**（源码注释原文）：cancel/quit > writer ack/失败 > blocked-writer 上报 > **定时器** > ACP > 任务/进度结果 > 更新 > 输入 > 慢轮询 > voice（最后）。
>
> ⚠️ **与旧版的差异**：`scroll_tick`/`deferred_draw`/`animation_tick`/`resize_debounce`/`status_line_refresh` 这五个自限定时器 arm 已**上移到 ACP 之上**——源码注释：重流下 `acp_rx` 几乎每轮就绪，会饿死其下方的 arm。`input_rx` 仍保持在 ACP **之下**（用门控而非重排，避免把饥饿方向翻转成「流式重绘饿死按键」）。

### 1.6 `crates/codegen/xai-grok-pager/src/app/app_view.rs`（根状态机）

**根组件 `AppView`**：持有全部会话、视图、输入、渲染、后台任务句柄；`handle_input` 做输入路由，`draw_inner` 做绘制，`tick` 做动画。

核心类型：

- `pub struct AppView { ... }`（第 499–1102 行，约 234 个 `pub` 字段）— 字段分组：
  - **会话/Agent**：`agents: IndexMap<AgentId, AgentView>`、`next_agent_id`、`active_view: ActiveView`、`auth_return_view`、`home_session_agent`/`optimistic_home_husk`、`active_agent()`/`home_session()`（第 1821/1828 行）。
  - **视图/overlay**：`dashboard`/`dashboard_return`/`dashboard_session_picker`、`tutorial`、`welcome_doc_viewer`、`import_claude_modal`、`new_worktree_dialog`、`session_picker_*`、`minimal_state`。
  - **输入**：`registry: ActionRegistry`、`pending_action: Option<PendingAction>`、`keyboard_normalizer`、`scroll_state`/`scroll_config`、`last_mouse_pos`/`last_scroll_pos`、大量 welcome hit-rect、`slash_mru`/`command_tags`。
  - **渲染/外观**：`scratch`、`cursor`、`appearance`、`current_ui`、`status_line`、`pending_notification_escapes`、`escape_writer`、`screen_mode`/`pending_screen_mode_switch`、`welcome_tick`/`welcome_shimmer_frame`、`fps_hud`/`scroll_debug_hud`。
  - **后台任务/通道**：`acp_tx`、`pending_effects`、`tracing_rx`、`notification_service`、`voice_*`、`pending_editor`/`pending_pager_path`、`auth_url_poll_handle`、`shared_prompt_queues`/`optimistic_prompt_echoes`。
  - **认证/权限/门禁**：`auth_state`/`auth_methods`/`trust_state`/`consent_state`、`is_zdr`/`zdr_access_enabled`、`gate`/`subscription_tier`/`pending_gate_verification`、`default_yolo`/`permission_mode_from_soft_default`/`yolo_policy_block`/`plan_mode`/`subagents`/`ask_user`。
  - **🆕 发行 / 登出 / voice 字段**（本次漂移新增）：`logout_pending: bool`（第 933 行）、`distribution: xai_grok_config::Distribution`（第 1077 行）、`voice_session: xai_grok_voice::VoiceSessionId`（第 1095 行）、`voice_trailing_final: Option<(VoiceSessionId, VoiceTarget)>`（第 1098 行）、`voice_clip_deadline: Option<Instant>`（第 1101 行）。
- `pub enum ActiveView { Welcome, Agent(AgentId), AgentDashboard }`（第 207 行）+ `agent_id()`（第 215 行）。
- `pub enum InputOutcome { Action, ActionThenForward, ActionPair, ArmPending{...}, Changed, Unchanged }`（第 355 行）— **输入处理结果契约**，事件循环据此决定 dispatch/重投/重绘。
- `pub enum AuthState { Done, Pending{error}, Authenticating{request_seq, handle, auth_url, mode} }`（第 308 行）、`pub enum AuthMode`（第 328 行）、`pub enum TrustState { Done, Pending{workspace} }`（第 342 行）。
- `pub enum TickDemand { None, Fast, Slow }`（第 248 行）。
- ⚠️ **voice 状态类型已迁出本文件**：`VoiceTarget` / `Partial` / `VoiceState` 现位于 `app/voice_state.rs`（第 24 / 39 / 65 行），本文件仅以 `pub use crate::app::voice_state::{Partial, VoiceState, VoiceTarget};`（第 9 行）再导出；`voice_state: VoiceState` 仍是 `AppView` 字段（第 1092 行）。
- `pub(crate) enum PasteProvenance { Terminal, X11Primary }`（第 381 行）。
- `pub struct PendingAction { action, shortcut, label, expires_at }`（第 396 行）+ `with_ttl`/`expired` — 双击确认（quit 等）。

关键函数：

- `pub fn new(acp_tx, models, bootstrap_acp_commands, escape_writer) -> AppView`（第 1341 行）— 构造根状态；初始化 registry、welcome prompt、settings registry、scratch/cursor。⚠️ 第三参数已由 `available_commands` 改名为 `bootstrap_acp_commands`。
- `pub fn handle_input(&mut self, ev: &Event) -> InputOutcome`（第 2220 行）— 便捷入口，转调下面的方法（`Instant::now()` + `PasteProvenance::Terminal`）。
- `pub(crate) fn handle_input_at_with_paste_provenance(&mut self, ev, arrived_at, paste_provenance) -> InputOutcome`（第 2223 行）— **输入路由入口**。顺序：`keyboard_normalizer.rescue` → Resize 记账（`note_terminal_resize` + `apply_effective_compact`）→ 双击 pending 匹配 → scroll 事件（`scroll_state.on_scroll_event_at` → `dispatch_scroll`）→ tutorial 拦截 → 按 `active_view` 分派：`Welcome` → `handle_welcome_input(...)`；`Agent(id)` → dashboard-overlay 键处理 + `AgentView` 输入 + modal → 最后对 quit/exit-session/new-session 做确认包装 → 未消费则 `handle_unconsumed_input`。
- `fn handle_unconsumed_input(&mut self, ev, key_event, scope) -> InputOutcome`（第 2855 行）— Resize 直接 `Changed`；`registry.lookup(key, When::Always)` → `handle_global_action`；`Ctrl+C`/`Ctrl+D` 在 agent 视图上 arm quit 双击确认。
- `fn handle_global_action(&mut self, action_id, key) -> InputOutcome`（第 2887 行）— 全局动作（quit 等），按 registry 的 `requires_confirmation` 决定是否转 `ArmPending`。
- `fn apply_quit_confirmation(&mut self, key_event) -> InputOutcome`（第 2933 行）/ `fn apply_exit_session_confirmation(...)`（第 2953 行）— quit / exit-session 的二次确认落地。
- `fn handle_welcome_input(ev: &Event, ctx: &mut WelcomeInputCtx<'_>) -> InputOutcome`（第 3078 行）— **Welcome 视图输入大分发**（独立函数 + `WelcomeInputCtx` 借用束，第 2979 行）：处理 auth 流程、trust/consent 菜单、session picker、import modal、changelog、worktree dialog、menu 导航/快捷键。配套 `handle_menu_shortcuts`/`handle_menu_nav`（第 3975/3997 行）、`dispatch_menu_action`（第 4051 行）。
- `fn dispatch_scroll(&mut self, lines, column, row)`（第 2130 行）— 把滚动增量经 hit-test 派发到对应 pane。
- `pub fn draw(&mut self, terminal: &mut PagerTerminal)`（第 4225 行）— `draw_inner` + `record_first_draw` + `run_deferred_release`。
- `fn draw_inner(&mut self, terminal: &mut PagerTerminal)`（第 4230 行）— **绘制核心**。minimal 走 `minimal_hook`；否则 `sync_native_selection_mouse`、dock reconcile、各类 tip 触发、收集一次性渲染参数，最后调 `crate::render::draw::draw_frame(terminal, cursor, terminal_context, |f, link_spans| { ... })`，内部按 `active_view` 分派 Welcome / Agent / AgentDashboard 的具体渲染。
- `pub fn tick(&mut self) -> bool`（第 5199 行）— **动画/定时 tick**：minimal frames、剪贴板 tip、welcome shimmer/loading、dashboard tick、pending_action 过期、tracing drain、逐 agent 的 `edit_hl_tick`/scrollback/todo/tasks/spinner tick、block viewer/image load tick，返回是否需要重绘。`pub(crate) fn tick_scroll(&mut self) -> bool`（第 5431 行）— 滚动残量 flush（16ms cadence）。
- `pub fn needs_animation(&self) -> bool`（第 5546 行）/ `pub fn tick_demand(&self) -> TickDemand`（第 5552 行）/ `fn view_tick_demand(&self)`（第 5555 行）— 决定动画 tick 是否/多快运行（供 `schedule_tick`）。
- `pub fn update_notifications(&mut self)`（第 5709 行）— 每帧刷新通知（bell/OSC/标题），累积 `pending_notification_escapes`。
- `pub fn apply_contextual_hints`（第 5049 行）、`pub(crate) fn poll_clipboard_focus_tip(&mut self) -> bool`（第 5152 行）、`pub fn show_toast(&mut self, msg)`（第 1852 行）、`pub fn set_appearance`（第 2034 行）、`pub(crate) fn apply_effective_compact(&mut self)`（第 2055 行）。
- **voice 相关（保留在 `app_view.rs` 的部分）**：`voice_available`（第 1621 行）、`voice_can_start_pipeline`（第 1627 行）、`apply_voice_mode_enabled`（第 1632 行）、`voice_target_on_active_surface`（第 1733 行）、`enforce_voice_session_bound`（第 1766 行）、`voice_esc_outcome`（第 1776 行）、`maybe_commit_voice_interim_before_submit_key`（第 1798 行）。⚠️ **真正的状态转移方法已搬到 `app/voice_state.rs`**：`voice_queue_cold_start`(:197)、`voice_begin_recording`(:204)、`voice_expire_outstanding_clip`(:235)、`voice_set_route`(:252)、`voice_set_interim`(:264)、`voice_commit_interim`(:282)、`voice_stop_keeping_final`(:293)、`voice_mark_transcribing`(:319)、`voice_capture_cancelled`(:347)、`voice_finish_transcribing`(:355)、`voice_reset`(:365)、`voice_hold_release`(:382)；查询谓词 `is_listening`/`is_pending_cold_start`/`is_transcribing`/`is_hold_owned`/`target`/`interim`/`owes_final`/`is_on_clip_route`/`blocks_new_capture` 亦在其中。
- 认证/权限同步：`apply_auth_meta`（第 1253 行）、`apply_tier_restrictions`（第 1671 行）、`sync_permission_mode_slash_gate`（第 1658 行）、`sync_billing_surface_to_agents`（第 1302 行）、`sync_session_announcement_slash_gate`（第 1717 行）。
- 状态门禁：`pub fn session_startup_allowed(&self) -> bool`（第 1223 行）、`pub fn ready_for_startup_typeahead(&self) -> bool`（第 1231 行）、`is_zdr_blocked`/`has_access`/`is_access_blocked`（第 1143/1147/1151 行）。

**输入分发链路**：

```
handle_input → handle_input_at_with_paste_provenance
  ├─(Welcome) handle_welcome_input
  └─(Agent)   AgentView 输入 + registry.lookup
        └─► InputOutcome::Action(...)
              └─► event_loop::drain_and_process.handle_one
                    └─► dispatch::dispatch(action, app)      // dispatch/router.rs · dispatch(+0) / dispatch_inner(+0)
                          └─► Vec<Effect> → process_effects → effects::execute  // app/effects/mod.rs · execute(+0)
```

### 1.7 reader_thread / terminal_restore / event_loop_stall / startup

**`app/reader_thread.rs`** — stdin 读线程所有者，保证 teardown 时它是唯一 stdin 读者。

- `pub(crate) struct ReaderThread { handle: Option<JoinHandle<()>> }`（第 34 行）+ `detached()`（第 39 行）。
- `pub(crate) fn spawn(tx: UnboundedSender<TimedInputEvent>, paused: Arc<AtomicBool>, parked: Arc<AtomicBool>) -> ReaderThread`（第 45 行）— 起线程：循环检查 `tx.is_closed()`；`paused` 时置 `parked` 并 sleep `POLL_TIMEOUT`(20ms) 让出 tty；否则 `crossterm::event::poll(POLL_TIMEOUT)` + `read()`，成功则 `TimedInputEvent::now(ev)` 发送；连续 50 次解析错误才退出。
- `pub(crate) fn join_within(self, grace) -> ReaderJoin`（第 103 行）— 有界 join：轮询 `is_finished()`，超 `grace` 则 detach 并返回 `TimedOut`（绝不 join 仍阻塞在 `read` 的线程）。
- `enum ReaderJoin { Joined, TimedOut, Absent }`（第 26 行）、`READER_JOIN_GRACE`（第 16 行，250ms）、`POLL_TIMEOUT`（第 21 行，20ms）。

**`app/terminal_restore.rs`** — 终端拆除（teardown）共享模块：被主循环后的 restore、panic hook、信号路径复用。

- `pub(super) fn restore_terminal(terminal, writer_thread, reader_thread, mode) -> io::Result<WriterJoin>`（第 189 行）— **主循环退出后的标准恢复**。先读 `kitty_flags_pushed()`，再调 `restore_terminal_with`，fence 闭包构造 `TeardownFence { reader, writer_timed_out, flags_pushed }.run()`。
- `fn restore_terminal_with(terminal, writer_thread, reader_thread, mode, drain, teardown, fence) -> io::Result<WriterJoin>`（第 143 行）— 通用恢复骨架：先 `reader_thread.join_within` → fullscreen 清屏 → 捕获 `inline_cursor_row` → `drain(...)`；writer join 超时则用 `run_bounded_teardown` 有界执行 teardown，否则直接 teardown → `fence(...)` → `disable_raw_mode` → `signal_handler::mark_restored()` → `disable_terminal_escape_restore` → `restore_native_stderr` → `report.record()`。
- `pub(super) fn emit_terminal_teardown_sequences(mode, inline_cursor_row)`（第 61 行）— **在线上字节序唯一定义处**：清 OSC 9;4 进度条 → `EndSynchronizedUpdate` → reset cursor color → `disable_mouse_paste_raw` →（若曾启用）`DisableMouseCapture`/`DisableFocusChange` → `pop_gboom_keyboard_flags_inline` → 条件 `PopKeyboardEnhancementFlags` → 恢复光标样式（仅 `CURSOR_STYLE_FORCED` 时）→ fullscreen `LeaveAlternateScreen` / inline 移到 `inline_cursor_row` →（Windows）`restore_stdin_mode`。**不调用 `disable_raw_mode`**。
- `fn drain_writer_thread_before_teardown(terminal, writer_thread) -> io::Result<WriterJoin>`（第 32 行）— drop terminal 后 `writer_thread.join_within(WRITER_JOIN_GRACE)`(2s)；超时记 `term.writer.join_timeout`。
- `fn run_bounded_teardown(f: impl FnOnce() + Send + 'static, grace)`（第 217 行）— 在 helper 线程跑 teardown 并最多等 `grace`；stderr 锁可能已卡死时防永不返回；spawn 失败则 inline 执行。
- `pub(super) fn set_panic_hook()`（第 243 行）— 装 panic hook：`run_bounded_teardown(emit_terminal_teardown_sequences(current_screen_mode(), None))` → `disable_raw_mode` → `mark_restored` → `restore_native_stderr` → `kill_all` → `record_crash_sample` → 原 hook。**必须在 panic 时现读 `current_screen_mode()`**，不能捕获。

**`app/event_loop_stall.rs`** — 主循环卡顿检测：把「事件从到达到被处理」的最大延迟按 60s 窗口滚动上报 telemetry。

- `pub(crate) const STALL_REPORT_WINDOW: Duration = 60s`（第 5 行）。
- `pub(crate) struct StallActivity { compaction_active, subagents_active, mcp_servers_connected }`（第 8 行）+ `read()`（第 15 行）— 从 telemetry gauge 快照当前后台活动，给 stall 归因。
- `pub(crate) fn input_wait(arrived_at, handled_at, loop_entry) -> Duration`（第 44 行）— 等待时长 = `handled_at - max(arrived_at, loop_entry)`（避免 startup 事件虚高）。
- `pub(crate) struct StallRollup { window, window_started_at, max_stall, max_stall_activity, count }`（第 55 行）— **只保留窗口内最差一次 stall** + 该时刻活动快照 + 事件计数。`observe(...) -> Option<StallWindow>`（第 75 行，首次 observe 才开窗，超窗则 flush）、`take_if_elapsed(now)`（第 95 行）、`take()`（第 104 行）、`deadline()`（第 108 行）、`flush(now)`（第 112 行）。

**`startup.rs`** — 启动警告的显示契约（无 UI 逻辑），被 welcome banner 消费。

- `pub struct StartupWarning { severity, message, action }`（第 48 行）+ `pub enum WarningSeverity { Warning, Info }`（第 58 行）— `Warning` 渲黄、`Info` 渲暗。
- `pub(crate) struct ActionableStartupWarning { warning, ids }` + `new(...)`/`into_warning()`（第 8 行）— 关联 `/doctor` 诊断 ID 的可操作警告。
- `pub fn banner_warning(warnings: &[StartupWarning]) -> Option<&StartupWarning>`（第 68 行）— 单槽 banner 选取：优先第一个 `Warning`，否则取最后一条（最新 Info 是用户刚操作后的直接反馈）。

### 1.8 本子系统调用链总览

**进程启动 → 进 TUI**

```
main() → PagerArgs::parse_cli()
      → dispatch_version_if_requested(:2013) / dispatch_doctor_if_requested(:2026)   // 早退分支
      → configure_process_env()(:1749) → raise_fd_limit()(:1701)
      → cli_worker_threads()(:1825) → tokio runtime build
      → run_and_shutdown(runtime, async_main(args), RUNTIME_SHUTDOWN_GRACE)(:1870)
            → async_main(args)(:2133)
                 ├─ 子命令分流: run_agent_command()(:1227) / run_headless / run_leader / run_leader_mgmt(:335)
                 └─ 交互路径: 构造 bg_update_rx → app::run(args, bg_update_rx)
```

**TUI 装配 → 主循环**

```
app::run()
  → seed_remote_ui_caches(:484) / resolve_leader_mode(:499) / resolve_voice_mode_*
  → session_startup::materialize_startup
  → screen_mode_relaunch::resolve_screen_mode
  → render::draw::spawn_writer_thread
  → init_terminal(:1503)                // raw / alt-screen / mouse / kitty / set_panic_hook / signal_handler::install
  → apply_screen_mode_globals(:431) / engage_startup_theme(:442) / finish_theme_after_probe(:454)
  → bounded_connect(:620) → acp::connect | connect_via_leader
  → TerminalState { .. } → event_loop::run(...)(:1034)
```

> **`resolve_voice_mode_*` 三件套**（`app/mod.rs`）：`resolve_voice_mode_enabled`(:283) 为公开入口，转调纯函数 `resolve_voice_mode_enabled_as(distribution, requirement, config, remote, is_api_key) -> bool`(:297)；`resolve_voice_mode_live(remote, is_api_key) -> bool`(:320) 供运行期实时查询。

**主循环内部（每轮）**

```
loop {
  SessionLoadBarrier::take_ready()   → dispatch(TaskComplete)
  workspace_sync::drain()            → process_effects()
  run_pending_suspends()             → suspend_for_child()      // $EDITOR / $PAGER
  run_pending_mode_switch()          → mode_switch::transition_terminal()
  tokio::select! {  /* 见 1.5 的 arm 列表 */ }
  stall_rollup.take_if_elapsed() → emit_event_loop_stall()
  process_effects(app.pending_effects)
  presenter.present_if_dirty(&mut app, terminal)
  schedule_tick(&mut animation_tick_at, &app, tick_interval)
}
→ flush_pending_stall() → finish_run(app) → RunResult
```

**退出 / 恢复 / 卡顿**

```
break → flush_pending_stall()(:3096) → finish_run_with_stall_flush()(:3101) → finish_run()(:3110) → RunResult
  → app::run(): exit_timeout::arm(code)
  → restore_terminal(terminal, writer_thread, reader_thread, current_screen_mode())
       → restore_terminal_with()
            → reader_thread.join_within(READER_JOIN_GRACE)
            → drain_writer_thread_before_teardown() → WriterThread::join_within(WRITER_JOIN_GRACE)
            → emit_terminal_teardown_sequences() → run_bounded_teardown() [writer 超时/panic 时]
            → TeardownFence::run() → disable_raw_mode() → signal_handler::mark_restored()
            → restore_native_stderr()
  → 处理 RunResult: 更新 / relaunch(exec) / resume 提示(print_exit_resume_hint)
       └─ 更新路径: finish_update_on_exit()(:2549) → run_update_blocking()(:2609)
            └─ 门禁: is_opted_out_of_updates(no_auto_update_flag)(:2626)   // 未 opt-out 才重试阻塞式 `grok update`
```

---

## 2. 输入系统

覆盖 `crates/codegen/xai-grok-pager-render/src/input/*` 与 `terminal/{mod,keyboard,kitty_keyboard,probe,da2,xtversion}.rs`。链路：**终端字节流 → 键事件归一化 → 行编辑 / 鼠标滚动**，外加支撑它的终端能力探测。

### 2.1 `input/mod.rs`

模块聚合与再导出层，本身无逻辑。声明 `key`/`keyboard_normalizer`/`line_editor`/`mouse`/`terminal_support` 子模块，`scroll_log` 为 `pub(crate)`，`macos_modifiers` 仅 macOS 编译。再导出 `KeyboardNormalizer`、`ModifierState` 及 `terminal_support` 的一组探测谓词（`is_mod_enter`、`is_delivered_super_enter`、`is_apple_terminal_newline_modifier_held`、`suppress_os_modifier_rescue`）。约第 1–14 行。

### 2.2 `input/key.rs`

键位抽象基座：`KeyShortcut`（键码+修饰键）与 `key!()` 宏，贯穿整个快捷键匹配与展示。

- `KeyShortcut::new(code, modifiers) -> KeyShortcut`（约第 31 行）— 构造入口，立即 `normalize_case`。
- `KeyShortcut::normalize_case(self) -> Self`（约第 46 行）— 把 `Shift+小写` 与 `大写` 归一成同一快捷键（大写自动补 `SHIFT`），跨终端匹配一致性的关键。
- `KeyShortcut::matches(&self, event: &KeyEvent) -> bool`（约第 60 行）— 核心匹配谓词：Release 直接 false；对事件重新归一后比较 `code`/`modifiers`。被所有谓词与 `ActionRegistry` 查找调用。
- `KeyShortcut::to_key_event(self) -> KeyEvent`（约第 69 行）— 测试用 Press 事件。
- `display()`/`modifiers_prefix()`/`code_display()`/`write_modifiers_prefix()`/`write_code_display()`（约第 74–137 行）— 紧凑展示（`Ctrl+c`、`Opt+x`；macOS `Cmd+`/`Opt+`）。
- `display_pretty(&self) -> String`（约第 140 行）— 帮助/速查形式（`Ctrl+Shift+Q`，`Shift` 恒显，`BackTab` 额外注入 `Shift`）。
- `display_telemetry(&self) -> String`（约第 197 行）— 遥测标签，修饰键不本地化、字母大写。
- `is_letter_or_shift_letter(&self) -> bool`（约第 239 行）— 是否裸 ASCII 字母（仅可含 `SHIFT`）；被 `ActionRegistry::lookup_with_mode` 用于关闭 vim 模式时抑制 `ScrollbackFocused` 绑定。
- `is_paste_key(key) -> bool`（约第 251 行）— Ctrl+V / Cmd+V（Windows 额外 Alt+V，规避 WT 拦截）。
- `is_inline_paste_key(key) -> bool`（约第 264 行）— Ctrl+Shift+V / Cmd+Shift+V。
- `is_undo_key(key) -> bool`（约第 270 行）— 委托 `xai_ratatui_textarea::is_undo_input`，保证撤销弦与 textarea 行为不脱节。
- `is_altgr(modifiers) -> bool`（约第 277/283 行）— Windows 上 AltGr 以 `Ctrl+Alt` 到达。
- `shift_tab_keys() -> [KeyShortcut; 3]`（约第 289 行）+ `is_shift_tab(key)`（约第 299 行）— Shift+Tab 的三种编码（`BackTab`、`BackTab+SHIFT`、`Tab+SHIFT`）。
- `RowWalk::from_key(key) -> Option<Self>`（约第 312 行）— 仅接受裸 `Tab`/`Shift+Tab`。`RowWalk::step(self, idx, len) -> usize`（约第 325 行）— 两端环绕并在越界时先钳制；列表行游走核心。
- `is_text_input_key(key) -> bool`（约第 349 行）— 仅 `Char` 且修饰为空/`SHIFT`/AltGr 才算文本输入。
- `key!()` 宏（约第 371 行）— 语法糖，支持 `key!('c', CONTROL)`、`key!(Enter)`、`key!(F(5))`。

### 2.3 `input/keyboard_normalizer.rs`

跨终端修饰键「救援」层：当终端丢了 Cmd/Opt 位时，用 OS 侧探测补回。

- `struct ModifierState`（约第 10 行）— 物理修饰键快照（`command`/`option`/`shift`/`control`）。
- `trait ModifierProbe { fn snapshot(&self) -> ModifierState }`（约第 18 行）— 便于测试注入 mock。
- `struct OsModifierProbe` + `impl ModifierProbe`（约第 24–36 行）— 生产探测：macOS 走 `macos_modifiers::snapshot()`，其他 OS 全 false。
- `struct KeyboardNormalizer<P> { probe, delivery: ModifierDelivery }`（约第 42 行）— 一个实例挂在 `AppView` 上，在 `handle_input` 顶部调用。
- `KeyboardNormalizer::rescue_key(&self, key: KeyEvent) -> Option<KeyEvent>`（约第 55 行）— **核心**：先把裸 `\u{0002}`（Ctrl+B 原始字节）规范化为 `Char('b')+CONTROL`（无条件）；随后仅当 `delivery.benefits_from_rescue()` 且未被抑制、事件无修饰、且是 `Backspace`/`Delete` 时才查 OS 快照，Cmd 优先补 `SUPER`，否则 Opt 补 `ALT`。仅当事件确实改变时返回 `Some`。
- `KeyboardNormalizer::rescue<'a>(&self, ev: &'a Event) -> Cow<'a, Event>`（约第 94 行）— 事件级包装：命中救援才 `Cow::Owned`，否则借用。被 `AppView::handle_input_at_with_paste_provenance` 首行调用。
- `KeyboardNormalizer::from_terminal_context() -> Self`（约第 105 行）— 从 `terminal_context().keyboard_capabilities().modifier_delivery` 构建。

### 2.4 `input/line_editor.rs`

单行输入编辑器：薄封装 `xai_ratatui_textarea` 的 `EditBuffer`，把键事件翻译成 `EditCommand`。

- `enum LineEditOutcome { Unhandled, HandledNoChange, CursorChanged, TextChanged }`（约第 7 行）。
- `struct LineEditor { buffer: EditBuffer }`（约第 16 行）。
- `text()`/`cursor_byte()`/`set_text()`/`reset()`（约第 21–35 行）— 基础读写；`set_text` 经 `sanitize_single_line`。
- `set_cursor_byte(cursor_byte) -> LineEditOutcome`（约第 38 行）。
- `delete_last_grapheme(&mut self) -> LineEditOutcome`（约第 42 行）— 忽略光标先移行尾，再 `DeleteGraphemeBackward`（按字素簇删）。
- `insert_paste(text)`（约第 47 行）→ `insert_paste_with_policy(text, allow_insert, max_chars)`（约第 51 行）— 清洗换行后按字符过滤与截断。`insert_paste_with_byte_limit(text, max_total_bytes)`（约第 69 行）— 按**字节**预算逐字符截断，不切断多字节字符。
- `handle_key(key)`（约第 94 行）→ `handle_key_with_insert_policy(key, allow_insert)`（约第 98 行）— **核心**：Release 直接 Unhandled；`Home`/`Super+Left` → `MoveLogicalLineStart`，`End`/`Super+Right` → `MoveLogicalLineEnd`，其余委托 `classify_key_event`；`Insert` 受 `allow_insert` 门控，最终 `buffer.apply(command)` 经 `from_edit_outcome` 映射。
- `viewport(&self, width) -> SingleLineViewport`（约第 137 行）、`from_edit_outcome(...)`（约第 141 行）、`sanitize_single_line(text)`（约第 152 行）。

### 2.5 `input/mouse.rs`（滚动状态机）

鼠标滚动的归一化状态机。**注意**：本文件的「解析」是方向解析；**命中测试的几何判定**在 `render/scrollbar.rs`（`scrollbar_grab_zone`/`scrollbar_click_to_offset`）与 `app/mouse.rs`。

- `enum ScrollInputMode { Auto, Wheel, Trackpad }`（约第 25 行）。
- 常量簇：`STREAM_GAP_MS=80`、`REDRAW_CADENCE_MS=16`、加速阈值与倍数、`MIN_DELTA_PER_FLUSH=6`（约第 47–77 行）。
- `is_vscode_embed(name)` / `default_accel_interval_{fast,medium}_ms_for_terminal` / `default_trackpad_detect_max_interval_ms_for_terminal`（约第 82–124 行）— xterm.js 嵌入（VS Code 家族）用更宽时间窗与更高 lpt。
- `speed_to_multiplier(speed: u8) -> f32`（约第 107 行）— 1–100 速度 → 0.1x–6.0x（50 为 1.0x）。
- `enum ScrollStreamKind { Unknown, Wheel, Trackpad }`（约第 127 行）、`enum ScrollDirection { Up, Down }`。
- `ScrollDirection::from_mouse_event(event: &MouseEvent) -> Option<Self>`（约第 152 行）— **鼠标事件解析入口**：`ScrollUp/ScrollDown` → `Up/Down`。被 `AppView::handle_input` 调用。
- `struct ScrollConfig { ept, wheel/trackpad lpt, 模式, 时间窗, 加速阈值, speed 乘子, viewport_height }`（约第 178 行）。
- `multiplexer_reencodes_mouse(multiplexer) -> bool`（约第 249 行）— tmux/screen/zellij/herdr 会重编码 SGR（cmux 透传不算）。
- `ScrollConfig::from_settings()`（约第 271 行）→ `from_terminal_context(brand, multiplexer, overrides)`（约第 282 行）— **核心**：按品牌/复用器定 ept 与 lpt（复用器重编码则退化为保守 ept=1），应用覆盖并组装全部时间窗。
- `ScrollConfig::with_viewport_height(rows)`（约第 401 行）、`flush_cap(self) -> i32`（约第 429 行，`max(viewport/2, 6)` 防瞬移）、`apply_direction(self, dir)`（约第 433 行）。
- `struct ScrollUpdate { lines, next_tick_in }`（约第 464 行）。
- `struct MouseScrollState { 当前流, carry_lines, last_finalized, ScrollLogRecorder?, 重绘节奏 }`（约第 531 行）。
- `MouseScrollState::on_scroll_event_at(now, direction, config) -> ScrollUpdate`（约第 578 行）— **核心入口**：应用方向反转；若已有流且超 80ms 间隔或方向翻转则 `finalize_stream_at`（翻转时取消 backlog）；否则续流；新流则重置/继承 carry 并记 `StreamStart`；`push_event` + `maybe_promote_kind`；到达重绘节奏或刚晋升时 `flush_lines_at` 并记 `Flush`。
- `MouseScrollState::on_tick_at(now)`（约第 657 行）— 时钟唤醒：超间隔且无可 flush 时 finalize，否则按节奏补 flush。
- `has_active_stream()`（约第 698 行）、`cancel_stream()`（约第 702 行）、`scroll_clock_deadline(now)`（约第 710 行）、`debug_snapshot(...)`（约第 716 行）、`toggle_scroll_log()`（约第 753 行）。
- `MouseScrollState::finalize_stream_at(now, stream, cancel_backlog) -> i32`（约第 769 行）— 结束流：定类、限制重定价、必要时 taper flush；仅保留亚行 `fract()` carry（wheel 清零）。
- `MouseScrollState::flush_lines_at(last_redraw_at, carry, now, stream) -> i32`（约第 818 行）— 实际投递行数；零投递不推进时钟（防忙旋）。
- `MouseScrollState::record_scroll_log(...)`（约第 840 行）、`next_tick_in(now)`（约第 883 行）。
- `struct ScrollStream`（约第 924 行）— 单条手势流状态。方法：`push_event(now, direction)`（约第 969 行）、`trackpad_line_rate()`（约第 997 行）、`clamp_trackpad_demand()`（约第 1004 行）、`avg_interval_ms()`（约第 1018 行）、`interval_accel()`（约第 1026 行）、`maybe_promote_kind(now)`（约第 1044 行，Auto 模式中途晋升）、`finalize_kind()`（约第 1075 行）、`limit_finalize_reprice(...)`（约第 1097 行）、`is_wheel_like()`/`effective_lines_per_tick_f32()`/`is_confirmed_trackpad()`（约第 1112/1124/1143 行）。
- `ScrollStream::desired_lines_f32(&self, carry) -> f32`（约第 1151 行）— **定价核心**：确认触控板用「加权事件 × 行单价 × speed + carry」；否则用「累积事件 × lpt/ept × speed」；carry 在所有乘子之后相加。
- `ScrollStream::flushable_now(&self, carry) -> i32`（约第 1185 行）— **投递决策**：coast 时按半衰 taper 且受一 cap 预算；否则取 min(pending, cap)。`effective_pending(&self, carry)`（约第 1203 行）— 截断 desired 减 applied；wheel-like 至少 1 行；方向钳制。

### 2.6 `input/macos_modifiers.rs` 与 `input/terminal_support.rs`

**macos_modifiers.rs** — macOS 物理修饰键探测，直接读 CoreGraphics，不经 PTY：

- `CGEventSourceFlagsState(stateID) -> u64`（extern "C"，约第 8 行）— 链接 CoreGraphics 的全局修饰键标志读取，无需特殊权限。
- `flags() -> u64`（约第 19 行）— 以 `kCGEventSourceStateHIDSystemState` 调用上式。
- `snapshot() -> ModifierState`（约第 27 行）— 一次系统调用解出全部修饰位。

**terminal_support.rs** — 针对「修饰键+Enter 换行」的 OS 级救援：

- `OS_MODIFIER_RESCUE_SUPPRESSED`（thread_local `Cell<bool>`，约第 11 行）+ `struct OsModifierRescueGuard` + `Drop`（约第 15–21 行）+ `suppress_os_modifier_rescue()`（约第 24 行）+ `os_modifier_rescue_suppressed()`（约第 29 行）。
- `is_apple_terminal_newline_modifier_held() -> bool`（约第 34 行）— 抑制中或 `enter_needs_rescue()` 为假则 false，否则查 OS 是否按住 Shift/Opt/Cmd。
- `is_mod_enter(key) -> bool`（约第 47 行）— 仅 `Enter` 且（`ALT|SHIFT` 命中 或 Apple Terminal 救援成立）；刻意排除 `SUPER`（多为全屏）。
- `is_delivered_super_enter(key) -> bool`（约第 61 行）— 恰好 `Enter+SUPER`（Kitty 能投递）时也为换行，但不并入 `is_mod_enter`。
- `os_any_newline_modifier_held() -> bool`（约第 66/72 行）。

### 2.7 `input/scroll_log.rs`

`GROK_SCROLL_LOG` 飞行记录器：把滚动状态机每次转换写成 JSONL，纯观察、不回馈行为。

- `enum ScrollLogEvt { StreamStart, Flush, Finalize }`（约第 26 行）、`enum ScrollLogTrigger { Event, Tick, Promotion, Finalize }`（约第 40 行）。
- `struct ScrollLogConfigEcho`（约第 57 行，仅 `StreamStart` 携带）、`struct ScrollLogEvent`（约第 69 行）、`struct ScrollLogRecord`（`#[derive(Serialize)]`，约第 100 行，含记录器补算的 `ts_ms`/`events_since_flush`/`ms_since_prev_flush`）。
- `enum Sink { Pending, Open, Disabled }`（约第 127 行）— 惰性打开、失败即永久禁用。
- `ScrollLogRecorder::from_env_at(base) -> Option<Self>`（约第 150 行）— 解析 `GROK_SCROLL_LOG`（未设/`0` 关闭，`1`/空用默认路径，其他值作路径）。`new(path, base)`（约第 165 行）。
- `record(now, event)`（约第 176 行）、`write_line(line, flush_now)`（约第 217 行，`Finalize` 触发 flush 使 `tail -f` 实时可见）、`open_writer(path)`（约第 242 行）、`default_log_path()`（约第 254 行，`~/.grok/logs/scroll-log-<utc>.jsonl`）。

### 2.8 `terminal/mod.rs`（终端环境识别的单一真相源）

- `enum TerminalName`（约第 60 行）— 已知品牌（`AppleTerminal`/`Kitty`/`Alacritty`/`Foot`/`Vte`/`JetBrains`/`Unknown`…）。谓词：`is_vte_based()`/`is_vscode_family()`/`is_xtermjs_embed()`/`is_capability_unclassified()`/`supports_osc52_clipboard()`/`width_shrink()`（约第 112–182 行）。
- `enum MultiplexerKind { Tmux, Screen, Zellij, Cmux, Herdr, Undetected }`（约第 193 行）+ `intercepts_csi_queries()`（约第 217 行）— 决定 XTVERSION/DA2 是否跳过。
- `struct TerminalContext { brand, env_brand, multiplexer, byobu, embedded_editor, is_ssh, term_var, vte_version, term_program_version, term_features, env_term_version }`（约第 248 行）— 环境事实聚合。
- `TerminalContext::keyboard_capabilities(&self) -> KeyboardCapabilities`（约第 297 行）— 委托 `keyboard_capabilities(self.brand)`。
- `TerminalContext::kitty_skip_reason(&self) -> Option<&'static str>`（约第 355 行）— **键盘协议协商输入**：按品牌（vscode/apple_terminal/vte/windows_terminal/jetbrains/unknown_no_multiplexer）优先，再落复用器原因。`kitty_multiplexer_skip_reason`（约第 394 行）独立于品牌的复用器层原因。
- `mouse_reporting_leaks_as_raw_text()`（约第 420 行）、`shift_enter_unavailable()`（约第 426 行，KKP 不可靠时 Shift+Enter 退化为裸 CR）、`prefer_alt_enter_newline()`（约第 464 行）、`ctrl_dot_unreliable()`（约第 471 行）、`hyperlink_skip_reason()`（约第 478 行，OSC 8 跳过原因）、`term_version()`（约第 537 行）、`telemetry_snapshot()`/`feedback_info()`（约第 542/573 行）。
- `terminal_context() -> &'static TerminalContext`（约第 605 行）— 进程级 `OnceLock` 入口，`get_or_init(detect_terminal_context)`。**被全子系统消费**。
- `detect_terminal_context()`（约第 626 行）— 真实检测：收集 env、精化品牌、tmux 后端补版本与 `extended-keys`。
- `build_terminal_context_from_env(env) -> TerminalContext`（约第 865 行）— **纯函数核心**，可注入 env 做全矩阵测试。
- `detect_terminal_brand_from_env(env)`（约第 659 行）— 品牌识别主流程（fork 标记 → `TERM_PROGRAM` → JediTerm → 各品牌专属变量 → `TERM`）。`refine_unknown_brand_for_host`（约第 764 行）、`mouse_reporting_leaks`（约第 774 行）、`detect_byobu_from_env`（约第 779 行）、`detect_multiplexer_from_env`（约第 816 行）、`detect_tmux_meta_from_env`（约第 855 行）、`terminal_name_from_term_program`（约第 909 行）。
- `detect_tmux_version()`/`detect_tmux_extended_keys()`/`detect_tmux_control_mode(ctx)`（约第 961/966/951 行）— 实时 tmux 子进程查询（委托 `tmux_probe`）。
- `determine_alt_screen_policy(cli_no_alt_screen, config_mode, ctx, is_control_mode) -> bool`（约第 993 行）— 备用屏策略（Zellij / tmux control mode 下 auto 内联）。

### 2.9 `terminal/keyboard.rs` / `kitty_keyboard.rs` / `probe.rs` / `da2.rs` / `xtversion.rs`

**keyboard.rs** — 把「某品牌在宿主 OS 上如何投递 Cmd/Opt/Enter」编成一张能力表：

- `enum ModifierFate { Native, Dropped, Unrecoverable, Unknown }` + `benefits_from_rescue()`（约第 13/27 行）— 仅 `Dropped` 可从 OS 救援。
- `struct ModifierDelivery { cmd, opt }` + `benefits_from_rescue()`/`label()`（约第 35/47/51 行）。
- `struct KeyboardCapabilities { modifier_delivery, enter_modifier }` + `enter_needs_rescue()`（约第 58/66 行）— 输入代码读的单一能力结构。
- `keyboard_capabilities(brand)`（约第 73 行）→ `keyboard_capabilities_for_host(brand, host)`（约第 78 行，仅 macOS 有表）→ `macos_capabilities(brand)`（约第 85 行）— **品牌分类表**：Ghostty/Kitty/Foot/iTerm2/VS Code 家族全 `Native`；WezTerm `cmd=Dropped`；Alacritty/Rio `opt=Dropped`；Warp 两者 `Dropped`；AppleTerminal `cmd=Unrecoverable, opt/enter=Dropped`；其余 `Unknown`。

**kitty_keyboard.rs** — Kitty 键盘增强标志协商与「已推送集」进程级记录（区分「推送了标志」与「真收到 release」）：

- `ALACRITTY_BROKEN_EVENT_TYPES_MAX_PACKED: u32 = 2401`（约第 32 行）— 会重复发送旧式 release 的 `alacritty_terminal` 最高版本。
- `negotiated_kitty_flags(skip_reason, da2_packed) -> KeyboardEnhancementFlags`（约第 36 行）— **协商核心**：有 `skip_reason` 则推空集；否则至少推 `DISAMBIGUATE_ESCAPE_CODES`，仅当 DA2 版本不是已知破损版才加 `REPORT_EVENT_TYPES`。
- `PUSHED_KITTY_FLAGS: AtomicU8`（约第 54 行）+ `pushed_kitty_flags()`/`set_pushed_kitty_flags(flags)`（约第 57/61 行）、`kitty_flags_pushed()`（约第 67 行）、`kitty_releases_reported()`（约第 74 行，hold-to-talk 等必须门控）、`kitty_event_types_withheld()`（约第 80 行）、`take_kitty_flags_pushed()`（约第 86 行，读清合一防并发 teardown 双重 pop）。

**probe.rs** — 探测原语：写查询 + 在裸 fd 上按截止时间轮询读 stdin：

- 常量 `MAX_PROBE_RESPONSE=256`、`LATE_REPLY_GRACE=100ms`、`LATE_REPLY_QUIET_MS=25`（约第 13–21 行）。
- `write_query(query) -> bool`（约第 24 行）— 经共享 stderr 锁写查询。`write_query_until(query, deadline)`（约第 41 行）、`write_all_until(fd, buf, deadline)`（约第 54 行）。
- `struct NonblockingGuard` + `set`/`Drop`（约第 106–143 行）— 临时置 `O_NONBLOCK` 并在 drop 时恢复。
- `enum TtyInput { Stdin, ControllingTty }`（约第 163 行）、`tty_input_fd()`（约第 182 行，stdin 非 TTY 时打开 `/dev/tty`）。
- `read_tty_reply(timeout, is_terminated) -> Option<Vec<u8>>`（约第 207 行）— **DA2 读取核心**：逐字节 poll-read 到终止谓词或 deadline。
- `finish_after_deadline(...)`（约第 242 行）、`drain_tty_until(fd, deadline, is_terminated) -> DrainStats`（约第 296 行）。
- `enum PollRead` + `poll_read_byte(fd, timeout_ms) -> PollRead`（约第 338 行）+ `last_errno_is_eintr()`（约第 381 行）。

**da2.rs** — 运行期 DA2（Secondary DA）探测，专为 Alacritty（无版本环境变量、拒绝 XTVERSION）：

- `DA2_VERSION: OnceLock<Option<Da2Version>>`（约第 19 行）、`struct Da2Version { packed, text }`（约第 24 行）、`detected()`/`detected_packed()`（约第 41/46 行）。
- `probe_at_startup()`（约第 51 行）— 门控 + stdin 是否 TTY，然后 `query_and_read`；**必须在 `enable_raw_mode()` 后、`EventStream` 前**运行。
- `gate_allows_probe(ctx) -> bool`（约第 68 行）— 仅 Alacritty 且复用器不拦截 CSI 才探测。
- `query_and_read()`（约第 73 行）、`parse_version(reply) -> Option<Da2Version>`（约第 105 行，从最后一个 `>` 起解析，抗 typeahead 干扰）、`unpack_version(packed)`（约第 122 行）。

**xtversion.rs** — XTVERSION 探测（发后不管），回复由事件循环过滤器识别并吞掉：

- `enum ProbeResult { Skipped, NoReply, Identified }`（约第 18 行）、`XTVERSION: OnceLock<ProbeResult>`、`QUERY_SENT: AtomicBool`。
- `detected()`（约第 36 行）、`reply_pending()`（约第 44 行，事件循环据此武装过滤器）、`record_reply(payload)`（约第 49 行）、`record_no_reply()`（约第 57 行）、`probe_at_startup()`（约第 67 行）。
- `gate_allows_probe(ctx)`（约第 83 行）— 允许 `Unknown|Kitty|WezTerm|Ghostty|Iterm2|Rio` 且复用器不拦截 CSI；**必须与 `da2` 探测集不相交**。
- `send_query()`（约第 92 行）、`sanitize_payload(payload)`（约第 109 行）。

### 2.10 本子系统调用链总览

**启动期（一次性探测与协商）**

```
terminal_context() → detect_terminal_context()
    → build_terminal_context_from_env()
        → detect_terminal_brand_from_env / detect_multiplexer_from_env / detect_byobu_from_env
    → refine_unknown_brand_for_host
    → detect_tmux_version / detect_tmux_extended_keys      (仅 tmux 后端)

xtversion::probe_at_startup() → gate_allows_probe() → probe::write_query()   …回复由事件循环过滤器 → record_reply()
da2::probe_at_startup()       → gate_allows_probe() → probe::write_query()
                              → probe::read_tty_reply() → parse_version() → unpack_version()

terminal_context().kitty_skip_reason()  ┐
da2::detected_packed()                  ┴→ kitty_keyboard::negotiated_kitty_flags() → set_pushed_kitty_flags()
```

**按键事件流（每帧）**

```
EventStream → AppView::handle_input_at_with_paste_provenance()
  → KeyboardNormalizer::rescue() → rescue_key()
        ├─ 裸 Ctrl+B 字节规范化（无条件）
        └─ OsModifierProbe::snapshot() → macos_modifiers::snapshot()   （Cmd/Opt 救援）
  → LineEditor::handle_key_with_insert_policy() → classify_key_event() → buffer.apply() → from_edit_outcome()
  （换行判定：terminal_support::is_mod_enter() / is_delivered_super_enter()）
```

**鼠标滚动流（每事件 / 每 tick）**

```
ScrollDirection::from_mouse_event()
  → MouseScrollState::on_scroll_event_at()
      → ScrollConfig::from_settings() → from_terminal_context()
      → finalize_stream_at()             （80ms 间隔或方向翻转）
      → ScrollStream::push_event() → interval_accel() / clamp_trackpad_demand()
      → ScrollStream::maybe_promote_kind()
      → flush_lines_at() → flushable_now() → effective_pending() → desired_lines_f32()
      → record_scroll_log() → ScrollLogRecorder::record() → write_line()
  → MouseScrollState::on_tick_at()       （时钟唤醒补 flush / finalize）
  → scroll_clock_deadline() / next_tick_in()   （事件循环排期）
```

---

## 3. 渲染管线

覆盖 `crates/codegen/xai-grok-pager-render/src/render/*`、`host/*`、`glyphs.rs`、`syntax.rs`。

### 3.1 `render/mod.rs` 与 `render/draw.rs`（帧入口 + 写线程）

**mod.rs**：渲染子系统模块聚合入口，纯声明 + 再导出（`render_image_overlay`、`PreviewConfig`/`render_preview_overlay`、`Renderable`、`SafeBuf`），约第 1–21 行。

**draw.rs** — **一帧渲染的真正入口**。绕过 ratatui `Terminal::draw()/try_draw()`，用底层 API 手写「diff → 光标去重 → 原子提交」，解决光标闪烁被每帧 `Show/MoveTo/Hide` 打断的问题；并引入独立写线程，避免慢终端阻塞事件循环。

写线程与同步协议：

- `type PagerTerminal = xai_ratatui_inline::Terminal<CrosstermBackend<TermWriter>>`（约第 53 行）。
- `enum WriterEvent { Written(u64), Failed(io::Error) }`、`enum WriterDrain { Drained, TimedOut }`、`enum WriterJoin { Joined, TimedOut }`。
- `struct WriterSync { queued, written, failed, writer_active, producer, event_tx }` — 帧与转义共用的**序号水位线**协议；`reserve_sequence` 先占号再发送，保证子进程接管 tty 前无乱序帧。方法：`reserve_sequence() -> u64`、`mark_written(seq)`（`fetch_max` 保持单调）、`mark_failed(err)`（CAS 只报一次）、`is_drained()`、`wait_drained(timeout) -> io::Result<WriterDrain>`。约第 103–149 行。
- `struct WriterPayload { sequence, data }` + `data()`。
- `send_payload(tx, sync, data) -> io::Result<()>`（约第 172 行）— **单生产者**约束：用 `OnceLock<ThreadId>` 锁死生产线程，`debug_assert_eq!` 防第二线程重排终端输出。
- `struct TermWriter`（实现 `io::Write`，约第 195–242 行）— 帧缓冲；`write` 只追加，`flush` 经 `send_payload` 交写线程；`discard()` 丢弃本帧；`escape_writer()` 生成带外转义句柄；`Drop` 时 flush 并释放 `writer_active`。
- `struct EscapeWriter`（`Clone`，约第 246–284 行）— 事件循环线程专用、非阻塞的带外转义入队器。
- `struct WriterThread` + `join_within(grace) -> io::Result<WriterJoin>`（约第 295–324 行）— 有界 join：超时则 detach 并告警。
- `spawn_writer_thread() -> io::Result<WriterThreadParts>` / `spawn_writer_thread_with(spawn)`（约第 375/379 行）— 起名为 `term-writer` 的线程，dup tui stderr 包 `BufWriter`，循环 `rx.recv()` 逐块 `write_payload`。`write_payload(writer, payload, sync)`（约第 343 行）。

光标去重与帧绘制：

- `struct CursorState { last_pos: Option<(u16,u16)> }`、`enum CursorAction { None, Reposition(x,y), Show(x,y), Hide }`。
- `CursorState::action(cursor_pos, has_changes) -> CursorAction`（约第 464 行）— 纯函数：位置相同且无变化→`None`（保留闪烁）；位置相同但有变化→`Reposition`；可见性跃迁→`Show`/`Hide`。
- `CursorState::apply(action, w)`（约第 480 行）— 用 `queue!`（非 `execute!`）把光标命令与帧批量刷出。
- `draw_frame(terminal, cursor, ctx, render_fn)`（约第 503 行）— **主入口**：按 `should_emit_synchronized_output(ctx)` 决定是否包 `BeginSynchronizedUpdate`，`autoresize()` 后调 `render_and_present`。
- `draw_frame_at_adopted_size(...)`（约第 524 行）— 同 `draw_frame` 但**不做 resize**（minimal 模式调用方已提前采纳尺寸）。
- `render_and_present(terminal, cursor, synchronized, render_fn)`（约第 542 行）— 帧核心：`get_frame()` → 调 `render_fn` 得 `(cursor_pos, PostFlush)` 并收集 `Vec<LinkSpan>` → `set_frame_links` → `flush_with_links()` 返回是否有变化 → `swap_buffers()` → 据变化与光标算 `CursorAction`；无变化且无光标命令则 `discard()`（空闲帧零字节）→ 否则写 `PostFlush` 转义、`apply` 光标、`EndSynchronizedUpdate`、`flush`。

### 3.2 `render/wrapping.rs`（词感知换行）

保留 ratatui `Span` 样式，区分软换行（joiner）与硬换行；表格、blockquote 特殊处理。

- `wrap_ranges_trim(text, width_or_options) -> Vec<Range<usize>>`（约第 12 行）— 调 `textwrap::wrap`，把每行结果用 `Cow::Borrowed` 指针差反推回**原文字节范围**（要求全 Borrowed，否则 panic）。
- `struct HighlightSegment { row, col_start, col_end }`、`byte_range_to_row_cols(text, wrap_ranges, match_range) -> Vec<HighlightSegment>`（约第 43 行）。
- `byte_offset_to_display_col(text, byte_offset) -> usize`（约第 71 行）。
- `wrap_byte_ranges_matching(text, width) -> Vec<Range<usize>>`（约第 86 行）— 与 `word_wrap_line_with_joiners` **断点必须一致**，供搜索高亮对齐。
- `struct RtOptions<'a>` + 链式 setter（约第 148–235 行）。
- `word_wrap_line(line, width_or_options) -> Vec<Line<'a>>`（约第 239 行）— 对外主 API。
- `flatten_line_and_bounds(line) -> (String, Vec<(Range<usize>, Style)>)`（约第 247 行）、`build_wrapped_line_from_range(...)`（约第 263 行）。
- `is_table_line(line) -> bool`（约第 285 行）— 表格**绝不换行**（换行会破坏列对齐）。`blockquote_prefix_len(flat)`（约第 316 行）。
- `word_wrap_line_with_joiners(line, width_or_options) -> (Vec<Line>, Vec<Option<String>>)`（约第 331 行）— **核心算法**：表格直接 `fit_line_to_width`；否则 flatten → blockquote 注入前缀 → 首行按 initial_indent 缩减宽度 wrap，续行按 subsequent_indent 缩减 wrap；用**单调 `span_cursor`** 让每行切片 O(rows+spans)（避免大行的 O(rows×spans) 卡死渲染线程）；joiner 记录换行处被跳过的空白。
- `slice_line_spans(original, span_bounds, range, cursor) -> Line`（约第 582 行）— 带单调游标的 span 切片。
- `word_wrap_lines(...)` / `word_wrap_lines_with_joiners(...)`（约第 449/477 行）— 多行入口，只有第一行用 initial_indent。
- `enum LineInput` + `trait IntoLineInput`（impl for `&Line`/`Line`/`String`/`&str`/`Cow`/`Span`/`Vec<Span>`，约第 512–578 行）。
- `wrap_header_hanging(header, width, extra_indent) -> Vec<Line>`（约第 637 行）、`wrap_header_flush(header, width, indent) -> Vec<Line>`（约第 678 行）。

### 3.3 `render/line_utils.rs`

行长/宽度工具与去危险字符；被 wrapping、preview_overlay、tool_paths 广泛调用。

- 再导出：`pub use super::tool_paths::{path_basename, path_for_tool_header, shorten_path};`（第 5 行）、`pub use crate::util::byte_offset_at_width;`（第 6 行）、`pub use xai_tty_utils::is_unsafe_display_char;`（第 7 行）。
- `line_to_static(line) -> Line<'static>`（第 10 行）、`push_owned_lines(src, out)`（第 26 行）。
- `is_unsafe_display_char(c) -> bool`（第 7 行再导出）— 判定不可信文本中必须清洗的字符：C0/C1 控制符 + bidi 控制/零宽格式字符（Trojan-Source 防伪）；**全局唯一判据**。⚠️ **实现已迁出**：现位于 `crates/codegen/xai-tty-utils/src/display_char.rs` · `is_unsafe_display_char(+0)`（同目录 `display_char_tests.rs` 为其测试），`line_utils.rs` 仅 `pub use` 转发。
- `floor_char_boundary(s, index) -> usize`（第 34 行）— nightly 的 polyfill。
- `truncate_str(s, max_width) -> String`（第 44 行）、`truncate_line(line, max_width) -> Line`（第 49 行，在预算耗尽的 span 内切并补 `…`）。
- `fit_line_to_width(line, width) -> Line`（第 90 行）— **按字素簇**裁剪或补空格使每列都是真实单元（防宽字形留下幽灵格）；表格行依赖它。
- `take_width(s, n) -> String`（第 155 行，`fn`，非 `pub`）、`cascade_truncate(avail, type, description, activity, meta) -> (String,String,String,String)`（第 163 行，空间不足时按「先丢描述→丢 meta→截 activity→截 type」级联裁剪）。

### 3.4 `render/scrollbar.rs`

基于 `tui-scrollbar` 的平滑 Unicode 滚动条；可见性同时表达 follow 状态（跟随=很暗，脱离=较亮）。

- `static SCROLLBARS_HIDDEN: AtomicBool` + `set_scrollbars_hidden(bool)`/`scrollbars_hidden()`（约第 45–55 行）。
- `split_area_for_scrollbar(area) -> (Rect, Option<Rect>)`（约第 68 行）— 恒定预留 gap(1)+track(1) 两列。`maybe_split_for_scrollbar(area, total_lines)`（约第 93 行）— 仅在确需滚动条时预留。`needs_scrollbar(total, viewport)`（约第 102 行）。
- `scrollbar_grab_zone(track) -> Rect`（约第 107 行）— track + 1 列 slop（贴边 thumb 被当成两列控件）。
- `enum ScrollbarClickResult { Top, Bottom, Offset(usize) }`、`scrollbar_click_to_offset(cell_index, track_cells, total, viewport) -> ScrollbarClickResult`（约第 130 行）— 渲染 `ScrollMetrics` 的逆映射。
- `render_scrollbar(buf, area, total, viewport, offset, is_following)`（约第 165 行）、`thumb_fill_style(thumb_style) -> Style`（约第 187 行，把 thumb 前景色同时设成背景色，覆盖 macOS Terminal.app 行缝条纹）、`scrollbar_styles(is_following) -> (Style, Style)`（约第 195 行）、`render_scrollbar_styled(...)`（约第 211 行）。

### 3.5 `render/highlight.rs`（搜索匹配高亮）

不是语法高亮：把匹配区间做反色叠加，压过底层配色。

- `paint_match_highlights(buf, area, row_y, viewport_bottom, skip, prefix_w, text, re, single_row, map_visual)`（约第 14 行）— 主函数。`single_row` 时按显示列直接反色；多行时用 `wrap_byte_ranges_matching` 求换行行范围、`byte_range_to_row_cols` 求每行区间，必要时经 `bidi::logical_cols_to_visual` 映射；只画到 `viewport_bottom`。
- `invert_cell(cell)`（约第 91 行）— 插入 `Modifier::REVERSED`，让终端原生交换前景/背景、尊重主题。

### 3.6 `render/color.rs`

颜色混合/淡出（如 sticky header 被顶出屏幕时的渐隐）、256 色量化、区域重绘。

- `indexed_to_rgb(index) -> (u8,u8,u8)`（约第 12 行）、`nearest_indexed(r,g,b) -> u8`（约第 56 行）、`nearest_cube_channel(v)`/`sq_dist(...)`（约第 94/108 行）。
- `color_to_rgb(color) -> Option<(u8,u8,u8)>`（约第 116 行）、`resolve_to_rgb(color) -> Option<(u8,u8,u8)>`（约第 125 行）。
- `blend_channel(base, original, opacity) -> u8`（约第 152 行）、`blend_color(base, original, opacity) -> Option<Color>`（约第 160 行）、`blend_line(line, base, opacity) -> Line`（约第 176 行）、`blend_line_with_default(...)`（约第 194 行）。
- `fade_region(buf, area, base, opacity)`（约第 216 行）、`blend_area(buf, area, fg, bg)`（约第 226 行）、`recede_area(buf, area, bg, opacity)`（约第 251 行）、`force_area_fg(buf, area, fg)`（约第 270 行）、`dim_area(buf, area, blend_bg, blend_factor)`（约第 281 行）。

### 3.7 `render/renderable.rs` 与 `render/safe_buf.rs`

**renderable.rs** — 虚拟化滚动的核心抽象：

- `trait Renderable { fn render(&self, area, buf); fn desired_height(&self, width) -> u16 }`（约第 10 行）— 对象安全，允许异构集合；高度需高效（滚动位置计算会频繁调用）。标准实现：`()`、`&str`/`String`/`Span`/`Line`、`Option<R>`、`Arc<R>`、`Box<R>`（约第 23–102 行）。

**safe_buf.rs** — ratatui `Buffer` 的越界安全写入扩展；resize 竞态下区域可能短暂越界，原生 `set_line/set_span/set_string` 会 panic：

- `trait SafeBuf` + `set_line_safe(x,y,line,width)` / `set_line_safe_bidi(...)` / `set_span_safe(...)` / `set_string_safe(...)` — 先做边界检查再写。
- `set_line_safe_bidi`（约第 39 行）— 唯一做 RTL 重排的版本：开启 bidi 时经 `bidi::visual_line` 重排后再写；scrollback/list 内容用它（它们掌握列映射），普通 chrome 用 `set_line_safe` 保持逻辑序以便命中测试。

### 3.8 `render/terminal_output.rs`（PTY 字节流 → 样式行）

把 Bash/终端工具的**原始 PTY 字节流**（含 ANSI SGR、光标移动、行擦除、回车覆盖进度条）过一个最小行导向的 VTE 模拟器，产出「终端实际会显示」的带样式行 + 去转义纯文本。不同于网格模拟器，它保留**无界、完整样式**的转录以映射到 pager 行模型。

- `struct RenderedLine { line: Line<'static>, plain: String }`。
- `render_terminal_lines(raw, base) -> Vec<RenderedLine>`（约第 27 行）— **主入口**：每次调用新建 `TermSink` + `vte::Parser`，`advance` 后 `finish`。
- `render_terminal_plain(raw) -> String`（约第 39 行）— 去转义纯文本（供剪贴板/搜索）。
- `struct Cell { ch, style }`、`struct TermSink { base, cur, rows, row, col }` — 内部状态机。方法：`ensure_row`（限 `MAX_ROWS=50_000`）、`put(ch)`（限 `MAX_COLS=8_192`）、`newline`、`erase_line(mode)`（EL 0/1/2）、`erase_display(mode)`（ED 0/2/3）、`apply_sgr(params)`（BOLD/DIM/ITALIC/UNDERLINE/REVERSED、16 色、`38/48` 扩展色）、`finish()`。约第 61–207 行。
- `impl Perform for TermSink`：`print`→`put`；`execute`（`\n`/`\r`/`\t`/退格）；`csi_dispatch`（`m` SGR、`K` 擦行、`J` 擦屏、`A/B/C/D`、`G`）。约第 209–250 行。
- `first_param(params, default) -> u16`（约第 253 行）、`ansi16(n)`/`ansi16_bright(n) -> Color`（约第 261/275 行）、`ext_color(groups, i) -> Option<Color>`（约第 290 行）、`parse_ext(sub) -> Option<Color>`（约第 315 行）、`row_to_line(cells, base) -> RenderedLine`（约第 331 行）。

### 3.9 `render/osc8.rs`（OSC 8 超链接检测）

扫描纯文本 URL 与绝对/相对文件路径，汇成 `LinkOverlay`，最终由帧 diff（`xai_ratatui_inline::Terminal::flush_with_links`）以 OSC 8 超链接发出。

- `enum LinkTarget { Url(Arc<str>), File(Arc<Path>) }`、`enum LinkPresentation { Opaque, SelfResolvingPath }`、`struct ResolvedLinkTarget { osc8_url, open_target }`。
- `resolve_link_target(target)` / `_with_presentation` / `_for_context(target, presentation, terminal) -> Option<ResolvedLinkTarget>`（约第 39–79 行）— 按终端上下文决定 OSC 8 目的地与 app 打开目标；官方 VS Code Remote 的自解析路径文件则**委托终端**（osc8/open 均为 None）。
- `struct OverlayLink { screen_row, col_start, col_end, target, presentation, id }`、`const SCANNER_ID_BASE: u32 = 1 << 31`（约第 100 行，避免与 markdown 映射的小 id 冲突）。
- `struct LinkOverlay { links, next_id }` + `new/push/extend_from/is_empty/links/overlaps(row, cs, ce)`（约第 104–165 行）。
- `link_finder() -> &'static LinkFinder`（约第 167 行，`OnceLock` 缓存，只认 Url/Email）、`linkify_href(text, link) -> Option<String>`（约第 184 行）。
- `relative_file_path_regex()`/`file_path_regex()`/`quoted_file_path_regex()`（约第 212/223/239 行，`OnceLock` 缓存的三类路径正则）。
- `path_to_file_target(path)`/`tool_path_file_target(path, cwd)`（约第 253/275 行）、`file_path_to_url(path) -> Option<Arc<str>>`（约第 257 行）、`file_link_presentation(painted, target, cwd)`（约第 308 行）、`local_link_to_file_target(dest, media_paths, cwd)`（约第 334 行）、`relative_link_target(path, media_paths, cwd)`（约第 361 行）。
- `struct RowSegment { screen_row, start, end }`、`scan_lines_for_url_overlays(lines, content_x, media_paths, overlay)`（约第 397 行）— **扫描主入口**：按 joiner 把软换行的多视觉行重新拼成逻辑行（硬换行/孤立续行另起组），组结束调 `scan_logical_line`。
- `push_link_segments(text, rows, content_x, match_range, target, presentation, overlay) -> bool`（约第 434 行）、`scan_logical_line(text, rows, content_x, media_paths, overlay)`（约第 489 行）— 对一条逻辑行跑 URL、引号路径、绝对路径、相对 media 路径四遍检测。

### 3.10 `render/bidi.rs`（可选双向文本）

UAX #9 重排（**默认关闭**，避免在已隐式 bidi 的终端上双重翻转）。开启后对 scrollback/list 内容做：剥离 override/isolate 控制符、按视觉行重排、按字素簇反转 RTL run、镜像配对标点；表格行保持逻辑序。

- `static RTL_BIDI_ENABLED: AtomicBool` + `is_enabled()`/`set_enabled(bool)`（约第 22–33 行）。
- `needs_bidi(text)`/`is_rtl_affecting(c)`（约第 37/42 行）、`is_bidi_control(c)`/`strip_bidi_controls(text)`（约第 48/55 行）、`paragraph_level(text)`（约第 63 行）。
- `visual_text(text)`/`visual_text_with_level(...)`/`visual_text_line(...)`（约第 74/87/104 行）、`visual_line(line) -> Option<Line>`/`visual_line_with_level(...)`（约第 125/133 行）。
- `logical_slice_for_visual_cols(text, vis_start, vis_end) -> String`（约第 199 行，剪贴板用）、`visual_col_to_logical_col(text, visual_col) -> usize`（约第 280 行，拖拽命中用）、`logical_cols_to_visual(text, logical_start, logical_end) -> Vec<(usize,usize)>`（约第 340 行，搜索高亮用）。
- `is_table_row(text)`/`chrome_prefix_len`/`marker_prefix_len`/`blockquote_prefix_len`（约第 391–479 行）、`reorder_body(body, level) -> String`（约第 481 行）、`mirror_grapheme(g) -> String`（约第 587 行）、`visual_grapheme_order(body, level)`（约第 593 行）。

### 3.11 `render/tool_paths.rs`

Read/Edit 工具路径解析与按「表面」（Collapsed/Expanded/Fullscreen）格式化。

- `enum ToolPathSurface { Collapsed, Expanded, Fullscreen }`、`struct ResolvedToolPath { display_path, relative_to_cwd }`。
- `expand_tilde_with_home(path, home) -> Option<PathBuf>`（约第 27 行，fail-closed）、`resolve_tool_path_target_with_home(path, cwd, home) -> Option<PathBuf>`（约第 49 行，**OS 实际收到的路径**，保留 `.`/`..`/符号链接语义）、`home_dir()`（约第 75 行）。
- `resolve_tool_path_with_home`/`resolve_tool_path`（约第 85/105 行，展示路径词法归一 + 相对 cwd）、`path_for_fullscreen_header`/`path_for_expanded_header`（约第 109/116 行）。
- `shorten_path(path, budget) -> String`（约第 124 行，fish 风格逐段缩短）、`path_basename(path, budget)`（约第 187 行）、`path_for_tool_surface(path, surface, cwd, width, reserved) -> String`（约第 205 行）。

### 3.12 overlay 家族

**`render/image_overlay.rs`**（模块根，**非** `mod.rs`）— 图片预览浮层：

- `render_image_overlay(buf, area, image, bg, text_fg, border_fg) -> Option<overlay::Escapes>`（约第 43 行）— 对外入口。
- `render_image_overlay_inner(...) -> Option<ImageOverlayRender>`（约第 55 行）— **核心**：区域太小直接 None；`plan_image_preview` + `overlay_geometry` 算几何；`dim_area` 压暗背景；`Clear` + 圆角 `Block` 画框；标题居中；预留 path footer；无像素时用 `Paragraph` 列 Format/Dimensions/Size，有像素时居中 `Loading...` 并生成 `overlay::static_image_for_protocol` 后刷转义。
- `content.rs`：`paint_path_line(...)`（约第 11 行）、`build_meta_line(image, display_path)`（约第 34 行）、`format_mime(mime)`（约第 49 行）、`truncate_path_for_overlay(path, max_chars)`（约第 61 行）。
- `geometry.rs`：常量 `MIN_BOX_WIDTH=28` 等；`plan_image_preview(image, protocol) -> ImagePreviewPlan`（约第 36 行）、`overlay_geometry(area, show_pixels, has_path, dimensions) -> Option<ImageOverlayGeometry>`（约第 46 行）。

**`render/video_overlay.rs`** — 视频浮层的边框/标题/进度条 chrome（视频帧由调用方以 post-flush 转义渲染）：

- `render_video_overlay(buf, area, viewer, bg, text_fg, border_fg) -> Option<Rect>`（约第 16 行）、`render_progress_bar(buf, popup_rect, viewer, text_fg, bar_dim, bg)`（约第 77 行）、`format_time(secs) -> String`（约第 124 行）。

**`render/gboom_overlay.rs`** — `/gboom` 彩蛋浮层 chrome：

- `render_gboom_overlay(buf, area, hud, bg, text_fg, border_fg) -> Option<Rect>`（约第 17 行）、`render_hud_bar(buf, popup_rect, hud, dim_fg, bg)`（约第 70 行，左 `HP/·/KILLS` 按血量绿/琥珀/红）。

**`render/preview_overlay.rs`** — 多行内容预览浮层（粘贴元素预览、队列项预览）：

- `struct PreviewStyle`、`struct PreviewConfig { preview_lines, width_ratio, bottom_gap, min_width, min_height, hint }`（约第 46–82 行，默认 3/0.75/0/20/5/None）。
- `render_preview_overlay(buf, area, content, style, config) -> Option<Rect>`（约第 90 行）— **主函数**：空内容或区域过小→None；算 `needs_dots` 与内容行数；框高=内容+2、宽=`area*width_ratio`；**底部锚定**；`Clear`+`set_style`+圆角 `Block`。
- `render_content_lines(...)`（约第 165 行，有省略时画 top N、`⋮ (N more lines)`、bottom N）、`render_line(...)`（约第 222 行）、`render_border_hint(...)`（约第 230 行）。

### 3.13 `host/mod.rs` 与 `host/display_refresh.rs`

**host/mod.rs** — 宿主平台与显示服务器的**分类**（不是逐帧渲染入口）：

- `collect_unicode_env() -> HashMap<String,String>`（约第 12 行）、`unicode_env_from_os(iter)`（约第 17 行）。
- `enum HostOs { Macos, Linux, Windows, Other }` + `HostOs::current()`（约第 28/38 行）。
- `pub use xai_tty_utils::is_wsl;`（约第 54 行）。
- `enum DisplayServer { Quartz, Wayland, X11, Win32, Unknown }` + `current()`（约第 70 行，`OnceLock` 缓存）+ `detect_from_env(env)`（约第 79 行）。

**host/display_refresh.rs** — 一次性探测主显示器刷新率（Hz），用于帧率上限/动画节奏；**fail-closed**：

- `enum DisplayRefreshSource { None, MacosCoreGraphics, WindowsEnumDisplaySettings, Linux }`（约第 15 行）、`struct DisplayRefreshProbeResult { hz, source, skip_reason, duration_ms }` + `outcome()`（约第 23/33 行）。
- `probe_display_refresh() -> DisplayRefreshProbeResult`（约第 45 行，`OnceLock`）→ `probe_uncached()`（约第 50 行）→ `probe_inner()`（约第 61 行）→ `decide(is_ssh, is_wsl, os, display, platform_hz)`（约第 82 行，纯决策矩阵）。
- `precheck_skip(is_ssh, is_wsl)`（约第 115 行，SSH/WSL 直接跳过）、`linux_skip_reason(display)`（约第 125 行）、`accept_hz(hz, source)`（约第 133 行，30..=500）、`probe_macos()`/`macos_main_display_refresh_hz()`（约第 144/161 行，CoreGraphics FFI，`0.0`→`"indeterminate"`）、`probe_windows()`/`windows_primary_display_refresh_hz()`（约第 193/211 行）。

### 3.14 `glyphs.rs` 与 `syntax.rs`

**glyphs.rs** — **legacy Windows ConHost** 的字符回退（Consolas/Lucida Console 缺 glyph 会渲染成 tofu）；每个函数按 `is_legacy_windows_console()` 在 fancy 与 ASCII/CP437 回退间选择，且所有变体保持相同列宽：

- `prompt_arrow() -> &'static str` + `PROMPT_ARROW_WIDTH=2`（约第 16/25 行）。
- `record_dot`/`collapsed_accent`/`ballot_x`/`check_mark`/`enlarge`/`copy_icon`/`token_arrow`/`diamond_filled/hollow/dotted`/`accent_bar`/`timeline_chevron_up/down`/`heavy_horizontal`/`light_horizontal`/`timeline_tick_active/hover`/`filled_dot`/`selection_bar`/`chevron()/chevron_left()/chevron_down()`/`disclosure_open/closed/up` 等（约第 28–334 行）。
- `monitor_icon_frames()`/`braille_spinner_frames()`/`dot_spinner_frames() -> &'static [&'static str]`（约第 100/148/162 行）。
- `legacy_glyph_fallback(s) -> Cow<str>`/`to_legacy_glyphs(s) -> String`（约第 337/364 行，`✓→√`、`✗→x`、`⚠→!`）、`sanitize_toast_message(msg)`（约第 349 行）、`is_legacy_windows_console() -> bool`（约第 377 行）、`decide_legacy_windows_console(host, brand) -> bool`（约第 406 行，Windows 且 brand 未知时**默认视为 legacy**）。

**syntax.rs** — 语法高亮的**主题/颜色映射层**（真正的 syntect 解析在 `xai-grok-markdown::Syntect`）：

- `static SYNTECT_GROKNIGHT / SYNTECT_TOKYONIGHT / SYNTECT_GROKDAY: OnceLock<Syntect>`（约第 22–24 行）。
- `syntect_to_ratatui_fg(style) -> Style`（约第 27 行）、`syntect_rgb_to_fg(r,g,b) -> Color`（约第 46 行）、`polarity_safe_syntax_fg(r,g,b) -> Color`（约第 56 行，低彩度→`Reset`；否则按 HSV 色相分桶到基础 16 色，绝不产生 White/Black）。
- `highlight_line(text, highlighter, syntect, fallback) -> Vec<Span>`（约第 90 行）、`get_syntect() -> &'static Syntect`（约第 119 行）。
- **缓存三层**：主题级 `OnceLock<Syntect>`（本文件）；语法集级由 `xai-grok-markdown` 的 `syntax_set()`（`OnceLock<SyntaxSet>`，two-face 250+ 语言）共享；语言级 highlighter 由调用方持 `Option<HighlightLines>` 按行增量推进以保持跨行语法状态。

### 3.15 本子系统调用链总览

```
app_view.rs
  └─ render::draw::draw_frame(terminal, cursor, ctx, render_fn)
       ├─ should_emit_synchronized_output(ctx) → BeginSynchronizedUpdate（可选）
       ├─ terminal.autoresize()
       └─ render_and_present
            ├─ terminal.get_frame() → render_fn(frame, &mut link_spans)
            ├─ terminal.set_frame_links(&link_spans)
            ├─ terminal.flush_with_links()      ← 发出 OSC 8 链接 + cell diff
            ├─ terminal.swap_buffers()
            ├─ CursorState::action(...) → CursorState::apply(...)
            ├─ PostFlush::write_to(...)          （图片/视频/gboom 像素转义）
            ├─ EndSynchronizedUpdate
            └─ backend.flush() → TermWriter::flush → send_payload → term-writer 线程 → write_payload

换行/高亮/链接（在 render_fn 内，典型由 scrollback/render.rs 驱动）：
word_wrap_lines_with_joiners
  ├─ is_table_line → fit_line_to_width（表格不换行）
  ├─ flatten_line_and_bounds → wrap_ranges_trim → slice_line_spans（单调游标）
  └─ (Line, joiner) ──► scan_lines_for_url_overlays ──► push_link_segments ──► LinkOverlay
wrap_byte_ranges_matching ──► byte_range_to_row_cols ──► paint_match_highlights

平台探测（进程级缓存）：
host::DisplayServer::current / HostOs::current
host::display_refresh::probe_display_refresh → probe_uncached → probe_inner → decide
glyphs::is_legacy_windows_console → decide_legacy_windows_console

Overlay 家族：
image_overlay::render_image_overlay → plan_image_preview + overlay_geometry + content::*
video_overlay::render_video_overlay → render_progress_bar
gboom_overlay::render_gboom_overlay → render_hud_bar
preview_overlay::render_preview_overlay → render_content_lines / render_border_hint
```

---

## 4. 主题与外观

覆盖 `crates/codegen/xai-grok-pager-render/src/theme/*` 与 `appearance/*`。**主题**负责「颜色数据 + 颜色能力量化」；**外观**负责「运行时可调参数（`pager.toml`/UI 设置）+ 缓存 + 系统深浅色探测」。二者通过 `Theme::current()` 与 `color_support::quantize` 交汇。

### 4.1 `theme/mod.rs`

主题系统中枢：`ThemeKind` 目录、`Theme` 的量化与极性适配、OSC 12 光标色。**所有颜色只来自 `Theme` 结构体**。

- `enum ThemeKind { GrokNight=0, GrokDay=1, TokyoNight=2, RosePineMoon=3, Auto=4, OscuraMidnight=5, Terminal=6 }`（约第 29 行）— 判别值刻意与 `cache::CURRENT` 的 `u8` 编码对齐；`Auto` 是「跟随系统」元变体，磁盘只存 `"auto"`，`CURRENT` 只存已解析的具体 kind；`Terminal` 受 rollout gate 隐藏。
- `ThemeKind::ALL: &[ThemeKind]`（约第 44 行）— 全部具体主题（不含 `Auto`），是其它目录函数（`selectable`/`available`）的唯一来源。
- `ThemeKind::selectable() -> &'static [ThemeKind]`（约第 54 行）— `ALL` 去掉受 gate 管控的 `terminal`。`ThemeKind::available() -> &'static [ThemeKind]`（约第 72 行）— `selectable` 再按终端颜色能力过滤（无 truecolor 时剔除 `requires_truecolor()` 的主题）。
- `display_name(self) -> &'static str`（约第 97 行）、`requires_truecolor(self) -> bool`（约第 110 行，TokyoNight/RosePine/Oscura 为 true）、`is_terminal_native(self) -> bool`（约第 126 行）、`aliases(self) -> &'static [&'static str]`（约第 131 行，`dark`→GrokNight、`light`/`day`→GrokDay、`transparent`/`native`→Terminal、`system`→Auto）。
- `ThemeKind::from_name(name: &str) -> Option<Self>`（约第 146 行）— **字符串→kind 的唯一入口**（大小写不敏感，匹配 `display_name` + `aliases`）。`impl FromStr for ThemeKind`（约第 169 行）。
- `canonical_name(value) -> Option<&'static str>` / `display_name_for_canonical(value) -> &str`（约第 179/185 行）。
- `impl Default for Theme`（约第 197 行，默认 `groknight()`）。
- `Theme::quantized(self, level: ColorLevel) -> Self`（约第 205 行）— 把全部颜色字段按 `color_support::quantize_color` 降级。
- `Theme::current() -> Self`（约第 293 行）— **渲染热路径取主题的唯一入口**。顺序：minimal 锁→`terminal_default()`；kind 为 terminal→`terminal()`（早退）；否则按 kind 取基色→采样 `is_dark()`→Windows 上 `windows_contrast_boost`→`quantized`→Basic/legacy ConHost 上 `ansi16_chrome_overrides`。
- `Theme::current_kind() -> ThemeKind`（约第 335 行）、`Theme::diff_uses_line_fg(&self) -> bool`（约第 342 行，`diff_*_bg` 均为 `Reset` 时改走整行红/绿前景）。
- `Theme::apply_kind(kind: ThemeKind) -> ThemeKind`（约第 348 行）— **切换主题的写入口**（内存态，仅事件循环发 OSC 12）；minimal 锁下 no-op；先 `clamp_to_terminal` 再 `cache::set`。`Theme::clamp_to_terminal(kind)`（约第 357 行，truecolor-only 主题在无 truecolor 终端上回退 GrokNight）。
- `Theme::windows_contrast_boost(self, dark) -> Self`（约第 367 行）— Windows gamma 补偿：用内部 `push_away(base,color,amount)` 把 `bg_light`/`bg_highlight`/`prompt_border_active` 推离 `bg_base`。
- `Theme::ghost_text_style(&self) -> Style`（约第 409 行，`dim()` + ITALIC）、`Theme::is_dark(&self) -> bool`（约第 415 行，BT.709 亮度判极性，实际委托 `osc11::classify_luminance`）、`Theme::ansi16_chrome_overrides(self, dark) -> Self`（约第 429 行，chrome 钉到 4 个中性槽，避免深色 RGB 全塌成 `Black`）。
- `cursor_color_escape() -> Option<String>`（约第 564 行，生成 OSC 12）、`apply_cursor_color()`/`reset_cursor_color_if_applied()`/`note_cursor_color_on_wire(applied)`/`reset_cursor_color()`（约第 571–628 行，基于 `CURSOR_COLOR_APPLIED` 原子的条件回滚；`CURSOR_COLOR_RESET_ESCAPE = \x1b]112\x07`）。

### 4.2 具体主题文件

`tokyonight.rs`（`Theme` 结构体**唯一字段定义处** + 主题无关辅助）：

- `pub mod palette`（约第 15 行）— TokyoNight Night/Storm 常量，命名规律「角色名 + 可选数字后缀」（`BLUE0`/`BLUE1`、`GREEN1`）。
- `struct Theme { ... }`（约第 46 行）— 约 60 个 `Color` 字段 + 6 个 `md_heading_*_mod: Modifier`；分背景/强调/文本/灰阶/语义/选中框/滚动条/diff/paste/markdown 十组。
- `Theme::tokyonight() -> Self`（约第 148 行，Storm 变体）、`Theme::fg(color)`/`muted()`/`muted_over_chrome()`/`link_style()`/`dim()`/`primary()`/`bold()`（约第 234–341 行，`muted`/`dim` 在 `gray`/`gray_dim` 为 `Reset` 时改挂 `Modifier::DIM`）、`Theme::faint(&self) -> Style`（约第 275 行，`gray_dim` 向 `bg_base` 混合 0.66）。
- `Theme::is_bandless(&self) -> bool`（约第 288 行，判据 `bg_visual == Reset`）— **所有「反色/装饰回退」分支都以此为准**。`block_cursor_over(surface)`/`selection_overlay()`/`hover_overlay()`（约第 293–319 行，bandless 用 `REVERSED`，否则用底色）、`row_hover_bg()`（约第 325 行）、`panel_border_fg()`（约第 331 行）。
- `wave_brightness(tick, row, wave_rows, speed) -> f32` / `pulse_brightness(tick, speed) -> f32`（约第 345/359 行，`sin²` 0–1 亮度振荡，供强调线动画）。

`groknight.rs`/`grokday.rs`/`rosepine.rs`/`oscura.rs` — 四个具体主题，各定义私有 `palette` 常量模块并实现一个 `const fn` 构造函数，结构完全同构：

- `Theme::groknight() -> Self`（groknight.rs 第 55 行）— 默认主题：中性灰底（`BG_STORM=#141414`）配 TokyoNight Night 强调色。
- `Theme::grokday() -> Self`（grokday.rs 第 53 行）— GrokNight 的浅色对偶（`BG_STORM=#eeeeee`）。
- `Theme::rosepine_moon() -> Self`（rosepine.rs 第 32 行）、`Theme::oscura_midnight() -> Self`（oscura.rs 第 51 行）。

`terminal_default.rs` — 终端原生（minimal 模式 / `terminal` 主题）调色板：每个字段都是 `Reset` 或命名 ANSI-16：

- `Theme::terminal_default() -> Self`（约第 28 行）— 全 `Reset` 背景 + 稀疏命名 ANSI 强调；正文/次级文字用 `Reset`（靠 `muted`/`dim` 加 SGR dim，绝不硬涂 `DarkGray`）。
- `Theme::terminal() -> Self`（约第 115 行）— 在 `terminal_default` 基础上把边框/滚动条/`gray_dim` 改成 `DarkGray`。

### 4.3 `theme/cache.rs`

主题的内存缓存与解析：`AtomicU8 CURRENT` + `LOADED`/`AUTO_MODE`/`TERMINAL_NATIVE_LOCK`/`TERMINAL_THEME_ENABLED` 标志；**磁盘写入不在此**（由 `Effect::PersistSetting` 落到 shell 的 `set_theme`）。

- `theme_kind_from_u8(byte) -> ThemeKind`（约第 36 行，越界回退 GrokNight）、`struct AutoThemeConfig { dark_theme, light_theme: Option<ThemeKind> }`（约第 57 行）。
- `current_kind()`（约第 65 行，minimal 锁下返回名义 GrokNight）、`selected_kind()`（约第 76 行，首次 `load_from_disk()` 惰性播种）、`set(kind)`/`store_kind(kind)`（约第 89/97 行，`store_kind` 是所有写 `CURRENT` 的必经点，同时 `sync_markdown_polarity()`）。
- `terminal_native_locked()`/`terminal_native_active()`/`set_terminal_native_lock(locked)`（约第 105–120 行）、`terminal_theme_enabled()`/`set_terminal_theme_enabled(enabled)`（约第 124/130 行）、`sync_markdown_polarity()`（约第 138 行）、`is_auto_mode()`/`set_auto_mode(enabled)`（约第 151/155 行）。
- `auto_theme_config() -> AutoThemeConfig`/`invalidate_auto_theme_config()`（约第 163/170 行）。
- `resolve_initial_theme() -> ThemeKind`/`resolve_initial_theme_no_osc11()`（约第 178/184 行）— 启动解析：env（`GROK_THEME`/`LC_GROK_THEME`）→ `[ui].theme` → GrokNight。`env_theme_name_from(env)`（约第 192 行）、`resolve_initial_theme_from(...)`/`resolve_from_config(...)`（约第 208/220 行）、`resolve_from_appearance(appearance)`（约第 237 行）、`resolve_auto()`（约第 246 行）。
- `load_from_disk() -> Option<ThemeKind>`（约第 254 行，兼容顶层旧键）、`load_auto_theme_config() -> AutoThemeConfig`（约第 269 行）。

### 4.4 `theme/color_support.rs`

颜色能力探测与量化。探测结果缓存在全局 `OnceLock<ColorLevel>`。

- `enum ColorLevel { None, Basic, Ansi256, TrueColor }`（约第 17 行，有序）。`has_color()/has_256()/has_truecolor()`（约第 33–43 行）。
- `detect() -> ColorLevel`（约第 83 行，终端原生锁下把上限压到 `Basic`）、`detect_raw()`（约第 92 行，`NO_COLOR`→None；否则 `supports_color::on(Stdout)` 映射；非 TTY 默认 TrueColor）。
- `enum StandaloneColorEvidence`/`standalone(terminal)`/`standalone_from_env(...)`（约第 133/138/172 行，供 `grok doctor --json`，只看 stderr/控制终端 + 环境）。
- `get() -> ColorLevel`/`set(level) -> Result<(), ColorLevel>`（约第 206/213 行）。
- `quantize_color(color, level) -> Color`（约第 220 行）— 降级：TrueColor 直通；Ansi256 走 `nearest_indexed`；Basic 走 `indexed_to_ansi16(nearest_indexed)`；None→`Reset`。`quantize(color)`（约第 237 行，用全局等级）。
- `terminal_supports_truecolor()`/`terminal_supports_truecolor_brand(terminal)`（约第 246/250 行，`COLORTERM` 缺失时的品牌回退）、`indexed_to_ansi16(n)`/`rgb_to_ansi16(r,g,b)`（约第 274/302 行）。

### 4.5 `theme/env_appearance.rs` / `system_appearance.rs` / `osc11.rs`

**env_appearance.rs** — 桌面 API 不可用时的环境变量深浅色提示（SSH 友好）：

- `detect() -> Option<SystemAppearance>`（约第 16 行）→ `detect_from_env_map(env)`（约第 22 行，有序：显式戳 `GROK_APPEARANCE`→`LC_GROK_APPEARANCE` → `COLORFGBG`）。
- `detect_explicit_from_env_map(env)`（约第 28 行，仅显式戳）、`detect_colorfgbg_from_env_map(env)`（约第 35 行）、`parse_appearance_var(raw)`（约第 47 行，`dark`/`light` + `night`/`day` 别名）、`parse_colorfgbg(raw)`（约第 58 行，取最后一段作 bg；`0–6|8`=Dark，`7|9–15`=Light）。

**system_appearance.rs** — 系统深浅色探测链与后台轮询 watcher：

- `enum SystemAppearance { Light, Dark }`/`as_env_value(self)`（约第 23/31 行）、`static OSC11_STARTUP: OnceLock<Option<SystemAppearance>>`（约第 20 行）。
- `detect() -> Option<SystemAppearance>`（约第 41 行，桌面 → 显式 env → 缓存 OSC 11 → `COLORFGBG`，不再发 OSC 11）、`detect_with_osc11_fallback()`（约第 53 行，启动专用，实发 OSC 11 并写 `OSC11_STARTUP`）、`resolve_appearance_chain(desktop, explicit, osc11, colorfgbg)`（约第 72 行，`desktop.or(explicit).or(osc11).or(colorfgbg)`）、`detect_desktop()`（约第 83 行，`dark_light::detect()`）、`to_theme_kind(appearance, dark_theme, light_theme) -> ThemeKind`（约第 110 行）。
- `struct SystemAppearanceWatcher` + `start_if_auto(is_auto) -> Option<Self>`（约第 129/136 行，`watch` channel + `tokio::spawn` 轮询 `detect()`）+ `changed()`/`current()`（约第 163/168 行）。

**osc11.rs** — OSC 11 终端背景色查询（**仅启动期**，crossterm `EventStream` 活跃后禁止调用）：

- 常量 `LUMINANCE_THRESHOLD=0.5`、`OSC11_TIMEOUT=500ms`、`OSC11_WRAP_TIMEOUT=80ms`、`OSC11_QUERY=b"\x1b]11;?\x07"`（约第 23–30 行）。
- `detect_via_osc11() -> Option<SystemAppearance>`（约第 34 行，先发裸查询，失败再按 `should_wrap_osc11` 走 tmux passthrough 短超时重试）、`query_osc11(query, timeout)`（约第 55 行）、`classify_luminance(r,g,b) -> SystemAppearance`（约第 65 行，BT.709 + sRGB gamma 逆；被 `Theme::is_dark` 复用）、`parse_osc11_rgb(response)`（约第 77 行）、`parse_channel(s)`（约第 92 行）、`srgb_to_linear(c)`（约第 103 行）。
- `struct TermiosGuard` + `Drop`/`make_raw_termios(snapshot)`（约第 115/134 行，仅 Unix，drop 时恢复原 termios，**不碰 crossterm 的进程级原始模式**）、`read_osc_response_with_fd(fd, timeout)`/`unix_read_with_timeout(timeout)`/`ends_with_osc_terminator(buf)`（约第 155/179/192 行）。

### 4.6 `theme/md_style.rs`

把当前 `Theme` 的 `md_*` 字段桥接为 `xai_grok_markdown::MarkdownStyle`（anstyle 类型）：

- `to_anstyle(c: ratatui::Color) -> Option<anstyle::Color>`（约第 8 行，`Reset`→`None`；命名色按 `Gray`/`DarkGray` 映射到 `White`/`BrightBlack`）、`fg(c)`/`bg(c)`/`modifier_to_anstyle(m)`（约第 34–64 行）。
- `heading_inner_styles(colors, mods) -> [Style;6]`/`heading_outer_styles(colors) -> [Style;6]`（约第 66/90 行）。
- `style()`/`build_style() -> MarkdownStyle`（约第 96/100 行，每次调用从 `Theme::current()` 重建整套 markdown 样式；`blockquote_outer` 与 `quote_bar.rs::quote_bar_style` 逐字段对齐）。

### 4.7 `appearance/mod.rs` / `config.rs` / `cache.rs`

**mod.rs**（59 行）— 门面与两个「全局原子」：

- 重导出 `AppearanceConfig`/`RawAppearanceConfig`/`ScrollMode`/`TextSelection`/`FollowUpBehavior`/`RenderMermaid`/`ConfigWatcher`（第 21–31 行）。
- `static TAB_WIDTH: AtomicU8`（第 38 行）+ `tab_width()`（第 41 行）/`set_tab_width(w)`（第 46 行）、`expand_tabs(text) -> Cow<str>`（第 53 行，按 tab 宽度替换为空格，因为 ratatui 会丢弃含控制字符的 cluster）。

**config.rs**（2358 行）— `pager.toml` 的 serde 形态（`Raw*`）与运行时形态（`AppearanceConfig`）及转换、颜色解析、TOML 模板生成与持久化：

- `enum BlockBackground { None, Light, Dark }`（第 12 行）、`struct AppearanceConfig { animation, prompt, scrollback, turn_status, show_timestamps, show_timeline, disable_plugins, show_plan_chip, alt_screen, minimal, minimal_live_rows, minimal_max_commit_rows, minimal_collapse_thinking }`（第 20 行）。
- 子配置：`PromptViewConfig`/`ScrollbackConfig`/`ScrollbackDisplayConfig`/`LayoutConfig`/`ScrollbarConfig`/`ScrollConfig`/`AnimationConfig`/`BlocksConfig`/`EditBlockConfig`/`ThinkingConfig`/`ToolConfig`/`PromptConfig`（约第 60–460 行）。
- `LayoutConfig::eff_outer_vpad(compact)`（第 194 行，另有 `eff_hpad_left/right`/`validated()`）、`ScrollbarConfig::total_width()`/`is_outside(outer_hpad_right)`（第 258/267 行）、`ScrollConfig::min_scroll_lines(viewport_height)`（第 319 行）、`AnimationConfig::tick_interval() -> Duration`（第 354 行，`1000/fps`）、`EditBlockConfig::effective_expanded(...)`/`effective_line_summary(...)`（第 413/419 行）。
- `struct RawAppearanceConfig { terminal, animation, prompt, scrollback, disable_plugins, show_plan_chip }`（第 624 行，全字段带文档注释）、`struct RawTerminalConfig {...}`/`enum RawAltScreenMode { Auto, Always, Never }`（第 645/673 行）。
- `impl From<RawAppearanceConfig> for AppearanceConfig`（第 1201 行）— **原始→运行时的总转换**。各子段一族 `From`（约第 1270–1440 行，如 fps 夹到 1–60）。
- `enum OptionalColor { None, Some(Color) }`（第 1444 行）+ `to_option()`/`to_option_raw()`（第 1454/1463 行，`to_option` 会经 `theme::quantize`）。
- `parse_color_string(s)`/`parse_hex_color(hex)`/`lookup_named_color(name)`（第 1512/1520/1573 行，`#` 前缀走 3/6 位 hex，否则查命名表）。
- `RawAppearanceConfig::to_toml_with_comments() -> String`（第 1631 行）、`persist_respect_manual_folds(enabled)`（第 1776 行，`PAGER_TOML_SAVE_LOCK` + `fs_atomic`）、**🆕 `persist_respect_manual_folds_to(path, enabled)`**（第 1794 行 — 本次漂移抽出的可测写入核心，`persist_respect_manual_folds` 现为其薄包装）、`upsert_respect_manual_folds(content, enabled)`（第 1813 行）、`annotate_table<T: DocumentedFields>(table)`（第 1837 行）。

**cache.rs**（1189 行）— UI 布尔/枚举设置的 thread-local 读缓存（渲染热路径），磁盘写由 shell 的 `set_<field>()` 负责：

- 默认常量族 `COMPACT_DEFAULT`…`SCROLL_LINES_MAX`（第 21–48 行）。
- compact 族：`load()`/`set(enabled)`（第 56/72 行）及同构的 `load_timestamps`/`set_timestamps`（第 82/97 行）、`load_show_timeline`/`set_show_timeline`（第 107/122 行）、`load_page_flip_on_send`/`set_page_flip_on_send`（第 133/148 行）、`load_combine_queued_prompts`/`set_combine_queued_prompts`（第 160/175 行）、`load_simple_mode`/`set_simple_mode`（第 217/232 行）、`load_vim_mode`/`set_vim_mode`（第 243/259 行）、`load_show_thinking_blocks`/`set_show_thinking_blocks`（第 272/288 行）、`load_group_tool_verbs`/`set_group_tool_verbs`（第 301/317 行）、`load_collapsed_edit_blocks`/`set_collapsed_edit_blocks`（第 330/346 行）— 每个设置一对 `thread_local! Cell<...> CURRENT + LOADED`，首读惰性播种，`set_*` 乐观更新。
- `load_prompt_suggestions_config() -> Option<bool>`（第 357 行，原始三态）、`load_prompt_suggestions()`/`set_prompt_suggestions(enabled)`（第 369/374 行）。
- `load_keep_text_selection() -> TextSelection`（第 386 行，⚠️ 返回类型由 `bool` 升为 `TextSelection`）/`set_keep_text_selection(value)`（第 398 行）/`apply_remote_keep_text_selection_default(remote_default, ui)`（第 406 行）。
- `load_follow_up_behavior()`/`load_follow_up_steer()`（第 187/202 行）、`set_follow_up_behavior(value)`（第 207 行）。
- `load_scroll_speed()`/`load_scroll_mode()`/`load_invert_scroll()`/`load_scroll_lines()`（第 426/455/487/521 行，env `GROK_SCROLL_SPEED`/`GROK_SCROLL_MODE`/`GROK_INVERT_SCROLL`/`GROK_SCROLL_LINES` 覆盖 `[ui]`），配套 `set_scroll_mode`/`set_invert_scroll`/`set_scroll_lines`（第 475/508/546 行）。
- `load_render_mermaid()`/`render_mermaid_from_config_str(value)`/`set_render_mermaid(value)`（第 558/572/579 行）。
- `prime(ui: &UiConfig)`（第 585 行）— **启动预热**：把 `UiConfig` 与分层配置里的键全部灌入缓存，使首帧不落盘；末尾调 `permission_cursor::prime()`。
- `load_bool_from_effective_config`（第 619 行）/`load_bool_option_from_effective_config`（第 623 行）/`text_selection_from_ui`（第 632 行）/`load_keep_text_selection_from_effective_config`（第 651 行）/`load_u8_from_effective_config`（第 666 行）/`load_str_from_effective_config`（第 679 行）。

### 4.8 其余 appearance 值类型

- `appearance/scroll_mode.rs`：`enum ScrollMode { Auto, Wheel, Trackpad }` + `as_canonical()`/`from_canonical(value)`（约第 10/22/31 行）。
- `appearance/text_selection.rs`：`enum TextSelection { Flash, Hold, WordSelect }` + `as_canonical()`/`from_canonical(value)`/`holds()`/`selects_word()`（约第 12/25/34/44/49 行）。
- `appearance/permission_cursor.rs`：`enum DefaultSelectedPermission { AlwaysAllowAllSessions, AllowOnce, AllowCommandAlways, Reject }` + `as_canonical()`/`display()`/`from_config_value(s)`/`matches_kind(kind)`/`from_kind(kind)`（约第 17/31/43/55/66/82 行）；`load_default_selected_permission()`/`set_default_selected_permission(value)`/`prime()`（约第 107/128/134 行）；`last_used_permission()`/`set_last_used_permission(kind)`（约第 148/155 行）；`resolve_initial_cursor(options: &[acp::PermissionOption]) -> usize`（约第 163 行）— **ACP handler 排队的唯一入口**：粘性 → 配置默认 → YOLO 行 → index 0；具体目标缺行时降级为一次性 allow，绝不升级到全局 always-approve。
- `appearance/follow_up_behavior.rs`：`enum FollowUpBehavior { Queue, Steer }` + `as_canonical()`/`from_canonical(value)`/`is_steer()`（约第 9/19/27/36 行）。
- `appearance/render_mermaid.rs`：`enum RenderMermaid { Auto, On, Off }` + `as_canonical()`/`from_canonical(value)`（约第 11/24/33 行）。
- `appearance/watcher.rs`：`struct ConfigWatcher { rx: watch::Receiver<AppearanceConfig>, state: WatcherState }`/`enum WatcherState::Static`（约第 9/14 行）+ `start()`/`start_static()`（约第 24/39 行，dev 模式热加载 `~/.grok/pager.toml`，prod 静态默认）+ `current()`/`changed()`（约第 27/31 行）+ `pager_config_path()`（约第 35 行）。

### 4.9 本子系统调用链总览

```
启动主题解析：
resolve_initial_theme() → env_theme_name_from() → load_from_disk() → resolve_from_config()
  →（Auto）set_auto_mode(true) → system_appearance::detect_with_osc11_fallback()
       → detect_desktop() / env_appearance::detect_explicit_from_env_map() / osc11::detect_via_osc11()
            → osc11::query_osc11() → parse_osc11_rgb() → classify_luminance()
  → resolve_from_appearance() → auto_theme_config() → system_appearance::to_theme_kind()

每帧取色：
Theme::current() → color_support::detect()
  →（kind）Theme::groknight()/tokyonight()/grokday()/rosepine_moon()/oscura_midnight()/terminal()/terminal_default()
  → Theme::is_dark()（内部 osc11::classify_luminance）
  →（Windows）windows_contrast_boost() → quantized() → quantize_color()
  →（Basic/legacy ConHost）ansi16_chrome_overrides()

主题切换：
/theme → ThemeKind::from_name() → Action::SetTheme(canonical)
  → Theme::apply_kind() → clamp_to_terminal() → theme::cache::set() → store_kind() → sync_markdown_polarity()

光标色：
cursor_color_escape() → Theme::current() + render::color::resolve_to_rgb(accent_user)
  → apply_cursor_color() / note_cursor_color_on_wire() / reset_cursor_color_if_applied() → reset_cursor_color()

markdown 样式：
md_style::style() → build_style() → Theme::current() → to_anstyle()/fg()/bg()/modifier_to_anstyle()

外观设置读取：
appearance::cache::prime(ui) → 各 set_*() / load_*() → load_*_from_effective_config()
权限弹窗：permission_cursor::resolve_initial_cursor() → last_used_permission() / load_default_selected_permission()
```

---

## 5. 核心控件与视图

### 5.1 `AgentView`（`app/agent_view/mod.rs`）

`AgentView` 是**单个会话的全部状态根**：持有 `scrollback: ScrollbackState`（消息流）、`prompt: PromptWidget`（输入框）、`todo/tasks/queue` 面板，以及大量覆盖层状态。渲染入口是 `AgentView::draw`。

- `pub struct AgentView`（第 740–1539 行，约 234 个 `pub(crate)` 字段）— 字段涵盖 `session`、`scrollback`、`prompt`、`todo/tasks/queue`、`active_pane`、`dock_*`、`line_viewer`/`block_viewer`/`image_viewer`/`video_viewer`、`jump_state`、`permission_queue`、`question_view`、`plan_approval_view`。🆕 本次漂移新增：`workspace_dashboard_enabled: bool`（第 1302 行，控制 dashboard 入口）、`load_failed: bool`（第 1439 行，媒体/内容加载失败态）。
- `pub struct PaneAreas` / `pub enum ActivePane`（定义在 `views/agent.rs`，此处 re-export `pub type AgentPane = ActivePane`，第 211 行）— `PaneAreas::hit_test(col,row)` 决定鼠标落在哪个 pane（Tasks→Todo→Queue→Dock→Scrollback→Prompt 顺序）。
- `pub struct AppRenderParams<'a>`（`render.rs` 第 39 行）— AppView 传给 `AgentView::draw` 的每帧外部输入（voice 状态、`status_line`、`overlay_header`、`overlay_stop_label`）。🆕 新增字段 `workspace_dashboard_enabled: bool`（第 48 行）。
- `pub struct OverlayHeader<'a>`（`render.rs` 第 59 行）+ `cycle_position()`/`can_cycle()`。
- `enum ShortcutsBarContent { Surface, Pane, Hidden }`（`render.rs` 第 74 行）。
- `pub enum PromptInputMode`（第 348 行）— Normal/Bash/Remember 等，提供 `accent_color`/`prefix_override`/`placeholder_override`/`send_action`/`is_exit_key`。
- `fn render_dropdown_chrome(...)`（第 1701 行）、`fn collect_citation_links(scrollback, model)`（第 2032 行）、`fn translate_local_submit(...)`（第 1582 行；测试包装 `translate_local_submit_for_test` 第 1559 行）。

### 5.2 `app/agent_view/render.rs`（帧渲染入口）

- `pub fn AgentView::draw(&mut self, area, buf, registry, scratch, pending_hint, overlay_focused, banner, in_dashboard_overlay, link_spans_out, app_params) -> (Option<(u16,u16)>, Option<PostFlush>)`（第 562 行，函数体极长）— **核心渲染函数**。职责：设置每帧缓存（`begin_frame`、`note_terminal_size`）、处理内联媒体清理与子代理全屏接管早返回、构造 `PromptStyle`、计算 banner/各覆盖层高度、🆕 取 `self.session.models.current_notice()` 并经 `crate::views::model_notice_banner::height(notice, text_width)` 算 `model_notice_height` 灌入 `AgentViewLayout::compute`（第 1073–1120 行）、`fill_background`、渲染 status bar/status line、`prepare_layout` 后经 `ScrollbackPane::render_with_scratch_and_selection_boundaries` 画消息流、画 scrollbar/timeline rail、画 todo/tasks/queue/dock/btw/turn_status、🆕 在 `layout.model_notice` 行调 `crate::views::model_notice_banner::render(inset, buf, notice)`（第 2196–2205 行）、再分派到各覆盖层（line viewer、block viewer、modal、jump、cancel-turn、question、permission、plan approval）与 prompt、最后画 `ShortcutsBar` 并回填 `self.pane_areas`。
- `fn shortcuts_bar_content(&self, registry) -> ShortcutsBarContent`（第 277 行）— 依 `key_owner()` 选底部栏内容。
- `fn normal_pane_hints(&self, registry) -> Vec<HintItem>`（第 340 行）— 按焦点 pane 与状态生成提示项（最长一处提示逻辑）。
- `fn current_shortcut_hints(&self, registry) -> Vec<HintItem>`（第 259 行）、`fn line_viewer_bar(&self) -> ShortcutsBarContent`（第 321 行）、`fn card_esc_hint(&self) -> HintItem`（第 169 行，读 `EscStep::label()` 保证提示与按键不脱节）。
- `fn live_standalone_subagent_tokens(&self) -> u64`（第 83 行）、`fn update_scrollback_selection_state(model, boundaries)`（第 93 行）、`fn draw_scroll_arrow(...)`/`fn fit_toast_text(...)`（第 4331/4357 行）。

> 消息块的**实际绘制**不在此文件，而在 `scrollback` 模块（见 5.9）；`draw` 只负责把 `layout.scrollback_content` 交给 `ScrollbackPane`。

### 5.3 `app/agent_view/panes.rs`

pane 级键盘/滚轮路由，以及 dock（面板坞）的数据投影与激活。

- `pub(super) fn handle_scrollback_key(&mut self, key) -> InputOutcome`（约第 20 行）— Scrollback pane 按键总入口。
- `pub fn handle_scroll(&mut self, lines, col, row)`（约第 1102 行）— 鼠标滚轮路由：先判下拉/prompt 内滚，否则滚消息流；覆盖层打开时不穿透。
- `pub(super) fn handle_dock_key(&mut self, key)`（约第 883 行）、`handle_bg_tasks_key`（约第 965 行）、`handle_todo_key`（约第 252 行）。
- `pub fn open_scrollback_search(&mut self, initial_query)`/`handle_scrollback_search_key`/`navigate_search`（约第 125/158/135 行）、`poll_scrollback_search`（约第 229 行）。
- `dock_workflow_rows`/`dock_subagent_rows`/`dock_task_rows`/`dock_watcher_rows(&self)`（约第 287/309/352/385 行）— 把各来源状态投影成 `dock::DockRow` 列表。
- `dock_layout(&self)`/`dock_layout_for(height)`（约第 507/518 行）、`dock_snapshot(&self) -> dock::DockData`（约第 650 行）、`activate_dock_item(&mut self, item)`（约第 791 行）、`clamp_dock_overflow`/`reconcile_dock_before_paint`（约第 579/611 行）、`search_reserved_rows(...)`（约第 148 行）。

### 5.4 `app/agent_view/selection.rs`（文本选择）

拖拽/多击/表格/块选择与复制。

- `pub fn tick_selection_highlight(&mut self) -> bool`（约第 46 行，`keep_text_selection` 开启时不过期）。
- `pub(in crate::app) fn handle_scrollback_click(&mut self, now, idx, header_row_click) -> (Option<(Instant,usize,u8)>, bool)`（约第 1082 行）— 单击/双击/三击语义。
- `begin_pending_text_drag(&mut self, mouse) -> bool`/`begin_pending_btw_text_drag`/`begin_pending_block_drag`（约第 471/475/893 行）、`update_text_drag`/`update_active_block_drag`（约第 525/946 行）、`handle_scrollback_drag_motion(&mut self, mouse)`（约第 651 行）、`reconstruct_drag_copy(&self, drag)`（约第 719 行）、`finish_text_drag`/`finish_block_drag`（约第 870/1000 行）。
- `select_word_at`/`select_line_at`/`select_paragraph_at`/`select_cell_at(&mut self, hit)`（约第 1249/1289/1335/1448 行）、`tick_drag_autoscroll`/`drag_autoscroll_for(row)`（约第 279/963 行）。
- `with_btw_output`/`with_entry_output_text_source`/`with_entry_table_copy_source`（约第 111/144/182 行）、`clear_btw_owned_selection`/`clear_stuck_scrollback_drag`/`reset_wedged_mouse_reporting`（约第 84/398/434 行）。

### 5.5 `app/agent_view/viewer.rs`（行/块查看器）

- `open_line_viewer(&mut self, path, initial_range)`（第 31 行）、`handle_line_viewer_key(&mut self, key)`（第 79 行）、`confirm_line_viewer(&mut self, include_range)`/`cancel_line_viewer(&mut self)`（第 289/330 行）、`handle_line_viewer_mouse(...)`（第 387 行）、`render_selection_buttons(&mut self, buf, box, area, theme)`（第 816 行）。
- 🆕 **计划注释的关闭按钮**：`handle_line_viewer_key` 中 `x` 键现统一走 `delete_plan_comment_at_cursor`（`in_plan_approval || self.is_plan_viewer()` 合并分支，旧的 `delete_casual_plan_comment_at_cursor` 已删除）；鼠标路径经 `viewer.comment_close_button_at(col,row)` 命中 `[✗]` 后调 `delete_plan_comment_by_id(comment_id)`（`plan.rs` 第 1097 行），并维护 `hovered_comment_id`/`close_button_hovered` 悬停态（`line_viewer.rs` 第 651/652 行，命中判定 `comment_id_at_screen_row` 第 981 行 / `comment_close_button_at` 第 1003 行）。
- `show_bg_task_viewer(&mut self, task_id) -> bool`/`install_block_viewer`/`show_block_viewer`（第 975/997/1020 行）、`dismiss_block_viewer`/`clear_block_viewer`（第 958/970 行，保存 resume 位置）、`handle_block_viewer_key`/`handle_block_viewer_mouse`（第 1086/1153 行）。
- `try_take_idle_enter_quote(&mut self, key) -> IdleEnterQuote`/`insert_quoted_reply`（第 1027/1049 行，空闲态 Enter 把块查看器选中文本引回 prompt）、`dismiss_btw_panel`/`clear_btw_drag_state`（第 347/370 行）、`selected_fold_label(&self)`（第 1213 行）。

### 5.6 `app/agent_view/input.rs`（输入总调度）

- `pub fn handle_input(&mut self, ev, registry) -> InputOutcome`（约第 234 行）→ `handle_input_with_prompt_paging`（约第 238 行）。
- `pub(super) fn handle_input_inner(&mut self, ev, registry, prompt_paging) -> InputOutcome`（约第 328 行）— **核心分发**：先处理拖拽 latch 恢复、`intercept_takeover_input`、jump 抑制、粘贴图片、`Esc Esc`→dump 日志，再按覆盖层优先级分派（image/video/gboom/workflows/goal-detail/active_modal/btw/…），最后落到 pane 级 `key_owner` 路由。
- `handle_agent_action(&mut self, action_id)`/`handle_agent_action_with_registry`（约第 1169/1200 行）、`set_active_pane(&mut self, target, force) -> bool`（约第 1329 行）、`set_input_mode`/`set_vim_mode_recursive`/`is_simple_mode`（约第 1364/1376/1383 行）。
- `modal_owns_input(&self)`/`no_input_overlay_pending`/`no_esc_consumer_pending`（约第 100/81/131 行）、`external_prompt_editor_access(&self) -> ExternalPromptEditorAccess`（约第 30 行）、`overlay_esc_backs_out`/`overlay_left_backs_out`（约第 160/207 行）。

### 5.7 `app/agent_view/key_owner.rs`（键盘所有权模型）

- `pub(crate) enum BlockingCard { Permission, CancelTurn, Question, McpElicitation }`（第 11 行）+ `focus_hint()`。
- `pub(crate) enum KeyOwner { LineViewer, BlockViewer, Card(BlockingCard), PlanApproval, Pane }`（第 42 行）— 按键归属排名。
- `pub(crate) enum EscStep { DismissFileSearch, LeaveTextInput, DiscardPatternEdit, ClearSelection, BackOutOverlay, ParkFocus, KeepRunning, DismissElicitWaiting }`（第 59 行）+ `label()`。
- `blocking_card(&self) -> Option<BlockingCard>`（第 96 行，Permission 优先）、🆕 `is_awaiting_user_answer(&self) -> bool`（第 111 行 — 是否有卡片正等用户答复，供 draw/input 判断）、`key_owner(&self) -> KeyOwner`（第 118 行）→ `key_owner_when_parked(&self, parked)`（第 125 行）— **排名实现**：`parked`（键盘在 scrollback）排除卡片/计划审批；否则 Permission > LineViewer > BlockViewer > PlanApproval > Card > Pane。
- `focused_card(&self)`（第 143 行）、`parked_card(&self)`（第 153 行，Tab 会回到它）、`card_esc(&self) -> Option<EscStep>`（第 175 行）、`handle_card_esc(&mut self) -> InputOutcome`（第 217 行，执行一级 Esc 阶梯）、`park_focused_card(&mut self)`（第 269 行）、`focused_permission`/`focused_question`/`permission_back_to_options`（第 163/169/260 行）。

### 5.8 `modals.rs` / `notices.rs` / `jump.rs`

**modals.rs** — 各类模态的按键/鼠标/粘贴：

- `handle_extensions_modal_key(&mut self, key)`（约第 634 行）、`handle_extensions_modal_mouse_with_copy(...)`（约第 1156 行）、`handle_mcp_setup_key`/`handle_modal_input_key`（约第 1054/1089 行）、`execute_modal_button_action`/`confirm_extensions_modal_action`（约第 1681/2295 行）。
- `handle_feedback_modal_key/mouse/paste(...)`（约第 120/151/214 行）、`handle_agents_modal_*`/`handle_persona_detail_*`（约第 273/348/373/412 行）、`feedback_modal_open_blocker`/`has_feedback_trace_capacity`（约第 20/39 行）。

**notices.rs** — 瞬时反馈：toast、提示行、模式横幅、终端尺寸/剪贴板反馈：

- `show_toast(&mut self, msg)`/`show_toast_ticks(&mut self, msg, ticks)`/`tick_toast(&mut self) -> bool`（约第 21/200/285 行）、`set_sticky_toast(&mut self, msg)`/`set_sticky_toast_recursive`（约第 180/192 行）、`active_toast_message(&self)`（约第 208 行）、`show_mode_switch_banner(&mut self, mode_name)`/`tick_mode_banner`（约第 226/233 行）、`ephemeral_tip_renderable(&self, screen_height)`（约第 107 行，提示 TTL 总闸门）。
- `note_terminal_size(&mut self, size)`/`note_terminal_resize(&mut self)`（约第 142/155 行）、`copy_to_clipboard(&mut self, text) -> CopyDelivery`/`copy_to_clipboard_debounced`（约第 248/255 行）、`open_url_or_show(&mut self, url)`/`open_untrusted_url_or_show`（约第 325/345 行）、`guard_image_support(&mut self) -> bool`（约第 271 行）。

**jump.rs** — `/jump` 跳转选择器（核心在 `views/jump.rs`）：

- `dismiss_jump_picker(&mut self)`（约第 13 行）、`restore_jump_viewport(&mut self, restore)`（约第 21 行）、`jump_slot_taken(&self)`（约第 34 行）、`dismiss_jump_picker_if_suppressed(&mut self) -> bool`（约第 41 行）、`sync_jump_preview(&mut self)`（约第 52 行）、`handle_jump_key`/`handle_jump_mouse`（约第 67/100 行）。

### 5.9 `scrollback/`（消息流渲染内核）

`AgentView::draw` 把 `layout.scrollback_content` 交给 `ScrollbackPane`，由后者遍历 `ScrollbackEntry` 并委托 `BlockContent::output()` 产出 `BlockOutput`，最后经 `EntryRenderer` 落到 `Buffer`。

**`scrollback/scrollback_pane.rs`** — 消息流主控件（`StatefulWidget`）：

- `pub struct ScrollbackPane { is_active, mouse_pos, dim_from_entry, hovered_entry, search_highlight, media_paths }`（约第 30 行，构建器模式 `active/with_mouse_pos/with_dim_from/with_hovered_entry/with_search_highlight/with_media_paths`）。
- `render_with_scratch_and_selection_boundaries(self, area, buf, state, scratch) -> RenderOutputWithSelectionBoundaries`（约第 150 行）— **消息流渲染主入口**：取 scroll info，按 `state.view_mode()` 分派 `render_single_turn` / `render_with_sticky_headers`，再叠加 tool-call hover。
- `render_with_sticky_headers(&self, area, buf, state, theme, entry_range, scratch)`（约第 294 行）— 构建 prompt 描述符、`compute_sticky_layout` 决定 pinned/pushed 粘性头、画 pushed（带淡出）与 pinned 头、调 `render_content` 画正文、最后 `prepend_header_selection`。
- `render_content(...) -> RenderOutputWithSelectionBoundaries`（约第 869 行）— 计算 `paint_window`（O(log n) 可见窗口），取 entries 与 layout 缓存，调 `render_scrolled_entries_with_selection_boundaries`。
- `render_entry_with_ctx_static(entry, ctx, theme, area, buf, mouse_pos, idx) -> Vec<ResolvedSelectableLine>`（约第 712 行）、`render_sticky_header(...)`（约第 563 行）、`render_tool_call_hover(...)`（约第 196 行）、`render_single_turn(...)`（约第 277 行）。

**`scrollback/render.rs`** — 可见窗口的逐 entry 绘制与选择几何构建：

- `render_scrolled_entries_with_selection_boundaries(buf, viewport, entries, scroll_offset, selected_idx, theme, appearance, entry_layouts_cache, tick, mouse_pos, dim_from_entry, search_highlight, content_y0, entry_index_base, media_paths, group_spans, cwd) -> ScrollRenderResultWithBoundaries`（约第 225 行）— **逐 entry 绘制核心**：按缓存高度/间隙推进虚拟 y，裁剪可见范围，算 `top/bottom_clipped` 与 `skip_rows`，构造 `EntryRenderer` 绘制，随后 `ensure_cached` 取缓存输出构建 `VisibleBlockGeometry`、`selection_model` 与选择边界。
- `render_scrolled_entries_with_scratch(...) -> ScrollRenderResult`（约第 181 行，对外 API）、`struct ScratchBuffer(Buffer)`（约第 69 行，复用离屏缓冲）、`struct ScrollRenderResult { total_height, selection_model, selected_area, scroll_info, link_overlay, inline_media, diagram_affordances, ... }`（约第 142 行）、`timestamp_reserved_for_block(...)`（约第 54 行）、`map_hyperlinks_to_overlay(...)`（约第 834 行）。

**`scrollback/block.rs` / `scrollback/entry.rs`**：

- `pub trait BlockContent`（约第 42 行）— 块渲染接口：`output(ctx)->BlockOutput` 为主，另有 `accent`/`bullet`/`background`/`has_vpad`/`is_foldable`/`next_fold_mode` 等。
- `pub enum RenderBlock { Stub, UserPrompt, AgentMessage, ToolCall, Thinking, System, SessionEvent, BgTask, Subagent, Workflow, Btw, ContextInfo, MemoryCapture }`（约第 298 行，经 `delegate_block!` 宏委托）+ `impl RenderBlock::rendered_output(&self, ctx) -> RenderedBlockOutput`（约第 388 行）。
- `pub struct ScrollbackEntry { block, display_mode, ... }`（约第 61 行）+ `ensure_cached`/`cached_rendered_output_ref`/`effective_output`/`context_with_mode_and_budget`（约第 316/381/426/537 行）、`pub struct EntryId(u64)`（约第 30 行）。
- 块实现散在 `scrollback/blocks/`：`agent.rs`/`user.rs`/`thinking.rs`/`system.rs`/`session_event.rs`/`bg_task.rs`/`subagent.rs`/`workflow.rs`/`btw.rs`/`context_info.rs`/`markdown_content.rs`/`mermaid_content.rs`/`quote_bar.rs`，工具块在 `blocks/tool/`（`edit`/`execute`/`read`/`search`/`web_fetch`/`web_search`/`use_tool`/`list_dir`/`memory_search`/`sent_message`/`other`）。

### 5.10 `views/` 面板

**`views/dock/mod.rs`** — 面板坞：

- `pub fn render(buf, area, theme, data)`（约第 257 行）— **dock 主渲染**：`DockLayout::with_cap(counts, area.height)` 定行，逐项画 Header/Row/RevealRemaining 并做选中/悬停高亮。
- `fn section_header(...)`（约第 363 行）、`fn paint_row(...)`（约第 386 行，图标 + kind + description + activity + 右侧 meta/动作）、`stop_button_rect(...)`/`hovered_stop_button_rect(...)`（约第 474/487 行）、`queue_body_rect(...)`（约第 237 行）。
- `struct DockData {...}`/`DockCounts`（约第 163/139/196 行）、`enum DockItem { Header(Section), Row(Section,usize), RevealRemaining(Section) }`/`enum Section { Workflows, Subagents, Tasks, Watchers, Queued }`（约第 121/78 行）。

**`views/dock/layout.rs`** — dock 行预算分配：

- `struct DockLayout { rows, scrollable, visible, offsets, queue_body_rows }`（约第 67 行）、`with_cap(counts, cap) -> Self`（约第 84 行）— **布局核心**：`grant_rows` 分配额度，按 section 展开状态生成 Header/Row/RevealRemaining，`truncate(height)`。`grant_rows`/`share_rows`/`normalize_no_lone_rows`（约第 243/420/340 行，保证不出现孤立行）。
- `desired_height(data) -> u16`（约第 449 行）、`item_at(row)`/`visible_rows`/`row_offset`/`hidden_rows`/`queue_body_rows`/`total_rows`（约第 143/148 行起）、`is_show_all_needed(counts, section)`（约第 465 行）。

**`views/prompt_widget/mod.rs`**（3858 行）— 输入框控件（`TextArea` + 下拉/幽灵文本/图片 chip）：

- `pub struct PromptWidget { textarea, textarea_state, textarea_area, file_search, slash_controller, slash_state, suggestions, prompt_suggestion, images, ... }`（第 627 行）。
- `pub fn draw(&mut self, buf, area, overlay_area, style, info, voice) -> PromptRenderResult`（第 2979 行）— **输入框主渲染**：填底色、画 accent/边框、按 `vpad_top/text/info_block` 切分、渲染 textarea 与信息行、处理 overlay/voice。
- `pub fn desired_height(&self, area_width, style, has_info, max_height) -> u16`（第 1612 行）、`handle_key(&mut self, key) -> PromptEvent`（第 1690 行）→ `handle_key_inner`（第 1754 行）、`route_enter(&mut self, key) -> EnterOutcome`/`route_enter_with_newline_modifier`（第 2158/2165 行）、`handle_mouse`/`handle_mouse_scroll`/`handle_paste`（第 2231/2235/2286 行）。
- `stash(&mut self) -> StashedPrompt`/`restore(&mut self, stash)`（第 1048/1073 行）、`set_text`/`set_text_preserving`/`append_text`/`insert_replacing_selection(...)`（第 1124/1177/1184/2406 行，⚠️ 旧名 `insert_str_replacing_selection` 已更名）、🆕 `set_text_discarding_images(&mut self, text)`（第 1106 行 — 换模型/换会话时改文案并丢弃图片 chip）、`refresh_slash(&mut self, models)`/`accept_slash_completion(...)`/`completion_dropdown_*`（第 1206/1344/864 行起）、`insert_image(&mut self, image) -> Result<(), String>`/`drain_images`/`sync_images_with_textarea`（第 2357/2620/2415 行）、`render_info_line(...)`（第 3521 行）。

**`views/list_pane/`** — 通用可滚动列表控件（picker、块查看器、行查看器复用）：

- `pub struct ListPane<'a, T: ListItem> { items, focused, style }`（约第 29 行）、`impl StatefulWidget for ListPane`（约第 64 行）— **渲染管线**：切出底部输入栏、按溢出分滚动条区、`render_items`、角标、复制 toast、滚动条、底栏。`render_items`（约第 214 行）、`render_item_framework(...)`（约第 154 行，NoWrap 截断 vs Wrap 逐行）、`render_corner_indicators`/`render_bottom_bar`/`render_truncation_ellipsis`（约第 437/513/404 行）。
- `pub trait ListItem`（`mod.rs`，第 96 行起）— `content`/`prefix`/`desired_height`/`stable_id`/`search_text`/`copy_text` 等。

**`views/status_line/mod.rs`** — 状态行：

- `pub enum StatusLineFrame { Off, Reserved{padding}, On{display,padding} }`（约第 113 行）+ `height`/`padding`/`display`、`pub enum StatusLineDisplay { Segments(Vec<StatusSegment>), Text(SanitizedText) }`/`line_count()`（约第 105/153 行）。
- `pub fn render_status_line(buf, area, display, padding, theme) -> Vec<LinkSpan>`（约第 165 行）— **状态行渲染**：填底色、内缩、`styled_lines` 取行、逐行 `elide` 裁剪、`project_links` 生成链接 span。`styled_lines`/`themed(line, theme)`（约第 218/249 行）、`inner_width(width, padding)`/`struct RowSize { cols, lines }`（约第 213/200 行）。

**`views/agent.rs`（布局，2349 行）** — AgentView 的布局求解器：

- `pub struct AgentViewLayoutParams { ..., model_notice_height: u16 }`（第 103 行，🆕 `model_notice_height` 第 127 行）。
- `pub struct AgentViewLayout { status_bar, tasks, scrollback, todo, queue, btw, turn_status, banner, plugin_cta, follow_ups, dock, voice_recording, prompt, shortcuts, status_line, scrollback_content, scrollbar_x, timeline_x, timeline_width, model_notice }`（第 137 行，🆕 `model_notice: Rect` 第 156 行）。
- `pub fn AgentViewLayout::compute(params) -> Self`（第 178 行）— **布局求解器**：按短终端规则裁剪 cta/follow_ups、堆叠各行（含 scrollback 最小 5 行）、`model_notice_height > 0` 时插入 `Constraint::Length(model_notice_height)`，算出所有 Rect。
- `pane_areas(&self)`/`inner_width(area, cfg, compact)`/`rows_available_for_prompt(params)`（第 444/433/423 行）、`PaneAreas::hit_test(col,row) -> Option<ActivePane>`（第 61 行）、`fill_background(...)`/`render_scrollbar(...)`/`render_entry_hover(...)`（第 456/623/522 行）、`effective_compact(user_compact, terminal_rows) -> bool`（第 97 行）。

**🆕 本次漂移新增的 `views/` 模块**（用于承载模型提示与通用列表/弹窗）：

- `views/model_notice_banner.rs`（81 行）+ 测试 `model_notice_banner_tests.rs` — 模型提示横幅（如「已切换到 X 模型」）。两件套：`height(notice, width) -> u16`（第 26 行，给布局预留行）、`render(area, buf, notice)`（第 31 行，画横幅）；数据源 `session.models.current_notice()`。被 `AgentView::draw` 与 `views/welcome/mod.rs`（`model_notice: Option<&ModelNotice>` 第 698 行）共同消费。
- `views/modal_list.rs`（171 行）+ 测试 `modal_list_tests.rs` — 抽取出的**通用模态列表绘制工具箱**（`RowStatus`/`RowTag`/`ListRow`、`DETAIL_INDENT`/`NAME_INDENT`），供 settings/remote-control/extensions 等模态复用，替代散落的列表绘制。
- `views/extensions_modal/skills_tab.rs`（151 行）— extensions 模态的「Skills」页签：编号式 fetch（`next_skills_fetch`/`show_skills_listing`）保证旧答案不覆盖新列表，从 `extensions_modal.rs` 拆出（后者 +32/−6）。
- 其他相关改动：`views/fps_hud.rs`（+142/−18，改为 **3 行 HUD**，`overlay_height()` 返回 3）、`views/shortcuts_help.rs`（新增 `filter_entries`/`hint_matches_query` 第 354/413 行，用于速查过滤）、`views/welcome/mod.rs`（+34/−7，接入 model_notice）、`views/tasks_pane.rs`（+20/−421）/`views/turn_status.rs`（+45/−225）大幅瘦身、`views/dashboard/*`（`state.rs`/`chrome.rs`/`row.rs`/`peek.rs`/`render.rs` 均有调整）、`views/agents_modal.rs`（+42/−128）、`views/file_search/line_viewer.rs`（+85/−1，注释关闭按钮）。

### 5.11 `xai-ratatui-textarea`（自研多行输入控件）

**`src/editor.rs`** — 无 UI 的文本编辑内核（缓冲区 + 编辑命令 + 计划/校验）：

- `pub enum EditCommand { Insert(char), MoveGraphemeLeft/Right, MoveWordLeft/Right(WordStyle), MoveLogicalLineStart/End, DeleteGraphemeBackward/Forward, DeleteWordBackward/Forward(WordStyle), DeleteToLineStart/End }`（约第 20 行）+ `category()`/`selection_collapse_edge()`。`pub enum Movement { Command(EditCommand, HorizontalEdge), VisualRowUp/Down/Start/End, LogicalLineStart/End }`（约第 55 行）。
- `pub struct EditBuffer { text, cursor_byte, identity: Arc<BufferIdentity>, generation }`（约第 212 行）+ `plan_command(&self, command, atomic_byte_ranges) -> EditPlan`（约第 346 行）— **命令 → 编辑计划**（不含 UI）。`plan_replace_byte_range(&self, range, replacement, atomic)`（约第 322 行）、`apply_plan(&mut self, plan) -> Result<EditOutcome, ApplyEditPlanError>`/`apply(&mut self, command) -> EditOutcome`（约第 480/486 行）、`validate_plan(&self, plan)`（约第 514 行，`StalePlan`/`InvalidRange`/`RemovedTextMismatch`/`InvalidCursor`）。
- `single_line_viewport(&self, display_width)`/`single_line_viewport_with_atomic_ranges(...)`（约第 586/590 行）、`pub struct EditPlan`/`EditDelta`/`enum EditOutcome { Unchanged, CursorOnly, TextOnly(EditDelta), TextAndCursor(EditDelta) }`（约第 158/127/133 行）。
- 边界工具：`previous_word_boundary`/`next_word_boundary`、`line_start_at`/`line_end_from`、`normalize_atomic_ranges`、`floor/ceil_grapheme_boundary` 等（约第 642 行起）。

**`src/editor_keys.rs`** — `pub fn classify_key_event(event) -> Option<EditCommand>`（约第 33 行）— **按键 → 编辑命令的唯一映射**（含 C0 控制字节、Kitty 退格变体、Ctrl/Alt/Super 组合）。`fn resolve_movement(event) -> Option<Movement>`（约第 6 行）、`backspace_command`/`delete_command`/`shifted_char`（约第 187/198/179 行）。

**`src/textarea.rs`** — `TextArea` 状态控件：文本 + 元素 + 选择 + 鼠标 + 滚动 + 撤销 + 渲染：

- `pub struct TextArea { text: EditBuffer, wrap_cache, elements, selection, clipboard_provider, scroll_override, show_scrollbar, click_tracker, ... }`（约第 180 行）、`pub struct TextAreaState { scroll: u16 }`（约第 264 行）、`pub struct TextElement { id, range, kind, display }`/`ElementId`/`ElementKind`（约第 99/31/45 行）。
- `pub fn input(&mut self, event: KeyEvent)`（约第 1870 行）— **按键总入口**：Shift+移动扩展选区；有选区时按类别拦截（插入替换/删除/cut/copy）；再走 `resolve_movement`/`classify_key_event`；最后处理 Enter/Ctrl-Y undo-redo/Ctrl-V paste 等。
- `handle_mouse(&mut self, ...)`（约第 1076 行）、`tick(&mut self, area, state) -> MouseAction`（约第 1040 行）、`render_lines(&self, area, buf, lines, range)`（约第 3225 行）— **逐行绘制核心**：把一行按「纯文本→元素→纯文本」分段绘制，再第二遍叠加选择高亮。
- `impl StatefulWidgetRef for &TextArea`（约第 3146 行）— 带滚动的渲染（`content_width`→`wrapped_lines`→`effective_scroll`→`render_lines`→`render_scrollbar`）。`render_scrollbar`（约第 3168 行）、`wrapped_lines(&self, width)`/`element_aware_wrap_ranges`/`greedy_wrap_segment`（约第 2885/2918/2968 行）、`effective_scroll(...)`/`content_width(...)`（约第 3074/3112 行）。
- 选区 API：`selection_range`/`selected_text`/`delete_selection`/`insert_str_replacing_selection`/`set_selection(...)`（约第 896/922/934/947/960 行）。撤销栈：`undo`/`redo`/`can_undo`/`can_redo`/`begin_undo_group`/`end_undo_group(...)`（约第 2144/2160/2175/2186/2196 行）。元素：`insert_element`/`replace_range_with_element`/`element_at_cursor`/`restore_elements(...)`（约第 2555/2568/2620/2658 行）。坐标映射：`screen_position_of`/`screen_spans_of_range`/`buffer_pos_at_screen`/`element_at_screen(...)`（约第 723/748/810/870 行）。`desired_height(&self, width) -> u16`（约第 682 行）、`cursor_pos`/`cursor_pos_with_state(...)`（约第 687/694 行）、`is_undo_input(key) -> bool`（约第 335 行）。

**`src/wrapping.rs`** — `pub fn word_wrap_line<'a, O>(line: &Line, width_or_options) -> Vec<Line>`（约第 177 行，样式保留的整行换行）、`wrap_ranges`/`wrap_ranges_trim(text, opts) -> Vec<Range<usize>>`（约第 9/45 行）、`pub struct RtOptions<'a>`（约第 71 行）、`slice_line_spans`/`word_wrap_lines`/`word_wrap_lines_borrowed`（约第 318/271/296 行）。

**`src/render/mod.rs` 与 `render/line_utils.rs`** — `line_to_static(line) -> Line<'static>`/`push_owned_lines(src, out)`/`prefix_lines(lines, initial, subsequent)`/`is_blank_line_spaces_only(line)`（约第 5/21/40/29 行）。

### 5.12 `xai-ratatui-inline`（内联视口终端）

标准 ratatui `Terminal` 只能全屏重绘。本 crate 提供**内联视口**：TUI 只占屏幕底部若干行，其上方是终端原生 scrollback。它让「已提交」的内容 `insert_before` 到视口上方（进入 scrollback），并处理内联视口在 resize 时的重排/重绘。

**`src/lib.rs`** — 导出 `Terminal`、`TerminalLike`、`with_synchronized_output`、`resize_purge_rerender`、`resize_viewport_height`、`emit_to_scrollback`、`split_into_line_segments`、`LinkSpan`、`WidthShrink`（约第 12 行）。

**`src/terminal.rs`**：

- `pub struct Terminal<B> { backend, buffers: [Buffer;2], current, hidden_cursor, viewport, viewport_area, last_known_area, last_known_cursor_pos, width_shrink, frame_count, link_ids, link_tables }`（约第 148 行）— 双缓冲 + 视口 + 链接层。
- `pub fn insert_before<F>(&mut self, height, draw_fn) -> io::Result<()>`（约第 644 行）— **把内容插到内联视口上方**；非 inline 视口无操作。`insert_before_rows(&mut self, rows)`（约第 661 行，wrap-aware 的 ANSI 行插入）、`insert_before_no_scrolling_regions`/`write_semantic_rows`/`insert_before_scrolling_regions`（约第 737/864/917 行）。
- `pub fn set_viewport_height(&mut self, new_height) -> io::Result<()>`（约第 692 行，增长时若溢出屏幕则先 `scroll_up` 把被覆盖行推入原生 scrollback）。
- `pub fn flush(&mut self) -> io::Result<bool>`/`flush_with_links(&mut self)`/`emit_frame_with_links(...)`（约第 343/399/1126 行，双缓冲差分输出，可选 OSC-8 链接）、`pub fn draw<F>(&mut self, render_callback) -> io::Result<CompletedFrame>`/`try_draw`（约第 484/497 行）。
- `pub fn set_frame_links(&mut self, spans: &[LinkSpan])`/`diff_large_with_links(...)`/`write_osc8_open/close(...)`（约第 357/1086/68 行）、`resize(&mut self, area)`/`autoresize(&mut self)`/`compute_inline_size(...)`/`reflowed_cursor_offset(&self, new_width)`（约第 438/470/1196/1257 行）、`set_viewport(&mut self, viewport)`/`set_viewport_area(&mut self, area)`（约第 1278/1309 行）。
- `pub struct LinkSpan`/`enum WidthShrink { Truncates, Rewraps }`（`Truncates` 带 `#[default]`；旧写法 `Reflows` 与当前源码不符）/`OurFrame<'a>`（约第 23/34/109 行）。

**`src/segment.rs`** — `pub fn split_into_line_segments<'a>(input, term_width) -> Vec<LineSegment<'a>>`（约第 84 行）— **零拷贝行切分**：用 `anstyle_parse` VTE 状态机逐字节解析，按可视宽度在 char 边界换行，处理 CR/LF/ANSI/宽字符。`pub struct LineSegment<'a> { content: &'a str, ends_with_crlf: bool }`（约第 8 行）。

**`src/scrollback.rs`** — `pub fn emit_to_scrollback<T: TerminalLike>(terminal, content) -> io::Result<()>`（约第 13 行）— **把一段文本提交到 scrollback**：清视口区、打印分段内容、为视口预留空行、把视口移到新位置并清空 back buffer。

**`src/resize.rs`** — `resize_purge_rerender<T: TerminalLike>(terminal, history) -> io::Result<()>`（约第 11 行，resize 后清屏 + 重放历史）、`resize_viewport_height<T: TerminalLike>(terminal, new_height)`（约第 68 行）。

**`src/common.rs`** — `pub trait TerminalLike { type Writer; size/viewport_area/clear/reset_back_buffer/set_viewport_area/writer_mut }`（约第 15 行）、`with_synchronized_output<T,F,R>(terminal, f) -> io::Result<R>`（约第 70 行，用同步更新序列 `?2026h/l` 包裹输出防闪）。

### 5.13 本子系统调用链总览

**帧渲染主链（消息流）**

```
AppView 事件循环 → AgentView::draw
  → note_terminal_size → AgentViewLayout::compute → fill_background
  → ScrollbackPane::render_with_scratch_and_selection_boundaries
       → render_with_sticky_headers（compute_sticky_layout）
       → render_content → render_scrolled_entries_with_selection_boundaries
       → ScrollbackEntry::ensure_cached / RenderBlock::rendered_output
       → EntryRenderer::render → Buffer
  回程 ScrollRenderResult → update_scrollback_selection_state → 选择高亮/滚动条
```

**输入主链**

```
handle_input → handle_input_with_prompt_paging → handle_input_inner
  →（覆盖层优先：image/video/gboom/workflows/goal/active_modal/btw →）
  → key_owner() 排名
       ├─ KeyOwner::Card       ⇒ handle_card_esc / card_esc
       ├─ KeyOwner::LineViewer ⇒ handle_line_viewer_key
       ├─ KeyOwner::BlockViewer⇒ handle_block_viewer_key
       └─ KeyOwner::Pane       ⇒ handle_scrollback_key / handle_dock_key / PromptWidget::handle_key
            → TextArea::input → classify_key_event/resolve_movement
            → EditBuffer::plan_command → apply_plan
```

**鼠标选择链**

```
handle_input_inner(Mouse) → begin_pending_text_drag / begin_pending_block_drag
  → handle_scrollback_drag_motion → update_text_drag / update_active_block_drag
  → finish_text_drag / finish_block_drag → reconstruct_drag_copy
  → copy_to_clipboard_debounced → show_toast
```

**布局与终端**

```
AgentView::draw → AgentViewLayout::compute → pane_areas()（PaneAreas::hit_test）
文本 I/O → xai-ratatui-inline::Terminal::draw → flush（diff_large_with_links / emit_frame_with_links）
提交历史 → insert_before → split_into_line_segments
resize → resize_purge_rerender / resize_viewport_height / set_viewport_height
```

---

## 6. 横切主题与设计要点

### 6.1 单向数据流：`InputOutcome` / `Action` / `Effect`

贯穿全系统的契约：

```
终端事件 ──► AppView::handle_input* ──► InputOutcome
   { Action | ActionThenForward | ActionPair | ArmPending | Changed | Unchanged }
                     │
                     ▼
       dispatch::dispatch(action, app)        // 同步改状态，返回 Vec<Effect>
                     │
                     ▼
       process_effects(effs, &mut tasks, ...) // effects::execute → JoinSet::spawn(TaskResult)
                     │
                     ▼
       主循环 tasks.join_next() → dispatch(TaskComplete) → after_task_complete_dispatch
```

要点：**输入不直接产生副作用**；`AppView` 是唯一可变状态容器；异步结果统一经 `TaskResult` 回流。这让 dispatch 可测试（sans-IO）。

### 6.2 终端 teardown 的单一定义

`emit_terminal_teardown_sequences(mode, inline_cursor_row)`（`app/terminal_restore.rs`）是**在线上字节序的唯一定义处**，三条路径（正常退出 / panic hook / 信号路径）全部复用。所有 join 都是**有界**的（reader 250ms、writer 2s），避免「终端不读 → `/quit` 永久挂起」。

### 6.3 事件循环卡顿检测

`drain_and_process` 前后用 `event_loop_stall::input_wait` 测等待，`StallRollup::observe` 按 60s 窗口滚动累积**最差一次** stall + 该时刻后台活动快照，超窗或退出时经 `emit_event_loop_stall → event_loop_stall_event` 上报 telemetry。

### 6.4 设计要点速记

- **入口分层清晰**：`main.rs`（进程外壳/子命令分流）→ `app::run`（TUI 装配）→ `event_loop::run`（循环）→ `AppView`（状态机）。
- **`biased` select! 的优先级是显式设计**：cancel/quit > writer 反馈 > ACP > 任务完成 > 输入 > 渲染/定时器 > voice（故意最后，防饿死）。
- **终端状态是进程级 + 无参可读**：`ScreenMode`/`MINIMAL_MODE_ACTIVE`/`CURSOR_STYLE_FORCED` 等原子让 panic hook、信号路径、post-loop restore 在无 `AppView` 时也能正确 teardown。
- **渲染热路径的两条硬约束**：① 一切 `Buffer` 写入走 `SafeBuf`（resize 竞态下区域可能短暂越界，原生 API 会 panic）；② `#![deny(clippy::indexing_slicing)]` 全局禁用索引切片。
- **写线程 + 序号水位线**：`WriterSync` 的 `reserve_sequence` 保证子进程接管 tty 前无乱序帧；`send_payload` 的单生产者约束（`OnceLock<ThreadId>`）防第二线程重排终端输出。
- **主题/颜色的极性安全**：`Theme::current()` 是唯一取色入口，先量化再适配；`is_bandless()`（`bg_visual == Reset`）是所有「反色/装饰回退」分支的判据；terminal-native 下近灰 token→`Reset`、彩色 token→基础 16 色。
- **能力探测全部进程级缓存**（`OnceLock`/`AtomicU8`）：终端品牌/复用器、颜色能力、Kitty 键盘、DA2/XTVERSION、显示刷新率、legacy ConHost 判定。

---

## 附录 A：关键文件索引

| 层    | 路径                                                                                                                                                                                                            | 职责                                                    |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 入口   | `crates/codegen/xai-grok-pager-bin/src/main.rs`                                                                                                                                                               | 进程外壳、子命令分流、runtime                                    |
| 入口   | `crates/codegen/xai-grok-pager-bin/src/agent_command.rs`                                                                                                                                                      | `agent stdio` 信号/生命周期                                 |
| 装配   | `xai-grok-pager/src/app/mod.rs`                                                                                                                                                                               | `app::run`、`init_terminal`、模式/leader 解析               |
| 循环   | `xai-grok-pager/src/app/event_loop.rs`                                                                                                                                                                        | 主循环、`Presenter`、`drain_and_process`、`process_effects` |
| 状态   | `xai-grok-pager/src/app/app_view.rs`                                                                                                                                                                          | `AppView` 根状态机、输入路由、`draw_inner`、`tick`               |
| 状态   | `xai-grok-pager/src/app/reader_thread.rs`                                                                                                                                                                     | stdin 读线程                                             |
| 拆机   | `xai-grok-pager/src/app/terminal_restore.rs`                                                                                                                                                                  | teardown 单一定义、panic hook                              |
| 观测   | `xai-grok-pager/src/app/event_loop_stall.rs`                                                                                                                                                                  | 卡顿检测                                                  |
| 会话视图 | `xai-grok-pager/src/app/agent_view/{mod,render,panes,selection,viewer,input,key_owner,modals,notices,jump}.rs`                                                                                                | AgentView 各面                                          |
| 消息流  | `xai-grok-pager/src/scrollback/{scrollback_pane,render,block,entry}.rs` + `blocks/`                                                                                                                           | 消息块渲染内核                                               |
| 面板   | `xai-grok-pager/src/views/{agent,dock/,prompt_widget/,list_pane/,status_line/}`                                                                                                                               | 布局与各控件                                                |
| 输入   | `xai-grok-pager-render/src/input/{key,keyboard_normalizer,line_editor,mouse,macos_modifiers,terminal_support,scroll_log}.rs`                                                                                  | 输入解析                                                  |
| 终端探测 | `xai-grok-pager-render/src/terminal/{mod,keyboard,kitty_keyboard,probe,da2,xtversion}.rs`                                                                                                                     | 环境/能力探测                                               |
| 渲染   | `xai-grok-pager-render/src/render/{draw,wrapping,line_utils,scrollbar,highlight,color,renderable,safe_buf,terminal_output,osc8,bidi,tool_paths,image_overlay,video_overlay,gboom_overlay,preview_overlay}.rs` | 渲染管线                                                  |
| 宿主   | `xai-grok-pager-render/src/host/{mod,display_refresh}.rs`                                                                                                                                                     | 平台/刷新率                                                |
| 主题   | `xai-grok-pager-render/src/theme/{mod,cache,color_support,env_appearance,system_appearance,osc11,md_style,tokyonight,groknight,grokday,rosepine,oscura,terminal_default}.rs`                                  | 主题与颜色                                                 |
| 外观   | `xai-grok-pager-render/src/appearance/{mod,config,cache,scroll_mode,text_selection,permission_cursor,follow_up_behavior,render_mermaid,watcher}.rs`                                                           | 运行时外观                                                 |
| 控件   | `xai-ratatui-textarea/src/{editor,editor_keys,textarea,wrapping}.rs`                                                                                                                                          | 多行输入控件                                                |
| 控件   | `xai-ratatui-inline/src/{terminal,segment,scrollback,resize,common}.rs`                                                                                                                                       | 内联视口终端                                                |

## 附录 B：建议阅读顺序

1. **先建骨架**：`xai-grok-pager-bin/src/main.rs` → `app/mod.rs::run` → `event_loop.rs::run` 的 select! arm 列表 → `app_view.rs` 的 `AppView` 字段分组。读到这里就有了「进程怎么起来、循环在转什么、状态装在哪」的全局图。
2. **再走一条最热的链路**：`app_view.rs::handle_input_at_with_paste_provenance` → `agent_view/input.rs::handle_input_inner` → `key_owner.rs::key_owner` → `dispatch/router.rs::dispatch` → `event_loop.rs::process_effects`。这条链串起了「输入 → 动作 → 副作用」。
3. **再看一帧怎么画出来**：`app_view.rs::draw_inner` → `render/draw.rs::draw_frame` → `agent_view/render.rs::draw` → `scrollback/scrollback_pane.rs::render_with_scratch_and_selection_boundaries` → `scrollback/render.rs::render_scrolled_entries_*` → `scrollback/wrappers/entry_renderer.rs`。
4. **最后按需深入**：输入解析细节看 `input/` 与 `terminal/`；颜色/主题看 `theme/`；外观参数看 `appearance/`；自研控件看两个 `xai-ratatui-*`；消息块看 `scrollback/blocks/`。

---

*本文档为只读源码调研产物，未改动任何源码。所有「约第 N 行」为采集时快照（正文基线 `HEAD = 7d70d52c`；§1.5 的 `Presenter`/`drain_and_process`/`process_effects`/臂序另在 `42f4d7d3` 复核），请以函数名为定位主锚点。机制层的对读文档是[第 8 篇《TUI 交互循环与渲染》](../sourceReader/08-TUI交互循环与渲染.md)。*
