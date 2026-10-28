# 证据卡：xai-grok-lifecycle 与 xai-grok-egress-proxy（新 crate 侦查）

- 侦查日期：2026-10-27；HEAD 快照。锚点记法：`文件 · 符号+偏移`，括号为绝对行号快照。
- 两 crate 均为 codegen 层新成员；跨 crate 唯一调用方都是 `xai-grok-workspace`。

## 一、crates/codegen/xai-grok-lifecycle

### 1. 定性
- 描述自述：**workspace server（远程 VM 内）的 pre-stop 生命周期 broker**——宿主在停止 VM 前调 `POST /lifecycle/pre-stop`，broker 把事件并发扇出给三类 handler（Cargo.toml description；`src/lib.rs` · crate doc +0~+16（快照 1-16））。它管的是「VM/工作区服务进程被停止那一瞬间的收尾」，不是 agent 会话循环。
- 不变量（`src/lib.rs` · crate doc Invariants）：一次只跑一个 trigger（并发 409）；回答不迟于绝对 deadline+250ms；所有外部输入有命名上限；exec 输出只进封顶日志文件不进响应；注册在同一 kernel boot 内跨重启存活、跨 boot 丢弃。

### 2. 与 xai-agent-lifecycle 的分工（对比表）

| 维度 | xai-grok-lifecycle | xai-agent-lifecycle |
|---|---|---|
| 管的层 | VM/服务进程停止前的 pre-stop 收尾（外部触发） | agent 会话/回合循环内的扩展钩子（内部事件流） |
| 触发者 | 宿主 HTTP 调用 `POST /lifecycle/pre-stop` | 宿主 agent loop 在 session/turn 边界派发 |
| 参与方模型 | `PreStopHandler`（trait）+ exec 子进程 + JSON 清单（`src/event.rs` · PreStopHandler +0（快照 73）） | Contributor trait：`SessionLifecycleContributor` / `TurnLifecycleContributor` / `TurnInputContributor` / `CommandContributor` 等（`src/send/contributors/session_lifecycle.rs` · SessionLifecycleContributor +0；`src/local/contributors/*.rs`） |
| 关键语义 | deadline/超时截断/verdict 汇总/幂等收尾 | 「contributor never own loop control」（`xai-agent-lifecycle/src/lib.rs` · crate doc +0（快照 1-3）），数据入参+能力注入 |
| 关机策略 | 无 shutdown policy 概念，只有绝对 deadline | `ShutdownPolicy`（如 `Drain`，`src/send/registry.rs` 快照 198） |
| 依赖 | axum/tokio/xai-tty-utils（Cargo.toml） | 仅 async-trait+tracing（其 Cargo.toml，无 IO/HTTP） |
- 两者是**完全不同的东西**，名字里都有 lifecycle 但零依赖交集。文档中必须分节并显式对比。

### 3. 对外 API（`src/lib.rs` · pub use +38~+44，快照 41-44）
- `LifecycleBroker` / `LifecycleConfig` / `DEFAULT_IMAGE_HANDLER_DIR`（=`/usr/share/grok/lifecycle/handlers.d`，`src/broker.rs` +26）
- `LifecycleError` / `Result`；`Disk` / `HandlerFuture` / `HandlerOutcome` / `PreStopEvent` / `PreStopHandler`；`HandlerName` / `ReasonToken`
- 入口符号：`LifecycleBroker::new`（broker.rs +70）、`register_builtin`（+99）、`router`（+117）、`trigger`（内部 +122）。

### 4. 状态机 / verdict（无 enum「运行状态」，是每次 trigger 的结果判定）
- handler 运行结果 `RunOutcome`：`Finished(HandlerOutcome)` / `HandlerTimeout`（exec 自身 timeout_ms 先 cut）/ `DeadlineCut`（`src/trigger.rs` · RunOutcome +0（快照 64-72））。
- `HandlerOutcome`：Ok / Failed / TimedOut（`src/event.rs` +54）。
- 汇总 `Verdict` 优先级：`no_handlers` → `ok` → `timed_out`（任一 DeadlineCut，压过 failed，便于宿主区分「预算太短」vs「handler 坏了」）→ `failed`（无一 ok）→ `partial`（`src/trigger.rs` · verdict +231（快照 231-247）+ 模块头注释）。
- 迁移触发者：仅 `POST /lifecycle/pre-stop`（routes.rs · trigger +55）；并发第二发被 `trigger_lock.try_lock` 拒为 409 Busy（broker.rs · Inner.trigger_lock +59、trigger() +127；routes.rs +72）。

### 5. 关键机制（逐条锚点）
| 机制 | 锚点 | 失败路径 |
|---|---|---|
| 启动即装载 | `LifecycleBroker::new`→`BootId::current()`+`HandlerRegistry::load_sync`（broker.rs +70~+90；persist.rs · BootId::current +38，仅 Linux 读 `/proc/sys/kernel/random/boot_id`，非 Linux 返回 None→仅内存） | boot id 读不到：注册留在内存，warn（persist.rs +49/+55） |
| 三类 handler 表 | builtins→image→registered 依序去重，先前源同名遮蔽后续（trigger.rs · handler_table +99；registry.rs · snapshot +57；image.rs · load_image_handlers +39） | 清单非法跳过并 warn（image.rs +138）；扫描超时→本轮无 image handlers（+52） |
| deadline/超时 | 绝对 deadline=收到时刻+budget(100~60000ms，exec_spec.rs MIN/MAX_TIMEOUT_MS +15/+18)；collect 松弛 `COLLECT_SLACK`=200ms（trigger.rs +30），超时 `tasks.abort_all()` 并按 DeadlineCut 报（+202~+209） | handler 卡死：任务被 abort，进程组仍由 GroupGuard 兜底杀 |
| exec 优雅关闭 | SIGTERM 整组→`TERM_GRACE`(1s) 或至 `deadline+KILL_SLACK`(100ms) 先到者→SIGKILL→reap（exec.rs · stop +155，常量 +27~+33） | 未 reap：交给 runtime reaper，warn（+171~+177）；spawn 失败→Failed+日志（+94~+99） |
| 泄漏兜底（崩溃/放弃） | `GroupGuard::Drop` 无条件 SIGKILL 整组（exec.rs +225~+229；注释 +102「spawn 与 enroll 间无 await」）；`ProcessScope` 属 broker，最后一个 handle drop 杀掉所有还在跑的组（broker.rs · processes +57）；输出 drain 用 `AbortOnDropHandle`（exec.rs +113） | enroll 失败：只能杀 leader，warn（+106） |
| 幂等收尾 | PUT/DELETE 按名字幂等；`500 persist_failed` 可能写仍后到，但 store+table 同成同败（routes.rs 模块头注释 +6~+7；registry.rs 模块头 +1~+5，`writes` 锁随阻塞任务走 +33~+36、run_blocking +120） | 写超时 2s（PERSIST_TIMEOUT +23）返回错误但继续完成 |
| ExecLog 封顶 | 64KiB 上限、只留最近一次 trigger、截断标记（exec_log.rs · EXEC_LOG_CAP_BYTES +15、start_trigger +49、append +89） | 打开失败/超时：本轮输出全部丢弃（+71~+77） |
| 持久化 | 每 handler 一个 JSON 文件+boot_id 盖章，tempfile 同目录 rename 原子写、无 fsync（页缓存足够活过一次进程重启）（persist.rs · save_sync +146，注释 +3~+5、+156） | 载入时清：异 boot/解析失败/超 cap/`.tmp-` 残留（load_sync +81~+143） |
- **与信号处理/电源的关系：无**。crate 内 SIGTERM/SIGKILL 只用于杀 exec 子进程组（exec.rs）；全仓库 grep `register_builtin` 无外部调用方、`signal_streams.rs`/`headless/signals.rs`（xai-grok-pager）与 xai-system-power 均不引用本 crate——未确认任何接线。pre-stop 由 VM 宿主经 diag socket 发起（`xai-grok-diag-server/src/lib.rs` · `DiagServeOptions.extra_routes` +413，broker.router() 以 fallback_service 挂载 +403）。

### 6. 调用方（谁在何时调）
- 唯一生产调用方：`xai-grok-workspace/src/bin/workspace_server.rs`。`lifecycle_broker()`（+43（快照 43-49））在启动、diag 绑定前构造：image_dir=`DEFAULT_IMAGE_HANDLER_DIR`、state_dir=`<workspace_home>/lifecycle/handlers`、exec_log=`<temp>/workspace-server-lifecycle.log`（常量 +28~+31）；仅 `#[cfg(unix)]`（注释 +35~+37：Windows loopback TCP 人人可达且宿主不发 pre-stop）。构造限时 `LIFECYCLE_BROKER_START_TIMEOUT`=5s（+31），失败/超时→**降级为无 lifecycle 路由继续供诊断**（+470~+486）。
- VM 宿主进程：POST 触发（仓外，未确认具体调用点）。runtime 注册方：VM 内任意进程 PUT/DELETE（lib.rs doc +6~+7）。

### 7. 配置/环境变量/feature flag
- 无 feature flag；`cfg(target_os="linux")`（boot id）、`cfg(unix)` 由调用方把关。
- 无读取环境变量的配置；反向它**设置** env 给 exec handler：`GROK_LIFECYCLE_EVENT/REASON/DISK/DEADLINE_MS`（exec.rs · ENV_* +40~+45）。
- 命名上限集中表：MAX_BUILTIN_HANDLERS=16（broker.rs +29）、MAX_REGISTERED_HANDLERS=16（registry.rs +20）、MAX_IMAGE_HANDLERS=32（image.rs +28）、MAX_ARGV_BYTES=4096（exec_spec.rs +12）、trigger body 1KiB / PUT body 4KiB（routes.rs +32/+35）、响应 2KiB（trigger.rs +26）。

### 8. 测试矩阵（52 个 test，按模块归纳；均在 `src/*_tests.rs`）
- 路由/契约：400 各类非法体、409 busy、契约示例解析、unix-socket 端到端过 diag server（`routes_work_over_a_unix_socket_through_the_diag_server`）。
- trigger/verdict：并发 409、deadline+epsilon、无 handler→no_handlers、遮蔽顺序、响应截断封顶。
- exec：后台孙进程被杀、SIGTERM 被无视→整组 SIGKILL、首个 await 被 drop 仍杀整组、env 传递、自身 timeout 先于 deadline。
- registry/persist：PUT 幂等+同 boot 重启存活、超时写后到仍两边一致、跨 boot 丢弃、超 cap 修剪。
- image/exec_log/token：缺目录、候选 cap 按名字序稳定截断、log 封顶打标记、名字/reason 正则。
- dev 依赖：`start_paused` 假时钟、nix mkfifo 会合（Cargo.toml dev-dependencies +36~+49）。

## 二、crates/codegen/xai-grok-egress-proxy

### 1. 定性
- **隐藏式本地 loopback HTTP/CONNECT 代理**，服务于「精确 origin 的网站出站策略」：Cargo.toml description "Hidden exact-origin local HTTP and CONNECT proxy for Grok"；lib.rs doc +0~+7（快照 1-7）：*启动本库并不隔离子进程网络，调用方必须先自备平台边界*。
- 与邻居关系：
  - `xai-grok-sandbox`：提供 `WebsitePolicy/WebsiteOrigin/CommandTag/Clock`（lib.rs use +30~+32，唯一业务依赖）。真边界在 sandbox：Linux 每 spawn 的 seccomp 网络过滤（`xai-grok-sandbox/src/lib.rs` 快照 11「child network is blocked per-subprocess via seccomp」、+97）+ macOS seatbelt（`command/backend/seatbelt_profile.rs` 引用 `NetworkPolicy::Proxy`）；内核策略「只允许 loopback 到代理端口」：`command/policy.rs` · NetworkPolicy::Proxy +122~+127、network_for +595~+599。
  - `xai-grok-http`：**无关**（agent 自己的模型 API HTTP 客户端；其 lib.rs 快照 647 只是探测代理 env 跳背景设置拉取）。
  - `xai-grok-extra-ca` / `xai-grok-auth`：无依赖、无引用（Cargo.toml 只有 tokio/rand/base64/httparse/subtle/async-trait/thiserror + sandbox）。
- 不做 PAC；「代理/直连」由 env 注入决定：`EnvPolicy::proxy_vars_at` 给子进程设 HTTP(S)_PROXY/ALL_PROXY/NO_PROXY 大小写八件套，NO_PROXY=`localhost,127.0.0.1,::1`（`xai-grok-sandbox/src/command/policy.rs` +166~+177；launch 侧 `xai-grok-workspace/src/sandbox/launch.rs` 快照 106）。

### 2. 对外 API 与核心类型（lib.rs）
- `EgressProxy::start`（+150）/ `start_with`（+159，校验选项 +165~+173，零值即 `InvalidOptions`）→ `EgressProxyHandle`：`address`、`proxy_authorization`（会话 Bearer 头 +232）、`mint_call_credential`/`revoke_call_credential`/`revoke_credential`（+241/+246/+252）、`blocked_requests`（broadcast 订阅 +257）、`metrics`、`is_running`（+270）、`abort`（+274）、`shutdown`（+300，drain 超时→`ShutdownTimeout`）、`Drop`→try_send(Abort)+task.abort()（+317~+326）。
- 可注入 seam：`Resolver`/`Connector` trait（+51/+57）+ `SystemResolver`/`TcpConnector`；`EgressProxyOptions` 12+ 字段与默认值（+88~+131：64 连接、32KiB 头、64KiB hello、10/5/10/5/5s 超时）。
- `decider` 模块（pub）：`Decider` trait（decider.rs +79：`decide`/`hold`(默认不 park 直接拒 +85~+92)/`admits_unauthenticated`(默认 false +97)/`stopping`(默认 no-op +105)）、`Decision{Allow,AllowAndRecord{would},Deny,Ask}`+44、`WouldBe`+60、`DenySource{DenyRow,WebFetchDenylist}`+68、`BlockedRequest`（无内容记录：host/port/call/outcome/hold_ms/deadline_unix，+133）、常量 `DEFAULT_HOLD_TIMEOUT`=600s（对齐 hub 权限 backstop，+28）、`DEFAULT_MAX_HELD`=16、`DEFAULT_MAX_HELD_PER_CALL`=8、`BLOCKED_REQUEST_CAPACITY`=256。
- `credential` 模块（pub）：`ProxyToken`（OsRng 32B→urlsafe b64，Debug 打 `***`，constant-time 比较，credential.rs +28~+47）、`ProxyCredential::proxy_url`=`http://grok:<token>@addr`（+76）、`CredentialRegistry` mint/revoke/revoke_exact/authenticate（接受 `Bearer <t>` 或 `Basic`，密码侧比较，+90~+160）。模块头明确：**这是归因不是隔离**——token 在子进程 env 里，同 uid 可读；「随 call 而死」才是保证（+5~+7）。

### 3. 完整链路（逐跳；★=跨 await/后台任务）
1. 请求产生：沙箱内子命令读 `HTTP_PROXY` env → 连 127.0.0.1:<port>（注入点 `sandbox/launch.rs` 快照 106；代理端口由 `NetworkSide::policy_endpoint` 供内核策略，network.rs +110~+113）。
2. 监听/准入：★`server::serve` 循环 accept（lib.rs start_with +191 spawn 为后台任务）；**只接受 loopback 对端**（server.rs +33~+35 非 loopback 直接 drop）；连接数超 `max_connections`→503 Overloaded（admit_connection +66~+79）。
3. 解析头部：`read_head` 封顶 max_header_bytes（request.rs +167）→ `ParsedRequest::parse`（HTTP/1.1 only、方法大写 ASCII，+16）→ `authenticate`：无/错凭证→407，除非 decider.admits_unauthenticated（server.rs +123~+135）。
4. origin 判定：CONNECT 走 `strict_connect_authority`（禁 `/@[]?#\` 等，request.rs +224）；HTTP 走 `parse_http_target`（仅 http:// 绝对形、host 头必须与 authority 规范化相等，http.rs +21~+33）；TRACE 拒（server.rs +117）；HTTP 请求带 body→`BodyUnsupported` 400（http.rs +36~+38）。
5. ★决策：`ProxyState::admit`（decider.rs +215~+295）——先 `policy.evaluate(origin)!=Allow` 即 403（**决策前**，不跑 decider）；`decide` 限时 request_timeout，不守约→Timeout；Ask：先取 per-call 预算再取全局 holds 信号量（满了 503，+249~+254），`hold` 限时 hold_timeout 后 `hold()` park（select：answer/stopping/deadline/client EOF，+326~+360；parked 期间客户端字节封顶 64KiB，+41）。
6. ★连接建立：`resolve_public`→DNS 超时/失败→Timeout/Dns；**解析出的地址任一非公网即全拒**（`AddressDenied`，lib.rs +328~+348，防 rebinding/内网/云元数据；`ip.rs` · is_public_ip +3 覆盖 v4/v6/内嵌 v4 全私有段）；`Connector::connect` 逐个试已核验地址（lib.rs +76~+86）+connect_timeout。
7. 隧道/TLS：CONNECT 先回 `200 Connection Established`（committed 后错误只计指标，connect.rs +49~+64），再解析 ClientHello：记录类型必须 0x16/handshake 必须 0x01、**SNI 必须存在且与 CONNECT authority 规范化相等、ECH（0xfe0d）直接拒**（tls.rs · validate_hello +72~+116）；然后 `copy_bidirectional` 盲转发（connect.rs +65）。
8. 失败降级：`ConnectionError::Precommit/Committed` 二分——committed 后绝不追加错误响应，只记 metric（error.rs +90~+105；测试 `partial_http_response_failure_never_appends_proxy_error`）。
9. 结果上报：`publish` 把 `BlockedRequest` 发进 broadcast（decider.rs +297~+315，无人订阅即丢弃）+ `ProxyMetrics` 12 个原子计数（metrics.rs · ProxyOutcome +5~+39，error→outcome/status 映射在 error.rs +46~+79）；workspace 侧消费：★`blocked_feed` 后台任务写入 observe summary（`sandbox/network.rs` +882~+900 → `note_blocked_request` +592 → `observe_summary` mod.rs +1071）。

### 4. 安全语义：fail-open / fail-closed（逐字证据）
- 被强制走受控出口的：enforce 模式下沙箱子命令的全部出站（内核策略只放行 loopback→代理端口：`command/policy.rs` · NetworkPolicy::Proxy +124~+126「Only loopback to the egress proxy on `port`」；NO_PROXY 只豁免 localhost）。
- **默认 fail-closed，多处硬编码**：
  - `EgressProxy::start` 文档：every origin the supplied policy does not allow is denied（lib.rs +151~+152）；`start_with` 用 `PolicyOnly`（decide 恒 Allow，仅补充层，+109~+116）。
  - admit：policy 不 Allow→`PolicyDenied` 403，先于 decider（decider.rs +222~+224）。
  - `Decider::hold` 默认实现返回「无人应答即拒」的 channel（dropped sender = deny，decider.rs +84~+92）；park 中 proxy stopping→deny（+347；lib.rs stopping 字段注释 +143~+145；server.rs +50~+53 注释 “Fail closed before anything is waited for”）。
  - 凭证缺失/撤销→407（lib.rs +245~+248；server.rs authenticate）；workspace decider 的 `admits_unauthenticated`：**enforce、或虽 observe 但仍有 enforce 活调用时一律拒**——注释逐字 “Fail closed for every caller until that call ends”（`permission/sandbox_network.rs` 快照 741~+750）。
  - Ask 且 sink 不在（无卡片通道）→Deny（sandbox_network.rs decide 内 `WouldBe::Asked => None 分支 Decision::Deny`，快照 736~+738）。
  - 代理起不来：`WorkspaceSandbox::serve` 文档——“commands then run with the network off under `enforce` and unproxied under `observe`”（`sandbox/network.rs` start_network_locked 文档 +264~+268；serve +176~+179「never fails，日志后无代理供服」）⇒ enforce 下无代理=断网，不是绕过。
  - SNI/ECH/字面 IP origin 拒（tls.rs；`network_policy.rs` 测试快照 353 拒 IP literal origin）。
- **唯一的“fail-open”是 observe 模式，且是记录不是放行**：`Decision::AllowAndRecord{would}` 放行并把 enforce 会做的判定发进 summary（decider.rs +47~+50、+58「Observe never blocks, deny lists included: the verdict is recorded, not applied」；sandbox_network.rs decide 快照 725~+727）。注释同时声明凭证是归因非隔离（credential.rs +5~+7）。

### 5. 配置项/环境变量
- 库本身不读任何 env/feature flag（Cargo features 无）；全部经 `EgressProxyOptions` + `Decider` 注入。
- 面向子进程的 env：`HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY`（大小写各一份）+ 每 call 凭证嵌在 URL userinfo（proxy_vars_at，sandbox policy.rs +166~+177；PROXY_USERNAME="grok"，credential.rs +22）。
- workspace 侧实例化只改 `clock`（与 grant 行同一时钟），其余默认（sandbox/network.rs +244~+247）。

### 6. 测试矩阵（tests/ 7 文件 ~2360 行，56 个 test，主题归纳）
- 生命周期/资源：ready+shutdown 无残留监听、abort 收敛活动任务、连接任务回收、drain 对 parked 回 deny 且只通知 decider 一次、shutdown 等待隧道有界。
- 鉴权：session bearer/basic、call 凭证归因+撤销 407、重复 mint 替换、撤销被替换者不动 live 者、admits_unauthenticated 路径、Debug 不泄 token。
- hold 预算：双层 cap、per_call 夹到 max_held、一答释放全部 held、超时 403+publish、客户端挂断→Abandoned 释放槽位、hold 比 request_timeout 长寿、stuck decider 被 cut。
- HTTP/CONNECT：policy 先于 decider、host/authority 规范化相等、分片 ClientHello 保真、SNI 不匹配/ECH 拒、205/204/304/HEAD 框架、committed 后不追加错误、请求体不支持、头超限。
- DNS/连接：空/私有/混合地址集拒、钉住公网地址集、`is_public_ip` 自带表驱动测试（ip.rs +71~+104）。
- metrics：`every_outcome_has_its_counter` 编译期护栏（metrics.rs +103~）。

## 三、归并建议（给文档主线）

| crate | 建议 | 理由 |
|---|---|---|
| xai-grok-lifecycle | **并进末篇《可靠性与通用技术实现说明书》**新增一节「pre-stop 生命周期 broker（VM 收尾）」；12 篇只放一行指针（它确实经 diag socket 挂载，但机制本体是取消/超时/幂等/兜底杀，正是末篇主题）。同时第 11 篇（Workspace 权限沙箱与 Git）加一句交叉引用：宿主调用于 workspace_server 启动路径。体量 3.8k 行、调用方唯一、心智上是「优雅关闭的又一种实现（外部 HTTP 触发）」，不值得独立章；但必须在末篇与 xai-agent-lifecycle 摆一张分工表防混。 | 高耦合=末篇主题；低耦合=12 篇（无认证/网络/更新逻辑） |
| xai-grok-egress-proxy | **12 篇《认证网络遥测与更新》新增独立一节「受控出口：本地 egress 代理」**（性质/链路/fail-closed 证据/凭证归因），并把与 xai-grok-sandbox 的「内核边界 vs 代理策略」两层关系写清；涉及 hold→卡片→settle 的用户交互闭环细节放第 11 篇（权限沙箱）交叉引用。若 12 篇篇幅超阈值，再考虑拆「出站管控」独立篇。4.6k 行、自带 2.3k 行测试，且带独立安全语义（SSRF/元数据防护、SNI 钉定、fail-closed），比 lifecycle 更有成章资本。 | 它是 12 篇「网络」主题的真子集但含安全合同；读者心智=「沙箱命令怎么上网、谁说了算、拒了怎样」 |
- 两 crate 都应在文档中显式标注：**xai-grok-lifecycle ≠ xai-agent-lifecycle**（前者 VM pre-stop 扇出 broker，后者 agent 循环 contributor 钩子，零依赖交集）。

## 未确认清单
- VM 宿主侧对 `/lifecycle/pre-stop` 的实际调用时机/重试策略：代码不在本仓库（宿主进程外置）。
- `EgressProxyHandle::metrics()` 是否有生产消费者：仓内只见于测试路径，未在生产代码 grep 到读点。
- lifecycle 与 signal_streams / headless/signals / xai-system-power 的接线：grep 为空，确认**无**（非未确认，是已确认未接线）。
