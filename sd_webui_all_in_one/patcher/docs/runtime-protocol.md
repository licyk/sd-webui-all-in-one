# Runtime 通信协议

`sd_webui_all_in_one_hotpatcher.runtime` 提供补丁系统和外部宿主之间的控制通道。当前协议是 TCP + JSON Lines，不兼容原系统的 Windows named pipe + GUID 二进制协议。

## 设计目标

- 跨平台。
- 宿主不限语言。
- 可手写、可抓包、易调试。
- 不把 runtime 绑死在某个 GUI、启动器或引擎上。

## 传输层

默认传输是 TCP。

连接参数：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST=127.0.0.1
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT=8765
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN=optional-secret
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT=5
```

代码入口：

```python
from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient

client = RuntimeClient.connect("127.0.0.1", 8765, token="optional-secret")
```

环境变量入口：

```python
client = RuntimeClient.connect_from_env()
```

## JSON Lines

每条消息是一行 UTF-8 JSON：

```text
{"type":"hello","version":1}
{"type":"progress.update","payload":{"id":1,"value":50}}
```

编码由 `runtime.protocol.encode_message()` 完成：

- `ensure_ascii=False`
- 紧凑 separators
- 每条消息末尾追加 `\n`

解码由 `decode_message()` 完成，要求每条消息必须是 JSON object。

## Hello 握手

客户端 TCP 连接建立后立即发送 hello：

```json
{"type":"hello","version":1,"token":"optional-secret","features":["config","progress","browser","fileops","faults","audit","logs","services"]}
```

字段：

- `type`：固定为 `hello`
- `version`：当前为 `1`
- `token`：宿主用于鉴权或关联会话
- `features`：客户端支持能力

当前客户端不会等待 hello ack。宿主可以记录 hello，也可以在 token 不合法时直接断开连接。

## 请求/响应

请求带 `id`：

```json
{"id":"abc","type":"config.get","payload":{}}
```

成功响应：

```json
{"id":"abc","ok":true,"payload":{"config":{"enabled":true}}}
```

失败响应：

```json
{"id":"abc","ok":false,"error":{"code":"cancelled","message":"user cancelled"}}
```

`JsonlTcpTransport.request()` 会：

1. 生成 message id。
2. 发送请求。
3. 持有 `_request_lock` 等待响应。
4. 读取 JSONL，直到找到同 id 响应。
5. `ok=true` 返回 payload。
6. `ok=false` 抛 `RuntimeRequestError`。

当前实现是同步单请求等待模型，不支持同一连接上并发多个 request。这是刻意的：实现小，宿主也容易写。事件仍可 best-effort 发送。

## 事件

事件不带 `id`，客户端发送后不等待响应：

```json
{"type":"progress.update","payload":{"id":123,"value":50}}
```

`RuntimeClient.event()` 会捕获发送异常并调用 `capture_exception()`。所以事件适合非关键路径，例如：

- progress
- browser.open
- audit.event
- error.exception
- log.record / log.stream / log.dropped

文件操作和配置拉取不应该用事件，因为它们需要知道宿主是否接受。

## 断线和超时

`JsonlTcpTransport.connect()` 使用 `socket.create_connection` 的 timeout。

`request(..., timeout=...)` 可以临时覆盖 socket timeout。超时、断开、空读取会抛异常。

`RuntimeClient.connect_from_env(required=False)` 连接失败会捕获异常并返回 `None`。`required=True` 时抛出原异常。

## 配置协议

请求：

```json
{"id":"...","type":"config.get","payload":{}}
```

推荐响应：

```json
{"id":"...","ok":true,"payload":{"config":{"enabled":true}}}
```

`RuntimeClient.get_config()` 会优先读取 payload 的 `config` 字段；如果没有 `config`，就把整个 payload 当配置。

配置来源：

- `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE=env`
- `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE=file`
- `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE=remote`
- `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE=auto`

`file` 来源读取 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE` 指向的 UTF-8 JSON 文件，文件内容必须是对象。

`auto` 默认优先 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON`，没有 env JSON 时读取 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE`，再没有时尝试远程。如果没有 host/port，返回空配置。

## Progress 事件

创建：

```json
{"type":"progress.create","payload":{"id":123,"name":"download","max":100,"indeterminate":false}}
```

更新：

```json
{"type":"progress.update","payload":{"id":123,"value":50}}
```

移除：

```json
{"type":"progress.remove","payload":{"id":123}}
```

`Progress` 使用 `id(self)` 作为 progress id。宿主只需要把它当成进程内临时 id。

## Browser 事件

```json
{"type":"browser.open","payload":{"url":"https://example.com"}}
```

`ManagedBrowser.open()` 只发送事件。`patch_webbrowser(client)` 会 patch 标准库 `webbrowser.open`，使其转发到宿主并返回 `True`。

## File operation 请求

文件操作需要响应。

开始：

```json
{"id":"...","type":"file.operation.begin","payload":{"operation_id":"..."}}
```

删除：

```json
{"id":"...","type":"file.delete","payload":{"operation_id":"...","path":"/tmp/example"}}
```

执行：

```json
{"id":"...","type":"file.operation.perform","payload":{"operation_id":"..."}}
```

结束：

```json
{"id":"...","type":"file.operation.end","payload":{"operation_id":"..."}}
```

如果宿主返回：

```json
{"id":"...","ok":false,"error":{"code":"cancelled","message":"user cancelled"}}
```

客户端会把 `RuntimeRequestError(code="cancelled")` 转成 `UserCanceledException`。

## Fault raw channel

`runtime.faults.install_faulthandler(client)` 会打开第二条 TCP 连接。

第一行仍然是 JSONL：

```json
{"type":"channel.open","channel":"fault","token":"optional-secret"}
```

之后这条连接变成 raw byte stream，交给 Python `faulthandler.enable(file=...)`。fatal crash 时，faulthandler 会直接向这条连接写栈信息。

宿主实现要注意：收到 `channel.open` 后，不要再按 JSONL 解析后续内容。

## Services 控制通道

`services.install_service_control_channel(client)` 会打开第二条 TCP JSONL 连接, 第一行是：

```json
{"type":"channel.open","channel":"services","token":"optional-secret"}
```

这条连接后续仍然保持 JSONL。宿主可以发送 `services.catalog.get`、`services.defaults.get`、`services.config.normalize`、`services.config.load`、`services.config.save`、`services.config.apply` 请求。客户端返回固定 ok/error 响应, 如果请求带 `id`, 响应也会带同一个 `id`。

## Audit 事件

```json
{"type":"audit.event","payload":{"event":"compile","args":[...]}}
```

`install_audit_hook(client, filters)` 按事件名过滤。

参数会被 `_json_safe()` 转换：

- 基础类型原样传。
- bytes 转 base64。
- code object 转 `{type,name,filename,strings}`。
- 其他对象转 `{type,repr}`。

Python audit hook 不能卸载，所以测试必须使用专用事件名，避免污染全局流程。

## Error 事件

普通 Python 异常通过 `runtime.errors` 上报：

```json
{"type":"error.exception","payload":{"type":"builtins.ValueError","message":"bad value","traceback":"..."}}
```

payload 包含：

- `type`
- `name`
- `message`
- `traceback`
- `frames`
- `process`

它和 fault channel 的区别：

- `error.exception`：普通 Python exception。
- `fault` channel：segfault、abort、fatal error 等 faulthandler 场景。

## Log 事件

日志采集通过 `runtime.logs.install_log_capture(client)` 启用，也可以设置：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGS=1
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGING=1
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_STREAMS=stdout,stderr
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_SUBPROCESS=safe
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_POLICY=bounded
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_MAX_CHARS=8192
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_QUEUE_SIZE=1000
```

Python `logging` 记录发送为 `log.record`：

```json
{"type":"log.record","payload":{"logger":"app","level":"WARNING","levelno":30,"message":"hello","created":1710000000.0,"pathname":"/app/main.py","lineno":10,"function":"run","thread":123,"process":456}}
```

`stdout`、`stderr` 和子进程输出发送为 `log.stream`：

```json
{"type":"log.stream","payload":{"stream":"stdout","text":"hello\n","pid":456,"source":"stream"}}
```

子进程输出会额外带 `subprocess`：

```json
{"type":"log.stream","payload":{"stream":"stderr","text":"child error\n","pid":456,"source":"subprocess","subprocess":{"pid":789,"args":["python","child.py"]}}}
```

队列满时发送 `log.dropped`：

```json
{"type":"log.dropped","payload":{"count":12,"reason":"queue_full"}}
```

策略：

- `bounded` 是默认值，会限制单条字符串长度和队列大小，超长 payload 带 `truncated=true`。
- `raw` 原样发送，不截断文本，适合调试但要由调用方承担体积和敏感信息风险。
- 默认排除 `sd_webui_all_in_one_hotpatcher` logger，避免 runtime 自身日志递归。可用 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGER_INCLUDE` / `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGER_EXCLUDE` 设置逗号分隔前缀。

子进程模式：

- `safe` 只捕获显式 `PIPE` / `capture_output=True` 后经 `communicate()` 返回的输出，不改变继承父进程 stdout/stderr 的子进程。
- `force` 会把未指定 stdout/stderr 的 `Popen` 改成 `PIPE`，后台读取、写回父进程原 stream，并发送 `log.stream`。
- v1 不 patch `asyncio.create_subprocess_exec/shell`。

如果同时启用 logging handler 和 stderr tee，同一条 logging 可能同时出现 `log.record` 和 `log.stream`。这属于预期行为，宿主可以按 `source` 或 logger 信息去重。

## 宿主最小实现

宿主伪代码：

```python
line = conn.readline()
hello = json.loads(line)

for line in conn:
    msg = json.loads(line)
    if "id" not in msg:
        handle_event(msg)
        continue

    try:
        payload = handle_request(msg["type"], msg.get("payload", {}))
        reply = {"id": msg["id"], "ok": True, "payload": payload}
    except UserCancelled:
        reply = {"id": msg["id"], "ok": False, "error": {"code": "cancelled"}}

    conn.write(json.dumps(reply) + "\n")
```

完整可运行示例在 `src/examples/runtime_host.py`。
