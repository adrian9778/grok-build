# 新 crate 侦查证据：xai-grok-cloud-config / xai-grok-config / xai-grok-config-types

快照：`SOURCE_REV=559751fd`（HEAD `2bdd1d6a`）。搬迁发生在上一次同步 `97f190f6`（`git log --diff-filter=A` 证实 cloud-config 在此提交新增）。
规模：`xai-grok-cloud-config` 全量 8,080 行、**非测试 4,216 行**（任务书给的 5,584 与实测不符，已复核：`find src -name '*.rs' ! -name '*tests*' | xargs wc -l` = 4216）。

---

## 1. 定位与边界

| crate | 职责（自述原文） | 关键证据 |
|---|---|---|
| `xai-grok-cloud-config` | 「fetches, caches, and refreshes the Grok config delivered from the cloud。**Parsing and composition stay in `xai-grok-config`**」 | `…/src/lib.rs` · 模块文档 +0~+1；`Cargo.toml` · package description +4 |
| `xai-grok-config` | 文件加载与**分层合并**、endpoint、remote settings **类型**、vendor compat、campaign overlay、MCP server list；lib.rs 头注释**直接写死 6 层合并序** | `…/src/lib.rs` · 模块文档 +5~+15 |
| `xai-grok-config-types` | 「从 `xai-grok-shell` 抽出的叶子配置值类型（依赖倒置）」 | `…/Cargo.toml` · description +4 |
| `xai-grok-shell/src/agent/remote_config/` | **只剩模型目录（catalog）侧**：endpoint/fetch/manager/resolution/model_fetch_auth/task_model_policy + `settings_get.rs` 薄适配器 | `crates/codegen/xai-grok-shell/src/agent/remote_config.rs` · 模块文档 +0「fetches the model catalog, caches it, and loads it at startup」 |

四类配置的归属（实测）：

| 配置类别 | 拉取/缓存/刷新 | 类型/合并 | 磁盘文件 |
|---|---|---|---|
| 企业托管策略（managed_config + requirements） | cloud-config `managed_config/` | config `managed_text`/`signed_policy`/`config_requirements` | `managed_config.toml`、`requirements.toml`、`managed_config_cache.json`(marker)、`managed_config.sig.json`、`managed_identity.sig.json`、`staged/managed_config_refresh.json` |
| 远端 settings（`/settings`） | cloud-config `settings_*` | config `remote_settings.rs` · `RemoteSettings`（**184 个 pub 字段**，+280） | `settings_cache.json` |
| 模型清单（`/v1/models`） | cloud-config `remote_settings/`（泛型后端）+ shell `remote_config/manager`（业务） | shell `agent/config.rs` · `ModelEntry` | `models_cache.json` |
| feature gate / 优先级 | 不在此 crate（remote 层值来自 RemoteSettings） | config-types `registry.rs` + config `resolved.rs` | — |

**命名陷阱（必须写进文档）**：`xai-grok-config/src/remote_settings.rs`（**类型定义**）与 `xai-grok-cloud-config/src/remote_settings/`（**模型清单缓存机制**）同名不同物。

**依赖方向**（`Cargo.toml` 实测）：`cloud-config → {config, dirs, env, extra-ca, http, login, telemetry, version, prod-mc-cli-chat-proxy-types}`。`cloud-config` **不**依赖 `config-types`；`config-types → xai-grok-config`（+ sandbox）。消费者仅 4 个：`xai-grok-login`、`xai-grok-shell`、`xai-grok-memory`、`xai-grok-workspace`。

---

## 2. 对外 API（`xai-grok-cloud-config/src/lib.rs` 全 22 行，逐条锚点）

| 导出 | 定义位置 |
|---|---|
| `pub mod managed_config` | lib.rs +7（模块）→ `managed_config/mod.rs` |
| `pub mod remote_settings` | lib.rs +8 → `remote_settings/mod.rs` |
| `pub mod settings_get` | lib.rs +12 |
| `CachedConfigInputs` / `load_config_with_cached_remote` | lib.rs +15 → `cached_config.rs` · `+23` / `+31` |
| `Commit` / `PolicyRepairPending` / `resolve_disk_auth` | lib.rs +16 → `commit.rs` · `+9` / `+6` / `+63` |
| `SettingsCacheMode` | lib.rs +17 → `settings_cache.rs` · `+19` |
| `SettingsEndpoint`（**`pub(crate)`**） | lib.rs +18 → `settings_endpoint.rs` · `+32` |
| `settings_cache_identity` | lib.rs +19 → `settings_endpoint.rs` · `+9` |
| `SettingsFetch` / `fetch_settings_blocking` | lib.rs +20 → `settings_fetch.rs` · `+7` / `+27` |
| `SettingsRefresh` | lib.rs +21 → `settings_refresh.rs` · `+8` |

私有模块（不进 API）：`cached_config` +0（绝对行 6）、`commit`+6、`settings_cache`+9、`settings_endpoint` +0（绝对行 11）、`settings_fetch` +0（绝对行 12）、`settings_refresh` +0（绝对行 14）。
`#![deny(clippy::indexing_slicing)]`（lib.rs +3）。feature `test-support`（Cargo.toml +8）暴露测试缝，`default-bazel` 默认开启（+9）。

`managed_config` 面（`managed_config/mod.rs` +8~+26）：`ManagedPolicyRefusal`、`ManagedConfigError`、`classify_auth_mode`/`clear_orphan`/`current_serving_identity`/`has_principal`/`is_fetch_enabled`（store +602/+128/+627/+604/+590）、`resolve_deployment_id`/`resolve_deployment_key`（store +562/+569）、`policy_repair_pending`（supervisor +486）、`ManagedConfigSync`/`SESSION_START_AUTH_DEADLINE`/`SESSION_START_SYNC_DEADLINE`/`SetupOutcome`/`SetupReport`/`ensure_managed_policy_present`/`fetch_setup_report`/`post_login_sync`/`run_setup`/`start_refresh_supervisor`/`sync`、`LaunchProfile`/`startup_profile`/`managed_policy_gate`（mod +32/+50/+74）。

---

## 3. 生命周期：拉取 → 缓存 → 合并 → 生效 → 指标

### 3.1 A 线：远端 settings

| 跳 | 事实 | 锚点 | 跨 await/后台 |
|---|---|---|---|
| endpoint | `{proxy_url}/settings`（**不是 `/v1/settings`**，注释与代码不一致） | `settings_fetch.rs` · `fetch_settings_blocking_with_attempts` +47 | 同步阻塞 reqwest `blocking` client |
| 鉴权 | `Authorization: Bearer`、`X-XAI-Token-Auth`、`x-userid`、`x-grok-client-version`、`x-email`、`x-grok-client-identifier`、client-mode | `settings_fetch.rs` · `add_cli_chat_proxy_headers_blocking` +0（绝对行 63） | — |
| 重试 | `SETTINGS_FETCH_MAX_ATTEMPTS=3`，backoff `500ms*attempt`；5xx/网络错误续、401 立即停、非 2xx 立即停、JSON 解析失败立即停 | `xai-grok-http/src/lib.rs` +23/+25；`settings_fetch.rs` · `classify_settings_response` +0（绝对行 89） | `std::thread::sleep`（阻塞线程） |
| owner 任务 | **每个 `(origin, identity)` 一个 owner**，`tokio::spawn` + `watch::channel`；同 key 复用、异 key `abort()` 替换 | `settings_get.rs` · `OwnerKey` +0（绝对行 153）、`Owner` +0（绝对行 174）、`warm_and_subscribe` +0（绝对行 186） | **是**：`spawn`；内部再 `spawn_blocking`（+459） |
| 全局状态 | `static STARTUP_STATE: OnceLock<Mutex<StartupState>>`，poison 用 `into_inner` | `settings_get.rs` · `startup_state` +232/+234 | 同步锁，**不跨 await 持有** |
| 缓存读 | `settings_cache.json`，TTL **3600s**，上限 **1 MiB**，HMAC-SHA256 信封（key 明文内嵌、非机密） | `settings_cache.rs` · `SETTINGS_CACHE_TTL` +0（绝对行 15）、`SETTINGS_CACHE_MAX_BYTES` +0（绝对行 16）、`load_verified` +0（绝对行 212）、`sign_cache_payload` +0（绝对行 336） | 同步 |
| 缓存键 | `identity = sha256(user_id|team|org|issuer|auth_mode|alpha)`（不含 token ⇒ **token 轮换不换 scope**）、`origin`、`client`、`grok_version` | `settings_endpoint.rs` · `settings_cache_identity` +0（绝对行 10）（`scope_hash` 见 `remote_settings/validation.rs` +21）；`check_scope` +229 | — |
| 写 | 原子 tmp+rename、`0600`、进程内 `WRITE_LOCK` 串行、**单调**（存 `fetched_at >= 新值` 则跳过；未来时间不阻塞写） | `settings_cache.rs` · `persist` +253；`xai-grok-config/src/cache_file.rs` · `write_atomic` +105 | — |
| 提交门 | 4 态 `Commit::{CacheAndServe,ServeInMemory,Retry,Abandon}`；只有活取走门，缓存命中不走 | `commit.rs` · `evaluate_commit` +0（绝对行 26）、`settings_get.rs` · `commit_for_fetch` +0（绝对行 574） | — |
| 生效 | `cfg.remote_settings = Some(..)` → `set_remote_campaigns_from_settings` → `apply_remote_settings_side_effects`（12 项进程级缓存 + OTEL policy + normalize cache） | `shell/src/agent/init.rs` · `install_settings_wait` +288/+293、`ensure_remote_settings_side_effects` +0（绝对行 318）；`shell/src/agent/config.rs` · `apply_remote_settings_side_effects` +0（绝对行 2767） | 阻塞在 `block_on_startup_settings` |
| 热加载 | 会话侧 fire-and-forget：`spawn_settings_reapply`（至多一个在飞）→ `fetch_settings_live`（`spawn_blocking`）→ 直读 `/settings`，**不查启动缓存**，成功后 `write_through` 落盘 | `shell/src/agent/mvp_agent/agent_ops.rs` · `spawn_settings_reapply` +0（绝对行 1812）、`fetch_settings` +0（绝对行 1601）；`settings_get.rs` · `fetch_settings_live` +0（绝对行 273） | **是**：`tokio::spawn` + `spawn_blocking` + `SETTINGS_REAPPLY_TIMEOUT=30s` |
| 指标 | `DegradedStartCause::{FetchFailed,DeadlineMissed}` → `unified_log::emit`，级别按 `LaunchProfile`（Managed=Warn / Personal=Debug） | `remote_settings/metrics.rs` · `+3/+10/+29`；调用 `shell/src/agent/init.rs` +277/+295 | — |
| 计时 | `InstrumentationTimer "startup.settings_get"`（Chrome 模式带 span） | `settings_get.rs` · `load_settings_blocking` +487 | — |

### 3.2 B 线：企业托管策略

| 跳 | 事实 | 锚点 |
|---|---|---|
| endpoint | `{proxy_url}/deployment/config`，可被 `managed_config_url` 覆盖 | `config/src/endpoints.rs` · `resolve_managed_config_url` +0（绝对行 151） |
| 凭证两路 | 先 `GROK_DEPLOYMENT_KEY`（env 胜 config，空串=未设），再 team OAuth 会话 | `store.rs` · `resolve_deployment_key` +0（绝对行 571）；`supervisor.rs` · `fetch_for_principal` +0（绝对行 341） |
| 回退 | DK 被 401/403 拒 且 有 team ⇒ 落 team；DK **无配置行** 且有 team ⇒ 落 team（否则空 body 会删团队文件）；网络/5xx **不**回退 | `supervisor.rs` · `fetch_for_principal` +357~+369 |
| nonce echo | 请求带 `MANAGED_CONFIG_NONCE_ECHO_HEADER`（重放探针，纯遥测）；sidecar 损坏则 fail-open | `supervisor.rs` · `fetch_managed_config_once` +111~+121 |
| 签名 | 有 `signatures` 时**必须**验签；外层 `key_id` 只选位、验签内部重选 key；body 与签名 payload 必须逐字相等 | `response.rs` · `verify_signed_envelope` +0（绝对行 215）、`pick_trusted_envelope` +0（绝对行 195） |
| 落盘 | `apply_fetched`：先验签→拿 flock→查凭证仍在→parked 新鲜度→收敛 artifact（服务端不再下发的**删除**）→换 principal 时驱逐前家 sidecar→写 sidecar→**最后**写 marker→清 stage | `store.rs` · `apply_fetched` +0（绝对行 327）、`apply_managed_config` +0（绝对行 275） |
| stage | 仅「已验签 且 写失败属 deny 类（`PermissionDenied`/`ReadOnlyFileness`/`ResourceBusy`）」才 park 到 `staged/managed_config_refresh.json`，下次 boot 沙箱前重放 | `store.rs` · `stage_refresh` +0（绝对行 444）、`apply_staged_managed_config` +0（绝对行 470）；`policy.rs` · `write_failure_is_deny` +0（绝对行 91） |
| 合并 | 6 层（低→高）：`/etc/grok/managed_config.toml` → `$GROK_HOME/managed_config.toml` → `$GROK_HOME/config.toml` → `$GROK_HOME/requirements.toml` → `/etc/grok/requirements.toml` → macOS MDM；每层先套 `[[version_overrides]]` | `config/src/lib.rs` · 模块文档 +5~+15 |
| 优先级（值级） | `requirement > cli > env > config > managed > feature_flag(远端) > default`；`resolve_string_flag` 为 `cli > env > config > remote` | `config/src/resolved.rs` · `resolve_bool_flag` +0（绝对行 108）、`resolve_string_flag` +0（绝对行 140） |
| **反向优先级例外** | `remote_fetch` 单独解析：deployment 的 `remote_fetch=false` **压过**用户 `true`；`env_overlay`/`campaigns` 被显式忽略 | `config/src/remote_fetch.rs` · `remote_fetch_enabled_from_layers` +21~+24 |
| feature 注册表 | `FEATURES` 表 21 个 `[features]` key，每行含 `key/env/path/default/remote/capability`；注释明示「**无 managed 层**」 | `config-types/src/registry.rs` · `FEATURES` +0（绝对行 147）、`FeatureSpec` +58（注释 +70）、`Feature::resolve` +449 |

### 3.3 C 线：模型清单（cloud-config 出泛型后端，shell 出业务）

`remote_settings/cache.rs` · `ModelsCache<E>`（+18，**新增泛型参数**，旧版不泛型）、`CACHE_TTL=300s`（+11）、`MODELS_CACHE_FILE`（+0，绝对行 11））、4 MiB 上限（+13）、`renew_ttl`（+0，绝对行 160），etag 未变只续 `renewed_at`，跨进程竞态「self-heals」）、`invalidate`（+0，绝对行 193））。
`backend.rs` · `fetch_catalog` +0（绝对行 58） / `commit_catalog_fetch` +0（绝对行 105） / `apply_models_commit` +0（绝对行 126）。
`prefetch.rs` · `InitialModelsLoad::join` +10、`spawn_catalog_thread` +0（绝对行 51）（**注释：`work` 不得跑在 tokio worker 上，因为 fetch 自建 runtime ⇒ 用裸 `std::thread`**）、`wait_catalog_prefetch` +0（绝对行 105）（`mpsc`+poll 循环）。
消费方：`shell/src/agent/remote_config.rs` · `ModelsCacheManager` 类型别名 +36（注入 `crate::agent::config::ModelEntry`）；`manager/mod.rs` · `refresh_if_new_etag` +0（绝对行 705）、`reload_from_disk_cache` +0（绝对行 806）。

---

## 4. `supervisor.rs` 并发模型

- **唯一调度点**：`start_refresh_supervisor`（+0，绝对行 204），注释「The one place a managed-config refresh can be scheduled」），`shell/src/agent/init.rs` +139 在 gate **之后**调用，`if !cfg!(test)` 包住。每次 boot 先 `store::clear_orphan()`（+205）。
- **槽位**：`static REFRESH_SUPERVISOR: Mutex<Option<ManagedConfigRefresher>>`（+199）；注释明示「**Mutex, not OnceLock**：随 agent 线程死掉的 supervisor 必须可替换」。`ensure_supervisor`（+0，绝对行 214））：`handle.is_finished()` 为假则原样保留，否则替换；poison 用 `into_inner`。
- **起**：`ManagedConfigRefresher::spawn(parent, work)`（+173）= `parent.child_token()` + `tokio::select!{biased; cancel; work}`；`biased` 注释「已取消的 token 甚至不该开始 work」。
- **停**：`impl Drop`（+191）= `cancel.cancel()` + `handle.abort()`；父 token 不受影响（测试 +73 钉死）。测试缝 `take_refresh_supervisor`（+224）。
- **循环体**（`spawn_refresh_supervisor` +0（绝对行 233））：① `revalidate_stale_start`（+0，绝对行 266））→ ② `interval(managed_config_sync_interval())`，默认 **5 min**，`GROK_DEPLOYMENT_CONFIG_REFRESH_INTERVAL_SECS` 覆盖，**下限 clamp 1s**（`tokio::time::interval` 对 0 panic，+154）→ ③ 丢弃首 tick → ④ 每 tick：`clear_orphan` → `bump_managed_rollback_floor`（时钟回拨防线）→ ⑤ 仅当 `is_managed_config_stale_for(当前身份)` 且 `is_fetch_enabled()` 才 `sync()`，否则 `continue`。
- **失败降级**：循环内 `sync()` 的 `Err` 只 `tracing::debug!`，任务**不退**（+259）；`Ok(false)` 静默。
- **预算矩阵**（`SyncBudget` +0（绝对行 12） / `max_attempts` +19 / `deadline` +26）：

| Budget | attempts | deadline | 用在哪 |
|---|---|---|---|
| Standard | 5 | 无 | `sync()`(+286)、`run_setup()`(+622)、`fetch_setup_report()`(+597) |
| Revalidate | 5 | 120s（`REVALIDATE_DEADLINE` +0（绝对行 37）） | `revalidate_stale_start` |
| Login | 2 | 15s | `post_login_sync`（+0，绝对行 436）） |
| SessionStart | 2 | 8s（`SESSION_START_SYNC_DEADLINE` +0（绝对行 42）） | `ensure_managed_policy_present`（+0，绝对行 512）） |

退避 `retry_backoff`（+0，绝对行 45））：base 1s，`1 << (attempt-1)`，`GROK_DEPLOYMENT_CONFIG_BACKOFF_MS` 覆盖。
- **两段有界等待**：`ensure_managed_policy_present` = ① `apply_staged_managed_config()`（同步，先于陈旧判定）→ ② `policy_repair_pending_from` 早退 → ③ `refreshed_team_principal`（+0，绝对行 555）：`tokio::spawn(auth())` + `timeout(8s)`；**注释：超时不杀任务，临期轮换的 token 仍会落盘**）→ ④ `has_principal`/`hard_stale` 双闸 → ⑤ `sync_bounded(SessionStart)`。
- **`policy_repair_pending`（+0，绝对行 487））** 是跨线闸门：为真期间**禁止任何带凭证的启动期请求**。`is_eligible`（settings_get +239）、`evaluate_commit`（commit +33）、`evaluate_models_commit`（validation +40）、`models_prefetch_inputs`（shell prefetch +69）四处消费。
  ⚠ 风格不统一：settings 线把它当 `fn() -> bool` **参数注入**（`PolicyRepairPending` commit.rs +6），models 线**直接调** `crate::managed_config::policy_repair_pending()`（validation.rs +40）。
- **单测锁死的行为**（`managed_config/tests.rs`，19 个）：`supervisor_slot_respawns_a_dead_task_and_keeps_a_live_one`（+0，绝对行 91）)、`refresher_drop_stops_work_without_cancelling_parent`（+0，绝对行 74）)、`gate_waits_out_a_contended_lock_inside_a_local_set_on_a_multi_thread_runtime`（+0，绝对行 30）)、`gate_snapshot_denies_when_lock_held_or_unopenable`（+0，绝对行 8）)、`gate_blocks_only_managed_principal_with_compromised_policy`（+0，绝对行 131）)、`apply_converges_over_a_squatting_directory`（+0，绝对行 242）)、`staging_classifier_matches_only_the_write_deny_class`（+0，绝对行 293）)、`transport_failure_maps_to_managed_config_error`（+0，绝对行 322）)、`purge_keeps_marker_when_an_artifact_removal_fails`（+0，绝对行 409）)、`served_principal_prefers_deployment_id`（+0，绝对行 450）)、`claim_persists_only_when_bound_to_served_principal`（+0，绝对行 477）)、`managed_config_gate_ignores_the_overlay_in_both_directions`（+0，绝对行 509）)。

---

## 5. 删除项影响（全部 grep 实证，非推测）

| 被删 | 行数 | 去向 | 语义是否保留 |
|---|---|---|---|
| `shell/src/managed_config/{mod,policy,response,store,supervisor,tests}.rs` | 整目录 | 1:1 搬入 `cloud-config/src/managed_config/`；`shell/src/lib.rs` +41 `pub use xai_grok_cloud_config::managed_config;` ⇒ **旧路径以 re-export 形式仍然可解析** | 保留；唯一改造是 `crate::util::config::*` → `xai_grok_config::*`、`crate::managed_config` → `super`/`store` |
| `shell/…/remote_config/scope.rs` | −101 | **拆成三份，非移除**：`Commit`+`evaluate_commit`+`origin_still_current`+`identity_still_current`+`resolve_disk_auth` → `cloud-config/src/commit.rs`（+9/+25/+46/+52/+63）；`evaluate_models_commit` → `remote_settings/validation.rs` +35；`settings_cache_identity`（原 `SettingsCacheManager::identity` 方法）→ `settings_endpoint.rs` +9 | 逐条等价。差异：`origin_still_current` 旧版内含 `!policy_repair_pending()`，新版把它上提到 `evaluate_commit` 首行（commit.rs +33），语义等价；`evaluate_models_commit` **改签名**多收 `models_fetch_enabled: bool` 并改调 `crate::managed_config::policy_repair_pending()` |
| `shell/…/remote_config/settings_cache.rs` | −633 | → `cloud-config/src/settings_cache.rs`（361 行）。新增 `SettingsCacheMode::{Enabled,Disabled}`+`from_process`(+19/+26) 取代旧 `settings_cache_disabled()`；`SettingsCacheManager::new()` → `new(grok_home, mode)`(+94)；新增 `write_through`（+0，绝对行 146）)、`load_for_any_client`（+0，绝对行 180）)、`Freshness`（+0，绝对行 291）)、`SettingsCacheWrite::commit`(+319) | HMAC key 字符串、TTL 3600s、1MiB 上限、scope/version 校验**逐字不变** |
| `shell/…/remote_config/{cache.rs,metrics.rs,settings_refresh.rs,cache_file.rs}` | — | `cache.rs`→`remote_settings/cache.rs`（**`ModelsCache<E>` 变泛型**）；`metrics.rs`→`remote_settings/metrics.rs`（**内容逐字不变，仅 `pub(crate)`→`pub`**）；`settings_refresh.rs`→`cloud-config/src/settings_refresh.rs`；`cache_file.rs`→**`xai-grok-config/src/cache_file.rs`**（+1~+144，逐字等价，`pub(in crate::agent::remote_config)`→`pub`） | 成立 |
| `shell/…/remote_config/settings_get.rs` | −659→72 | 实现搬 `cloud-config/src/settings_get.rs`(717)，shell 侧保留**薄适配器**（每个函数注入 `policy_repair_pending`） | 成立；`/v1/settings` 注释与实际 `/settings` 路径不一致**沿用旧错** |
| `config-types/src/trust.rs` | −376（`97f190f6` 加、`2bdd1d6a` 删） | → `xai-grok-permission-rules/src/folder_trust.rs`：`TrustLevel` +0（绝对行 6）、`DecideInputs` +0（绝对行 26）、`PromptPolicy` +0（绝对行 35）、`TrustDurability` +0（绝对行 41）、`TrustResolution` +0（绝对行 53）、`folder_trust_inert` +0（绝对行 121） | 换 crate，语义保留 |
| `config-types/src/flags.rs` 的 `ConfigSource`/`Resolved`/`BoolFlag` | −约 90 | → `xai-grok-config/src/resolved.rs`（+7/+23/+41），flags.rs 改 `pub use xai_grok_config::{BoolFlag, ConfigSource, Resolved}`（+2） | 优先级序（requirement>cli>env>config>managed>feature_flag>default）**未变** |

---

## 6. `xai-grok-config-types` 关键类型与消费者

| 主题 | 类型（定义行） | 消费者（实测） |
|---|---|---|
| Memory（**本轮主体增量**，memory.rs 1,476 行） | `MemoryMode` +0（绝对行 16）、`MemorySettings` +0（绝对行 37）、`MemoryV2Config`+51、`MemoryIndex/Embedding/Search/InitialInjection/Session/Watcher/Gc/Dream/Flush/Pruning` 各 `*Settings`(+#119~+209) 与 `*Config`(+#221~+557) 两套、聚合 `MemoryConfig`+574 | `xai-grok-memory`：`dream.rs`+9(`MemoryDreamConfig`)、`backend.rs`+126/+133(`MemoryEmbeddingConfig`/`MemorySearchConfig`)、`v2_consolidation.rs`+1267(`MemoryIndexConfig::default()`)、`storage_v2_tests.rs`+4(`MemoryMode`)；`shell/src/config/mod.rs`+6 re-export，`pager`+794/`headless`+429/`acp/spawn`+270 用 `xai_grok_shell::config::MemoryConfig`；热加载 `shell/src/config/reloader.rs` · `ConfigUpdate::Memory`+32 |
| Model/工具行为 | `LazinessDetectorPerModelConfig`（flags.rs +10；注释：`enabled=true` 且 `max_nudges_per_session>0` 才注入 nudge，`idle_threshold_ms`/`min_confidence`/`include_reasoning` 的 `None` = 让 harness 默认值） | `xai-grok-shell`（`[model.*]`；`reloader.rs` · `ModelsChanged`+39） |
| Feature gate | `Feature`(21 变体)+12、`FeatureSpec` +0（绝对行 60）、`FeatureSources`+75、`FeatureConfigLayer` +0（绝对行 97）、`FeatureConfigLayers` +0（绝对行 126）、`FEATURES` +0（绝对行 147）、`Feature::resolve`+449（注释「the only place precedence lives」）、`config_layers`+405 | `xai-grok-shell/src/config_docs`+265、`registry_tests.rs`（312 行） |
| 权限/沙箱/隐私/MCP/文件加速 | `permission.rs`(73)、`sandbox.rs`(132)、`privacy.rs` · `PrivacyMode`/`SharedPrivacyMode`、`mcp.rs`(27)、`auth_provider.rs`(26)、`file_acceleration.rs`(36) | `login/src/lib.rs`+68 re-export `AuthProviderConfig`、`workspace/src/worktree/mod.rs`+2968 用 `WorktreeAutoGcSettings`；`shell`：`RemoteRequestEncoding`×7、`AuthProviderConfig`×5、`McpServerConfig`×2、`FileAccelerationConfig`×2 |
| **re-export 转发**（不是定义） | lib.rs +21~+25：`CampaignOverride`/`ConsentGate`/`ContextualHintsRemote`/`DisplayRefreshSettings`/`DoomLoopRecoverySettings`/`GoalRoleModel`/`LongReasoningReminderSettings`/`RemoteRequestEncoding`/`RemoteSettings`/`WorktreeAutoGcSettings`/`WorktreeKindMaxAge`/`deserialize_tolerant` ← 全部来自 `xai_grok_config` | 任何「`RemoteSettings` 定义在 config-types」的旧表述**均已成错** |

`RemoteSettings` 真实定义：`xai-grok-config/src/remote_settings.rs` · +279（184 个 pub 字段），含 `memory_v2: Option<MemoryV2Settings>`（`config/src/memory_v2.rs` · `MemoryV2Rollout`/`MemoryV2Settings`）、`sandbox_mode`（`deserialize_with = sandbox_mode::optional_sandbox_mode`）、`turn_transient_retry`/`uncharged_401_park`（`deserialize::optional_bool`，注释「malformed values must not fail the parse」）。

---

## 7. 失败路径与降级

| 场景 | 行为 | 锚点 |
|---|---|---|
| `/settings` 网络/5xx | 重试至 3 次 → `SettingsFetch::Retry`；`load_settings_blocking` 出 `FetchFailed` → `SettingsOutcome::failed()`（settings=None, attempted=true）→ 上层走 defaults 并 `record_degraded_start(FetchFailed)` | `settings_fetch.rs` +59/+102；`settings_get.rs` +95/+527；`shell/…/init.rs` +283/+294 |
| `/settings` **401** | `SettingsFetch::Rejected`（**不重试**，注释：「No remote policy will ever reach this leader」）→ 交 `OtelGate`；会话侧 `fetch_settings_self_healing_401` 先刷 token 再取一次（仅当 token 变了） | `settings_fetch.rs` +11~+17/+112；`shell/…/agent_ops.rs` +1619/+1641 |
| 等待超时 / 取消 | `SettingsWait::{TimedOut,Cancelled}` → `consume_wait` 返回 `None`；**owner 任务继续跑**（测试 `caller_timeout_does_not_drop_a_later_publish` 钉死） | `settings_get.rs` +139/+336；tests +645 |
| 无 tokio runtime | `warm_and_subscribe` 返回 `None` → `TimedOut`（「falling open」）；current-thread runtime 不阻塞 → `TimedOut` | `settings_get.rs` +189/+393~+415 |
| 缓存文件损坏/被篡改 | `ParseFailed`/`SignatureInvalid` → **`tracing::warn!`** 后当未命中；scope/version/stale → `debug`；文件缺失 → 静默 | `config/src/cache_file.rs` · `CacheLoadError::log` +25 |
| 缓存超 size cap | `read_capped` 返回 `None` → 当未命中（settings 1 MiB / models 4 MiB） | `cache_file.rs` +46 |
| 缓存被手写（旧版本/异 client） | `VersionMismatch`/`ScopeMismatch` 拒；测试 `hand_written_file_with_stale_version_or_client_misses` | `settings_cache.rs` +222/+230；tests +139 |
| `grok_home` 是文件 | `write_atomic` 的 `create_dir_all` 失败向上报；测试 `write_into_a_grok_home_that_is_a_file_reports_the_failure` | `cache_file.rs` +112；tests +350 |
| 托管 fetch 验签失败 | `ApplyOutcome::SignatureRejected`：**不 persist、前一份可信策略存活**；`post_login_sync`/`run_setup` 把它当 **Failed 而非 NoChange**（「the gate may refuse next session」） | `store.rs` +334~+344；`supervisor.rs` +451/+626 |
| 托管 401/403 | `DeploymentKeyRejected`（DK 路）或 `TeamAuthRejected`（团队路），文案分开；`is_auth_rejection` 为真 ⇒ **不可重试**；DK 被拒时若有团队则回退 | `response.rs` +19/+80；`supervisor.rs` +127/+359 |
| 沙箱拒写托管文件 | 仅 deny 类才 park，下次 boot 沙箱前重放；fetch-disabled 或不可验签的 build **unread 直接删 stage**；stage 的 `key_fingerprint` 与当前 DK 不符也删（重新拉，不 rebinding）；`parked_at==0` 或早于 marker ⇒ 永不 apply | `store.rs` +377/+469~+519 |
| 登录态消失 / 换租户 | `clear_orphan`（best-effort，`auth.json` 读失败**保留**策略；`fail_closed` 已武装则不清）；`gate_snapshot_locked` 先 `purge_prior_tenant_locked` 再抬 rollback floor | `store.rs` +128/+228/+243 |
| 托管 gate 拒启 | `ManagedPolicyRefusal::{Compromised,Busy,LockUnavailable}`；`GATE_LOCK_WAIT=2s` 有界轮询（注释：**不用 `block_in_place`**，bootstrap 跑在 `LocalSet` 上会 panic）；`Err` 冒泡为 `BootstrapError::PolicyRefusal` | `managed_config/mod.rs` +29/+74~+115；`policy.rs` +7/+14；`shell/…/init.rs` +19/+134 |
| 时钟回拨 | marker 存 `rollback_floor` 高水位，静态校验用 `max(now, floor)`；**fetch 期验签不 clamp**（新鲜信封能治愈被抬高的 floor）；tick 失败**不**拒绝会话 | `config/src/managed_cache.rs` +33/+428；`response.rs` +223；`store.rs` +259 |
| `auth.json` 读错误 | 不当作「未登录」：`team_principal_signed_in` 的 `Err` 让 `managed_principal_present()` 返回 true（防换文件逃策略）；`credential_present(TeamOauth)` 用 `unwrap_or(true)` | `store.rs` +118/+554/+609 |

---

## 8. 测试矩阵（crate 内 50 个 `#[test]`/`#[tokio::test]`）

| 文件 | 数量 | 覆盖点 |
|---|---|---|
| `managed_config/tests.rs` | 19 | gate/lock/apply/purge/staging/transport 映射/cert 文案/served principal/claim 绑定/auth_mode 分类/overlay 免疫（见 §4 名单） |
| `settings_cache_tests.rs` | 16 | 命中免 fetch(+38)、延迟写(+58)、disabled(+73)、失败不落盘(+87)、identity/origin/TTL miss(+97)、手写条目(+139)、篡改(+159)、不可读时覆盖(+177)、不回退到旧值(+228)、轮换 key 仍可读(+261)、清 live-fetch-only 字段(+281)、损坏文件(+299)、size cap(+316)、未来时间(+338)、grok_home 是文件(+350)、0600(+364) |
| `settings_get.rs` 内联 | 3 | ineligible 不起 owner(+613)、超时不丢后到 publish(+645)、cancel 只丢观察(+695)；均 `#[serial(startup_settings)]` |
| `settings_refresh.rs` 内联 | 3 | 5 并发合流 1 次 leader fetch(+146)、leader 被丢后 follower 真的重取(+180)、连续丢 3 次后返回 `None` 而非 Retry(+218)；均 `flavor="current_thread"` |
| `cached_config_tests.rs` | 3 | 只用自己 campaigns 指向的 endpoint 的条目(+59)、**stale 条目只能关 vendor hooks**(+170)、已登录无条目 ⇒ `Unavailable`(+202) |
| `remote_settings/backend.rs` 内联 | 1 | 四态提交门：只有 `CacheAndServe` 落盘、`ServeInMemory` 供而不写(+173) |
| `remote_settings/prefetch_tests.rs` | 1 | fetch 后策略被关 ⇒ 丢弃且不写(+18) |
| `remote_settings/validation_tests.rs` | 1 | campaign 成员决定 preferred 翻转(+5) |
| `settings_endpoint_tests.rs` | 1 | identity 抗 token 轮换、其余任一输入变则变(+3) |
| `settings_fetch_tests.rs` | 1 | axum 真服务，状态码 → `Fetched/Rejected/Retry` 映射(+41) |
| `managed_config/response_tests.rs` | 1 | 先选受信 key、否则取首个(+3) |

**覆盖缺口（实测）**：`remote_settings/cache.rs`、`remote_settings/metrics.rs`、`managed_config/store.rs`、`managed_config/supervisor.rs` 在本 crate 内**无独立 tests 文件**（store/supervisor 的行为由 `managed_config/tests.rs` 覆盖；cache/metrics 的模型侧测试留在 `shell/src/agent/remote_config/manager/tests.rs`，2,669 行）。

---

## 9. 旧文档改写对照表

| 旧文档写的路径/归属 | 现状 | 语义是否仍成立 | 建议改写 |
|---|---|---|---|
| `xai-grok-shell/src/managed_config/{mod,policy,response,store,supervisor}.rs`（第 06/12 篇「托管配置逻辑在 shell」） | 移到 `xai-grok-cloud-config/src/managed_config/*` | **成立**；`shell/src/lib.rs` +41 有 `pub use xai_grok_cloud_config::managed_config`，故 `crate::managed_config::*` 符号仍可解析 | 归属改 cloud-config，正文保留「shell 通过 re-export 暴露」一句 |
| `shell/src/agent/remote_config/cache.rs` | `cloud-config/src/remote_settings/cache.rs` | 成立，但 **`ModelsCache<E>` 变泛型** | 补泛型与「shell 用 `ModelEntry` 实例化」的类型别名说明 |
| `shell/src/agent/remote_config/metrics.rs` | `cloud-config/src/remote_settings/metrics.rs` | **逐字成立**（仅可见性 `pub(crate)`→`pub`） | 只换路径 |
| `shell/src/agent/remote_config/settings_refresh.rs` | `cloud-config/src/settings_refresh.rs` | 成立 | 换路径；可补 `MAX_DROPPED_LEADER_REATTEMPTS=3` |
| `shell/src/agent/remote_config/cache_file.rs` | **`xai-grok-config/src/cache_file.rs`**（注意：不是 cloud-config） | 成立 | 换 crate；这是两个缓存共用的底座 |
| `shell/src/agent/remote_config/scope.rs` | **已删除** → `cloud-config/src/commit.rs` + `remote_settings/validation.rs` + `settings_endpoint.rs` | 拆分后逐条等价；`evaluate_models_commit` **多了 `models_fetch_enabled: bool` 参数** | 删除该条目，改写为三处新家并标参数变化 |
| `shell/src/agent/remote_config/settings_cache.rs` | **已删除** → `cloud-config/src/settings_cache.rs`（633→361 行） | HMAC key/TTL/size/scope 校验**逐字不变**；新增 `SettingsCacheMode`/`write_through`/`load_for_any_client`/`Freshness` | 换路径 + 补新 API |
| `shell/src/agent/remote_config/settings_get.rs` 描述为「settings 拉取实现」 | 现在是 72 行**适配器**，实现在 `cloud-config/src/settings_get.rs`（717 行） | 部分成立 | 明确「适配器只注入 `policy_repair_pending`」；这是文档里最容易写错的一层 |
| 第 06 篇 §299「`Struct：RemoteSettings` 在 `xai-grok-config-types · lib.rs +0~+5`」 | **错**：定义在 `xai-grok-config/src/remote_settings.rs` +279；config-types 只在 lib.rs +21~+25 re-export | 不成立 | 归属改 `xai-grok-config`，并说明 config-types 充当转发面 |
| 第 06 篇层序（+511 行那条 8 层列表） | `config/src/lib.rs` 头注释给的是**官方 6 层**（overlay 与 campaigns 不在其内） | 部分成立 | 以 `config/src/lib.rs` +5~+15 为准引用，并注明 `remote_fetch` 是**反向着例**（`remote_fetch.rs` +21） |
| 第 12 篇 `/v1/settings` 措辞 | 代码拼的是 `{proxy_url}/settings`（`settings_fetch.rs` +47）；`/v1/models` 侧注释也混用 | 未确认服务端真实路径（代码内注释与实现自相矛盾） | 记为「代码走 `{proxy}/settings`；旧注释仍写 `/v1/settings`」，不下结论 |
| 第 12 篇「更新/遥测」段（`deployment_id`、`refresh_deployment_config`） | `deployment_id` 解析现在来自 `cloud-config::managed_config::resolve_deployment_id`（store +562），被 shell 6 处 + `update` 注入 | 成立 | 补注入点归属；`auto_update.rs` +2779~+2794 走 `has_principal/is_fetch_enabled/clear_orphan/sync` |
| 第 09 篇 模型循环（若提到 scope/settings_cache） | 现由 `cloud-config::remote_settings::*` 提供，`shell/…/remote_config.rs` 做类型别名与 re-export | 成立 | 换路径 |
| `install_allowed`/`startup_profile`/`managed_policy_gate`/`LaunchProfile` 等若标注为 shell 类型 | 全部来自 `cloud-config::managed_config`；`startup_profile` 只**单向升级** Personal→Managed（+48~+65） | 成立 | 换路径 + 保留「升级不可逆」这一关键语义 |

---

## 10. 未确认 / 需主线注意

1. **`load_config_with_cached_remote` 无生产调用点**：全仓 grep 只命中自身定义与 `cached_config_tests.rs`；依赖它的 `CachedRemote::NotApplicable/Entry/Unavailable` 三态在 `config/src/effective_config.rs` +291 定义。它服务的是「从不拉取远端 settings 的进程读别人缓存的条目」这条路径（如 diag/子命令），**本仓当前无调用方** —— 不要在文档里写成主链路。
2. `xai-grok-config-types` 的 `+1,712 行` 无法归因到本轮：`git log` 是 squash 的 monorepo sync，`97f190f6..2bdd1d6a` 对 config-types 的净变化只有 `flags.rs −101`、`lib.rs −1`、`trust.rs −376`（共 3 文件）。memory.rs 的 1,476 行在更早同步已存在。**按「零覆盖」补文档可以，但不要写成「本轮新增 1,712 行」。**
3. `xai-grok-cloud-config` 内**没有 OTEL 计数器**，只有 `unified_log::emit`（metrics.rs）与 `InstrumentationTimer`（settings_get.rs +487、supervisor.rs +530/+543）。「指标」一词要区分这两类。
4. 服务端契约（`/settings` 响应字段、`/deployment/config` 的 `signatures` 生成方、fail_closed 语义）不在本仓，仅 `prod/mc/cli-chat-proxy-types` 提供 `fail_closed_flag_status`（`response.rs` +147）。
