[上一篇：权限规则引擎](18-权限规则引擎.md) · [总目录](README.md) · 第 19 / 22 篇 · [下一篇：Git Worktree 快速铺设与 GC](20-Git-Worktree快速铺设计与GC.md)

> **本篇位置**：第 19 / 22 篇

# 19 · 外部 Agent 配置迁移

> **场景**：用户从 Claude Code 迁到 Grok Build，`~/.claude/settings.json`、`~/.claude.json`、项目里的 `.claude/settings*.json` 与 `.mcp.json` 已经攒了一批权限规则、环境变量、MCP server、hook 与 skills/rules 目录。本篇讲「读别家的配置 → 转成本仓库的 `config.toml` + `hooks/imported-from-claude.json`」这一条完整链路，重点是把**跨 crate 的分工**讲清楚：谁发现文件、谁解析、谁转换、谁写入、谁记状态。
>
> **阅读说明**：源码基准 `HEAD = 42f4d7d3`（2026-10-27，`SOURCE_REV = 559751fd`；前次基准 `HEAD = 0e2bfffb` / `SOURCE_REV = 036a5d83`）。工具链 Rust 1.94.0（`rust-toolchain.toml` `[toolchain].channel`）；workspace members 共 **107** 个。本篇引用的 crate 全部在 `crates/codegen/` 下。
>
> **索引记法**：`文件路径 符号：名字 偏移：+N`。**顶层符号**（自由函数 / 类型 / 常量）的定义行即 `+0`，不写偏移；**成员**（impl / trait 内的方法、struct 字段）相对其 `impl X` / `struct X` / `enum X` 头行记 `+0`。偏移全部回当前源码实测（`python3 docs/adrian/sourceReader/.progress/sr_tools.py offset FILE SYM` 可复核）。
>
> **三条最容易写错的事实**（每条都在本篇正文里给了证据位置）：
> 1. **迁移入口只有 slash 命令 `/import-claude` 一个**。欢迎屏那套「有 Claude 配置待导入」的菜单行与 `ctrl+i` / `ctrl+shift+i` 快捷键，在本快照里**不可达**——门变量 `has_claude_import` 全仓从未被置为 `true`。不要写成「启动时会提示」。见 3.1 与 4.4。
> 2. skills / rules 目录**只登记路径、不复制文件**，而且登记出来的 `[paths] extra_skill_dirs` 并不参与 skill 注入。见 3.3 与 4.3。
> 3. **引擎 crate 完全不认识 Claude 的 JSON**：解析闭包留在 shell 适配层。`crates/codegen/xai-grok-shell/src/claude_import.rs` 全文只有 144 行（不是「+2,181 行的适配器」，那个数字是 merge diff 的行数）。见 3.2。
>
> 相关 crate 分工：`crates/codegen/xai-grok-external-agent-migration`（迁移引擎本体，12 个源文件共 1,784 行）、`crates/codegen/xai-grok-shell`（Claude 适配器 + 状态哈希）、`crates/codegen/xai-grok-permission-rules`（settings 文件发现与规则字符串解析）、`crates/codegen/xai-grok-config`（MCP 读取、marker 读取、compat 开关）、`crates/codegen/xai-grok-pager`（入口命令、TUI 审阅弹窗）、`crates/codegen/xai-grok-hooks`（marker 的下游消费者）。只有 pager 与 shell 两个 crate 依赖 migration crate（各自的 `Cargo.toml` `[dependencies]`）。

---

## 第一层 · 简单框架（系统骨架）

**这个功能是什么。** migration crate 的 `[package].description` 原文给出了范围：

> "Import Claude settings into Grok config: permissions, hooks, MCP servers, environment variables, skill directories, and rule directories"

拆成代码事实：迁移的单元是 `crates/codegen/xai-grok-external-agent-migration/src/config_values.rs` 的 `enum ImportableItem`，**恰好五个变体**，也就是「可迁移的东西」的全集——

| 变体 | 载荷 | 落到本仓库的哪里 |
|---|---|---|
| `Permission` | `ImportPermission{action, tool, pattern, pattern_mode}` | `config.toml` 的 `[permission] allow / deny / ask` 字符串数组 |
| `EnvVar` | `key` + `value` | `config.toml` 的 `[env]` 表 |
| `McpServer` | `name` + `Box<McpServerConfig>` | `config.toml` 的 `[mcp_servers]` 表 |
| `Hook` | `event` / `matcher` / `command` / `timeout` | `hooks/imported-from-claude.json` |
| `PathEntry` | `PathKind`（`Skill` 或 `Rule`）+ 路径字符串 | `config.toml` 的 `[paths] extra_skill_dirs` / `extra_rule_dirs` |

**不迁移什么**（按代码边界，不是按常识）：会话历史是**另一个独立功能**（`crates/codegen/xai-grok-foreign-sessions/src/lib.rs` · `ForeignSessionTool`，其 `Claude` 变体走 resume 路径），与本 crate 零关系；`crates/codegen/xai-grok-external-agent-migration/src/config_values.rs` · `ClaudeSettingsSnapshot` 只有 `permissions` 与 `env` 两个字段，所以 `defaultMode` 与 `additionalDirectories` 虽然被解析出来，却**不进 plan**；CLAUDE.md 之类指令文件的内容不复制（只在运行时 compat 层被读）；**凭据文件不读也不写**——但这不等于「迁过来的东西里没有机密」：`env` 与 MCP 的 `headers` 是字面值直搬，详见 3.8 的两轴拆法。

**跨 crate 分工表**——「谁负责哪一段」是本篇的第一价值：

| 段 | 负责方 | 入口符号 | 它知道什么 / 不知道什么 |
|---|---|---|---|
| 入口与门 | `crates/codegen/xai-grok-pager/src/slash/commands/import_claude.rs` | `ImportClaudeCommand` | 只发一个 `Action`，不含任何迁移逻辑 |
| 派发与审阅 | `crates/codegen/xai-grok-pager/src/app/dispatch/import_claude.rs` | `dispatch_import_claude` | 决定「扫不扫、给不给用户勾、什么时候落盘后记状态」 |
| Claude 适配器 | `crates/codegen/xai-grok-shell/src/claude_import.rs` | `scan_importable_settings` | 知道 Claude JSON 长什么样、知道规则串怎么解析、知道 marker 缓存在哪 |
| 迁移引擎 | `crates/codegen/xai-grok-external-agent-migration/src/source_cla.rs` | `scan_importable_settings` | **不认识 Claude JSON**：文件发现与解析都由调用方注入 |
| 写入器 | `crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` | `apply_import` | TOML 合并写、原子写、symlink 语义、幂等去重 |
| 文件发现 | `crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` | `find_claude_settings_paths` | `.claude/settings*.json` 的逐层扫描；同时服务运行时权限 |
| 规则字符串解析 | `crates/codegen/xai-grok-permission-rules/src/rules.rs` | `parse_permission_rule` | `Tool(pattern)` → `PermissionRule`；工具别名表也在这里 |
| MCP 读取 | `crates/codegen/xai-grok-config/src/mcp_servers/json_config.rs` | `load_claude_json_mcp_servers_as_configs_unfiltered` | `~/.claude.json` 与 `.mcp.json` 的 server 抽取 |
| 状态记录 | `crates/codegen/xai-grok-shell/src/claude_import_state.rs` | `mark_imported` | 写 `claude_import_state.json` 的内容哈希 |
| marker 读写 | `crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` 写、`crates/codegen/xai-grok-config/src/claude_import.rs` 读 | `write_import_marker` / `is_claude_import_marked` | `[claude_compat] imported = true` 是「兼容层总闸」 |

骨架图（一次 `/import-claude` 的数据流；节点里只写「文件名 · 符号」，完整路径见上面的分工表）：

```
   用户敲 /import-claude
        │  import_claude.rs · ImportClaudeCommand
        ▼
   Action::ImportClaudeSettings ── router.rs · dispatch_inner（偏移 +116）
        │
        ▼
   dispatch/import_claude.rs · dispatch_import_claude
        │ ①「扫」——只做一次调用
        ▼
   shell claude_import.rs · scan_importable_settings(cwd)
        │        │
        │ ②发现  │ ②解析（注入的闭包）
        ▼        ▼
   permission-rules claude_settings.rs      permission-rules rules.rs
   · find_claude_settings_paths             · parse_permission_rule
   permission-rules project_config.rs               │
   · find_mcp_json_files                            │
   config json_config.rs                            │
   · load_claude_json_mcp_servers_as_configs_unfiltered
        │        │
        └───┬────┘
            ▼ ③汇总/分组：migration source_cla.rs · scan_importable_settings
   ImportPlan { global_items, project_items }
            │ ④审阅：views/import_claude_modal.rs · ImportClaudeModalState
            ▼
   用户勾选 → 确认 → dispatch/import_claude.rs · dispatch_import_claude_confirm
            │ ⑤转换后的落盘（filtered_plan → apply_import）
            ▼
   migration rewrite.rs · apply_import
        ├─→ $GROK_HOME/config.toml            （+ 项目 .grok/config.toml）
        └─→ <grok dir>/hooks/imported-from-claude.json
            │ ⑥记状态（两段，顺序固定）
            ▼
   claude_import_state.rs · mark_imported   +   claude_import.rs · mark_claude_imported
   （内容哈希，本快照只写不读）               （[claude_compat] imported = true）
```

图中文件名到完整路径的映射：**只出现在图里的短名**按上面的分工表还原——`import_claude.rs`（slash 命令）与 `dispatch/import_claude.rs`、`views/import_claude_modal.rs`、`router.rs` 都在 `crates/codegen/xai-grok-pager/src/` 下；`claude_import.rs` 与 `claude_import_state.rs` 都在 `crates/codegen/xai-grok-shell/src/` 下；`source_cla.rs`、`rewrite.rs` 在 `crates/codegen/xai-grok-external-agent-migration/src/` 下。

**一句话记住分工**：migration crate 是「不认识 Claude 的引擎」（它连 permission-rules 都不依赖，`Cargo.toml` 的 `[dependencies]` 只有 dunce / git2 / serde_json / thiserror / toml / tracing / xai-dirs / xai-grok-config），shell 是「认识 Claude 的适配器」，pager 是「只负责问人」的 UI 层。

---

## 第二层 · 一个完整例子（全路径走读）

取一份最典型的用户级 `~/.claude/settings.json`（键形态由 `crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` 的 `ClaudeSettings` 与 `extract_string_map` 决定，不是示意性编造）：

```jsonc
{
  "permissions": {
    "allow": ["Bash(cargo:*)", "Read(~/.cargo/**)"],
    "deny":  ["WebFetch"]
  },
  "env": { "ANTHROPIC_MODEL": "claude-x", "MAX_RETRIES": 3 },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash",
        "hooks": [ { "type": "command", "command": "bash ~/check.sh", "timeout": 10 } ] }
    ]
  }
}
```

从这个文件出发，一路走到磁盘：

1. **入口**：`crates/codegen/xai-grok-pager/src/slash/commands/import_claude.rs` · `ImportClaudeCommand` 的 `impl SlashCommand` 函数：`run`（偏移：+7）返回 `CommandResult::Action`，动作是 `crates/codegen/xai-grok-pager/src/app/actions.rs` 的 `enum Action` 变体：`ImportClaudeSettings`。带参数会被忽略并 warn（同函数开头两行）。
2. **路由**：`crates/codegen/xai-grok-pager/src/app/dispatch/router.rs` · 符号：`dispatch_inner`（偏移：+116）把它交给 `dispatch_import_claude`；紧随其后 +117 / +118 是 Confirm 与 Cancel 两条。
3. **发现**：`crates/codegen/xai-grok-pager/src/app/dispatch/import_claude.rs` · `dispatch_import_claude` 调 shell 侧的入口函数拿 plan。
   该入口是 `crates/codegen/xai-grok-shell/src/claude_import.rs` · 符号：`scan_importable_settings`（偏移：+1 取 settings 路径、偏移：+2 取 `.mcp.json` 路径），它只做三件事：拿路径 + 交出解析闭包 + 转调引擎。
   路径集合由 `crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · `find_claude_settings_paths` 给出（项目层由 `collect_project_claude_paths` 从 cwd 逐层走到 repo root，再 `splice` 到列表最前 ⇒ 具体度优先）。
4. **解析**：`crates/codegen/xai-grok-shell/src/claude_import.rs` · 符号：`snapshot_at` 先调 `load_claude_settings`（偏移：+1），再把 `permissions.allow/deny/ask` 逐条喂给 `parse_permission_rule`，成功的过 `import_permission` 变 `ImportPermission`，失败的 `debug!` 跳过（偏移：+13 与 偏移：+20 两处分支）。
   `env` 直接取强转后的字符串表——例子中的 `3` 变成 `"3"`，见 `crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · 符号：`extract_string_map`（偏移：+23~+27）。
5. **汇总成分组**：`crates/codegen/xai-grok-external-agent-migration/src/source_cla.rs` · 符号：`scan_importable_settings`。判定 global 的唯一依据是「路径是否在 `home/.claude` 之下」（偏移：+14）⇒ 本例这份文件是 global。`permissions` / `env` 从 snapshot 摊平成 item（偏移：+23~+32），**hooks 不在 snapshot 里**：引擎自己再读一次同一个文件（偏移：+32 处调用 `extract_hooks_from_settings_file`）。`~/.claude.json` 里的 server 一律进 global 列表（偏移：+36 的注释写明 "Both are stored in the global list"）。
6. **审阅**：plan 非空 ⇒ `ImportClaudeModalState::new` 建弹窗，**默认全选**（`crates/codegen/xai-grok-pager/src/views/import_claude_modal.rs` · `impl ImportClaudeModalState` 函数：`new`，偏移：+2）。用户按 Enter ⇒ 状态机回 `Confirmed` ⇒ 路由到 `dispatch_import_claude_confirm`。
7. **落盘**：`filtered_plan`（同一 impl，偏移：+36）按勾选重切成一个 `ImportPlan`，交给 `crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · 符号：`apply_import`——先 global 后 project（偏移：+3 与 偏移：+13），本例只有 global。
8. **写出来的东西**（本例的最终磁盘形态）：

```toml
# $GROK_HOME/config.toml（节名来自 rewrite.rs）
[permission]
allow = ["Bash(cargo:*)", "Read(~/.cargo/**)"]   # append_missing_strings 去重后追加
deny = ["WebFetch"]

[env]
ANTHROPIC_MODEL = "claude-x"
MAX_RETRIES = "3"                                  # 数字被强转成字符串，写盘仍是字符串

[claude_compat]
imported = true                                    # 总闸，见 3.7
```

```jsonc
// $GROK_HOME/hooks/imported-from-claude.json（结构来自 hooks_cla.rs）
{ "hooks": { "PreToolUse": [
  { "matcher": "Bash",
    "hooks": [ { "type": "command", "command": "bash ~/check.sh", "timeout": 10 } ] }
] } }
```

9. **记状态**：`apply_import` 成功后，`dispatch_import_claude_confirm` 顺序调 `mark_imported`（写内容哈希）与 `mark_claude_imported`（写 marker + 刷新进程内缓存），再把摘要作为一条 Info 级 startup warning 回显（`crates/codegen/xai-grok-pager/src/app/dispatch/import_claude.rs` · 符号：`dispatch_import_claude_confirm`，偏移：+40 起）。
10. **回显文案**里 env 值**不打明文**：`crates/codegen/xai-grok-external-agent-migration/src/reporting.rs` · 符号：`format_item_summary`（偏移：+62 的注释 "An env value can be a token"，偏移：+63 输出 `<redacted, N chars>`）；但 hook 的 `command` 全文进摘要。

**这一步之后真正发生了什么**：`$GROK_HOME/hooks/` 本来就是运行时 hook 的发现源之一（`crates/codegen/xai-grok-config/src/global_hook_sources.rs`），所以搬进来的 hook 立刻可用；而 `[paths] extra_skill_dirs` 搬进来的目录**不会**让 skill 生效（见 4.3）——这就是「同一份 plan，五类东西迁移后的活跃度并不相同」。

---

## 第三层 · 详细逐步说明（主链路拆解）

### 3.1 步骤 1 — 入口与它的可达性

活跃入口只有一个 slash 命令，两处注册：

- `crates/codegen/xai-grok-pager/src/slash/commands/import_claude.rs` · 符号：`ImportClaudeCommand`（`slash_meta!` 声明 `name: "import-claude"`）；它被放进 `crates/codegen/xai-grok-pager/src/slash/commands/mod.rs` 的默认命令列表（`Arc::new(import_claude::ImportClaudeCommand)`）。
- `crates/codegen/xai-grok-shell/src/session/slash_commands.rs` · 符号：`PAGER_COMMAND_KEYS`（表内含字符串 `"import-claude"`）——allowlist，决定这个键会被路由到 pager 而不是当成 prompt 命令。

**欢迎屏那条路是死的。** 全仓 grep `has_claude_import` 的**全部**赋值只有一种：置 `false`——结构体初始化（`crates/codegen/xai-grok-pager/src/app/app_view.rs` · 字段：`has_claude_import`）与 `crates/codegen/xai-grok-pager/src/app/dispatch/import_claude.rs` 里三个 handler 收尾各一次。没有任何代码把它写成 `true`。因此下面这几处「读它」的代码永不触发：

- `crates/codegen/xai-grok-pager/src/app/app_view.rs` · 符号：`handle_welcome_input`（偏移：+538 是 `ctrl+i`、偏移：+541 是 `ctrl+shift+i`）
- `crates/codegen/xai-grok-pager/src/views/welcome/mod.rs` · 符号：`render_welcome_done`（偏移：+77，那一行把 "Import Claude settings" 插到菜单第一项）
- `crates/codegen/xai-grok-pager/src/views/welcome/mod.rs` · `struct WelcomeRenderParams` 字段：`has_claude_import`（偏移：+22）

为什么不可达：欢迎屏的行需要「启动时检测到有 `.claude` 内容可导」这个前置判断，而承担这个判断的两半都缺一半——检测函数 `crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · `has_claude_compat` **没有任何调用方**（全仓只有它自己的定义行）。

另一半：`crates/codegen/xai-grok-shell/src/claude_import_state.rs` · 符号：`load_import_state` 是 `pub(crate)` 且只被同文件的 `mark_imported` 调用（写前先读旧状态），**没有比对新旧哈希来决定要不要提示的调用方**。所以本快照里哈希状态是「只写不读」的。结论照写：**只有 `/import-claude` 能触发迁移；启动横幅与 `ctrl+i` 都不存在**。

另外两条入口形态确认不存在：没有 CLI 子命令（`crates/codegen/xai-grok-pager-bin` 里 grep `claude` 零命中）；crate 的 `Cargo.toml` 没有 `[features]` 段，也就没有 feature gate。

### 3.2 步骤 2 — 两层分工：引擎 / 适配器 / UI

这不是两个独立功能，而是**同一个流程的两层**，靠一个注入式设计缝合：

| 层 | 文件 | 职责边界 |
|---|---|---|
| 引擎 | `crates/codegen/xai-grok-external-agent-migration/src/source_cla.rs` | 收「路径列表 + 一个 `&Path -> Option<ClaudeSettingsSnapshot>` 闭包 + `.mcp.json` 列表」，输出 `ImportPlan`；负责 global/project 分组与 skills/rules 目录登记 |
| 适配器 | `crates/codegen/xai-grok-shell/src/claude_import.rs` | 供文件发现、供解析闭包（Claude 规则串 → `ImportPermission`）、marker 读写与进程内缓存、以及 `import_marker()` 这座给 hooks discovery 用的桥 |
| UI | `crates/codegen/xai-grok-pager/src/app/dispatch/import_claude.rs` 与 `crates/codegen/xai-grok-pager/src/views/import_claude_modal.rs` | 触发、逐项勾选、结果提示 |

为什么要这么切：`parse_permission_rule` 住在 permission-rules crate，而引擎**刻意不依赖它**（见第一层那句 `Cargo.toml` 的 `[dependencies]`）。于是「认识 Claude」的知识只能留在 shell，引擎只处理已经翻译过的中间模型。副作用有两个，都要写清：① 引擎里的 hook 提取是**第二次读同一个文件**（`extract_hooks_from_settings_file`），因为 `ClaudeSettingsSnapshot` 里没有 hooks 字段；② 规则解析能力的复用度取决于适配器的解析闭包，而不是引擎。

适配器还额外维护一份进程内 marker 缓存：`crates/codegen/xai-grok-shell/src/claude_import.rs` · `static MARKER_CACHE`（一次读盘、后续命中内存），三个符号配合——`is_claude_import_marked`、`refresh_marker_cache`、`is_claude_import_marked_with_log`（后者首次命中门时打一行 info，偏移：+5）。`import_marker` 把它包装成 `crates/codegen/xai-grok-config/src/claude_import.rs` 的 `enum ClaudeImport`，交给 hook 发现层用。

### 3.3 步骤 3 — 文件发现：四族外部输入，四个不同的负责人

| 外部来源 | 谁发现 / 谁读 | 读什么键 | 归属哪一层 |
|---|---|---|---|
| `~/.claude/settings.json`、`~/.claude/settings.local.json`、项目 `<dir>/.claude/settings{,.local}.json` | `crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · `find_claude_settings_paths`（global 两份来自 `global_claude_settings_paths`，项目层由 `collect_project_claude_paths` 从 cwd 逐层上溯） | `permissions.allow/deny/ask`（字符串数组）、`env`（对象）、`hooks` | 路径以 `home/.claude` 开头 ⇒ global，否则 project |
| `~/.claude.json` | `crates/codegen/xai-grok-config/src/mcp_servers/json_config.rs` · `load_claude_json_mcp_servers_as_configs_unfiltered` | `projects["<cwd>"].mcpServers` 与顶层 `mcpServers` | **两者都进 global 列表**（不是 project），源码注释明写 |
| `<dir>/.mcp.json`（repo root → cwd 逐层） | `crates/codegen/xai-grok-permission-rules/src/project_config.rs` · `find_mcp_json_files`（shell 经 `crates/codegen/xai-grok-shell/src/util/config/mcp.rs` 再导出后调用） | `mcpServers` 对象 | project |
| `~/.claude/skills`、`~/.claude/rules`、`<projectRoot>/.claude/{skills,rules}` | `crates/codegen/xai-grok-external-agent-migration/src/source_cla.rs` · `existing_claude_path_dirs`（偏移：+4 只收 `is_dir()`） | 只看目录是否存在 | global 与 project 各扫一遍，**canonicalize 去重**防同一目录被记两次（`scan_claude_path_dirs`，偏移：+5 与 偏移：+17） |

三点值得单独记住：

1. **优先级只体现在顺序上**：`find_claude_settings_paths` 把项目层 `splice` 到最前（偏移：+5），引擎按列表顺序把 item 追加进同一个 `Vec`，所以「更具体的文件先出现在 plan 里」，但**没有冲突消解**——两份文件都有的同一条规则会变成两个 item，最终由写入端的去重吸收（见 3.6）。
2. **`~/.claude.json` 的项目 server 被当 global**：这意味着在一个项目里给别人配过的 MCP server，会写进你的 `$GROK_HOME/config.toml`。这是代码行为，不是文档措辞。
3. **skills/rules 只登记目录**：全程没有文件复制；`PathEntry` 载荷就是一个字符串路径。

### 3.4 步骤 4 — 解析与字段映射，以及每一处降级

规则串的往返是 `Claude 文本 → PermissionRule → ImportPermission → Claude 文本`，四步分别归四个符号：

| 环节 | 位置 |
|---|---|
| `Tool(pattern)` 解析 | `crates/codegen/xai-grok-permission-rules/src/rules.rs` · 符号：`parse_permission_rule` |
| 工具别名折叠 | 同文件 · 符号：`tool_name_to_filter`（偏移：+4 `Write`→`Edit`、偏移：+6 `Glob`→`Grep`、偏移：+9 `SendSubagentMessage` / `SendAgentMessage`→`AgentMessage`） |
| 结构体逐字段搬运 | `crates/codegen/xai-grok-shell/src/claude_import.rs` · 符号：`import_permission` |
| 写回成字符串 | `crates/codegen/xai-grok-external-agent-migration/src/config_values.rs` · 符号：`format_rule_string` |

降级与丢失点，逐条给位置：

- `EnterWorktree` / `NotebookEdit` / `NotebookRead` ⇒ `RuleParseError::UnsupportedToolPrefix`（`crates/codegen/xai-grok-permission-rules/src/rules.rs` · 符号：`parse_permission_rule`，偏移：+43~+50 带括号形态、偏移：+81 裸名形态）；未知前缀 ⇒ `UnknownToolPrefix`（偏移：+53）。
  两种错误在迁移路径上都只被 `debug!` 记一行然后**丢这条规则**（`crates/codegen/xai-grok-shell/src/claude_import.rs` · 符号：`snapshot_at`，偏移：+13 与 偏移：+20），**用户界面上没有任何告警**——这是本链路最安静的一处数据丢失。
- `Bash(cmd:*)` 的 `cmd:` 前缀语义被转成 glob（同文件偏移：+60 处调用 `strip_bash_colon_wildcard`，紧邻注释说明「当作 glob 什么都匹配不到」）。
- `WebFetch(domain:x.com)`：`ImportPatternMode::Domain` 在写回时重新加 `domain:` 前缀（`crates/codegen/xai-grok-external-agent-migration/src/config_values.rs` · 符号：`format_rule_string`，偏移：+28）；`Any` 且无 pattern ⇒ `*`（偏移：+3）；`ImportTool::Mcp` 写回的标签是 `MCPTool`（同文件 `tool_label`，偏移：+7），与 `tool_name_to_filter` 认识的写法对称，因此 MCP 规则可往返。
- 空 pattern 与 `*` 被归一成「无 pattern」（`parse_permission_rule` 偏移：+35~+38 一段），所以 `Bash(*)` 与裸 `Bash` 落到同一字符串。
- `env` 值：数字/布尔强转字符串，`null` / 数组 / 对象跳过并 warn（`crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · 符号：`extract_string_map`，偏移：+23~+27 与 偏移：+29）。`null` 特意不转成 `"null"`（同一函数上方的注释给出理由：一个值为 `"null"` 的环境变量更可能是用户写错）。
- hooks：只认 `type == "command"` 的 handler，其它类型 `debug!` 跳过（`crates/codegen/xai-grok-external-agent-migration/src/hooks_cla.rs` · 符号：`extract_hooks_from_settings_file`，偏移：+27）；缺 `command` 直接跳过（偏移：+36 附近）；`timeout` 缺失就是缺失，不补默认值。

冲突策略一句话：**内部优先、保留现状**。`env` 已存在同名键就不写（`crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · 符号：`merge_env_vars`，偏移：+11）。

MCP server 同名则**整个跳过**、不做字段级合并（`crates/codegen/xai-grok-external-agent-migration/src/mcp.rs` · 符号：`merge_mcp_servers`，偏移：+13）。

### 3.5 步骤 5 — plan 的形状与审阅粒度

`ImportPlan` 是两个 `Vec<ImportableItem>`（global / project），没有别的结构（`crates/codegen/xai-grok-external-agent-migration/src/config_values.rs` · 符号：`ImportPlan`，其 `impl ImportPlan` 只有 `total_items`（偏移：+2）与 `is_empty`（偏移：+7）两个方法）。

UI 侧的勾选粒度比 plan 更细：`crates/codegen/xai-grok-pager/src/views/import_claude_modal.rs` · 符号：`Row` 把列表摊平成「scope 头 / 类型头 / 单项 / 空行」四形态，点头行会整组切换；`impl ImportClaudeModalState` 函数：`filtered_plan`（偏移：+36）按摊平后的下标回填到两个 `Vec`。默认全选来自同一 impl 函数：`new`（偏移：+2，`vec![true; total]`）。**Esc 与「一个都不勾」是两条不同的路**：前者走 `dispatch_import_claude_cancel`，不写任何状态；后者仍然会走完 3.7 的记状态两步（选中数为 0 时只跳过写盘分支）。

摘要文本由引擎渲染：`crates/codegen/xai-grok-external-agent-migration/src/reporting.rs` · `impl ImportPlan` 函数：`summary`（偏移：+2），分组标题直接打印落点路径（global 打 `$GROK_HOME/config.toml`，project 打 `find_project_root(cwd)` 拼出来的路径）。

### 3.6 步骤 6 — 写入落点、幂等与符号链接

| 落点 | 谁写 | 备注 |
|---|---|---|
| `$GROK_HOME/config.toml` | `crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · `apply_import` → `apply_items_to_grok_dir`（偏移：+6 拼文件名，文件名常量是 `crates/codegen/xai-grok-config/src/loader.rs` 的 `USER_CONFIG_FILENAME`） | 节名：`[permission]` / `[env]` / `[mcp_servers]` / `[paths]` / `[claude_compat]` |
| `$GROK_HOME/hooks/imported-from-claude.json` | 同文件 `apply_items_to_grok_dir`（偏移：+12 定位 hooks 目录）→ `crates/codegen/xai-grok-external-agent-migration/src/hooks_cla.rs` · `apply_hooks_to_dir` | 这个目录正是运行时 hook 的发现源，落进去即生效 |
| `<projectRoot>/.grok/config.toml` 与 `.grok/hooks/imported-from-claude.json` | 同一对函数，scope 换成 Project | project root 由 `crates/codegen/xai-grok-external-agent-migration/src/scope.rs` · `find_project_root` 决定：git2 discover 成功用 workdir，否则退回 cwd |

幂等机制逐条（都在实测的源码里）：

- 字符串数组类（权限规则、`extra_*_dirs`）走 `append_missing_strings`（`crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · 符号：`append_missing_strings`）：先按已有值建 `HashSet`，只追加没见过的。重跑 `/import-claude` 不会产生重复条目。
- `env` / `[mcp_servers]`：存在即跳过（见 3.4 末）。
- hooks：按 `(event, matcher, command)` 命中已存在的 handler 时**原位刷新 timeout**、不追加新条目（`crates/codegen/xai-grok-external-agent-migration/src/hooks_cla.rs` · 符号：`apply_hooks_to_dir`，偏移：+49 调用；`refresh_existing_hook_timeout` 偏移：+25 处还会**删掉** timeout 键——源侧没了，目标侧跟着没）。
- 只要 `count > 0` 才写 `config.toml`（`crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · 符号：`apply_items_to_config`，偏移：+47）；hooks 则是 `count > 0 || dirty` 才写（`crates/codegen/xai-grok-external-agent-migration/src/hooks_cla.rs` · 符号：`apply_hooks_to_dir`，偏移：+80）——**只有 timeout 变了也会重写整个文件**。
- marker 本身幂等：`[claude_compat].imported` 用 `insert` 覆盖为 `true`，重写不丢其它节（`crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · 符号：`write_import_marker`，偏移：+8 取/建节、偏移：+13 写键）。
- 「上次跳过的项这次想导」是被设计支持的：MCP 读取走的是 **unfiltered** 版本，即不受 `[compat.claude]` 与 marker 两道门影响（`crates/codegen/xai-grok-config/src/mcp_servers/json_config.rs` · 符号：`load_claude_json_mcp_servers_as_configs_unfiltered` 与 `load_mcp_json_servers_as_configs_unfiltered`；两者定义行上方的注释都写明是给 `/import-claude` 用的）。对照运行时用的带门版本 `load_claude_json_mcp_servers_as_configs`（同一文件，开头就是 compat + marker 双条件短路）。

符号链接语义是这一节最不显然的部分，而且**两种 scope 的行为相反**：

- global：**穿透** symlink 写目标文件，并且做 TOCTOU 双次绑定校验（`crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · 符号：`write_scoped`，偏移：+2~+4 先 `bind_follow_destination` 再 `require_same_bound_destination`）。
- project：**替换** symlink 本身，不动它指向的文件（同一符号，偏移：+8 走 `bind_slot_destination`）。
- 两条落盘都经 `crates/codegen/xai-grok-config/src/fs_atomic.rs` · `write_atomically_bound`（tmp + rename），调用点传 `None`（上面 `write_scoped` 内偏移 +16 那一行）。**权限位现在有结论，分两种情形**：
  - **目标文件已存在 ⇒ 继承它当前的权限位**，且这是被测试钉死的。`None` 分支在 rename 之前调 `apply_current_dest_mode`（同一文件里，`write_atomically_bound` 定义行 +16 处），它用 `unix_file_mode(dest)`（跟随 symlink）读现值，再用 **`std::fs::set_permissions`** 打到 tmp 上——`set_permissions` 不受 umask 削位，所以「chmod 过就还在」。护栏是 `fs_atomic_tests.rs` 里的 `write_atomically_bound_survives_chmod_and_inherits_live_mode`：先 `set_permissions(0o600)`、再以 `None` 写入，断言 `assert_eq!(0o600, mode)`。旁证是相邻测试的文档注释：「A `None` mode must inherit the destination's mode」。
  - **目标文件不存在（首次导入）⇒ 收紧到 `0600` 并不会发生**。同一份代码里 `write_via_temp_with` 只在 `Some(mode)` 时调 `OpenOptions::mode(...)`，`None` 时 tmp 以 `create_new` 的默认 `0o666 & ~umask` 创建，随后 `unix_file_mode(dest)` 返回 `None` ⇒ 连 `set_permissions` 都不发。也就是说：**导入一份新 config 后，文件权限由进程 umask 决定**（常见 umask `022` ⇒ `0644`，同机其他用户可读）。
    这一条**没有测试钉死**（absent 分支无用例），属实现级推导，且真机未实测；但它对「迁移把 env 里的 token 落到哪、谁看得见」有直接关系（见 3.8 的明文边界），所以按「实现可确定」写进正文，不再留白。
- **第二条落盘路径（hooks JSON）在这点上行为不同**：`crates/codegen/xai-grok-external-agent-migration/src/hooks_cla.rs` · 符号：`apply_hooks_to_dir` 用的是 `std::fs::write(target.with_extension("json.tmp"))` + `std::fs::rename`，**不经过** `fs_atomic`。`std::fs::write` 会 truncate/新建，权限位取 `0o666 & ~umask`；rename 是换 inode，所以**旧文件的权限不会被继承**。结论：即使 `imported-from-claude.json` 上次被收紧成 `0600`，重跑一次迁移后它就回到 umask 值——与上面「dest 存在则继承」那条**正好相反**，两条路径不能混记。
- 测试锁住了符号链接那两条：`crates/codegen/xai-grok-external-agent-migration/src/rewrite_tests.rs` 的 `global_import_writes_through_user_config_symlink` 与 `project_import_replaces_config_symlink_not_referent`。

**没有事务、没有回滚。** `apply_import` 先 global 后 project，global 成功后 project 失败 ⇒ global 已经落盘（部分迁移），错误冒泡到 dispatch，`dispatch_import_claude_confirm` 在 Err 分支提前 return ⇒ **两个状态都不会写**（`crates/codegen/xai-grok-pager/src/app/dispatch/import_claude.rs` · 符号：`dispatch_import_claude_confirm`，偏移：+27~+33），修好文件重跑即可。重跑的收敛性由上面那组幂等机制保证。

### 3.7 步骤 7 — 状态与门：两层防重复打扰，但只有两层里的一层真的在挡

| 状态 | 位置与形态 | 谁写 | 谁读 |
|---|---|---|---|
| 内容哈希状态 | `~/.grok/claude_import_state.json`：`{version: 1, global: {last_hash, last_checked}, projects: {…}}`（模型是 `crates/codegen/xai-grok-shell/src/claude_import_state.rs` 的 `ImportState` 与 `ScopeState`） | `mark_imported`（`mark_dismissed` 只是它的别名） | **本快照内无人比对**（见 3.1） |
| 导入 marker | `$GROK_HOME/config.toml` 的 `[claude_compat] imported = true` | `crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · `write_import_marker` | `crates/codegen/xai-grok-config/src/claude_import.rs` · `is_claude_import_marked`（缺文件 / 缺键 / 坏 TOML 一律当作「未导入」） |

哈希怎么算：`crates/codegen/xai-grok-shell/src/claude_import_state.rs` · 符号：`compute_settings_hash`——只读存在且可读的文件、按路径排序保证确定性（偏移：+7）、把「路径 + `\0` + 内容 + `\0`」串起来喂 SHA-256（偏移：+12~+15，所以**改文件名也会变哈希**），输出带 `sha256:` 前缀（偏移：+18）。global 覆盖 `~/.claude/settings.json`、`settings.local.json`、`~/.claude.json` 三个文件（`compute_global_hash`）；project 覆盖项目层 settings 路径加 `.mcp.json` 候选链（`compute_project_hash` 偏移：+9 处先把 `home/.claude` 下的路径剔掉，避免同一目录被算成两种 scope）。落盘同样是 tmp + rename（`save_import_state`）。

**marker 才是真正生效的那一层**，因为它是「运行时兼容层的总闸」：置位后本仓库不再回读 `.claude`。三个消费点各自都写了这个条件：

- env 注入：`crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · 符号：`load_claude_env_with_project` 函数**第一行**就是门（偏移：+2），置位直接返回空表。
- hook 源发现：`crates/codegen/xai-grok-hooks/src/discovery.rs` · 符号：`discover_hook_source_paths`（偏移：+2 是 `compat.claude && claude_import == NotImported` 这个合取），不满足就不把 `~/.claude/settings*.json` 列为 hook 源。
- MCP 源：`crates/codegen/xai-grok-config/src/mcp_servers/json_config.rs` · 符号：`claude_json_resolutions`（偏移：+5）与 `load_mcp_json_servers_as_configs`（同一文件，紧随 `claude_json_resolutions` 之后）。

三个 handler 都会写 marker，含义各不相同：`dispatch_import_claude` 在 plan 为空时写（空 plan 也算「看过了」）；`dispatch_import_claude_confirm` 在落盘后写；`dispatch_dismiss_claude_import` 在用户按 `ctrl+shift+i` 放弃时也写——该函数上方的注释把理由说得很直白：dismiss 等于「我决定了不要 `.claude` 里的东西」，因此同时切断运行时静默回读。注意这条 dismiss 路径在 3.1 所述状态下**同样不可达**（它是欢迎屏快捷键），实际只有前两条会写 marker。

folder-trust 与迁移的关系：`crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · 符号：`claude_settings_paths_for_trust` 是**运行时**加载用的门（不受信任的目录只读用户级 `~/.claude`）。迁移扫描走的是未过滤的 `find_claude_settings_paths`，也就是说 plan 里**可以包含未信任项目里的规则与 env**；本篇只陈述这个差异，不评价它。

### 3.8 步骤 8 — 安全与隐私

- **「凭据不迁移」这句要拆成两轴，否则读者会得出错的安心结论**：
  - **轴一：机密文件本身不读、不写**——这条是**实现级**证据，不再只是 grep 零命中。迁移的写入目标只有两处：`config.toml`（`rewrite.rs` 的 `write_scoped`）与 `.grok/hooks/imported-from-claude.json`（`hooks_cla.rs` · 符号：`apply_hooks_to_dir`，写 `.json.tmp` 再 rename）。Grok 自身凭据存储（`$GROK_HOME/auth.json` 一类）在本 crate **没有任何写入路径**：对 `crates/codegen/xai-grok-external-agent-migration/src/`（排除 `*_tests.rs`）grep `auth` / `credential` / `api_key` / `apikey`（忽略大小写）**零命中**；读取侧也没有 `~/.claude/.credentials.json` 的解析入口（grep `credential` / `oauth` / `apiKeyHelper` / `secret` 在迁移 crate 与 `crates/codegen/xai-grok-shell/src/claude_import.rs` 只命中下面那条注释）。
  - **轴二：但「机密字面值」会跟着配置一起搬过来**——最强正证据是 `crates/codegen/xai-grok-external-agent-migration/src/reporting.rs` · 符号：`format_item_summary` 内部那条注释原文：`// An env value can be a token. The summary shows only its length.`
    设计**承认** env 值可能就是 token，它做的只是**摘要里不打出来**，写盘不脱敏。
  - **机制边界要说清（这条决定「会不会漏」）**：MCP 条目反序列化成 `xai-grok-config` 的 `McpServerConfig`（`crates/codegen/xai-grok-config/src/mcp_server_config.rs` · 符号：`McpServerConfig`）后**由结构体重新序列化**落盘（`merge_mcp_servers` 走 `toml::Value::try_from(*config)`），该 struct **没有** `#[serde(deny_unknown_fields)]`、transport 是 `#[serde(flatten)]` + `#[serde(untagged)]`。后果两条：①Claude JSON 里多出来的未知键（比如某个裸写的 `apiKey`）**会被静默丢弃**，不会被原样搬过去；这个「看不见未知键」是**已知盲区**——同一个文件里有一份**手工维护**的 `KNOWN_MCP_SERVER_FIELDS` 常量，注释原文写明 `Listed by hand because serde_ignored cannot see unknown keys inside the flattened untagged transport enum`，而这份清单的消费者是 `crates/codegen/xai-grok-shell/src/config_docs/mod.rs`（用来断言文档覆盖了每个已知字段），**不是**运行时的未知键告警；②**类型化字段里的字面值照搬**：`Stdio.env`、`StreamableHttp.headers` 是 `HashMap<String, String>`，值原样进 `config.toml`。
  - **对比项：引用式字段不搬机密**。`bearer_token_env_var` / `oauth_client_secret_env_var` 存的是**变量名**、`bearer_token_file` 存的是**路径**（注释写明「Re-read on every request」）——这三个即使迁移成功，落盘的也只是指针，token 本体仍在原处。所以「迁移带不带凭据」取决于配置用的是**引用式**还是**字面式**写法，不能一句话答「不带」。
- **但明文通道确实有两条**：① `env` 的值原样写进 `config.toml` 的 `[env]`，`merge_env_vars` 没有脱敏也没有过滤；② MCP server 整个配置经 `toml::Value::try_from` 序列化进 `[mcp_servers]`（`crates/codegen/xai-grok-external-agent-migration/src/mcp.rs` · 符号：`merge_mcp_servers`，偏移：+15），其中可能带 token 的 `env` / `headers` 一并落盘。脱敏只发生在**摘要展示**那一层（`crates/codegen/xai-grok-external-agent-migration/src/reporting.rs` · 符号：`format_item_summary`，偏移：+62~+63），写盘不脱敏。
- **确认提示：有，而且是逐项的**。弹窗默认全选但必须显式 `Confirmed` 才 apply；`Cancelled` 走 `dispatch_import_claude_cancel`，不落盘也不写状态。
- **日志**：`xai_grok_external_agent_migration=info` 在默认日志指令串里（`crates/codegen/xai-grok-pager/src/tracing.rs` · 符号：`default_directives`，偏移：+4）。info / warn 打的是路径与计数；唯一进日志的「内容」是被跳过的规则串本身（`snapshot_at` 的 `debug!` 分支，级别低于 info）。hook 的 `command` 会全文进摘要，这是明文之外的第二个暴露面。

### 3.9 步骤 9 — 失败路径汇总

| 场景 | 行为 | 锚点 |
|---|---|---|
| 源文件缺失 / 不可读 | 解析闭包返回 `None`，引擎 `continue` 跳过该文件；hook 提取返回空 `Vec` | `crates/codegen/xai-grok-shell/src/claude_import.rs` · 符号：`snapshot_at`（偏移：+1）与 `crates/codegen/xai-grok-external-agent-migration/src/source_cla.rs` · 符号：`scan_importable_settings`（偏移：+10~+12） |
| 源 JSON 非法 | 同上：`load_claude_settings` 解析失败即弃（不给部分结果），hook 提取静默空 | `crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · 符号：`load_claude_settings`（偏移：+17） |
| 源路径是 FIFO / 目录等非普通文件 | 先查 `metadata`，不是 regular file 就 warn 并返回 `None`——注释说明这是防止阻塞会话 actor | 同一符号，偏移：+1~+2 |
| 单条规则不认识 / 解析失败 | `debug!` 跳过这一条，同文件其余规则继续；静默丢失 | `crates/codegen/xai-grok-shell/src/claude_import.rs` · 符号：`snapshot_at`（偏移：+13、偏移：+20） |
| 目标 `config.toml` 是非法 TOML | `MigrationError::InvalidToml`，**文件保持原样**、整体失败；注释解释「重写会丢掉本导入不写的节」 | `crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · 符号：`read_toml_root`（偏移：+2）与 `crates/codegen/xai-grok-external-agent-migration/src/error.rs` · 符号：`MigrationError` |
| 目标节类型不对（如 `[permission]` 不是表、`permission.ask` 不是数组） | `NotATable` / `NotAnArray` 直接中止；`[env]` 不是表是唯一例外——warn 后跳过 env 这一路 | `crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · 符号：`merge_permissions`（偏移：+7）、`merge_env_vars`（偏移：+4） |
| `imported-from-claude.json` 已损坏 | warn + **整体替换重写**，文件里手工改过的内容丢失 | `crates/codegen/xai-grok-external-agent-migration/src/hooks_cla.rs` · 符号：`read_hooks_root`（偏移：+2） |
| hooks 目录里 `hooks.<event>` 不是 JSON 数组 | `NotAJsonArray` 中止 | `crates/codegen/xai-grok-external-agent-migration/src/hooks_cla.rs` · 符号：`apply_hooks_to_dir`（偏移：+41~+47） |
| 写盘 IO 失败 | `MigrationError::Io` 冒泡；状态与 marker 都不写，可修正后重试 | `crates/codegen/xai-grok-pager/src/app/dispatch/import_claude.rs` · 符号：`dispatch_import_claude_confirm`（偏移：+27~+33） |
| MCP server 序列化失败 | `McpSerialize`，带 server 名 | `crates/codegen/xai-grok-external-agent-migration/src/mcp.rs` · 符号：`merge_mcp_servers`（偏移：+15） |
| 「对方版本不认识」 | **没有版本协商概念**：settings schema 宽容解析（未知键被 serde 忽略），也没有兼容版本号可比较 | `crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · 符号：`ClaudeSettings` |
| 什么都没扫到 | 不弹模态，写状态 + marker，并追加一条 Info 摘要 "No Claude settings found to import." | `crates/codegen/xai-grok-pager/src/app/dispatch/import_claude.rs` · 符号：`dispatch_import_claude`（偏移：+4~+18） |

---

## 第四层 · 补全所有逻辑与技术要点

### 4.1 配置项 / 环境变量 / 开关

| 键 / 变量 | 形态 | 作用 | 归属 |
|---|---|---|---|
| `[claude_compat].imported` | `config.toml` 布尔 | 兼容层总闸（3.7）；迁移只写它 | 写在 `crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` · `write_import_marker`，读在 `crates/codegen/xai-grok-config/src/claude_import.rs` · `is_claude_import_marked` |
| `_GROK_CLAUDE_MARKER_OVERRIDE` | 环境变量，值为 `1` | 测试逃生阀：让 permission-rules 侧的门当作 marker 已置位（`crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · 符号：`is_claude_import_marked`，偏移：+3 及其上方注释） | 只服务于跨 crate 的测试 |
| `[compat.claude]` 六面 | `config.toml`：`skills` / `rules` / `agents` / `mcps` / `hooks` / `sessions` | 决定「迁移前 `.claude` 是否被静默消费」；默认**全 true**（`crates/codegen/xai-grok-config/src/compat.rs` · `impl Default for VendorCompat`，偏移：+3~+8） | 运行时兼容层，不参与迁移本身 |
| `GROK_CLAUDE_{SURFACE}_ENABLED` | 环境变量六个 | 优先级高于配置文件（`crates/codegen/xai-grok-config/src/compat.rs` · 符号：`COMPAT_CELLS`，18 个 cell 覆盖 cursor / claude / codex 三 vendor） | 同上 |
| `claude_*_enabled` | 远端下发 | 优先级最低的一档（`crates/codegen/xai-grok-config/src/remote_settings.rs` 的 `claude_skills_enabled` 一类字段） | 同上 |
| 写入侧目标键 | `[permission].{allow,deny,ask}`、`[env]`、`[mcp_servers]`、`[paths].extra_skill_dirs`、`[paths].extra_rule_dirs` | 迁移产出的全部落点 | `crates/codegen/xai-grok-external-agent-migration/src/rewrite.rs` |

`enum CompatVendor` 里有三个 vendor，但**迁移只实现 Claude 一家**：引擎目录里没有 cursor / codex 的 source 模块，`source_cla.rs` 是唯一的来源文件。这一点值得写清，因为 crate 名字（external-agent-migration）比实现范围大。

### 4.2 与运行时 compat 的边界（为什么不能并进配置篇）

同一批外部文件被两条互不相干的链路读：迁移链路（本篇，一次性、有用户确认）与运行时 compat 链路（每次会话都可能读、无人确认）。两者唯一的耦合点就是 3.7 的 marker：迁移置位 ⇒ compat 停读。把这条链画出来，能避免「迁移后 compat 还在偷偷读」这类误判：

```
   /import-claude 确认 / dismiss
        │ write_import_marker → [claude_compat] imported = true
        ▼
   config claude_import.rs · is_claude_import_marked（缺文件/缺键/坏 TOML ⇒ false）
        │
        ├─→ permission-rules claude_settings.rs · load_claude_env_with_project（env 注入）
        ├─→ hooks discovery.rs · discover_hook_source_paths（hook 源）
        └─→ config json_config.rs · claude_json_resolutions（MCP 源）
```

### 4.3 「迁移后不生效」的两处，必须写进用户可见文档

- `[paths] extra_skill_dirs`：**只用于展示**。`crates/codegen/xai-grok-shell/src/extensions/skills.rs` · 符号：`discover_auto_sources` 会读它（偏移：+63 起把目录列成「来源目录」），但目录里的 skill 是否被加载与之无关。
  加载侧不读这个键：`crates/codegen/xai-grok-agent/src/prompt/skills.rs` · 符号：`list_skills_with_plugins`；仓库自带文档也这么写（`crates/codegen/xai-grok-pager/docs/user-guide/08-skills.md`：「`[paths] extra_skill_dirs` is written by `/import-claude`. It does not inject skills.」）。要真正注入得手工改 `[skills] paths`。
- `[paths] extra_rule_dirs`：**真的生效**（与上面形成对照）。`crates/codegen/xai-grok-agent/src/prompt/paths.rs` · 符号：`PathsConfig` 的 `extra_rule_dirs` 字段被 `crates/codegen/xai-grok-agent/src/prompt/agents_md.rs` 按 home 作用域扫描成规则文件。

也就是说：同一个 `PathEntry` 变体，`Skill` 与 `Rule` 两种 kind 迁移后的活跃度不一样。文档若把两者写成「登记目录路径，迁移后可直接使用」就是错的。

### 4.4 这个功能**不该**在什么时候被期待发生

| 不成立的期待 | 事实 |
|---|---|
| 「打开 Grok 会提示我有 Claude 配置可以导」 | 不成立：门变量从未置 true（3.1），检测函数无调用方，哈希状态只写不读。入口只有 `/import-claude`。 |
| 「`ctrl+i` 能打开导入弹窗」 | 不成立：快捷键存在但被同一个恒 false 的变量挡在前面。 |
| 「迁移会把 `.claude/skills` 里的 skill 复制过来」 | 不成立：只登记目录路径（3.3），且不复制任何文件。 |
| 「迁移完 skills 目录就生效」 | 不成立：见 4.3。 |
| 「迁移会带过来我的会话历史 / CLAUDE.md 内容 / 登录凭据」 | 前半成立、后半要分两层：范围就是 `ImportableItem` 五个变体（第一层），凭据文件本体既不解密也不复制；**但**若你在 Claude 的 `env` 或 MCP `headers` 里**明文**写过 token，那串字面值会跟着配置一起进 `config.toml`（3.8 轴二）。 |
| 「`defaultMode` 会被导成 Grok 的默认权限模式」 | 不成立：`crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · `extract_default_mode` 解析了它，但适配器只取 `permissions` 与 `env`（3.3 表右列的 `ClaudeSettingsSnapshot` 只有两个字段）。 |
| 「迁移失败会回滚已写的部分」 | 不成立：无事务（3.6 末）。 |
| 「没被识别的工具规则会在界面上提醒我」 | 不成立：只 `debug!`（3.4）。 |
| 「有 CLI 子命令或某个 feature gate 能不开 TUI 就跑迁移」 | 不成立：crate 无 `[features]`，无 CLI 入口；`scan_importable_settings` 全仓唯一调用方就是 pager 的 dispatch。 |

### 4.5 测试矩阵

| 位置 | `#[test]` 数 | 覆盖点 |
|---|---|---|
| `crates/codegen/xai-grok-external-agent-migration/src/rewrite_tests.rs` | 11 | 权限去重、env 不覆盖也不建多余节、marker 新建 / 保留原内容 / 幂等、`[paths]` 写入、global 穿透 symlink 与 project 替换 symlink 两条对照 |
| `crates/codegen/xai-grok-external-agent-migration/src/hooks_cla_tests.rs` | 12 | 多事件与 matcher 提取、非 command 跳过、坏字段静默、空 command 照收、写文件、去重、timeout 刷新与删除 |
| `crates/codegen/xai-grok-external-agent-migration/src/config_values_tests.rs` | 1 | `format_rule_string` 与 Claude 原文一致（往返保真） |
| `crates/codegen/xai-grok-shell/src/claude_import_tests.rs` | 14（另加 1 个 `#[tokio::test]`） | marker 对 hook 发现 / env 注入 / MCP 源 / 权限解析四类门的开闭、trust 门、`[paths]` 反序列化 |
| `crates/codegen/xai-grok-shell/src/claude_import_state.rs`（文件内联 `mod tests`） | 4 | 哈希确定性、排序、跳过缺失文件、内容变更敏感 |
| `crates/codegen/xai-grok-config/src/claude_import_tests.rs` | 1 | marker 读取三态（缺文件 / 缺键 / 坏 TOML 都算未导入） |
| `crates/codegen/xai-grok-pager/src/views/import_claude_modal.rs`（文件内联 `mod tests`） | 15 | `filtered_plan` 的逐项与分组勾选 |
| `crates/codegen/xai-grok-shell/tests/config_write_symlink.rs` | 1 | marker 写盘与 symlink 的交互 |

矩阵的空白处也要说：plan **分组**（global / project 判定、`~/.claude.json` 双份都进 global、目录去重）没有独立的引擎侧单测文件——`crates/codegen/xai-grok-external-agent-migration/src/source_cla.rs` 没有配套的 `#[path = …]` 测试模块（`crates/codegen/xai-grok-external-agent-migration/src/lib.rs` 只声明了三个 test 模块），这部分行为目前靠 shell 侧的适配器测试间接覆盖。

### 4.6 设计不变量小结（本章范围内）

1. **引擎不认识来源格式**：所有 Claude JSON 知识集中在 shell 的解析闭包，引擎只处理 `ImportableItem`。新增第二家 vendor 时，新增的是一个 source 模块 + 一个适配器，不是改写入器。
2. **写入是合并而非替换**：任何一次落盘都先读原文件、只补缺失键；非法 TOML 直接拒绝写入而不是重建文件。
3. **冲突一律「内部优先」**：已存在的 env 键、同名 MCP server、已存在的 hook 组合都不覆盖（唯一例外是 hook 的 `timeout` 会被原位刷新）。
4. **可重跑**：去重 + 存在即跳过 + unfiltered 读取三者合起来，让 `/import-claude` 是一个收敛操作而非累加操作。
5. **状态分两层，语义不同**：marker 是功能闸（决定运行时还读不读 `.claude`），哈希状态是提示抑制器（本快照里没人读）。写 marker 的三个时机（导入 / 空 plan / dismiss）都表达同一件事：「用户对 `.claude` 做过决定了」。
6. **global 与 project 是两条独立作用域**：判定看路径前缀、落点分别是 `$GROK_HOME` 与 `<projectRoot>/.grok`、symlink 语义**故意相反**。
7. **无事务**：global 与 project 之间、`config.toml` 与 hooks 文件之间都没有原子性；正确性靠「失败不写状态 + 幂等重跑」兜。
8. **明文边界**：迁移不读任何凭据文件（Grok 的 auth 存储连写入路径都没有），但 `env` 值与 MCP `env`/`headers` 的**字面值**是明文落盘、只在摘要里打码；`bearer_token_env_var`/`bearer_token_file` 这类引用式字段只搬变量名或路径，不搬机密。

---

## 变更记录

### 初稿，基准 `HEAD = 42f4d7d3`（2026-10-27，`SOURCE_REV = 559751fd`）

**本篇为何独立成篇**：链路跨 6 个 crate（migration / shell / permission-rules / config / pager / hooks），且「运行时 compat / 一次性迁移 / 迁移状态」是三套不同的东西，塞进第 06 篇（配置）会把它们搅在一起；与第 13 篇（持久化）只共享 `claude_import_state.json` 一小节，交叉引用即可。落点决定见 `.progress/C-PLAN.md` §二。

**本篇做的事**：四层结构按第 11 篇样板写；所有 `符号(+偏移)` 回源码实测（`sr_tools.py offset` / `outline` 与直接 Read），来源证据卡 `.progress/evidence/new-external-agent-migration.md` 作为线索使用。

**相对证据卡的更正与补充**（一律以源码为准）：

1. 卡片的「13 文件 ~1,784 行」→ 实测 `crates/codegen/xai-grok-external-agent-migration/src/` 是 **12 个文件、共 1,784 行**（8 个实现 + 3 个 `#[path]` 测试模块 + `lib.rs`）。行数对得上，文件数差 1。
2. 卡片 §3 说「`claude_import_state` 的哈希在本快照中只写不读，**疑在上游/未接入（未确认）**」→ 本篇把它确认了：`crates/codegen/xai-grok-permission-rules/src/claude_settings.rs` · `has_claude_compat` 全仓零调用方，`crates/codegen/xai-grok-shell/src/claude_import_state.rs` · `load_import_state` 是 `pub(crate)` 且只被 `mark_imported` 内部调用。`has_claude_import` 恒 false 的结论同样复核为**仍然成立**。
3. 卡片 §6 说「dismiss 也写 marker（dispatch L13/L99）」→ 成立，但补充一条卡片没说的：dismiss 路径本身挂在恒 false 的 `has_claude_import` 门上，所以它在当前树里同样不可达；实际会写 marker 的只有「导入」与「空 plan」两条。
4. 卡片 §2 把 `~/.claude.json` 的项目 server 归入 global 是对的，本篇补上它的用户可见后果（在别人项目里配的 server 会进你的用户级 `config.toml`）。
5. 卡片 §4 的 `Mcp` 标签只写了「否则 `Tool(pattern)`」→ 实测 `crates/codegen/xai-grok-external-agent-migration/src/config_values.rs` · `tool_label` 把 `ImportTool::Mcp` 写成 `MCPTool`，与 `crates/codegen/xai-grok-permission-rules/src/rules.rs` · `tool_name_to_filter` 认识的 `MCPTool` 对称，因此可往返；本篇补了这条以及「空 pattern 与 `*` 归一」的细节。
6. 卡片 §9 说 `extra_skill_dirs` 不注入 skills（引 user-guide）→ 本篇回代码确认，并补上卡片未提的**不对称**：`extra_rule_dirs` 是被真实加载的（`crates/codegen/xai-grok-agent/src/prompt/paths.rs` · `PathsConfig`）。
7. 卡片 §5 把 project root 写成 `scope.rs · find_project_root`；实测该文件全文 9 行、只有一个函数，行为是「git2 discover 成功取 workdir，否则退回 cwd」，本篇照此写。
8. 卡片 §1 未提的一处：迁移扫描用的是**未过滤**的 `find_claude_settings_paths`，不受 folder-trust 门影响（运行时加载才走 `claude_settings_paths_for_trust`）。本篇在 3.7 末尾陈述了这个差异。

**留白（当前源码无法确定）**：`fs_atomic::write_atomically_bound` 传 `None` 时最终文件权限位是否为 `0600`（3.6 末，未下结论）；「凭据不迁移」是 grep 零命中级别的结论，无法证明存在显式拦截（3.8）。
↑ 这两条**已由下面的收口轮回补**，此处仅作历史保留。

### 收口轮（2026-10-28，同基准 `HEAD = 42f4d7d3`）——清掉初稿留白

1. **`write_atomically_bound(..., None)` 的权限位有结论了**（3.6 已改写）。分两种情形，且**证据等级不同**：
   - dest 已存在 ⇒ **继承 dest 当前权限位**，`set_permissions` 路径不受 umask 削位；**测试钉死**（`crates/codegen/xai-grok-config/src/fs_atomic_tests.rs` · `write_atomically_bound_survives_chmod_and_inherits_live_mode`，先 chmod `0600` 再以 `None` 写入、断言仍是 `0600`）。
   - dest 不存在（首次导入）⇒ **不会收紧成 `0600`**：`write_via_temp_with` 只在 `Some(mode)` 时调 `OpenOptions::mode`，`None` 时 tmp 以 `create_new` 默认的 `0o666 & ~umask` 创建，随后 `unix_file_mode(dest)` 返回 `None` ⇒ 连 `set_permissions` 都不发。此分支**无测试**，属实现级推导、真机未实测，正文按「实现可确定」标注。
   - 顺带查出**两条落盘路径行为相反**：hooks JSON 用 `std::fs::write` + rename（不经 `fs_atomic`），rename 换 inode ⇒ **不继承**旧文件权限，重跑一次迁移就把上次收紧的 `0600` 打回 umask 值。这条初稿完全没有。
2. **「凭据不迁移」拆成两轴**（3.8 已改写），原来那句一刀切的结论会给出错的安心感：
   - 轴一「凭据文件不读不写」升级为**实现级**证据：迁移写入目标只有 `config.toml` 与 `.grok/hooks/imported-from-claude.json` 两处，且对迁移 crate（排除 `*_tests.rs`）grep `auth`/`credential`/`api_key`/`apikey` **零命中**。
   - 轴二「机密字面值仍会搬」补了**源码自证**：`crates/codegen/xai-grok-external-agent-migration/src/reporting.rs` 里那条注释原文 `An env value can be a token. The summary shows only its length.`
   - 补了机制边界：MCP 条目按 `xai-grok-config` 的 `McpServerConfig` 反序列化后**由结构体重新序列化**落盘，`deny_unknown_fields` 缺失 + `flatten` + `untagged` ⇒ 未知键静默丢弃；该盲区在源码里是**已知**的（同一文件手工维护 `KNOWN_MCP_SERVER_FIELDS`，注释点明 serde_ignored 看不见 flatten 里的未知键），其消费者是 `xai-grok-shell` 的 config_docs 覆盖断言，不是运行时告警。
   - 补了「引用式 vs 字面式」的区分：`bearer_token_env_var` / `oauth_client_secret_env_var` / `bearer_token_file` 只搬变量名或路径，`env` / `headers` 搬字面值 ⇒ 「带不带凭据」取决于用户在 Claude 侧怎么写。
3. 第一层「不迁移什么」、第五层误解表、第八层第 8 条同步按两轴口径改写。
4. **仍未收口的**：`apply_hooks_to_dir` 的 tmp 名固定为 `target.with_extension("json.tmp")`（不是 pid+nonce），并发两个导入会话理论上会互相覆盖 tmp——只读了实现、没测；`/import-claude` 之外是否还有别的路径能把 Claude 侧凭据搬进来（超出本 crate 范围，未查）。

**待收录到其它篇（由刷新者执行，本篇不改）**：第 06 篇补 `[claude_compat].imported` 与 `[compat.claude]` 六面键的一行归属说明；第 13 篇补 `~/.grok/claude_import_state.json` 一行；README 覆盖矩阵与 00 篇文档地图收录本篇（第 19 篇），并把全库 `第 N / M` 的分母重排。（**2026-10-28 收口轮回写状态：四条均已落地，逐条回该文件核实过。**① [第 06 篇](06-配置与数据流.md)正文已有 `[compat.*]` 六面与 `[claude_compat].imported` 的归属；② [第 13 篇](13-持久化记忆与会话恢复.md)已写清两层互不相同的导入状态（全局布尔标记与按 cwd 记录的 `~/.grok/claude_import_state.json`）并指针回本篇；③ [README](README.md) 覆盖矩阵与 [第 00 篇](00-阅读指南与文档地图.md) §2 均收录本篇；④ 全库分母 22，`nav` 实测 195 条链接、断链 0、无孤儿页。详见 `.progress/C-PLAN.md` 五之三。）

### 更早的基准

本篇为新增章节，此前无对应文档。基准沿革同全库：`HEAD = 0e2bfffb` / `SOURCE_REV = 036a5d83`（上一轮刷新）→ 本轮 `HEAD = 42f4d7d3`。

---

[上一篇：权限规则引擎](18-权限规则引擎.md) · [总目录](README.md) · [下一篇：Git Worktree 快速铺设与 GC](20-Git-Worktree快速铺设计与GC.md)
