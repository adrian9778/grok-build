# 新层：per-command 沙箱策略子系统（xai-grok-sandbox::command）

主题：docs 第 11 篇只覆盖进程级 `SandboxManager`（Landlock/Seatbelt/seccomp，启动时一次），本次 merge 新增
`crates/codegen/xai-grok-sandbox/src/command/` 与 workspace 侧 `sandbox/` + `permission/sandbox_*` 配对：
新目录 37 个文件 = 19 个非测试 `.rs`（8464 行）+ 15 个 `*_tests.rs` + 3 个内嵌 `.sbpl`，合计 21583 行。
每条结论均带符号锚点；绝对行号仅为本快照（HEAD）。

约定：锚点 = `文件` · 符号：`Name`（+N 为符号体内相对偏移，+0 = 定义行；绝对行号写在括号里，标注「快照」）。简写
`CMD/` = `crates/codegen/xai-grok-sandbox/src/command/`，`WS/` = `crates/codegen/xai-grok-workspace/src/`，
`TOOLS/` = `crates/codegen/xai-grok-tools/src/`。

## 1. 这一层为什么存在（与进程级沙箱的分工）

| 维度 | 进程级（旧层） | per-command（新层） |
|---|---|---|
| 施加时机 | 守护进程启动一次 | 每次 spawn 前重新构建 |
| 粒度 | 整个进程树共用一份粗 profile | 每条命令一份 `SandboxPolicy` |
| 网络 | 进程级放开（agent 要调 LLM API），子进程靠 seccomp 一刀切断网 | loopback egress 代理 + 逐 host/port 授权（可续期） |
| 写 | 启动时固定的 allow 集 | `write_roots` + 违规→提问→grant→重放 |
| 读 | — | `ReadPolicy::Roots` 可选限读（含 git 元数据） |
| 平台 | Linux Landlock + bwrap bind-over + seccomp；macOS Seatbelt | **仅 macOS Seatbelt**（v1） |
| 拒用方式 | apply 失败即进程受限失败 | 包装失败 = 该命令不跑，绝不静默裸跑 |

- 旧层定性（对照证据）：`crates/codegen/xai-grok-sandbox/src/lib.rs` · 模块 doc：「Applied once at process startup… Network is
  left open at the process level (agent needs LLM API); child network is blocked per-subprocess via seccomp」（快照 :10-11）；
  `SandboxManager::new(ProfileName, workspace).apply().install()`（doc 示例，快照 :18-25）。
- 新层定性：`CMD/mod.rs` · 模块 doc：「policy a single child command runs under, the backend that renders it into an OS wrapper,
  the decoder that turns a denial into a grantable Violation, and the expiring grant store that widens the next policy」（+0，快照 :1-3）。
- 新层四条独立于后端的不变量：`CMD/mod.rs` · 模块 doc 列表（+5..+11）：
  1. **daemon 永不被 confinement**（「Nothing here calls the process-wide `nono` sandbox」）；
  2. wrapper 失败 = 拒绝运行，绝不静默无沙箱启动；
  3. protected 地板由每个后端最后渲染、永不可 grant（加载时与 `with_grant` 双重拒绝）；
  4. 过期在每次 build 时经注入 `Clock` 求值，绝不在 load 时。
- 关键设计意图：旧层无法回答「这条命令能不能写 `dist/`、能不能连 `api.github.com:443`、能不能读 `.git/hooks`」，
  也无法在拒绝后给用户一个**带 TTL 的、可撤销的、按作用域收窄的**授权回路。新层把「拒绝」变成产品交互。
- Linux 现状（重要修正）：`CMD/detect.rs` · `HostProbe::preferred_backend`（+0，快照 :48）在非 macOS 返回
  `BackendChoice::Unavailable { reason: "no per-command sandbox backend for {os}: v1 has Seatbelt on macos only …" }`。
  `grep -rn bwrap|landlock CMD/` 无匹配 ⇒ **command 层没有任何 Linux 后端**；Linux 侧 per-command 强制 = 无（旧层仍适用）。

## 2. 模块地图（非测试文件；一句话职责 + 主入口符号）

| 文件 | 职责 | 主入口符号 |
|---|---|---|
| `CMD/mod.rs` | 门面 + 不变量声明 + 统一 re-export | 顶层 `pub use`（+30..+60，快照 :30-60） |
| `CMD/policy.rs` | policy-as-data：从输入构建一次命令的策略 | `SandboxPolicy::build`（+0，快照 :282）→ `build_at_pin`（+16） |
| `CMD/policy/apply.rs` | grant 施加 / 是否会允许 / 地板判定 | `with_grant`（+0，快照 :36）、`would_allow`（+90）、`is_protected`（+164） |
| `CMD/backend.rs` | 后端抽象 + 唯一 spawn 入口 | `wrap_for_mode`（+0，快照 :218）、trait `SandboxBackend`、`OriginalArgv`、`RenderedPolicy` |
| `CMD/backend/seatbelt.rs` | `#[cfg(target_os="macos")]` 安装 sandbox-exec 包装 | `SeatbeltBackend::wrap`（+0，快照 :61）、`install_wrapper`（+34）、`probe_sandbox_exec`（+158） |
| `CMD/backend/seatbelt_profile.rs` | SBPL 渲染器（规则顺序 = 语义） | `pub(crate) render_enforce`（+0，快照 :42） |
| `CMD/backend/sbpl/*.sbpl` | 内嵌基底策略（**逐字抄自 OpenAI Codex CLI** commit 93b44c3a） | `base.sbpl` (+25 `deny default`)、`platform_defaults.sbpl`、`preferences.sbpl` |
| `CMD/detect.rs` | **宿主探测/后端选择**（不是命令分类） | `HostProbe::run`、`preferred_backend`、`detect_backend`（+0，快照 :187） |
| `CMD/grants.rs` | grant 数据模型（subject/scope/expiry/decision/host pattern） | `GrantSubject`、`GrantScope`、`Expiry`、`HostPattern`、trait `Clock` |
| `CMD/grant_store.rs` | TOML 持久化 + flock 读改写 + 过期裁剪 | `GrantStore::{open,add,revoke,live_allows}`（`add` 快照 :371）、`edit_rows_locked`（+0，快照 :842） |
| `CMD/protected.rs` | 不可 grant 的地板表与组装 + 文件原语 | `floor_with_unread`（+0，快照 :1023）、`is_protected`（+0，快照 :134）、`hard_linked_protected_file`（+0，快照 :1235） |
| `CMD/git_config.rs` | 以 git 的方式读 git 元数据，产出保护项 | `git_entries_in`（+0，快照 :204）、`GitConfigEnv`、`GitMetadataUnread` |
| `CMD/violation.rs` | 拒绝 → 可 grant 的 `Violation` | `decode`（+0，快照 :372）、`refused_under_grant`（+36）、`Violation::produces_card`（+0，快照 :228） |
| `CMD/violation/coarse.rs` | **唯一解码通道**：exit + stderr 关键词 | `decode_coarse` |
| `CMD/violation/coarse/macos.rs` | Seatbelt `deny(1) <op> <target>` 报告解析 | `deny_report`（+0，快照 :16）、`network_report`（+0，快照 :37） |
| `CMD/violation/propose.rs` | 提议最小可 grant 目标 | `propose`、`proposal_dir`、`is_too_broad` |
| `CMD/violation/attribute.rs` | 归属：这条命令是否真的指向该目标 | `OwnTargets{trees,named}` |
| `CMD/observe.rs` | Observe 模式的内存计数（无内容、无阻塞） | `ObserveSummary::record`、`WouldBlock`、`WouldVerdict` |
| `CMD/canonical.rs` | 路径恒等（realpath/firmlink/APFS/NFC） | `canonical_path`、`ServedRoot`、`VolumeRule`、`is_within` |
| `CMD/env.rs` | 子进程环境过滤/注入 | `apply_env_policy`（+0，快照 :126）、`apply_env_set_only`（+17） |
| `xai-grok-config/src/sandbox_mode.rs` | 模式解析纯逻辑（被 `command::mode` re-export） | `SandboxMode::resolve`、`resolve_on_host`、`RefusedLayers` |

Workspace 侧配对（详见 §9）：`WS/sandbox/{mod,launch,calls,network,grants,result_path}.rs`、`WS/sandbox_mode.rs`、
`WS/permission/{sandbox_gate,sandbox_wire,sandbox_network}.rs`、`TOOLS/sandbox_launch.rs`。

## 3. 核心链路（命令请求 → 策略 → 渲染 → spawn → 违规 → 提问/重放）

标注：`[in-proc]` 同进程调用；`[lock]` 取锁；`[await]` 异步点；`[task]` spawn_blocking/线程；`[flock]` 跨进程文件锁；
`[proc]` 进程边界；`[wire]` hub/桌面跨进程往返。

1. **[in-proc] 工具侧准备**：spawn 点（`TOOLS/computer/local/terminal.rs` 等）持 `tokio::process::Command`，调注入接缝
   `TOOLS/sandbox_launch.rs` · trait `SandboxLaunch::prepare`（+0）。接口只吃 argv/cwd，不吃 builder；模块 doc 明确：
   **stdio / kill_on_drop / detach / `child_net::restrict_child_network` 必须在 prepare 之后再装**（`wire_prepared`）。
2. **[in-proc][lock] 模式与策略**：`WS/sandbox/launch.rs` · `prepare_inner`（+0，快照 :132）
   = `mode = held pin else self.mode().max(floor)` → `Off` 直接 None → `engaged` 检查（Observe 未 engage 也返回 None）
   → `refuse_unless_session_dir_safe` → 取 grants（`live_allows_now(session)` + call 域 `settling.once`）
   → `build_policy`（快照 :54）→ **清空 `policy.env.set`**（指针只能由 `point_at_proxy` 写，快照 :81）。
   策略内部：`CMD/policy.rs` · `SandboxPolicy::build`（+0）→ `build_at_pin`（+16）：pin 校验（`ServedRoot::check`）→
   地板组装 → 逐条 grant 施加，施加失败「warn + drop」（一条过期行只收窄，不拒全体）。
3. **[in-proc] 代理指针**：`point_at_proxy`：仅 `CallKind::Tool` 且将被包装时 `mint_call_credential` 逐 spawn 铸一次性
   token，`EnvPolicy::proxy_vars_at` 写入 8 个变量（`http://grok:<token>@127.0.0.1:<port>`，
   `NO_PROXY=localhost,127.0.0.1,::1`）。
4. **[in-proc] 模式分流（唯一入口）**：`CMD/backend.rs` · `wrap_for_mode`（+0，快照 :218）
   - `Off`：不碰 cmd，`Ok(None)`；
   - `Observe`：仅 `env::apply_env_set_only`，`Ok(None)`（照常跑，只记账）；
   - `Enforce`：无后端 → `Unavailable`；`policy.unread_git_metadata.first()` → 拒绝；
     `protected::hard_linked_protected_file` → 拒绝（`hard_link_refusal`，+45）；然后 `env::apply_env_policy` + `backend.wrap`。
5. **[proc] Seatbelt 安装**：`CMD/backend/seatbelt.rs` · `wrap`（+0，快照 :61）：逐写根 `refuse_symlinked_root` →
   `render_enforce`（`seatbelt_profile.rs` +0，快照 :42）→ `install_wrapper`（+34，快照 :95）：
   新建 `tokio::process::Command` 指向绝对 `/usr/bin/sandbox-exec`，args `[-p, profile, -D K=V…, --, prog, args…]`，
   逐条搬运 env/cwd，`pre_exec` 里 `mark_inherited_fds_cloexec`（`proc_pidinfo PROC_PIDLISTFDS`，32KiB 栈缓冲，
   失败退化为 3..`sysconf(_SC_OPEN_MAX)` 扫描；只有 0-2 存活）。
   渲染顺序（SBPL last-match-wins ⇒ 顺序即语义）：`base.sbpl`(`deny default`) → 读允许 → 写允许（`require-not` 挖洞 +
   目录 unlink 拒绝）→ 网络（只允许 `localhost:<proxy_port>` outbound）→ 偏好项 → **强制拒绝最后**（地板
   `deny file-write* file-link`、unix-socket 出站、每条 deny entry、`render_nodes` 四类 Node、祖先 unlink 钉、
   最后 `deny file-read*`）→ 收尾 `deny mach-lookup (xpc-service-name-prefix "")` 与
   `deny system-fcntl (fcntl-command 80 110)`（F_MAKECOMPRESSED/F_TRANSFEREXTENTS 可用只读 fd 改数据）。
   每条规则带 `(with message "<tag>")`，路径经 `(param "NAME")` 间接化防 SBPL 注入。
6. **[in-proc] 记账**：`prepare_inner` 末尾把 `CallRecord` 存进 `WS/sandbox/calls.rs` 的调用表（单锁、`MAX_OPEN_CALLS`，
   `CallOwner{session_id,policy,transport,command}`），供事后解码。
7. **[await] 结果回来**：`WS/sandbox/result_path.rs` · `run_shell_call_with_replay`（+0，快照 :145）：逐调用
   `sync_network` + `refresh_grants`，`ReplayBudget::One`（+32），跑完调 `after_shell_run`。
8. **[in-proc] 解码**：`WS/sandbox/mod.rs` · `WorkspaceSandbox::finish`（+0，快照 :978，async）：取 record →
   Off/Observe 走 `Ran` + metric；Enforce → `CMD/violation.rs` · `decode`（+0，快照 :372）→
   `Finished::Violation`（快照 :167）；若本次是 grant 后的重放则走 `refused_under_grant`（+36）；违规则
   `open_settlement`（+0，快照 :828）把 call 的 mode/grants 带过重放。
   解码次序：快拒（没跑在沙箱里 / 成功 / 126 / 127）→ `decode_coarse` → `would_allow`+`is_os_denial` 过滤 →
   `propose` → 未归属则降级（`BuildCaches` 例外：「a toolchain names its cache in no argv」）。
9. **[wire] 提问**：`WS/permission/sandbox_gate.rs` · `settle_violation`（+0，快照 :244）→ `decide`（+9）：
   `produces_card()==false` → Recorded；deny 行覆盖 → `rejected_by_row`；无 transport → Denied（fail-closed）；
   仅拒绝上限 → `settle_informational`（只发不等）；否则经 hub 发 `sandbox_violation` 卡 → 等用户答案。
10. **[in-proc] 落 grant + 重放**：Allow → `record_grant` → `CMD/grant_store.rs` · `GrantStore::add`（+0，快照 :371）→
    `edit`（快照 :141）→ **`[task]` `tokio::task::spawn_blocking`** → `edit_rows_locked`（+0，快照 :842）
    → **`[flock]`** `protected.rs` · `lock_in_turn`（`cfg(unix)` 快照 :692 / 非 unix 快照 :702）→ 重读 → 丢过期 →
    `HeldDir::replace`（0o600 原子换）；然后 `mark_replay`（`WS/sandbox/mod.rs` +0，快照 :1078）→
    `AfterRun::Replay`（`result_path.rs` +22）**同 call id 再 dispatch 一次**；第二次违规即终局（`ReplayBudget::Spent` 拒再重放）。
11. **网络旁路（命令执行中）**：`WS/sandbox/network.rs` 每 folder 一个 loopback 代理，decider 把未授权 origin
    挂成 held connection 并**在命令还活着时**发卡（`CMD/violation.rs` · `Replay::Resume{hold_id}`，唯一构造点即 decider；
    答案类型 `HoldAnswer`）→ `WS/permission/sandbox_network.rs` 落 host grant → 连接放行。
    `exited()`（`launch.rs`，`SandboxLaunch for WorkspaceSandbox` 实现）撤销 call credential、refuse 挂起、resync。

## 4. 机制分解

### 4.1 policy（`CMD/policy.rs`）
- 结构：`SandboxPolicy{read, write_roots, network, env, protected, build_cache_trees, unread_git_metadata}`。
- `ReadPolicy::{AllExcept{deny}, Roots{roots, deny}}`；`DenyEntry::{Path, Glob{root,tail}, TreeExcept{tree, except}}`，
  `covers()`：**不可解析的 glob 覆盖一切（fail-closed）**。
- `NetworkPolicy::{Off, Proxy{port}}`：doc 明示内核层网络策略只有这两个取值，**host grants 永不放宽内核策略**，
  放宽只发生在代理 decider 里。
- `EnvPolicy::default_excludes()`：`*KEY*,*SECRET*,*TOKEN*,*PASSWORD*,*CREDENTIAL*,*_PAT,LD_PRELOAD,LD_LIBRARY_PATH,DYLD_*`。
- `PolicyInputs`：workspace_root 必须是已 pin 的 `ServedRoot`；`control_socket_dir` **必填**（缺失即 PolicyError）；
  另含 profile/grants/proxy/tmp_dirs/grok_home/user_home/git_env。
- `read_denies_for`：秘密目录 + symlink 目标重影 + `GROK_HOME_SECRET_GLOBS`（auth*/credentials*）+ grants lock sidecar +
  其他 workspace 的 sessions（`TreeExcept`）+ profile denies + 控制 socket。
- `absolute_deny_entry`：`~` → canonical home，相对 → workspace 真实根。
- `WritableLocations`（daemon 单例，OnceLock）+ `record`/`holds`：由 `grant_store::recorded_write_roots` 播种。
- 失败语义：`PolicyError` 12 变体；`build_at_pin` 中单条 grant 施加失败 → warn 后丢弃，不整体拒绝。

### 4.2 apply / would_allow（`CMD/policy/apply.rs`）
- `with_grant`：deny 行**永不放宽**策略；`FsWriteRoot` 需通过校验且不与 family-denied / missing-holds 地板冲突，否则跳过。
- `GrantSubject::BuildCaches` → 追加 `BUILD_CACHE_TREES` 到 write_roots。
- `NetHost` 在无代理时只 warn：「network grant without an egress proxy has no enforcement point」。
- `would_allow`：先查地板（两种拼写都查）；`Net`/`Capability`/`Unknown` **一律不由策略判定允许**（代理说了算）。
- `is_protected`：额外覆盖 `git_dir_nodes`、`glob_prefix_nodes`、`missing_ancestor_nodes`（重命名防御）。
- `validated_grant_root` + `symlink_free_spelling`：index≤1 豁免；`NotFound` 终止遍历；其它错误 → `UninspectableRoot`（拒）。

### 4.3 backend（`CMD/backend.rs` + macOS）
- `BackendName` 只有一个变体 `Seatbelt`；`BackendCapabilities{reduced}`；`CallKind::{Tool, ShellInit}` ↔
  `CallId` 线上拼写前缀 `tool:` / `shell-init:`，`parse` 为逆。
- `CommandTag` = `grok-<call>`，是 SBPL `(with message …)` 归属标签的来源。
- trait `SandboxBackend::wrap` 契约：不 spawn、确定性、强制拒绝在最后、无回退。
- `probe_sandbox_exec`（seatbelt.rs +158，快照 :219）：TRIVIAL_PROFILE `(version 1)(allow default)` 跑一次
  `/usr/bin/true`，`PROBE_TIMEOUT=5s`，`ProbeFailure::{Spawn,Exit,Timeout}`，stderr 截 4096，
  子进程登记进 `xai_tty_utils::global_process_scope`。
- `detect_backend`（`CMD/detect.rs` +0，快照 :187）→ `Option<Box<dyn SandboxBackend>>`；`None` 的含义按模式分岔见 §6。
- `ProbedFile::{Unchecked,Missing,NotAFile,File{mode}}` 让 `sandbox.status` 能答「为什么没有后端」。

### 4.4 grants / grant_store
- `CMD/grants.rs`：`GrantId` = UUIDv7；`GrantScope::{Call,Session,Workspace{root},Global}`，`is_persisted` 排除 Call；
  `Expiry::{Ttl,At,Never}`；`GrantDecision::{Allow,Deny}`（deny 赢）；
  `Provenance{command≤200 字符, tool_call_id}`；`Grant.granted_by` ∈ `desktop:<device_id>` | `cli` | `hub:<session_id>`；
  `Clock`/`SystemClock`/`FixedClock` 注入。
- `HostPattern`（grants.rs）匹配规则：`*` 全放；`*.suffix` 只匹配**真子域**（不匹配 suffix 本身）；
  IP 字面量做规范化比较；忽略尾点。**decider 与 store 共用同一实现**（避免两处判定漂移）。
- `CMD/grant_store.rs`：落盘路径 `<grok_home>/sessions/<enc(root)>/sandbox_grants.toml` 与 `<grok_home>/sandbox_grants.toml`；
  session 行只在内存（键为 hub session），call 行**永不进 store**。
  `Commit{signature:(mtime,len,inode), rows}`；写路径 = flock `.lock` sidecar → 锁内重读 → 丢过期 →
  `HeldDir::replace`（owner-only 0o600 原子替换 + 落地 inode 校验 + fsync）；**内存跟随磁盘，绝不反向**。
  `Store::{Create,ExistingOnly}`：revoke 永不创建文件。`refused_subject`：相对/受保护/符号链接/过宽 一律拒。
  `allows_not_denied`（+0，快照 :790）+ `subject_covers`/`subject_cuts`：deny 遮蔽 allow，**切分型 deny 随 allow 一起走**。
  `live_shared`（+0，快照 :338）：某个文件读不到时 fail-closed，只共享 deny 行。
  `MAX_GRANTS_FILE_BYTES=1MiB`、`GRANT_LOCK_WAIT=5s`；`parse_rows` 丢坏行只 warn 一次并把未来 `granted_at` 夹回。

### 4.5 protected（地板）
- `Protected::{Path,Glob,TreeExcept,Node}` + `covers/reaches_into/anchor`；`is_protected`（+0，快照 :134）双拼写比较。
- 表（`CMD/protected.rs`，均为常量表）：`WORKSPACE_PROTECTED_SUBPATHS`（`.grok/.cursor/.claude/.vscode/.idea`）、
  `GIT_DIR_PROTECTED_ENTRIES`（hooks、config、config.worktree、info）、`DAEMON_SETTINGS_FILENAME`（workspaced.toml）、
  `GROK_HOME_PROTECTED_NAMES`（约 26 项）、`HOME_PROTECTED_FILES`（约 30）、`HOME_PROTECTED_DIRS`（约 12，含 macOS
  LaunchAgents）、`HOME_PROTECTED_TOOL_TREES`（6）、`VERIFIED_BUILD_CACHES`（10，摘要自校验 ⇒ 默认可写）、
  `BUILD_CACHE_TREES`（9，未校验 ⇒ 需一张 `BuildCaches` 卡）、`SECRET_READ_DENY_DIRS`（9）、`SECRET_READ_DENY_FILES`（7）、
  `GROK_HOME_SECRET_GLOBS`（auth*/credentials*）。
- `floor_with_unread`（+0，快照 :1023）：完整组装 = 各表 + `TreeExcept(grok_home except ws 或 command dir)` +
  sessions `TreeExcept` + grant 文件与 `linked_grant_files` + symlink 目标重影。
  模块 doc 自陈**已承认的局限**：嵌套仓库的 `.git` 未覆盖。
- 文件原语：`FileOwner`；`open_nofollow`（`cfg(unix)`：`O_NOFOLLOW|O_NONBLOCK` + fstat 判定；非 unix：
  `FILE_FLAG_OPEN_REPARSE_POINT`）；`HeldDir`（`cfg(unix)` openat 逐段走 + read + `open_lock`（O_EXCL 竞争重试）+ replace）；
  `lock_in_turn`+`Turnstile`/`Turn`：**flock 无队列 ⇒ 自造 (dev,ino) 公平票据队列**，队首每 10ms 轮询，
  跨进程仍在同一 5s 等待窗口内竞争。
- `hard_linked_protected_file`（`cfg(unix)` +0，快照 :1235；非 unix 版本快照 :1432 直接返回 None）：
  `HardLinked`/`Alias::{Writable,Unsearched,Unlisted}`，`HARD_LINK_SCAN_LIMIT=4096`，
  `walk` BFS **从不跟随符号链接**；secret/tool 树受列举上限约束时「只不检查、不拒绝」。
- `unread_dir_refuses` + `SESSION_COMMAND_DIRNAME = "commands"`。

### 4.6 git_config（攻击面叙事在这里，不在 protected.rs）
- 模块 doc：`core.hooksPath` 指定的树、worktree 指针文件、config include 链，**必须按 git 自己的读法读（穿过符号链接）**；
  git 会读的每个文件都以全部拼写进保护，每个链接另立为 `Node`。只有「git 会读且地板拦不住」才触发拒绝。
- `GitConfigEnv{config_global, xdg_config_home}` + `from_host`/`from_lookup`；`global_configs` 优先级：
  `GIT_CONFIG_GLOBAL` 独占，否则 `XDG_CONFIG_HOME` + `~/.gitconfig`；相对路径 ⇒ `Unreadable`。
- 上限：`GIT_METADATA_READ_LIMIT=1MiB`（快照 :45）、`GIT_CONFIG_INCLUDE_DEPTH=10`（:124）、
  `GIT_CONFIG_FILES_LIMIT=64`（:127）、`GIT_DIRS_LIMIT=512`（:131）、`SYMLINK_HOPS=40`（:134）。
- `GitMetadataUnread::{TooLarge,Unreadable,NotUtf8,IncludesUnfollowed,GitDirsUnlisted}` → 进 `policy.unread_git_metadata`
  → enforce 下 `wrap_for_mode` 首条即拒（**宁可什么都不跑**）。
- `git_entries_in`（+0，快照 :204）吃 `workspace/user_home/write_roots/env`；`GIT_HOOK_NAMES`（:144）；
  hooks 路径落在 ws/home/write_roots 之上时 `narrowed`（:307）退化为具体命名文件。
- 其余内部（`GitScan` 快照 :334、`read_git_file` :561、`hooks_path_trees` :667、`ConfigHooksPath` :689、
  `include_path` :821、git config 词法 `config_entries` :853 等）**已读到定义与职责，逐行语义未逐条复核**。

### 4.7 violation（解码/提议/归属）
- `CMD/violation.rs`：`Blocked::{FsWrite,FsRead,Net{host?,port?},Capability{Ptrace|Mount|SetUid},Unknown{stderr_snippet}}`；
  `Replay::{Rerun,Resume{hold_id}}`；`Disposition::{Grantable,Informational{reason}}`；
  `InformationalReason::{ProtectedTarget,ProfileDeny,Capability,UnproxiedNetwork,PolicyDenylist,Unattributed,DecodeFailed}`；
  `Violation{blocked,proposed,disposition,partial_output,replay,exit_code,stderr_snippet≤512}`；
  `CommandExit{code,signal}`（`From<ExitStatus>`）。
- `decode`（+0，快照 :372）顺序见 §3 步 8；`refused_under_grant`（+36，快照 :408）处理 grant 之后的那一次运行；
  `produces_card`（+0，快照 :228）：**`Unknown` 永不出卡**；`denied_text`/`kept_blocked_text` 是给模型看的固定措辞。
- `violation/coarse.rs`：**唯一解码通道 = stderr 关键词 + 退出码**，故每个 target 都只是猜测、必须用户确认。
  `Marker{Write,Read,Denied}`、`SHARED_MARKERS/WRITE_HINTS/READ_PROGRAMS/READ_HINTS/REMOTE_MOUNT_ROOTS`（自动挂载根**从不 stat**）；
  `decode_coarse` 次序：setuid exec 拒绝 → 网络 → marker 行 + path token → 按程序判能力 → 跳过 pycache 噪声 → `Unknown`；
  `is_never_sandbox`（publickey、docker.sock 例外）；带空格/引号 path token（`Application Support` 靠 `is_dir` 试探）；
  `rename_sides`（`mv A B` 只有 A 未保护且 B 受保护才归到 B）；`nearest_existing_dir`；`network_failure`
  （curl/wget/getaddrinfo/bash `/dev/tcp`/Seatbelt 报告形；loopback ⇒ None）；`stderr_tail` 保持字符边界。
- `violation/coarse/macos.rs`（cfg macOS）：`deny_report`（+0，快照 :16）解析 `Sandbox: <proc>(<pid>) deny(1) <op> <target>`，
  `file-write*`→Write、`file-read*`→Read、其它 `file-*`→Denied、`network-*`/`system-*`→返回 None 交给网络/能力规则；
  注释强调**裸词 `sandbox` 绝不做 marker**（cargo 打印 target 目录、Chromium `--no-sandbox`、Deno `(deno sandbox)` 都是正常输出）。
  `network_report`（+0，快照 :37）：`deny(1) network-outbound remote:*:<port>`（地址被掩码，只有端口精确）或
  `/private/var/run/mDNSResponder`（一次解析，无端口）；**行内永不含 host**。
- `violation/propose.rs`：`proposal_dir` = 最近存在目录，除非过宽/基础目录 ⇒ 取**最高的缺失祖先**；
  `narrowed_past_denies`、`HOME_BASES`、`NEVER_PROPOSED`、`MIN_PROPOSED_COMPONENTS=3`、
  `resolves_too_broad`（挡 `<ws>/out -> /`）、`bases_from_env`（`PYTHONUSERBASE`、`XDG_DATA_HOME`）。
- `violation/attribute.rs`：`OwnTargets{trees:[cwd, served_root, env_bases], named: argv 路径 token（shell 扫一层）}`，
  `MAX_NAMED=256`；模块 doc 给出「未归属 ⇒ 降级 informational」的理由。

### 4.8 observe
- `CMD/observe.rs`：每 workspace 的**内存、内容无关**计数；不阻塞、不发问、不落盘。
  `WouldBlockKind`、`WouldVerdict::{Ask,DenyRow,PolicyDenylist}`、`WouldBlock{kind,target,verdict,count,last_at}`、
  `ObserveSummary::record/evict_oldest/counts_by_kind`，`OBSERVE_SUMMARY_MAX_ROWS=200`。
  网络行只能来自代理的 `AllowAndRecord`（不是 stderr 猜的）。

### 4.9 canonical
- `CMD/canonical.rs`：`canonical_path` = fold_dots + 最长前缀 realpath + `/private` firmlink + NFC；
  `VolumeRule::{Exact,Apfs}`（按 cfg 选宿主；测试缝 `with_volume_rule`），APFS 下比较键做别名折叠 + 小写 + NFC（
  `is_within`/`is_same_path`/`strip_within`/`dedup_paths` 都走 `comparison_key`）；
  `ServedRoot{spelled, real, moved_to: OnceLock}` 五条编号不变量：**解析一次、拼写只是身份、每次 build 前校验、
  未重新 serve 前一律拒绝**，`RootMoved` 是 fail-closed 路径；`FIRMLINKS = ["tmp","var","etc"]`；
  `resolved_spellings`（deny/地板：包含已解析形态）vs `firmlink_spellings`（roots：**从不解析**，理由「build 之后没有路径被换过」）；
  `depth()`；`PathGlob` 记忆化（`GLOB_MEMO_LIMIT` 生产 1024）。

### 4.10 env
- `CMD/env.rs`：`EnvGlobs` 用 globset（ASCII 大小写不敏感，建表时一次性编译）；`apply_env_policy`（+0，快照 :126）
  先从继承环境和显式环境里删排除项，**再**设 `policy.set`（顺序保证代理指针不被自家排除规则吃掉）；
  `apply_env_set_only`（+17，快照 :143）只设不删，服务 Observe。

## 5. 关键数据结构（判决/grant/violation 形状）

```text
SandboxPolicy（一次 spawn 的全部输入，serde，可跨 hub 传）
  read: ReadPolicy::AllExcept{deny[]} | Roots{roots[], deny[]}   · write_roots: [canonical…]（protected 在其上挖洞）
  network: Off | Proxy{port}（没有 "Open"）                      · env: EnvPolicy{excludes[], set[]}
  protected: [Protected…]（永不可 grant）                        · build_cache_trees / unread_git_metadata

Verdict 三态（谁判）：策略层 would_allow(blocked)->bool（只有 Fs* 判，Net/Capability/Unknown 不判）
  | 代理层 decider（deny 源全部先读再读 allow，host 授权只在这里生效）
  | 交互层 Disposition::Grantable | Informational{reason}

Grant：id=GrantId(UUIDv7) · subject=FsWriteRoot{root}|FsRead{root}|NetHost{host,port}|BuildCaches
  · scope=Call|Session|Workspace{root}|Global · decision=Allow|Deny（Deny 遮蔽）
  · expires=Ttl|At|Never（每次 build 求值）· provenance={command≤200, tool_call_id}
  · granted_by="desktop:<device_id}"|"cli"|"hub:<session_id>"

Violation：blocked=FsWrite|FsRead|Net{host?,port?}|Capability{Ptrace|Mount|SetUid}|Unknown{stderr_snippet}
  · proposed=Option<GrantSubject>（受 MIN_PROPOSED_COMPONENTS=3 / NEVER_PROPOSED / is_too_broad 约束）
  · disposition · replay=Rerun|Resume{hold_id} · exit_code · partial_output · stderr_snippet≤512
  · produces_card()==false 当 blocked 是 Unknown

上层回程：AfterRun = Keep(Box<ToolRunResult>) | Replay；ReplayBudget = One | Spent（result_path.rs +22/+32）；
  Finished = Ran | Violation | RefusedUnderGrant …（WS/sandbox/mod.rs 快照 :167）
```

## 6. 安全边界语义

默认拒（deny by default）
- SBPL 起手 `(deny default)`（`base.sbpl`，快照 :25），所有 allow 之后再把强制拒绝渲染在最后。
- `NetworkPolicy` 无 Open 取值；内核层网络永远 Off|Proxy{port}，**host grant 不放宽内核策略**。
- 环境默认排除密钥类变量（`EnvPolicy::default_excludes`）。
- 保护地板：`protected.rs` 各表，**加载时和 `with_grant` 时双重拒绝**，永不进 grant。
- 代理 unix socket、控制 socket 目录：`PolicyInputs.control_socket_dir` 必填 + `assert_control_socket_protected`
  防御性拒绝（`WS/sandbox/mod.rs`，`ControlSocketUnprotected`）。
- `unread_git_metadata` 非空 ⇒ enforce **一条命令都不跑**（hooks 去向未知）。
- 缺后端 / 缺 transport / 解码失败 / pin 丢失 ⇒ 一律 fail-closed（`Denied`、`PIN_LOST_TEXT`）。

默认可用（opt-out 型）
- workspace 根作为写根；`default_tmp_dirs`（`cfg macOS`：`/private/tmp`、`/private/var/folders`）；`VERIFIED_BUILD_CACHES`（读时校验摘要 ⇒ 默认可写）。

显式 opt-in（一张卡换一次）
- `BUILD_CACHE_TREES`（未校验 ⇒ 一个 workspace 一张 `GrantSubject::BuildCaches`）；每个网络 host/port（`NetHost` + `HostPattern`）；
  额外读根 `FsRead`；Observe 记账。

按模式/宿主分层
- 模式：`Off < Observe < Enforce`（`Ord`，「收紧 = 更大」），解析优先级见 §7。
- **`WorkspaceHostKind` 只有 `{Sandbox, Daemon}` 两个变体，没有 `Local`**（`WS/host_kind.rs` +0，全文 84 行；
  `#[default]` 是 `Daemon`，即未知宿主按保守取值）。该枚举描述的是**凭据/API 工具语义**，不是命令沙箱分层：
  在 `CMD/` 与 `WS/sandbox*` 的强制路径里 **grep 不到 `WorkspaceHostKind` 分支**（仅测试引用）。
  命令层的真实分层轴是 `SandboxMode` + `detect_backend()` 是否为 `None`（`CMD/backend.rs` · `wrap_for_mode` +24）。
- 平台：macOS 有 Seatbelt 强制；其它平台后端为 `None` ⇒ 强制只落在旧进程层（Landlock/seccomp/bwrap），per-command 层
  在这些平台上不做任何内核 confinement，只贡献策略计算/观察/代理记账。

一条重要的产品级取舍（`CMD/detect.rs` 模块 doc，快照 :1-7）
- `Enforce` 且无后端：**开发者自己选的** enforce 保持 enforce 并拒绝每一条命令；**灰度开关选的** enforce 在该宿主上
  作为 `Off` 运行（`SandboxMode::resolve_on_host` → `EnforceWithoutBackend` + `ModeDegradation::ConfigRefused`/降级标记）。

## 7. 配置项 / 环境变量 / feature flag

| 名称 | 位置 | 语义 |
|---|---|---|
| `GROK_SANDBOX_MODE` | `xai-grok-config/src/sandbox_mode.rs` · `SANDBOX_MODE_ENV` | 最高优先级模式覆盖；值 `off/observe/enforce` |
| `RemoteSettings.sandbox_mode` | 同上（fleet 层） | 远端灰度；缺省时回落到 `<grok_home>/managed_config.toml`（`WS/sandbox_mode.rs` · `managed_mode_layer`） |
| `<grok_home>/workspaced.toml` | `WS/sandbox_mode.rs` | 用户层（daemon 自有文件，**不读 CLI 的 `config.toml`**） |
| `<workspace>/.grok/workspaced.toml` | 同上 | **只能收紧**；即使目录 untrusted 也读；显式 `off` 在默认层仍被归属记录 |
| `sandbox.profile` | `~/.grok/sandbox.toml` + `<ws>/.grok/sandbox.toml`（`WS/sandbox/launch.rs` · `resolve_profile`） | per-command 策略基线；**`GROK_SANDBOX_PROFILE` 被显式忽略**（永远从 `workspace` 起）|
| `GROK_HOME_SECRET_GLOBS` 等 | `CMD/protected.rs` | 常量表，非配置 |
| `sandbox_grants.toml` | `CMD/grant_store.rs` · `workspace_file`/`global_file`（快照 :292/:296） | grant 持久层；`.lock` sidecar 0o600 |
| `GIT_CONFIG_GLOBAL` / `XDG_CONFIG_HOME` | `CMD/git_config.rs` · `GIT_CONFIG_GLOBAL_ENV`/`XDG_CONFIG_HOME_ENV`（快照 :49/:52） | 影响保护集（以 git 的读法） |
| 代理 8 变量 | `CMD/policy.rs` · `EnvPolicy::proxy_vars_at` | `http(s)_proxy`/`all_proxy` 及 `_no_proxy` 等，指向 `127.0.0.1:<port>` |
| feature `enforce` | `xai-grok-sandbox/Cargo.toml` `[features]`（快照 :53-59） | 默认开；**marker feature**，`nono` 是**非可选 unix 依赖**（`=0.53.0` pin），强制代码门在 `cfg(all(feature="enforce", unix))`；非 unix 上是 no-op |
| `nono` 版本 pin | 同上（快照 :34-44 注释） | 明确警告：Seatbelt 拒绝优先级依赖 nono 观测到的规则发射顺序，升级需重验 `deny_paths_e2e`（CI 自跳过） |
| `ignore` | `Cargo.toml` `[target.'cfg(target_os="linux")']` | 仅旧 Linux 层展开 glob 用；与 command 层无关 |
| 内嵌 SBPL 出处 | `CMD/backend/sbpl/*.sbpl` 头 15-16 行 | 三个文件均注明「Copied verbatim from the OpenAI Codex CLI … commit 93b44c3a」 |

代码级常量（非配置，但决定边界）：`MAX_GRANTS_FILE_BYTES=1MiB`、`GRANT_LOCK_WAIT=5s`、`HARD_LINK_SCAN_LIMIT=4096`、
`OBSERVE_SUMMARY_MAX_ROWS=200`、`MAX_OPEN_CALLS`、`MAX_NAMED=256`、`MIN_PROPOSED_COMPONENTS=3`、`PROBE_TIMEOUT=5s`、
`GIT_METADATA_READ_LIMIT=1MiB`、`GIT_CONFIG_INCLUDE_DEPTH=10`、`GIT_CONFIG_FILES_LIMIT=64`、`GIT_DIRS_LIMIT=512`、
`SYMLINK_HOPS=40`、`GLOB_MEMO_LIMIT=1024`、`CARD_DEADLINE`、`MAX_PERSISTED_TTL_SECONDS=7d`、
`OFFERED_TTLS_SECONDS=[3600,86400,604800]`、`MAX_FOLLOWUP_CHARS=2000`。

## 8. 测试矩阵（文件规模 = wc -l；主题来自文件名与模块 doc）

| 测试文件 | 行数 | 覆盖点 |
|---|---|---|
| `CMD/policy_tests.rs` | 2381 | build/输入校验、deny 覆盖、读根/写根、fail-closed 语义 |
| `CMD/backend/seatbelt_tests.rs` | 2252 | SBPL 渲染顺序、param 转义、Node 四族、fd 继承（仅 macOS 运行） |
| `CMD/grant_store_tests.rs` | 1859 | 落盘/并发 flock/过期裁剪/坏行/拒绝 subject/live_shared fail-closed |
| `CMD/protected_tests.rs` | 1486 | 各保护表、floor 组装、HeldDir、lock_in_turn 公平性、硬链接拒绝 |
| `CMD/violation_tests.rs` | 1191 | decode 次序、快拒、Disposition、produces_card、refused_under_grant |
| `CMD/git_config_tests.rs` | 1126 | hooksPath/worktree/include/上限/Unread 各变体 |
| `CMD/violation/coarse_tests.rs` | 723 | 关键词电池、rename_sides、network_failure、误报排除 |
| `CMD/backend_tests.rs` | 563 | wrap_for_mode 三态、无后端拒绝、CallId 拼写往返 |
| `CMD/violation/propose_tests.rs` | 471 | 提议收窄、过宽判定、缺失祖先 |
| `CMD/canonical_tests.rs` | 250 | fold_dots/firmlink/APFS 大小写与 NFC/ServedRoot pin |
| `CMD/detect_tests.rs` | 201 | 纯选择表（跨平台可测）、ProbedFile 文本 |
| `CMD/observe_tests.rs` | 188 | 计数/驱逐/无内容 |
| `CMD/grants_tests.rs` | 176 | HostPattern 匹配规则、Expiry、scope 持久性 |
| `CMD/env_tests.rs` | 142 | 排除顺序、set 后写入、Observe 只 set |
| `CMD/violation/attribute_tests.rs` | 110 | OwnTargets 归属、未归属降级 |
| `WS/sandbox/tests.rs` | 3153 | WorkspaceSandbox 全生命周期（mode pin/floor、finish、metrics） |
| `WS/sandbox/network_tests.rs` | 3447 | 代理、decider 次序（先 deny 后 allow）、hold/Resume、凭据撤销 |
| `WS/sandbox/real_wiring_tests.rs` | 1800 | 接缝真接：tools→prepare→wrap→finish |
| `WS/sandbox/result_path_tests.rs` | 386 | ReplayBudget=One、第二次终局、`[sandbox] ` 注记 |
| `WS/permission/sandbox_gate_tests.rs` / `sandbox_wire_tests.rs` / `sandbox_network_tests.rs` | 存在（未逐行读） | 卡往返、clamp-down、schema v1 |
| `WS/sandbox_mode_tests.rs` | 存在 | 三层读取 + 符号链接拒绝 + 不可读记为 enforce |

具体断言内容除上表主题外未逐用例核对（未确认）。

## 9. Workspace / Tools 侧接线（谁在什么时候调）

- `TOOLS/sandbox_launch.rs`（223 行）· trait `SandboxLaunch{prepare, prepare_restoring, exited}` + `OriginalArgv`/`CallId`/
  `CallKind`/`BackendName` 从 `xai_grok_sandbox::command` re-export（+21..+24，快照 :22-24）；实现经 `Resources` 注入，tools 侧不认识策略。
- 实际 spawn 调用点：`TOOLS/computer/local/terminal.rs` 5 处（快照 ~779 prepare、~898 prepare_restoring、
  ~3204、~3366、~3404）、`computer/local/static_shell.rs`（快照 ~78）、`computer/local/shell_state.rs`（快照 ~307）。
  模块 doc 规定 `wire_prepared` 在 prepare 之后装 stdio/kill_on_drop/detach 与旧层 `child_net::restrict_child_network`。
- `WS/sandbox/mod.rs`（1133 行）· `WorkspaceSandbox`（每 serve folder 一个实例）实现该 trait；doc「Nothing here spawns a process」。
  模型可见固定措辞：`ENFORCE_UNAVAILABLE_TEXT`/`SESSION_DIR_UNSAFE_TEXT`/`CALL_TABLE_FULL_TEXT`/`MODE_LAYER_WRITE_TEXT`。
- `WS/sandbox/launch.rs`（279）· `prepare_inner`（§3 步 2-6）；`SandboxLaunch::exited` 撤销凭据 + refuse holds + resync。
- `WS/sandbox/calls.rs`（1465）：以 `CallId` 为键、单锁的调用表；`CallOwner{session_id,policy,transport,command}`；
  `MAX_OPEN_CALLS`；`Released{credentials,epochs}` 必须被上层用于撤销/refuse。
- `WS/sandbox/network.rs`（900）：每 folder 一个 egress 代理，靠 `sync_network` 同步；`NetworkSide{address,proxy,tasks,decider,web_fetch}`；
  doc 要点「credential is attribution, not isolation」。
- `WS/sandbox/grants.rs`（359）：daemon 视角的 store（`Engaged::refresh_live`、`live_allows_now`、`sandbox.*` 控制动词的 JSON）。
- `WS/sandbox/result_path.rs`（339）· `run_shell_call_with_replay`（+0，快照 :145）：重放预算 + `[sandbox] ` 注记 + 后台 `detach_call`。
- `WS/permission/sandbox_gate.rs`（642）· `SandboxPath{None,Shell,Gated}`：`for_tool` 判据 = Execute 类工具 + 输出可解码 +
  模式 Enforce ⇒ `Gated`（沙箱卡取代**事前**提问并 pin enforce；后台运行降级为 `Shell`）；
  `settle_violation`（+0，快照 :244）/`decide`（+9）：Allow → `record_grant` + `mark_replay` → `Replay`；
  `Deny{remember}` → 落 deny 行（Always-reject = workspace 7d；held-connection 保持阻止 = call 域）；
  `Cancelled`/`SubjectRefused`/`DecodeFailed`/`NoSandboxDecision` **全部保持拒绝**。
- `WS/permission/sandbox_wire.rs`（920）：卡线上格式，`SANDBOX_VIOLATION_KIND="sandbox_violation"`、`SCHEMA_VERSION=1`、
  答案**只向下降级（clamped DOWN）**、`OfferedScope{Call,Session,Workspace,Global}`、TTL 档位 1h/1d/7d。
- `WS/permission/sandbox_network.rs`（807）：decider 侧的卡与 hold；`HoldAnswer` 从 command 层 re-export（快照 :21）；
  读顺序 = 所有 deny 源先于 allow；每 (call,host,port) 一张卡；锁序 pending → call-table → rows；`GrantView` trait。
- 其他引用点：`WS/hub.rs`（快照 :521/:534 用 `CallId::tool`）、`WS/permission/hub_gate.rs`（`SandboxMode`）、
  `WS/permission/state.rs`（复用 `FileOwner`/`HeldDir` 原语读权限状态文件）、`WS/sandbox/metrics.rs`。
- `WS/sandbox_mode.rs`（491）：`resolve_sandbox_mode`（+0，快照 :66）/ `resolve_sandbox_mode_in`（+20，快照 :85）/
  `SandboxModeInputs`（快照 :48，注入 env/grok_home/backend_available/WritableLocations）；
  模块 doc 三条不变量：①**绝不开天窗**——层存在但被拒/不可读 = 记为 `enforce` 并 warn，`sandbox.status` 显示
  `degraded: config_refused`；②点文件符号链接仍可用（目标落在任何「命令可写或曾可写」之外才跟）；③链进可写处的层文件一律拒，
  `sandbox.mode.set` 绝不穿过链接写。

一句话接线定性：**xai-grok-tools 只认一个 trait；所有策略/授权/卡片语义都在 xai-grok-workspace 的 `sandbox/` +
`permission/sandbox_*` 里；命令层本体（xai-grok-sandbox::command）不认识 daemon，策略/授权/解码平台无关，
渲染强制只有 macOS 的 Seatbelt 后端（`BackendName` 仅此一个变体，快照 :20-22）。**
