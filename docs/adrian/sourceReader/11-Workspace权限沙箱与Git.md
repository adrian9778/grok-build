[上一篇：工具协议与扩展体系](10-工具协议与扩展体系.md) · [总目录](README.md) · [下一篇：认证网络遥测与更新](12-认证网络遥测与更新.md)

# 11 · Workspace 权限、沙箱与 Git

> **场景**：一个工具要「读文件 / 写文件 / 跑命令 / 改 Git」，但有三条线必须同时满足——(1) **Workspace 边界**：操作只能发生在工作区之内；(2) **权限边界**：每次敏感操作要过配置规则 + 运行时授权两道关卡；(3) **OS 沙箱边界**：进程级用 Landlock/Seatbelt 兜底，子进程网络按 seccomp 封禁。本章把这三件事拆开讲清楚。
>
> **阅读说明**：源码基准 `SOURCE_REV = d5a0335a47221e8c9519936cb693e9b6450227ec`。三个子系统分别在：`crates/codegen/xai-grok-workspace-client`（Git/文件 RPC 客户端）、`crates/codegen/xai-grok-workspace/src/permission`（权限双层）、`crates/codegen/xai-grok-sandbox`（OS 级沙箱）。所有 `file:line` 对应当前工作区代码。

---

## 第一层 · 简单框架（系统骨架）

把「一次文件/命令/Git 操作」的约束拆成三道同心圆：

```
                         ┌────────────────────────────────────┐
                         │   工具调用 (bash / read_file / ...)   │
                         │   来自 CompoundResolver 派发 (见 10 章) │
                         └───────────────────┬────────────────┘
                                             │ 调用前先过两关
                 ┌───────────────────────────┼───────────────────────────┐
                 ▼                            ▼                           ▼
   ┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────┐
   │ ① Workspace 边界       │   │ ② 权限双层                │   │ ③ OS 沙箱             │
   │ WorkspaceClient        │   │  config 规则层 + 运行时层  │   │ SandboxManager        │
   │ (git_* / fs 调用)      │   │  PermissionManager(actor) │   │  nono / Landlock /     │
   │ 见 workspace-client    │   │  gate_preflight 合并判断   │   │  Seatbelt / seccomp   │
   │ lib.rs:159             │   │  permission/manager:1404  │   │  sandbox/lib.rs:159    │
   └──────────────────────┘   └──────────────────────────┘   └──────────────────────┘
```

| 子系统 | 入口类型 | 位置 | 一句话职责 |
|--------|---------|------|-----------|
| Workspace 操作 | `WorkspaceClient` | `xai-grok-workspace-client/src/lib.rs:159` | 文件列举/读取、Git 全量操作（status/diff/commit/checkout/stash…）的 RPC 客户端 |
| 权限双层 | `PermissionManager`（actor） | `xai-grok-workspace/src/permission/manager/mod.rs:1404` | 配置规则 + 运行时 prompt/auto/yolo 双层裁决 |
| 预检合并 | `gate_preflight` | `xai-grok-workspace/src/permission/gate_preflight.rs:1` | 一次性评估「直接规则命中 + 两道 bash 安全门」，保留 `Ask` 溯源 |
| OS 沙箱 | `SandboxManager` | `xai-grok-sandbox/src/lib.rs:159` | 进程启动期套 Landlock/Seatbelt；子进程网络 seccomp 封禁 |

「双层」是权限系统的关键：**第一层是配置规则（fail-closed，匹配不到就 Ask）**；**第二层是运行时授权（用户在 TUI 里 allow/deny，或 auto/yolo 模式自动放行）**。两层都过了才真正执行。

---

## 第二层 · 一个完整例子（全路径走读）

以「模型让 bash 工具执行 `rm -rf build/`」为例（危险操作最能暴露全链路）：

```
① 模型产出 tool_use: { name: "grok_build__bash",
                        arguments: { command: "rm -rf build/" } }
        │
② 会话派发进 bash 工具（见 10 章 execute_tool_calls_batch -> ToolDispatch::call）
        │
③ bash 工具先向 PermissionManager 申请授权：
   PermissionManager::request_with_path_context(...)   manager/mod.rs:1083
        │  内部调用 gate_preflight：
        │   - 直接规则是否命中 Allow/Deny？        gate_preflight.rs:1
        │   - 两道 bash 安全门（exec_risk 拆解命令）是否 fail-closed？
        │   - 保留 Ask 的「来源」：规则命中 Ask vs 分析失败 Ask
        ▼
④ 裁决分支：
   ├─ 规则命中 Deny  → 直接拒绝（Terminal(Err(permission_denied))）
   ├─ yolo 模式       → 直接放行（manager/mod.rs:880 set_yolo_mode / :1021 is_yolo_mode）
   ├─ auto 模式       → 分类器判断后放行（manager/mod.rs:905 set_auto_mode）
   └─ 其余            → 在 TUI 弹 prompt，用户 allow/deny（prompter）
        │
⑤ 授权通过 → 真正执行前套沙箱：
   SandboxManager::apply(workspace)  sandbox/lib.rs:179
   restrict_child_network()  sandbox/lib.rs:271  → 子进程 seccomp 封网络
        │
⑥ 子进程跑 `rm -rf build/`，落在 workspace 内；WorkspaceClient 校验路径不越界
        │
⑦ 结果经 ToolStream 回传（Terminal(Ok(TypedToolOutput))），见 10 章
```

关键观察：**权限与沙箱都在「工具真正执行之前」横切**。`bash` 工具自身不实现授权逻辑——它只是 `PermissionManager` 的调用方；沙箱则在更底层由进程启动统一套上，对工具透明。

---

## 第三层 · 详细逐步说明（主链路拆解）

### 步骤 1 — Workspace 操作入口 `WorkspaceClient`

`WorkspaceClient`（`crates/codegen/xai-grok-workspace-client/src/lib.rs:159`，`impl` 在 `:172`）是绝大部分文件/Git 操作的 RPC 客户端。它把「工作区内的 fs/Git」封装成异步方法，工具（bash/read_file/grep/search_replace）通过这些方法落地，而非直接 `std::fs`。好处：所有路径都经过统一的「工作区根」约束（`git_resolve_root` 在 `lib.rs:352`，`git_current_commit` 在 `:358`）。

### 步骤 2 — 切片：Git 操作全集

`WorkspaceClient` 暴露的 Git 方法（均 `lib.rs`，行号见第四层 4.1）：`git_status`(286) / `git_status_ext`(295) / `git_files`(301) / `git_diff`(307) / `git_stage`(310) / `git_stage_content`(313) / `git_unstage`(319) / `git_discard`(322) / `git_commit`(325) / `git_sync_base`(331) / `git_checkout`(337) / `git_stash`(340) / `git_info`(343) / `git_branches`(346) / `git_resolve_root`(352) / `git_current_commit`(358) / `git_checkout_commit`(370) / `git_branch_info`(376) / `git_metadata`(379) / `git_collect_changes`(383)。这些就是模型能在 Git 上做的全部动作面。

### 步骤 3 — 权限双层：第一层（配置规则）

配置层数据结构全在 `crates/codegen/xai-grok-workspace/src/permission/types.rs`：

- `PermissionConfig`(`:389`) = `Vec<PermissionRule>` 容器。
- `PermissionRule`(`:418`) 描述一条规则：`PatternMode`(`:428`) 决定匹配方式，`RuleAction`(`:436`) 是 `Allow`/`Deny`/`Ask` 三类，`ToolFilter`(`:445`) 限定作用的工具。
- `EditPolicy`(`:234`) 控制「写文件」策略；`PromptPolicy`(`:406`) 控制「何时弹 prompt」。
- `RequirementSource`(`:458`) + `Sourced<T>`(`:505`) 记录每条规则来自哪一层配置（用户/托管/MDM），用于合并优先级。

**语义**：规则命中 `Deny` 立即拒绝；命中 `Allow`（且范围匹配）直接进入第二层；都没命中 = **fail-closed → Ask**（`Decision` 枚举见 `:219`，`AccessKind` 见 `:200`）。

### 步骤 4 — 权限双层：第二层（运行时授权）

运行时层由 `PermissionManager` actor 承载（`crates/codegen/xai-grok-workspace/src/permission/manager/mod.rs:1404` `spawn_permission_manager`，`:1442` `spawn_permission_manager_with_hub` 含 Hub 远程授权）。它持有可变的授权状态，对外只暴露请求 API：

- `request`(`:1057`) / `request_with_path_context`(`:1083`) / `request_with_path_context_resolved`(`:1110`)：工具侧调用入口。
- `set_yolo_mode`(`:880`) / `is_yolo_mode`(`:1021`)：yolo = 全放行（危险模式，通常仅受控开启）。
- `set_auto_mode`(`:905`) / `is_auto_mode`(`:1028`)：auto = 让分类器（`set_classifier` `:927`、`AUTO_DENY_CONSECUTIVE_LIMIT` / `AUTO_DENY_TOTAL_LIMIT` 在 `request_classification.rs`）自动裁决。
- `deny_read_globs`(`:1048`)：禁止读取的 glob 集合（读保护）。
- `always_allow_row_is_effective` / `always_allow_scope_persists`（`bash_grants.rs`）：bash 类「始终允许」配置的作用域与持久化。

### 步骤 5 — `gate_preflight` 把两层结论合并

`crates/codegen/xai-grok-workspace/src/permission/gate_preflight.rs:1` 的设计要点：**一次性评估「直接规则 pass」+「两道 bash 安全门」，并各自保留 `Ask` 的 provenance**。这样 manager 能区分两种 Ask——

- 「规则真的匹配到了，需要问用户」（停在 prompt）；
- 「分析无法拆解命令去查规则，fail-closed 的 Ask」（auto 模式下交给分类器，而不是在每个决策点并行比对一堆布尔值）。

`exec_risk.rs`（命令执行风险分析）与 `bash_command_splitting.rs`（命令拆分）是这两道 bash 安全门的具体实现。

### 步骤 6 — OS 沙箱兜底

即便权限层全过，进程级兜底仍生效（`crates/codegen/xai-grok-sandbox/src/lib.rs`）：

- `SandboxManager::new(ProfileName::Workspace, workspace)`(`:167`) → `apply(workspace)`(`:179`) → `install()`(`:249`)。用的是 `nono` 库，内核级 Landlock（Linux）/ Seatbelt（macOS）。
- `restrict_child_network()`(`:271`)：子进程网络按 seccomp 封禁；**进程自身的网络保持开放**（要连 LLM API）。
- `should_restrict_child_network()`(`:90`)、`should_auto_allow_bash()`(`:96`)、`is_active()`(`:124`)、`profile_name()`(`:128`)、`log_violation()`(`:136`)、`metrics()`(`:155`) 是开关/可观测性钩子。
- `support_info()`(`:263`) 报告当前内核是否支持沙箱（不支持时降级为轻量 helper：`log_violation` / `should_restrict_child_network` / `child_net`，全平台可编译）。

---

## 第四层 · 补全所有逻辑与技术要点

### 4.1 `WorkspaceClient` Git 操作全集（位置：`xai-grok-workspace-client/src/lib.rs`）

| 方法 | 行 | 作用 |
|------|----|------|
| `git_status` | 286 | 工作区状态 |
| `git_status_ext` | 295 | 扩展状态 |
| `git_files` | 301 | 列举文件 |
| `git_diff` | 307 | 差异（`GitDiffReq` → `GitDiffsData`） |
| `git_stage` | 310 | 暂存（`GitStageReq` → `StageData`） |
| `git_stage_content` | 313 | 按内容暂存 |
| `git_unstage` | 319 | 取消暂存 |
| `git_discard` | 322 | 丢弃改动 |
| `git_commit` | 325 | 提交 |
| `git_sync_base` | 331 | 同步基线 |
| `git_checkout` | 337 | 切换（`GitCheckoutReq`） |
| `git_stash` | 340 | 储藏（`GitStashReq`） |
| `git_info` | 343 | 仓库信息（`GitInfoReq` → `GitInfoData`） |
| `git_branches` | 346 | 分支列表 |
| `git_resolve_root` | 352 | 解析工作区根 |
| `git_current_commit` | 358 | 当前 commit |
| `git_checkout_commit` | 370 | 切到指定 commit |
| `git_branch_info` | 376 | 分支信息 |
| `git_metadata` | 379 | 仓库元数据 |
| `git_collect_changes` | 383 | 收集改动 |

文件侧操作（read/list/grep/replace）走同类 RPC，统一受「工作区根」约束。所有 Git/文件请求都经 `WorkspaceClient` 而非裸 `std::fs`/`std::process::Command`，保证路径校验集中在一处。

### 4.2 权限模块（`xai-grok-workspace/src/permission/`）全貌

`mod.rs` 重新导出各子模块，拼出完整能力面：

- `auto_mode` —— auto 模式分类器编排（`manager/mod.rs:905` 的 `set_auto_mode` 落点）。
- `hub_permission` —— 远程/Hub 工具的授权（与本地规则合并判断）。
- `manager` —— `PermissionManager` actor（`spawn_permission_manager` `manager/mod.rs:1404`，`spawn_permission_manager_with_hub` `:1442`）。
- `policy` —— 策略求值（规则应用）。
- `prompter` —— 向 TUI 弹授权提示的桥。
- `shell_access` —— `ProtectedEditPermission` / `ProtectedEditReason`（受保护文件的写保护）。
- `state` —— `PermissionState` + `cleanup_stale_permission_state`（授权状态持久化与过期清理）。
- `types` —— 全部数据结构（见 4.3）。
- 其余辅助：`exec_risk`（命令风险）、`bash_command_splitting`（命令拆分）、`claude_settings`（从 Claude 设置导入）、`resolution`（裁决结果处理）、`request_classification`（auto 模式分类限流）。

### 4.3 权限数据结构（`permission/types.rs`）

| 类型 | 行 | 含义 |
|------|----|------|
| `PermissionEvent` | 8 | 一次权限事件的记录 |
| `PermissionResolution` | 123 | 最终裁决结果 |
| `ClientType` | 131 | 调用方类型（TUI / Hub / …），含 `user_agent_label` / `feedback_label` |
| `AccessKind` | 200 | 访问种类（读/写/命令…） |
| `Decision` | 219 | 裁决：`Allow` / `Deny` / `Ask` |
| `EditPolicy` | 234 | 写文件策略 |
| `RequestPathContext` | 274 | 请求附带的路径上下文（用于规则匹配） |
| `PermissionCommand` | 279 | 命令类权限请求 |
| `PermissionConfig` | 389 | 规则容器 |
| `PromptPolicy` | 406 | 何时弹 prompt |
| `PermissionRule` | 418 | 单条规则 |
| `PatternMode` | 428 | 规则匹配模式 |
| `RuleAction` | 436 | `Allow` / `Deny` / `Ask` |
| `ToolFilter` | 445 | 规则作用的工具过滤 |
| `RequirementSource` | 458 | 规则来源（用户/托管/MDM） |
| `Sourced<T>` | 505 | 带来源标注的值（用于合并优先级） |

### 4.4 双层模型的两个「Ask」来源（来自 `gate_preflight`）

`gate_preflight.rs:1` 把一次请求拆成：

1. **直接规则 pass**：`PermissionRule` 是否命中 `Allow`/`Deny`/`Ask`。
2. **两道 bash 安全门**：`exec_risk` 命令风险 + `bash_command_splitting` 命令拆分，判断是否 fail-closed。

它把两个门的 `Ask` provenance 都保留下来：

- 规则**真命中** Ask → 停在 prompt（真实策略匹配）。
- 分析**无法拆解**命令导致 fail-closed Ask → auto 模式下交给分类器，避免每个决策点平行比对布尔值。

这是「双层」在工程上的落点：配置层给确定结论，分析层给 fail-closed 兜底，运行时层（auto/yolo/prompt）给最终裁决。

### 4.5 OS 沙箱（`xai-grok-sandbox`）

- **机制**：`nono` 库提供的内核级 Landlock（Linux）/ Seatbelt（macOS）。进程启动期 `SandboxManager::apply`(`lib.rs:179`) + `install`(`:249`) 一次性套上，覆盖进程内 `tokio::fs` 与子进程。
- **网络策略**：进程级网络**保持开放**（要连 LLM API，见 `lib.rs:11`）；子进程网络按 seccomp 封禁（`restrict_child_network` `:271`、子进程 helper 在 `child_net.rs` / `network_policy.rs`）。
- **路径策略**：允许/拒绝路径在 `paths.rs` / `allow_path.rs` / `deny/`（含 `hook_write_deny.rs`，禁止钩子写某些路径）。
- **Profile**：`ProfileName`（`profiles.rs`）区分 `Workspace` 等工作模式；`configured_profile_name`(`:107`) / `requested_confinement_profile`(`:116`) / `profile`(`:275`) 读取当前档位。
- **降级**：`enforce` feature 关掉时仍提供 `log_violation` / `should_restrict_child_network` / `child_net` 等轻量 helper，全平台（含 musl）可编译（`lib.rs:14-18`）。
- **可观测**：`support_info`(`:263`) 报告内核支持度；`metrics`(`:155`) / `log_violation`(`:136`) / `flush`(`:147`) 收集违规事件。

### 4.6 授权状态持久化

`permission/state.rs` 的 `PermissionState` 记录「用户已 allow/deny 过什么」，`cleanup_stale_permission_state` 清理过期条目。持久化让「允许一次 rm」在会话内或跨会话（按配置）保持一致，避免每次重复弹窗。

### 4.7 真实函数体拆解（SandboxManager / PermissionManager）

把 11 章最密集的两个入口拆成真实函数体，看清「沙箱怎么套上」与「权限请求怎么走」。

**`SandboxManager::new` / `apply` / `install` / `restrict_child_network`**（`xai-grok-sandbox/src/lib.rs:167` / `:179` / `:249` / `:271`）。`apply` 只在 `enforce` + unix 下真正调用内核；其余平台是同名 stub（`:241`）：

```rust
pub struct SandboxManager { profile: ProfileName, logger: SandboxLogger, net_restricted: bool, applied: bool }

#[cfg(all(feature = "enforce", unix))]
pub fn apply(&mut self, workspace: &Path) -> anyhow::Result<()> {
    if self.profile == ProfileName::Off { return Ok(()); }              // 关 = 直接放行
    if requires_hook_write_deny(&self.profile, workspace) {
        xai_grok_config::ensure_grok_hook_slots(paths::grok_home().as_path())?;
        hook_write_deny::maybe_install_namespace_lockdown_inside_bwrap(&self.profile)?;
    }
    let config = profiles::load_sandbox_config(workspace);
    let mut resolved = self.profile.resolve_profile(workspace, &config)?;
    self.net_restricted = resolved.restrict_network;
    let support = Sandbox::support_info();
    if !support.is_supported { self.logger.log(SandboxEvent::apply_failed(...)); return Ok(()); } // 降级
    let caps = ProfileName::capability_set_from_profile(workspace, &resolved)?;
    resolved.deny = deny::effective_deny_paths(workspace, &resolved.deny);
    match Sandbox::apply(&caps) {                        // 内核级 Landlock/Seatbelt，不可逆
        Ok(_)  => { self.applied = true; Ok(()) }
        Err(e) => { self.logger.log(SandboxEvent::apply_failed(...)); Ok(()) }  // 套不上也继续跑
    }
}

pub fn install(self) {                                   // 把状态存进进程级全局 SANDBOX
    let _ = self.logger.flush_to_disk();
    let _ = SANDBOX.set(GlobalSandboxState { profile: self.profile.to_string(),
        logger: self.logger, applied: self.applied,
        restrict_network_at_known_linux_launches:
            restrict_network_at_known_linux_launches(self.applied, self.net_restricted) });
}

pub fn restrict_child_network(&self) -> bool {           // 仅子进程封网，进程自身保持开放
    restrict_network_at_known_linux_launches(self.applied, self.net_restricted)
}
```

要点：`apply` 是**不可逆**的内核操作（注释明确写 "Irreversible"），失败时**降级继续**而非崩溃——这就是「沙箱兜底」的工程落点；`restrict_child_network` 只封子进程网络，父进程仍要连 LLM API。

**`PermissionManager::request` / `request_with_path_context`**（`xai-grok-workspace/src/permission/manager/mod.rs:1057` / `:1083`）——两层都是薄壳，真正裁决在 `request_with_path_context_resolved`（`:1110`，其 `match self {` 在 `:1119`）里发 `PermissionCommand::Request` 给 actor，由 `gate_preflight` 合并配置层结论 + bash 安全门：

```rust
pub async fn request(&self, access, tool_call_update, session_id, subagent_type, subagent_description) -> Decision {
    self.request_with_path_context(access, tool_call_update, None, session_id, subagent_type, subagent_description).await
}

pub async fn request_with_path_context(&self, access, tool_call_update, path_context, session_id, subagent_type, subagent_description) -> Decision {
    self.request_with_path_context_resolved(access, tool_call_update, path_context, session_id, subagent_type, subagent_description).await.decision
}
```

注意 `request` 不带路径上下文，`request_with_path_context` 带「请求方 session 的执行 cwd」——共享父/子 agent 管理器必须用后者，因为路径规则与编辑目标都锚定在真实 cwd 上（见 `RequestPathContext`，`types.rs:274`）。两层薄壳都最终落到 actor 的 `PermissionCommand::Request`，由运行时层（prompt / auto / yolo）给出 `Decision`。

### 4.8 设计不变量小结（本章范围内）

1. **集中落地**：所有 fs/Git 操作经 `WorkspaceClient`，路径校验只在一处。
2. **fail-closed**：规则未命中 = Ask，而非默认放行。
3. **双层裁决**：配置规则层 + 运行时授权层（prompt/auto/yolo）都过才执行。
4. **Ask 溯源**：`gate_preflight` 区分「规则命中 Ask」与「分析失败 Ask」。
5. **沙箱兜底**：即便权限全过，进程级 Landlock/Seatbelt + 子进程 seccomp 仍生效，对工具透明。
6. **网络分离**：进程网络开放（LLM），子进程网络封禁（安全防护）。

---

[上一篇：工具协议与扩展体系](10-工具协议与扩展体系.md) · [总目录](README.md) · [下一篇：认证网络遥测与更新](12-认证网络遥测与更新.md)
