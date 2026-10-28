> 本文件是**本轮刷新的唯一规范**。任何参与刷新的人（含子代理）必须先读本文件，再动手。
> 它同时是「已确认变化清单」——读到这里就够了，**不要重复侦查这些事实**。

## 1. 基准

| 项 | 值 |
|---|---|
| 本次刷新基准 | `git HEAD = 42f4d7d3`，`SOURCE_REV = 559751fd`（2026-10-27 校验） |
| 上一轮文档基准 | `HEAD = 0e2bfffb` / `SOURCE_REV = 036a5d83`（README 标注，2026-09-28） |
| 代码漂移量 | `0e2bfffb..HEAD` = **1006 文件**（+131,449 / −27,964）；新增 366 / 修改 597 / 重命名 37 / 删除 6（`git diff --shortstat` 与 `--name-status` 双口径复算；早先记的「990 文件」是最后一次合并提交之前的读数，已作废） |
| 漂移来源 | 两次上游同步 `97f190f6`、`2bdd1d6a` + 合并 `52e0a1eb`（"Synced from monorepo"） |
| workspace members | **107**（旧文档写 102，已过期） |
| Rust 工具链 | `1.94.0` 未变；**但 `channel` 现在在 `rust-toolchain.toml:2`**（旧文档全库写 `:11`，需改） |
| 关键依赖 | `ratatui 0.29` / `tokio full` / `agent-client-protocol 0.10.4` / `tree-sitter 0.26` / `Cargo.lock` 中 `rmcp 3.4.0` |

**注意**：本轮之前各章头部标注**互不一致**（`2178c69c` / `cb8e30bd` / `0e2bfffb` 三种都有）。本轮统一改为 §1 表首行的基准，并保留「前次基准」一句。

## 2. 定位记法（硬要求）

绝对行号**不能**当主依据。统一写法：

| 场景 | 写法 |
|---|---|
| 顶层符号 | `crates/codegen/<crate>/src/<path>.rs` · 符号：`Name`（定义行即 `+0`，不重复标偏移） |
| 符号体内某段 | 同上 `偏移：+35~+40` |
| impl / trait 成员 | `文件 路径` · `impl <Type>` 函数：`name` `偏移：+N`，**`+0` = 该 impl/trait 头行** |
| 模块常量 | `Module:` 前缀 + `Const:NAME` |
| 调用关系 | 两侧都标：`a.rs · A::x` ↓ `b.rs · B::y` |
| 快照行号 | 只允许写在**括号里**并带「快照」二字，如 `（快照行 1507，已漂移）` |

**索引类文档**（第 16 篇的总表）只给「符号 → 文件」映射，不给行号 —— 这样永不失效。

**裸行号一律算违规**：`file.rs:123`、`Cargo.toml:8` 这类没带「快照」二字的行号，
无论出现在正文、表格还是 mermaid/框线图里，都要改成 `文件 · 符号(+N)`；
根 `Cargo.toml` 的定位改用**表 + 键**（如 `Cargo.toml` `[workspace].members`、`[workspace.dependencies].tokio`）。
本轮起点实测（19 篇 + tui-guide，A 组编辑器仍在改的部分会变动）：**13 篇共 252 处裸行号**
（05 篇 119、04 篇 40、09 篇 35 为三大头），失效路径 1 处、搬家待标注 6 处、符号待判读 23 处。

读者换算方式：`python3 .progress/sr_tools.py offset FILE SYM` 会打印定义行**与合法偏移上界**（函数体行数）。

## 3. 内容红线

1. **代码是唯一 source of truth**：文档与代码冲突 → 改文档，绝不反向迁就。
2. **禁止臆测**：没读到证据就写「未确认」。历史教训：多次「以为被删了」其实是文档少写一层目录。
3. **路径能解析 ≠ 描述正确**：改了架构必须顺手核对语义描述（本轮沙箱/权限就是这种）。
4. **「文件还在」≠「逻辑没变」**：留存的桩/兼容层最容易漏。
5. **失败路径与成功路径同等篇幅**；不写「同上」「略」「类似」。
6. **历史演进只进文末「变更记录」区**，正文只留最新状态。
7. 记法统一：两个路径之间**不要用 `·`**（校验器会把第二个路径的首段当符号）；并列用 `、` 或分列。

## 4. 已确认的架构级变化清单（本轮的核心工作量来源）

### 4.1 拆出 5 个新 crate（文档基本零覆盖）

| 新 crate | 规模（非测试 / 含测试） | 来源 | 影响的旧文档 |
|---|---|---|---|
| `xai-grok-permission-rules` | 15,958 / 23,387 行 | 从 `xai-grok-workspace/src/permission/` 拆出 | 11、05、可靠性、16 |
| `xai-grok-sandbox/src/command/`（同 crate 内新子系统，非新 crate） | 8,464 / 21,583 行，37 个新文件 | 上游新增 | 11、10、可靠性 |
| `xai-grok-cloud-config` | 5,584 行 | 从 `xai-grok-shell/src/managed_config/` + `agent/remote_config/` 拆出 | 06、12、09、16 |
| `xai-grok-egress-proxy` | 4,593 行 | 新增 | 12、可靠性、16 |
| `xai-grok-lifecycle` | 3,844 行 | 新增；**与已存在的 `xai-agent-lifecycle` 是两个东西，别写混** | 07、12、可靠性 |
| `xai-grok-external-agent-migration` | 1,784 行 | 新增，配套 `xai-grok-shell/src/claude_import.rs`（+2,181 行） | 06、13、07 |

### 4.2 权限层搬家（**归属叙述必须改写，不只是换路径**）

- 走掉的：`policy.rs`、`rules.rs`、`resolution.rs`、`gate_preflight.rs`、`shell_access.rs`、`exec_risk.rs`、
  `bash_command_splitting.rs`、`bash_permission_script.rs`、`claude_settings.rs`、`project_config.rs`、
  `git_content_filters.rs`、`reasons.rs`、`managed_policy/*`、`trust.rs` → 现在在 `xai-grok-permission-rules/src/`
- **仍留在** `xai-grok-workspace/src/permission/` 的：`manager/`、`hub_gate.rs`、`sandbox_gate.rs`、`sandbox_wire.rs`、
  `sandbox_network.rs`、`grants/`、`prompter.rs`、`state.rs`、`auto_mode/`、`managed_hooks.rs`、`types.rs`、`mod.rs`
- 文档里 **18 处**引用旧权限路径、**16 处**引用 `managed_config` → 全部要改归属，并核对语义是否仍成立。

### 4.3 配置层搬家

- `xai-grok-shell/src/managed_config/`（整目录）**已删除** → `xai-grok-cloud-config/src/managed_config/`
- `xai-grok-shell/src/agent/remote_config/{cache,metrics}.rs` → `xai-grok-cloud-config/src/remote_settings/`
- `xai-grok-shell/src/agent/remote_config/settings_refresh.rs` → `xai-grok-cloud-config/src/settings_refresh.rs`
- `xai-grok-shell/src/agent/remote_config/cache_file.rs` → `xai-grok-config/src/cache_file.rs`
- `xai-grok-shell/src/agent/remote_config/{scope.rs, settings_cache.rs}` **已删除**（去向需 grep 确认，不许猜）
- `remote_config/` 还剩 `endpoint.rs`/`fetch.rs`/`manager/`/`model_fetch_auth.rs`/`prefetch.rs`/`resolution.rs`/`settings_get.rs`/`task_model_policy.rs`
- `xai-grok-config-types/src/lib.rs` +1,712 行

### 4.4 沙箱长出命令级策略层（新内容，不是搬家）

`xai-grok-sandbox/src/command/`：`policy`、`backend`（含 `seatbelt`）、`grants`、`grant_store`、`protected`、
`git_config`、`violation`、`observe`、`detect`、`canonical`、`env`。
原有第 11 篇只写了「进程级沙箱」`SandboxManager`（`xai-grok-sandbox/src/lib.rs` · 符号：`SandboxManager`，快照行 172）+ `child_net.rs` 的 seccomp 那一层。

### 4.5 被删除的文件（6 个，文档需检查引用）

`xai-grok-pager/src/slash/commands/scroll_debug.rs`、`xai-grok-test-support/src/uds_proxy.rs`（文档 1 处引用）、
`xai-grok-shell/src/agent/remote_config/scope.rs`、`.../settings_cache.rs`、`xai-fast-worktree/tests/e2e_grove_worktree.rs`、
`xai-fast-worktree/src/grove_arm_tests.rs`

### 4.6 已核出的具体错误（本轮必改）

| 位置 | 错在哪 |
|---|---|
| 15 篇 | 写 `xai-grok-workspace/src/sandbox/lib.rs` —— 该目录只有 `mod.rs`，无 `lib.rs` |
| 11 / 16 篇 | `xai-grok-workspace/src/permission/{policy,gate_preflight}.rs` —— 已搬到 permission-rules |
| 全库 | `rust-toolchain.toml:11` —— `channel` 现在在第 2 行 |
| 11 / 10 篇 | 残留 5 + 5 处「在 N 行」式绝对行号作主依据 —— 要降为括号快照或改符号锚点 |

### 4.7 不算错误、**不要去「修」** 的形态

- `third_party/ffmpeg/{binding.rs, fetch_local.py, local/lib}`（14 篇）：`.cargo/config.toml` 的 `[env]` 确实引用它，但本快照没同步该目录 —— 文档**已经**用 ⚠️ 说明这是上游同步残留，路径本身保持原样。
  **本轮补强的证据（14 篇要把这段写准）**：`grep -rn "rsmpeg\|rusty_ffmpeg" Cargo.toml crates/*/*/Cargo.toml` **零命中**
  ⇒ 不是「目录没同步进来所以不命中」，而是**依赖图里已无任何 crate 消费 rusty_ffmpeg**，那三行 `FFMPEG_*` env 是**死配置**。
- ASCII 框线图里因排版被折成两行的路径（校验器报成 `crates/common/xai-computer-hub-` 这类尾部带 `-` 的 token）。
- 裸文件名缩写（`handle.rs`、`mod.rs`）、运行期配置名（`config.yaml`）、示例名（`your_tool.rs`）。
- 「该文件已不存在」这类**说明性**句子。

## 5. 工具

`python3 docs/adrian/sourceReader/.progress/sr_tools.py <子命令>`（在本仓库任意目录都能跑，路径自解析）

| 子命令 | 用途 |
|---|---|
| `locate SYM...` | 全库找符号定义（生产树优先，tests 兜底，同名多处会全列 + 计数） |
| `outline FILE [--top]` | 文件符号骨架 + 行号（省 token） |
| `offset FILE SYM` | 定义行 + **合法偏移上界**（函数体行数） |
| `verify DOC\|DIR...` | 分档校验：路径 ok / 失效 / 搬家 / 符号待判读 / 绝对行号 / **裸行号** / 折行 / 说明性 / 裸文件名 / 非仓库名 |
| `nav DIR...` | 文档间断链与孤儿页（把 `docs/adrian` 整目录传进去，才能跨 `sourceReader/` 与 `topic/` 判孤儿） |

起点快照与逐条清单见 `.progress/baseline-verify.txt` 与 `.progress/GATE-CHECKLIST.md`。

## 6. 完成门禁（全满足才算同步完成）

1. `verify`：**失效路径 = 0**、**搬家未标注 = 0**、**裸行号 = 0**（改成符号+偏移，或显式标「快照」）、**符号待判读逐条有结论**（要么改对、要么在同一行写清原因）。
2. `nav docs/adrian`：断链 0、孤儿 0。**已知：`topic/tui-guide.md` 当前是孤儿页**（全库无链接），必须由 README 或 00 篇链接过去。
3. 每篇头部基准 = §1 表首行；每篇文末「变更记录」新增一条（写了什么、为什么）。
4. 每篇**人工抽样回核 3~5 处**引用：符号存在、偏移落在函数体/impl 块内。
5. 6 个新库的证据卡在 `.progress/evidence/`，正文结论能对上卡内锚点。
6. `.progress/state.json` + `tasks.json` 更新到本轮基准。

## 7. 本轮不做的事

- **不动仓库自带文档**（`crates/codegen/xai-grok-pager/docs/{tutorial,user-guide}`、各 crate README/CHANGELOG、根 `README.md`）。老板明确只要自家库。
- 不改 `crates/` 下任何源码。
- `docs/adrian/topic/tui-guide.md` 写于最后一次代码变更之后，**基准最新**，只做复核，不重写。
