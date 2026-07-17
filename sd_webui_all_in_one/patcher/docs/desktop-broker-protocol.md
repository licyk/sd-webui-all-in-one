# 桌面运行时代理协议 v2

桌面代理是由 Rust 桌面应用程序管理的第二种 Hotpatch 运行时传输方式。
它不会取代旧版 TCP JSONL 传输。进程通过以下变量选择且仅选择一种实现：

```text
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRANSPORT_MODE
```

- 缺失、为空或显式设置为 `legacy` 时，选择 `RuntimeClient` 和现有的
  TCP JSONL 运行时宿主。
- 显式设置为 `desktop_broker` 时，选择 `DesktopBrokerClient`。
- 值区分大小写且不会去除首尾空白。不接受任何别名。
- 桌面模式初始化或身份验证失败时，绝不会回退到旧版宿主。

该选择仅作用于当前进程。旧版和桌面代理解释器可以同时运行，且不会共享
Python 客户端状态。

## 启动环境

Rust 会向选中的 WebUI 任务提供以下六个变量：

```text
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRANSPORT_MODE=desktop_broker
SD_WEBUI_ALL_IN_ONE_RUNTIME_BROKER_URL=http://127.0.0.1:<port>
SD_WEBUI_ALL_IN_ONE_RUNTIME_SESSION_ID=<session-id>
SD_WEBUI_ALL_IN_ONE_RUNTIME_TOKEN=<unpredictable-session-token>
SD_WEBUI_ALL_IN_ONE_RUNTIME_IDENTITY=<runtime-identity>
SD_WEBUI_ALL_IN_ONE_RUNTIME_PROTOCOL_VERSION=2
```

URL 必须是使用 `http` 的字面量回环地址，必须显式指定端口，且不能包含用户信息、
路径、查询参数或片段。会话 ID、令牌和运行时标识均不能为空，长度上限为 256 个字符。
只有在显式选择桌面模式后才会读取这些变量。桌面客户端既不要求也不使用旧版的
`HOST`、`PORT` 和 `TOKEN` 变量。

标准库 HTTP opener 已禁用代理处理，因此会话凭据不会跟随环境中的 `HTTP_PROXY`
设置，连接代理时也不需要进行主机名查询。协议 v2 不定义重定向。客户端使用会产生
终止性 `redirect_rejected` 故障的处理器替换 urllib 的重定向处理器，并且该故障发生在
创建任何重定向请求之前，因此 `Authorization` 和会话身份标头不会被转发到
`Location` 目标。

桌面启动流程还会提供 `CONFIG_SOURCE=env` 和 `CONFIG_JSON`。本协议不包含通过旧版
运行时 API 获取远程配置的功能。

## 身份验证与身份标识

每个请求都会通过标头携带完整的会话绑定信息：

```http
Authorization: Bearer <session-token>
X-Runtime-Protocol-Version: 2
X-Runtime-Session-Id: <session-id>
X-Runtime-Identity: <runtime-identity>
```

Rust 代理会在读取或修改会话状态前验证全部四个值。HTTP 401/403 被归类为
`authentication_rejected`；HTTP 409/426 被归类为 `protocol_mismatch`。客户端会
保持桌面模式，并以有界退避策略重试；它绝不会尝试建立旧版连接。

时间戳为有限的非负 Unix 纪元秒数。字段名使用 camelCase。请求体和响应体均为
JSON 对象。

协议 v2 将尚未解决的 `activeDiagnostic` 与已确认的诊断历史分开。历史故障不会仅仅
因为是最新保留的条目就变为活动故障。`/v1/runtime/*` 路由命名空间保持不变；必需的
环境变量值和请求标头会显式选择协议版本 2。版本 1 和未知版本会通过现有的显式协议
不匹配响应失败。

## 端点

### 连接

```http
POST /v1/runtime/connect
{}
```

响应：

```json
{"status":"connected","acknowledgedSequence":0,"acknowledgedDiagnosticSequence":0}
```

确认序列号使重新连接的客户端可以丢弃 Rust 已接收的事件和诊断历史。从
degraded/disconnected 健康状态恢复的会话可能返回 `status: "reconnecting"`；这同样
代表身份验证连接成功。成功通过身份验证的连接会清除 Python 客户端的活动传输诊断，
但不会清除尚未确认的历史条目。工作线程会恢复重放，并将其本地传输报告为已连接，
随后下一次心跳会让 Rust 完成其权威健康状态转换。

### 事件

```http
POST /v1/runtime/events
```

```json
{
  "events": [
    {
      "sequence": 1,
      "eventType": "browser.open",
      "payload": {"url": "http://127.0.0.1:8188"},
      "createdAt": 1780000000.25
    }
  ]
}
```

响应：

```json
{"acknowledgedSequence":1}
```

序列号从 1 开始。Rust 会确认已连续接收的最高序列号。小于或等于该值的事件属于重复
重试：它们不会创建重复的保留状态，但仍会被确认。如果批次中存在序列缺口，Rust 会
返回 HTTP 200，且最高连续 `acknowledgedSequence` 保持不变；缺口处及其后的任何事件
都不会修改代理状态。客户端会保留其未确认前缀，并从上次确认位置开始重试。未知事件
类型会占用其连续序列号，并生成有界的 `unknown_event_type` 诊断，而不是带类型的事件
状态。

`browser.open` 要求载荷为包含字符串 `url` 的对象。运行时身份由经过身份验证的请求
绑定携带，不会信任事件载荷中的身份信息。

现有功能生产方继续使用其旧版公共事件名称。只有桌面客户端会将 `log.*` 映射为
`runtime.log`、将 `error.*` 映射为 `runtime.error`、将 `progress.*` 映射为
`runtime.progress`；它会把原始名称原样添加为保留载荷字段 `sourceEventType`，且不会
修改调用方的对象。因此，Rust 可以保留这些规范事件族，而无需更改旧版 TCP 消息。
`browser.open` 和未知事件类型不会被重写。

### 心跳

```http
POST /v1/runtime/heartbeat
```

```json
{
  "transportStatus": "connected",
  "lastAcknowledgedSequence": 1,
  "queuedEventCount": 0,
  "activeDiagnostic": null,
  "diagnostics": [
    {
      "sequence": 1,
      "code": "connection_failed",
      "message": "[WinError 10053] software caused connection abort",
      "createdAt": 1780000001.0,
      "occurrences": 1
    }
  ],
  "diagnosticsStartSequence": 1,
  "diagnosticsTruncated": false
}
```

响应：

```json
{
  "status": "connected",
  "acknowledgedSequence": 1,
  "acknowledgedDiagnosticSequence": 1
}
```

`activeDiagnostic` 可以是 `null`，也可以是当前尚未解决的传输故障周期所对应的完整诊断
信封 `{sequence, code, message, createdAt, occurrences}`。它会独立于历史记录进行验证。
成功重新连接会将其设置为 `null`；成功上传事件或结果以及轮询命令本身都不会推断传输
已经恢复。

`diagnostics` 只包含最早的未确认历史前缀，绝不会重复提供最新本地条目的快照。诊断
序列号从 1 开始，并在每个运行时会话中单调递增。Rust 只确认已连续接收的最高序列号。
重复序列具有幂等性；重试可以携带更大的 `occurrences`，Rust 会取最大值进行合并，而
不会追加另一条历史记录。未声明的缺口会使确认序列号保持不变。

`diagnosticsStartSequence` 是本地可用历史记录中的第一个序列号；队列为空时，则为客户端
的下一个诊断序列号。如果有界的本地保留策略淘汰了未确认条目，`diagnosticsTruncated`
会变为 `true` 并持续可见。Rust 会记录截断，并可以将其确认基线调整为
`diagnosticsStartSequence - 1`；这是普通无缺口推进规则的唯一例外。心跳响应丢失时，
Python 仍会保留该前缀，因此相同序列可以安全地重放。

Rust 负责维护权威的心跳接收时间、活动会话健康状态和保留的调试历史。无效的历史诊断
信封不会修改活动传输状态，无效的活动诊断信封也不会导入历史记录。经过身份验证的心跳
响应可以报告 `connected`、`degraded`、`reconnecting` 或 `disconnected`；Python 会
接受每一种非终止代理状态，同时保留自身的重新连接工作流。

### 命令

```http
GET /v1/runtime/commands?afterSequence=0&waitMs=100
```

响应：

```json
{
  "commands": [
    {
      "commandId": "command-uuid",
      "sequence": 1,
      "commandType": "config.apply",
      "payload": {"config": {}},
      "createdAt": 1780000000.0,
      "deadline": 1780000030.0
    }
  ]
}
```

Python 客户端只接受序列号严格递增的命令；允许存在缺口，因为 Rust 可能在交付前让更早
的命令过期。每个命令 ID 最多执行一次，客户端会缓存其结果；当 Rust 重新交付 ID 和
内容相同的命令时，客户端会重新将缓存结果加入队列。过期命令会返回
`command_expired`，且不会调用处理器。目前桌面命令接口仅包含 `config.apply`；它会使用
选中的桌面事件接收器调用 `services.apply_config()`。未知命令返回 `unknown_command`。
旧版模式下，旧版 `services.*` 请求仍可通过 `ServiceControlChannel` 使用。

### 结果

```http
POST /v1/runtime/results
```

成功结果：

```json
{
  "results": [
    {
      "commandId": "command-uuid",
      "ok": true,
      "payload": {"applyResult": {"applied": [], "warnings": [], "errors": []}},
      "completedAt": 1780000001.0
    }
  ]
}
```

失败结果使用 `ok: false`，并包含一个具有稳定 `code` 和 `message` 字段的 `error` 对象。
Rust 返回：

```json
{"acceptedCommandIds":["command-uuid"]}
```

已接受的结果会从重放队列中移除。在 Rust 端，重复交付结果具有幂等性。

## Python 限制与重试策略

桌面客户端只使用 Python 标准库中的 HTTP 和线程 API。所有网络操作均由一个守护工作
线程执行，绝不会由被热补丁的目标执行。

| 状态 | 限制 |
| --- | ---: |
| 未确认的出站事件，硬性上限 | 256 个事件 |
| 普通事件准入 | 240 个排队事件 |
| 为 `browser.open` 预留的容量 | 16 个事件 |
| 单个事件载荷 | 16 KiB 编码后的 JSON |
| 单次事件上传 | 32 个事件 / 256 KiB |
| HTTP 响应 | 256 KiB |
| 单个 Rust 命令响应 | 32 个命令 / 256 KiB |
| 未确认的诊断历史 | 64 个条目 / 128 KiB |
| 单个诊断代码 | 128 字节 UTF-8 |
| 单条诊断消息 | 2 KiB UTF-8 |
| 单个心跳诊断批次 | 8 个条目 / 64 KiB |
| 待处理的命令结果 | 128 个结果 |
| 单个命令结果载荷 | 64 KiB 编码后的 JSON |
| 已完成命令 ID 历史 | 256 个命令 |
| 单个 Python 结果批次 | 32 个条目 / 256 KiB |

事件入队操作会在锁内创建 JSON 兼容载荷的快照，然后直接返回，不会执行 HTTP 或重新
连接操作。仅当排队事件少于 240 个时，日志、错误、进度及其他所有普通事件才会被接收。
剩余的 16 个槽位专门为经过严格规范化的 `browser.open` 事件保留。即使队列中只有浏览器
事件，仍受 256 个事件的硬性上限约束。

普通事件准入失败会记录确切的诊断代码 `ordinary_event_capacity_exhausted`，消息为
`ordinary event queue reached its 240-event admission limit; 16 slots are reserved for browser.open`。
队列完全耗尽时会拒绝浏览器事件，并记录 `critical_event_capacity_exhausted`，消息为
`outbound event queue reached its 256-event hard limit; browser.open was rejected`。

两个拒绝路径都发生在分配序列号之前。客户端绝不会淘汰已分配序列号但尚未确认的事件，
因此已接收的普通事件和浏览器事件共享同一条连续的线上序列。上传分批、确认、重新连接
重放以及最终刷新都会继续处理这一个有序队列。

连接失败会保留尚未确认的事件，并使状态进入 `disconnected` 或 `reconnecting`。重试从
100 毫秒开始，每次翻倍，最大为 5 秒。连接期间每 5 秒发送一次心跳；命令长轮询每个
请求最多等待 100 毫秒。进程关闭时默认请求一次最长 500 毫秒的最终事件/结果刷新。
即使操作系统请求卡住，`close()` 也不会无限等待。

传输故障会创建或更新一个活动诊断周期和一条带序列号的历史记录。相同的重试会增加有界
的 `occurrences`，而不是为每次尝试分配序列号。不同的代码/消息或恢复后再次发生的故障
会开始新的序列。`status()` 会公开当前的 `activeDiagnostic`、
`unacknowledgedDiagnostics`、其数量和编码后的字节数、
`acknowledgedDiagnosticSequence`、`diagnosticsStartSequence`，以及具有粘性的
`diagnosticsTruncated` 元数据。已确认的条目会离开 Python 的出站重放队列；Rust 有界
保留的会话历史仍作为调试记录。如果某个尚未解决的相同故障在其历史信封已被确认后重复
发生，只有已分离的活动摘要中的 `occurrences` 会继续增加。协议 v2 不会修改或重放已经
确认的历史信封；恢复后再次发生的故障周期会获得新的序列号。

## 浏览器行为

浏览器模式仍与传输选择相互独立：

- `host`：将一个 `browser.open` 事件加入队列，并在本地阻止浏览器打开。
- `suppress`：不发送事件，直接在本地阻止浏览器打开。
- `passthrough`：调用原始的标准库浏览器实现。

在桌面 `host` 模式下，`webbrowser.open()` 不会发起 HTTP 请求，也不会等待任何工作线程
状态。即使代理断开连接、包含 256 个事件的队列已完全填满、凭据被拒绝或协议不匹配，
也绝不会回退到操作系统浏览器。相关故障会改为出现在有界传输诊断中。
