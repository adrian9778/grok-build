# 证据卡：xai-grok-external-agent-migration（Claude 设置迁移）

快照：commit `42f4d7d3`（2026-10-14）。锚点记法 `文件 · 符号(+N)`；绝对行号仅作快照参考。

## 0. 功能定性（Cargo.toml description 原文）
> "Import Claude settings into Grok config: permissions, hooks, MCP servers, environment variables, skill directories, and rule directories"
- `crates/codegen/xai-grok-external-agent-migration/Cargo.toml` · package description（快照 L6）

**只迁移 Claude Code 的"配置面"，共 5 类**：permission 规则、env 变量、MCP server、hooks、skills/rules **目录路径登记**。
**不迁移**（grep 全 crate 无引用）：会话历史/transcript、记忆（memory）、CLAUDE.md 文件内容（仅运行时 compat 读，见 §8）、`defaultMode`、`additionalDirectories`、任何凭据文件、agents/personas 定义文件本体。
- 会话历史是**另一个独立功能**（foreign sessions / `/resume-claude`，`xai-grok-pager/src/app/foreign_sessions.rs` · ForeignSessionTool::Claude），与本 crate 无关。
- `ClaudeSettingsSnapshot` 只含 `permissions + env` 两字段（`config_values.rs` · ClaudeSettingsSnapshot+0）；`load_claude_settings` 解析出的 `default_mode`/`additional_directories` 被丢弃不入 plan（`xai-grok-shell/src/claude_import.rs` · snapshot_at 只取 .permissions/.env）。

## 1. 读取的外部文件形态（全部读码确认，非按常识推断）
| 来源文件 | 发现函数 | 格式/键 |
|---|---|---|
| `~/.claude/settings.json`、`~/.claude/settings.local.json`、项目 `<dir>/.claude/settings{,.local}.json`（cwd→repo root 逐层，local 优先） | `xai-grok-permission-rules/src/claude_settings.rs` · `find_claude_settings_paths+0`、`collect_project_claude_paths+0` | JSON：`permissions.allow/deny/ask`（字符串数组）、`env`（对象，数字/布尔强转字符串，null/数组/对象跳过+warn：`extract_string_map+0`）、`hooks`（event→[{matcher, hooks:[{type:"command",command,timeout}]}]，非 command type 跳过：`xai-grok-external-agent-migration/src/hooks_cla.rs` · extract_hooks_from_settings_file+0） |
| `~/.claude.json` | `xai-grok-config/src/mcp_servers/json_config.rs` · `load_claude_json_mcp_servers_as_configs_unfiltered+0` | `projects["<cwd 字符串>"].mcpServers` + 顶层 `mcpServers`，**两者都进 global_items**（migration `source_cla.rs` · scan_importable_settings+0 注释「Both are stored in the global list」） |
| `<dir>/.mcp.json`（repo root→cwd 逐层） | `xai-grok-permission-rules/src/project_config.rs` · `find_mcp_json_files+0`（shell `util/config` 再导出；`claude_import.rs` · scan_importable_settings 调用） | `mcpServers` 对象；缺失文件静默跳过（`compute_settings_hash` 亦跳过不存在文件） |
| `~/.claude/skills`、`~/.claude/rules`、`<projectRoot>/.claude/{skills,rules}` | migration `source_cla.rs` · `existing_claude_path_dirs+0` | **只登记目录路径**（`is_dir()` 才收），不复制文件；canonicalize 去重防同一目录同时记 global+project（scan_claude_path_dirs+0） |

global/project 判定：路径以 `home/.claude` 开头即 global（scan_importable_settings+0 的 `is_global`）；home 用 `xai_dirs::home_dir()`（对齐 Node os.homedir，Windows 走 USERPROFILE，见 claude_import_state.rs 注释）。

## 2. 入口与调用链（入口→发现→解析→转换→写入）
```
斜杠命令 /import-claude（唯一活跃入口）
  xai-grok-pager/src/slash/commands/import_claude.rs · ImportClaudeCommand
  （allowlist 注册：xai-grok-shell/src/session/slash_commands.rs L486 "import-claude"）
→ Action::ImportClaudeSettings（app/actions.rs · ImportClaudeSettings）
→ app/dispatch/router.rs L281 → dispatch/import_claude.rs · dispatch_import_claude+0
→ 发现+解析+转换：xai-grok-shell/src/claude_import.rs · scan_importable_settings+0
    ├─ claude_settings::find_claude_settings_paths（permission-rules，经 workspace 再导出）
    ├─ snapshot_at+0 → load_claude_settings + rules.rs::parse_permission_rule
    └─ migration crate scan_importable_settings（纯函数，注入 snapshot 闭包）→ ImportPlan
→ TUI 审阅：views/import_claude_modal.rs · ImportClaudeModalState（逐项勾选，默认全选：new+0）
→ 确认：dispatch_import_claude_confirm+0 → filtered_plan → migration · apply_import+0
→ 写入（§5）+ mark_imported（哈希状态）+ mark_claude_imported（marker）
```
- 欢迎屏第二入口：`ctrl+i` 打开 / `shift+ctrl+i` 直接 dismiss（`app/app_view.rs` · 3616/3619 快照行，`has_claude_import` 门）。**注意：当前树里没有任何代码把 `has_claude_import` 置 true**（全仓 grep 仅见 `= false` 与 `: false`），`claude_import_state` 的哈希（§6）在本快照中**只写不读**——启动检测调用方缺失，疑在上游/未接入（未确认，勿在文档中断言启动横幅会出现）。
- 无 CLI 子命令（`xai-grok-pager-bin` grep "claude" 无结果）。
- feature gate：crate Cargo.toml 无 `[features]`。

## 3. 与 shell claude_import.rs 的分工（两层，同一流程）
| 层 | 文件 | 职责 |
|---|---|---|
| 引擎（无 Claude JSON 权限解析知识） | `xai-grok-external-agent-migration`（13 文件 ~1,784 行） | scan 汇总/分组、ImportPlan/ImportableItem 数据模型、TOML/JSON 合并写入、错误类型、summary 渲染 |
| 适配器 | `xai-grok-shell/src/claude_import.rs`（现仅 144 行，**不是 +2,181**；2,181 应为 merge diff 行数） | 提供文件发现路径、`snapshot_at` 解析闭包（Claude 字符串规则→ImportPermission 映射）、marker 读写与进程内缓存（MARKER_CACHE + is_claude_import_marked_with_log）、`import_marker()` 桥给 hooks discovery |
| UI | pager dispatch + modal | 触发、勾选、结果提示 |
- **不是两个独立功能**：crate 通过 `scan_importable_settings(cwd, paths, snapshot闭包, mcp_files)` 的注入式设计把解析逻辑留在 shell（因为 parse_permission_rule 依赖 permission-rules crate，而 migration crate 刻意不依赖它）。

## 4. 字段映射与降级
- Claude 规则串 `Tool(pattern)` → `parse_permission_rule`（`rules.rs` · +0）→ `PermissionRule{action,tool,pattern,pattern_mode}` → shell `import_permission+0` 逐字段转 `ImportPermission` → 写回时 `format_rule_string+0`（`config_values.rs`）：Any 无 pattern→`*`；Domain 模式→`domain:{p}`；否则 `Tool(pattern)`。
- 工具别名折叠（rules.rs · tool_name_to_filter+0 快照 L244）：`Write→Edit`、`Glob→Grep`、`SendSubagentMessage/SendAgentMessage→AgentMessage`；`EnterWorktree/NotebookEdit/NotebookRead`→显式 UnsupportedToolPrefix；未知前缀→UnknownToolPrefix。**两者在 snapshot_at 只 debug! 跳过该条规则（静默丢失，无用户可见告警）**。
- `Bash(cmd:*)` 特判：`cmd:` 前缀语义转 glob（rules.rs 注释 快照 L168）。
- env：逐键复制，**已存在的键不覆盖**（merge_env_vars+0：`contains_key` 才跳过→count 不计）。MCP：按 server 名，**同名已存在则整个跳过**（mcp.rs · merge_mcp_servers+0）。冲突策略一律"内部优先、保留现状"。
- 权限目标键：`[permission] allow/deny/ask` 字符串数组，append_missing_strings 去重（rewrite.rs）。

## 5. 写入落点与幂等
- global：`$GROK_HOME/config.toml`（rewrite.rs · apply_import+0 → apply_items_to_grok_dir+0，`USER_CONFIG_FILENAME`=`config.toml`，config/loader.rs+0 快照 L91）+ `$GROK_HOME/hooks/imported-from-claude.json`（hooks_cla.rs · apply_hooks_to_dir+0；该目录正是运行时 hook 发现源：`xai-grok-config/src/global_hook_sources.rs` · resolve_global_hook_sources+0 快照 L469）。
- project：`find_project_root(cwd)/.grok/config.toml` 与 `.grok/hooks/imported-from-claude.json`；project root = git2 discover，否则 cwd（scope.rs · find_project_root+0）。
- 幂等：字符串数组 append_missing_strings 去重；env/MCP 存在即跳过；hooks 按 (event,matcher,command) 匹配则**原位刷新 timeout**（可删 timeout）不重复追加（refresh_existing_hook_timeout+0）；marker 幂等（rewrite_tests · write_import_marker_idempotent）。重跑 `/import-claude` 安全，unfiltered loader 就是为重导"上次跳过项"设计（json_config.rs 注释 快照 L59/L111）。
- 符号链接语义（rewrite.rs · write_scoped+0，测试 global_import_writes_through_user_config_symlink / project_import_replaces_config_symlink_not_referent）：**global 写穿透 symlink（含 TOCTOU 双次 bind 校验），project 写替换 symlink 本身**。原子写走 fs_atomic tmp+rename。
- 回滚：**无事务/回滚**。count>0 才写；已有 config.toml 非法 TOML 时整段拒绝写入（read_toml_root+0 注释「Rewriting would drop unknown sections」）。global 成功后 project 失败 → global 已落盘（部分迁移），错误冒泡到 dispatch，**marker 不写**（confirm+0 的 Err 分支提前 return），可修正后重试。

## 6. 状态与门（双层防重复打扰）
- `~/.grok/claude_import_state.json`：`{version:1, global:{last_hash, last_checked}, projects:{root:…}}`，hash=SHA-256(排序后 路径\0内容\0 串接)（`xai-grok-shell/src/claude_import_state.rs` · compute_settings_hash+0）。mark_imported/mark_dismissed 同义（记录哈希=不再提示直到文件变化）。本快照内**无读取比对方**（见 §2 注意）。
- `[claude_compat] imported = true` 写入 `$GROK_HOME/config.toml`（rewrite.rs · write_import_marker+0）；读取 `xai-grok-config/src/claude_import.rs` · is_claude_import_marked+0（缺文件/缺键/坏 TOML 一律按未导入）。
- **marker 是"兼容层总闸"**：置位后运行时不再回读 .claude——env 注入（claude_settings.rs · load_claude_env_with_project+0 首行 gate）、hook 发现（`xai-grok-hooks/src/discovery.rs` · discover_hook_source_paths+0：`compat.claude && claude_import==NotImported` 才把 `~/.claude/settings*.json` 列为源）、MCP 源（json_config.rs claude_json_resolutions+0 等）。dismiss/空 plan 也写 marker（dispatch L13/L99 注释：dismiss 即"决定不要"，同时切断运行时静默回读）。
- 未信任目录：`claude_settings_paths_for_trust+0` 只取用户级 `~/.claude`（folder-trust 门与扫描共用 collect_project_claude_paths 防漂移）。

## 7. 安全与隐私（读到代码证据）
- **凭据不迁移**：crate 及 shell 适配器 grep `credential|oauth|apiKeyHelper|secret` 零命中；不触碰 `~/.claude/.credentials.json`（该类文件从未被引用；注意这是"代码中无证据"级结论）。
- **但明文通道存在两条**：① `env` 值原样写入 `[env]` config.toml（merge_env_vars 无脱敏/过滤；reporting.rs 注释承认「An env value can be a token」——仅在**摘要展示**时 `<redacted, N chars>`，写盘不脱敏）；② MCP server 配置整体 `toml::try_from` 序列化进 `[mcp_servers]`，其 env/headers 可含 token，同样明文。
- 确认提示：有。modal 逐项勾选（默认全选）→ 显式 Confirmed 才 apply；Esc 取消不落盘。文件权限模式未显式指定（write_atomically_bound 传 None）——未确认是否收紧到 0600。
- 日志：`xai_grok_external_agent_migration=info` 在默认 log 指令里（pager/tracing.rs+0 快照 L376），info/warn 打路径与计数，未见打印 env 值/hook command 参数以外的敏感面（hook command 本身会进 summary 展示）。

## 8. 失败路径汇总
| 场景 | 行为 | 锚点 |
|---|---|---|
| 源文件缺失/不可读 | snapshot 返回 None→整文件跳过；hooks 返回空 vec | claude_settings.rs load_claude_settings+0；hooks_cla.rs extract+0 |
| 源 JSON 非法 | load_claude_settings→None（serde 解析失败即弃）；hooks 解析失败静默空 | 同上 |
| FIFO/非普通文件 | metadata 检查拒读（防 session actor 阻塞） | load_claude_settings+0 注释 |
| 单条规则非法/工具不认识 | debug! 跳过该条，其余继续 | shell claude_import.rs snapshot_at+0 |
| 目标 config.toml 非法 TOML | InvalidToml 错误，**文件保持原样**，整体失败 | rewrite.rs read_toml_root+0、error.rs InvalidToml |
| 目标节类型错（如 [permission] 非表） | NotATable/NotAnArray 错误中止 | rewrite.rs merge_permissions+0 |
| imported-from-claude.json 已损坏 | warn + **替换重写，手改丢失** | hooks_cla.rs read_hooks_root+0 |
| 写盘 IO 失败 | MigrationError::Io 冒泡；marker 不写、可重试 | dispatch confirm Err 分支 |
| "版本不认识" | 无版本协商概念；settings schema 宽容解析（未知键忽略），无兼容版本号 | claude_settings.rs ClaudeSettings（serde 忽略未知字段） |

## 9. 配置项/环境变量/开关
- `[claude_compat].imported`（config.toml，marker）；`_GROK_CLAUDE_MARKER_OVERRIDE=1`（测试逃生阀，claude_settings.rs is_claude_import_marked+0 快照 L442）。
- 运行时兼容矩阵（管"迁移前 .claude 是否被静默消费"）：`[compat.claude]` skills/rules/agents/mcps/hooks/sessions 六面，默认全 true（`xai-grok-config/src/compat.rs` · VendorCompat default+0）；env `GROK_CLAUDE_{SURFACE}_ENABLED` 最高优先级（compat.rs COMPAT_CELLS 快照 L144-174）；远端开关 `claude_*_enabled`（remote_settings.rs 快照 L460-476）。
- 写入侧键：`[permission].{allow,deny,ask}`、`[env]`、`[mcp_servers]`、`[paths].extra_skill_dirs` / `extra_rule_dirs`。注意 user-guide 明示 `extra_skill_dirs` **不注入 skills**（08-skills.md 快照 L50：仅作登记，list_skills_with_paths 不读）——文档要写清这个"迁移后不生效"陷阱。

## 10. 测试矩阵
| 位置 | 数 | 覆盖点 |
|---|---|---|
| migration/src/rewrite_tests.rs | 11 | 权限去重、env 不覆盖、marker 新建/保内容/幂等、paths 写入、global 穿透/项目替换 symlink |
| migration/src/hooks_cla_tests.rs | 12 | 提取（多事件/matcher、非 command 跳过、坏字段静默、空 command 照收）、写文件、去重、timeout 刷新/删除 |
| migration/src/config_values_tests.rs | 1 | format_rule_string 与 Claude 原文一致 |
| shell/src/claude_import_tests.rs | 14 | marker 对 hook 发现/env 注入/MCP 源/权限解析四类 gate 的开闭、cursor 对照、trust 门、config 反序列化 |
| shell claude_import_state.rs 内联 | 4 | 哈希确定性/排序/跳过缺失/变更敏感 |
| config/src/claude_import_tests.rs | 1 | marker 读取三态 |
| pager import_claude_modal.rs | 15 | filtered_plan 逐项/分组勾选 |
| shell/tests/config_write_symlink.rs | 1 | marker 写与 symlink 交互 |

## 11. 收尾建议
建议**独立成篇**（新第 20 篇「外部 Agent 配置迁移」）而非并入 06/13/07：①跨 5 个 crate 的完整链路与双层 gate 自成体系，塞进 06（配置）会把运行时 compat/迁移/状态三套东西搅在一起；②与 13（持久化）仅共享 claude_import_state.json 一小节，交叉引用即可；③与 07（若为权限篇）只在 §4 规则映射处需要衔接。06 补一行 `[claude_compat]`/`[compat.claude]` 键说明、13 补 claude_import_state.json 一行即可。写作时注意三个"易错事实"：has_claude_import 启动横幅在当前树不可达；crate 不复制 skills 文件只登记路径且不生效；`+2,181 行`的 claude_import.rs 实际 144 行。
