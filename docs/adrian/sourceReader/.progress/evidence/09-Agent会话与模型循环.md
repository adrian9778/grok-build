# 09-Agent会话与模型循环.md 同步证据

## 主题：memory capture 捕获取消回合 + turn_start 锚点 + UsageTurn ack

### 1. is_capturable_turn_result（重命名）
- 定义：`memory_capture.rs:261` `pub(super) fn is_capturable_turn_result(result: &PromptTurnResult) -> bool`
- 前：`is_successful_query_loop`，只匹配 `Completed + EndTurn`
- 后：匹配 `Ok(PromptTurnOk{completion_kind: Completed, stop_reason: EndTurn, ..})` 或 `Ok(PromptTurnOk{completion_kind: Cancelled{..}, ..})`
- 注释：「Cancelled turns count too: their partial work stays in the durable log.」
- 调用者：`run_loop.rs:2343`

### 2. enqueue_v2_turn_capture（重命名）
- 定义：`memory_capture.rs:510` `pub(super) async fn enqueue_v2_turn_capture(self: &Arc<Self>, source_prompt_index: usize)`
- 前：`enqueue_v2_completed_turn`
- 调用者：`run_loop.rs:2365`（正常完成路径）、`cancel.rs:975`（取消路径）

### 3. is_capturable_front（新增）
- 定义：`memory_capture.rs:498` `pub(super) fn is_capturable_front(state: &State, prompt_id: &str) -> bool`
- 条件：`front_message_committed` + front input 的 `prompt_id` 匹配 + `queue_meta.is_some()` + `!is_synthetic()` + 非 slash + 非 bash 命令
- 注释：「Only a committed human prompt records the log item tool_context.prompt_index names.」
- 调用者：`run_loop.rs:2345`、`cancel.rs:645`

### 4. record_turn_start（新增）
- 定义：`xai-chat-state/src/handle.rs:250` `pub fn record_turn_start(&self, timestamp_ms: i64)`
- 发送 `ChatStateCommand::RecordTurnStart { timestamp_ms }`
- 调用者：`turn.rs:529`（handle_prompt 入口）、`turn.rs:2629`（process_conversation_turn_with_recovery 入口）
- 测试：`turn_start_anchor_tests.rs` 验证 host turn 覆盖过期锚点（11 小时前的旧时间戳被 /session-info 覆盖）

### 5. UsageTurn ack（新增 respond_to）
- 定义：`persistence.rs:316` `PersistenceMsg::UsageTurn { turn_number, live, respond_to: oneshot::Sender<io::Result<()>> }`
- 注释：「Persist this turn's session usage, then ack. Callers that publish turn-end (and x.ai/session/state) wait so usage.json is visible before the turn resolves.」
- 发送方：`turn.rs:2447-2454`（`persist_live_usage` 创建 oneshot、发送 UsageTurn、await ack）
- 消费方：`persistence.rs:2486-2495`（actor match arm：写 usage.json 后 send result）

### 6. captures_cancelled_turn（cancel 路径新增）
- 计算：`cancel.rs:641` `kind != Teardown && rewound_input.is_none() && cancelled_prompt_id.is_some_and(|pid| is_capturable_front(&state, pid))`
- 注释：「Read before the front drains; teardown ends the session and rewind drops the turn.」
- 使用：`cancel.rs:973` `if captures_cancelled_turn { session.enqueue_v2_turn_capture(source_prompt_index).await }`
- 注释：「The aborted task skips the completion arm; no next turn starts before this returns.」

### 7. run_loop.rs 中的 v2 capture 决策（更新后）
- `run_loop.rs:2342-2365`：
  1. `is_capturable_turn_result(&result)` → 判断结果是否可捕获
  2. `is_capturable_front(&state, &prompt_id)` → 判断 front 是否可捕获
  3. 两者都 true → 读 `prompt_index`
  4. `handle_completion` 后调 `enqueue_v2_turn_capture`

### 8. commands.rs FlushMemory 注释更新
- `commands.rs:472` `FlushMemory` 注释从「Capture every completed turn now」改为「Capture every finished or stopped turn now」

### 9. handle_prompt 中的 record_turn_start
- `turn.rs:528-529`：在 `handle_prompt_start` 之后、`active_skill` 清除之前调用
- `turn.rs:2628-2629`：在 `process_conversation_turn_with_recovery` 入口处也调用
