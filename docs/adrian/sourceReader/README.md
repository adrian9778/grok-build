# Grok Build 新手重构级源码指南（4 层规范版）

> **范围**：本文档库是 Grok Build（终端 AI coding agent，二进制 `xai-grok-pager-bin`，发行安装名 `grok`；TUI 主体在 `xai-grok-pager`）的**重构级完整源码指南**。它按「先简单框架、再一条全路径小例子、再逐步拆解、最后补齐全部逻辑」四层推进，目标是让读者仅凭本库就能重新实现功能等价的系统。
> **工具版本**：Rust `1.94.0`（`rust-toolchain.toml` `[toolchain].channel`，组件 `rustfmt`/`clippy`）；`cargo` 随工具链；`ratatui = 0.29`、`tokio = full`、`agent-client-protocol = 0.10.4`（见根 `Cargo.toml` `[workspace.dependencies]`）；`Cargo.lock` 中 `rmcp = 3.4.0`（前次 `3.2.0`）。
> **同步说明**：本库于 2026-10-27（CST）对齐至 `git HEAD = 42f4d7d3`（`SOURCE_REV = 559751fd`；上一轮基准 `0e2bfffb` / `SOURCE_REV = 036a5d83`）。两轮之间上游并了 **1006 个文件、+131,449/−27,964 行**，本库据此做了三类同步：
> **① 五个新 crate（约 3.9 万行 src）**：`xai-grok-permission-rules`（23,387 行，权限规则引擎，从 `xai-grok-workspace` 拆出）、`xai-grok-cloud-config`（5,584 行，远端/托管配置，从 `xai-grok-shell` 拆出）、`xai-grok-egress-proxy`（4,593 行，受控出站代理）、`xai-grok-lifecycle`（3,844 行，VM/workspace-server 停机扇出）、`xai-grok-external-agent-migration`（1,784 行，外部 agent 配置迁移）；workspace members 由 102 增至 **107**。
> **② 两处「拆出去」式重构改变了归属**：权限判定文件（`policy.rs`/`gate_preflight.rs`/`shell_access.rs`/`bash_command_splitting.rs`/`exec_risk.rs` 等）现居 `xai-grok-permission-rules`，`xai-grok-workspace/src/permission/` 只剩运行时装配那一半；远端配置链路同理搬到 `xai-grok-cloud-config`。全库的旧路径引用已按各篇「变更记录」逐条改写。
> **③ 沙箱从两层变成三层**：进程级 `SandboxManager`（Landlock/seccomp/bwrap/Seatbelt）＋ **新的命令级策略层**（`xai-grok-sandbox::command`，策略→拒绝→提问→TTL 授权→重放）＋ 宿主编排 `WorkspaceSandbox`。为此新增 [17](17-命令级沙箱策略层.md)；权限规则引擎新增 [18](18-权限规则引擎.md)；外部 agent 迁移新增 [19](19-外部Agent配置迁移.md)；worktree 快速铺设与 GC 新增 [20](20-Git-Worktree快速铺设计与GC.md)；egress 代理写入 [12](12-认证网络遥测与更新.md) 第四层；lifecycle 写入[可靠性说明书](可靠性与通用技术实现说明书.md) 第四层。全库正文分母随之为 **22 篇**（`00`–`20` 共 21 篇 + 可靠性说明书）。
> 上一轮（`f0e3be11` → `0e2bfffb`）的同步内容（WinGet 安装检测、team capability hydration、取消回合也捕获记忆、`SignalStreams`/`HeadlessSignals` 抽取、Dashboard 移除 `Subagent` 行、resize `WidthShrink` 与 minimal reprint、按 host 截断 toolset 等）仍散见各篇正文，未因本轮而失效。
> **阅读说明**：本文讲**调用关系与数据流**，不把行号当稳定 API。源码索引一律用 `` `crate/path` · `符号(+函数内偏移)` ``（如 `crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs` · `SessionActor::handle_turn_input(+0)`），**不写 `文件:行号`**；绝对行号只允许出现在明确标了「快照」的括号里，且不构成主依据。若你本地已有后续修改，**以当前源码为准**。

---

## 本库内容（按四层分组）

| 层 | 序号 | 文档 | 一句话定位 |
|---|---|---|---|
| 方法 | `00` | [阅读指南与文档地图](00-阅读指南与文档地图.md) | 怎么读、Rust 预备、证据优先级、四条路径 |
| **第一层 · 简单框架** | `01` | [简单框架-系统骨架](01-简单框架-系统骨架.md) | 有哪些进程/模块、各自职责、谁依赖谁、数据从哪进到哪出 |
| **第二层 · 全路径小例子** | `02` | [简单例子-全路径走读](02-简单例子-全路径走读.md) | 选一条最小例子（TUI 输入一条 prompt → 回答上屏），从入口追到返回 |
| **第三层 · 逐步拆解** | `03` | [详细逐步说明-主链路拆解](03-详细逐步说明-主链路拆解.md) | 把第二层的主链按调用顺序逐跳展开，配时序图 |
| 第四层 · 补齐全部逻辑 | `04` | [核心模块与类关系](04-核心模块与类关系.md) | Handle / Actor / Command / Event 真实类型与关系 |
| 第四层 | `05` | [API 与接口设计](05-API与接口设计.md) | CLI、ACP、Tool 端口、Workspace RPC、Sampler 端口、Auth、Persistence |
| 第四层 | `06` | [配置与数据流](06-配置与数据流.md) | 配置合并优先级、环境变量、会话数据、Prompt/工具/权限数据流 |
| 第四层 | `07` | [程序入口与运行模式](07-程序入口与运行模式.md) | `main()`→`async_main()` 分发、TUI/headless/leader/workspace 等模式 |
| 第四层 | `08` | [TUI 交互循环与渲染](08-TUI交互循环与渲染.md) | Action/Effect 事件循环、Ratatui 渲染、PTY/alternate screen |
| 第四层 | `09` | [Agent 会话与模型循环](09-Agent会话与模型循环.md) | Session Actor 回合循环、采样、工具批次、压缩、取消 |
| 第四层 | `10` | [工具协议与扩展体系](10-工具协议与扩展体系.md) | Tool trait、MCP、Computer Hub、Hooks、Plugins、Skills |
| 第四层 | `11` | [Workspace 权限沙箱与 Git](11-Workspace权限沙箱与Git.md) | WorkspaceOps、权限双层模型、OS 沙箱、Git、Hunk |
| 第四层 | `12` | [认证网络遥测与更新](12-认证网络遥测与更新.md) | Auth、HTTP 客户端、重试、Telemetry、Crash、Update |
| 第四层 | `13` | [持久化记忆与会话恢复](13-持久化记忆与会话恢复.md) | JSONL 持久化、崩溃恢复、fork/rewind、Memory |
| 第四层 | `14` | [构建测试第三方与许可证](14-构建测试第三方与许可证.md) | 构建、测试矩阵、vendored、许可证 |
| 第四层 | `15` | [跨模块完整运行链与场景](15-跨模块完整运行链与场景.md) | 3 个深度端到端场景（完整编码任务 / 权限+沙箱 / 取消·崩溃·压缩恢复） |
| 第四层 | `17` | [命令级沙箱策略层](17-命令级沙箱策略层.md) | 每条命令的「策略→拒绝→提问→TTL 授权→重放」闭环（与 11 的进程级沙箱是两套强制模型） |
| 第四层 | `18` | [权限规则引擎](18-权限规则引擎.md) | `xai-grok-permission-rules`：配置求值、bash 拆解、gate 预检、受管策略、YOLO pin、shell 访问门 |
| 第四层 | `19` | [外部 Agent 配置迁移](19-外部Agent配置迁移.md) | 把别家 agent 的配置读进来→转换→写入的跨 crate 链路与幂等/防重复打扰 |
| 第四层 | `20` | [Git Worktree 快速铺设与 GC](20-Git-Worktree快速铺设计与GC.md) | `xai-fast-worktree`：CoW/reflink 并行克隆、Btrfs/overlay 快照、worktree 登记库与自动 GC（与 11 的宿主视角互补） |
| 方法 | `16` | [术语表与源码查找手册](16-术语表与源码查找手册.md) | 术语消歧 + `rg`/`cargo` 查找配方 |
| 实施 | — | [可靠性与通用技术实现说明书](可靠性与通用技术实现说明书.md) | 失败/重试/取消/背压/幂等/结果未知的统一语义 |
| 专题 | — | [TUI 专题（函数级）](../topic/tui-guide.md) | 事件循环、输入解析、渲染管线、主题外观与 ratatui 组件的逐函数走读 |

---

## 推荐阅读路径

```mermaid
flowchart TD
    A["00 阅读指南"] --> B["01 简单框架"]
    B --> C["02 全路径小例子"]
    C --> D["03 逐步拆解"]
    D --> E["04 核心模块与类关系"]
    E --> F["05 API 与接口设计"]
    F --> G["06 配置与数据流"]
    G --> H["07 程序入口与运行模式"]
    H --> I["08 TUI"]
    H --> J["09 Agent"]
    J --> K["10 工具"]
    K --> L["11 Workspace/权限/沙箱"]
    J --> M["13 持久化"]
    I --> N["12 认证/网络/遥测"]
    J --> O["15 跨模块场景"]
    O --> P["14 构建/测试"]
    P --> Q["可靠性说明书"]
    D --> R["16 术语表"]
```

- **路径 A（第一次理解工程）**：`00 → 01 → 02 → 03 → 04 → 09 → 10 → 11 → 15`。
- **路径 B（准备维护现有代码）**：`16 → 04 → 05 → 目标专题（07–13、17–20）→ 对应测试索引`。
- **路径 C（从零重新实现）**：`01 → 04 → 05 → 06 → 可靠性说明书 → 14 → 07/09/10/11/18 → 17/08/12/13`（要做「每会话独立工作树」再加 `11 → 20`）。
- **路径 D（只做权限/沙箱这条线）**：`11 → 18 → 17 → 15 的场景二 → ../topic/tui-guide.md 的提问界面章节`。

---

## 编写约定（本库所有文档遵守）

1. **真实符号**：写 crate 名、文件路径、类型名、函数名；禁止只写「某模块负责某某」。
2. **Why → What → How**：每主题先讲设计初衷，再讲结构，最后拆实现。
3. **图表分工**：端到端协议/网络流用 **ASCII 框线图**；代码/调用关系/架构用 **Mermaid**（`flowchart`/`classDiagram`/`sequenceDiagram`）。
4. **调用关系写全**：谁调用谁、参数、返回、错误、是否跨 `await`/channel。
5. **失败路径与成功路径同等篇幅**。
6. **不省略核心逻辑**：不用「同上」「略」「类似」。
7. **源码索引**：每关键结论给 `` `crate/path` · `符号(+偏移)` ``；顶层符号定义行即 `+0`，impl/trait 成员相对 `impl`/`trait` 头记偏移。绝不写 `文件:行号`，行号只作已标注的快照。
8. **与源码冲突时以源码和可复现测试为准**。

---

## 源码规模（阅读时的心理预期）

- Workspace members：**107 个**（见根 `Cargo.toml` `[workspace].members`），分布在 `crates/codegen/`（89）、`crates/common/`（12）、`crates/build/`（1）、`third_party/`（4）、`prod/mc/`（1）。本轮新增成员 5 个：`xai-grok-permission-rules`（权限规则引擎，从 workspace 拆出）、`xai-grok-cloud-config`（远端/托管配置，从 shell 拆出）、`xai-grok-egress-proxy`（受控出站代理）、`xai-grok-lifecycle`（VM/workspace-server 停机扇出）、`xai-grok-external-agent-migration`（外部 agent 配置迁移）。workspace 依赖含 `tree-sitter = "0.26"`。
- 核心生产 crate 集中在 `crates/codegen/`（`xai-grok-pager`、`xai-grok-shell`、`xai-grok-sampler`、`xai-chat-state`、`xai-grok-tools`、`xai-grok-workspace`）与 `crates/common/`（`xai-tool-runtime`、`xai-tool-types`、`xai-tool-protocol`）。
- 组合根只有一个 `main.rs`：`crates/codegen/xai-grok-pager-bin/src/main.rs`，有意不放领域逻辑。
- 工具链：`rust-toolchain.toml` `[toolchain].channel` 钉死 `1.94.0`。

---

## 核心心智模型（全库共用）

```mermaid
flowchart LR
    INPUT["Terminal / ACP / CLI"] --> VIEW["Pager AppView / Headless reducer"]
    VIEW --> ACTION["Action"]
    ACTION --> DISPATCH["dispatch::dispatch"]
    DISPATCH --> EFFECT["Effect::SendPrompt"]
    EFFECT --> ACP["ACP transport → acp_send"]
    ACP --> CMD["SessionCommand::Prompt"]
    CMD --> TURN["SessionActor::handle_prompt"]
    TURN --> BUILD["ChatStateHandle::build_request"]
    BUILD --> SAMPLE["SamplerHandle / SamplingEvent"]
    SAMPLE --> CALLS["execute_tool_calls_batch"]
    CALLS --> TOOL["ToolDyn::execute"]
    TOOL --> WS["WorkspaceOps / Permission / Sandbox"]
    WS --> RESULT["ToolRunResult"]
    RESULT --> BUILD
    SAMPLE -->|Completed| RESP["PromptTurnResult"]
    RESP --> VIEW
```

六条不变量：

1. UI 状态、会话状态、对话事实、文件事实由不同模块拥有。
2. 模型增量 token 不是规范完成消息；`Completed` 才是提交屏障。
3. 每个工具调用必须由相同 call id 的结果闭合。
4. 权限决定、进程级 OS 沙箱、命令级沙箱策略是**三层**（分别见 11、11 §4.5.1、17）。
5. 取消不自动撤销已经发生的副作用。
6. 结果未知时先对账，不盲目重试。
