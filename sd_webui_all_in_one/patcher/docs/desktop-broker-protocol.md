# Desktop runtime broker protocol v2

The desktop broker is a second Hotpatch runtime transport owned by the Rust
desktop application. It does not replace the legacy TCP JSONL transport.
Processes choose exactly one implementation with:

```text
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRANSPORT_MODE
```

- Missing, empty, or explicit `legacy` selects `RuntimeClient` and the existing
  TCP JSONL runtime host.
- Explicit `desktop_broker` selects `DesktopBrokerClient`.
- Values are case-sensitive and are not trimmed. No aliases are accepted.
- A desktop initialization or authentication failure never falls back to the
  legacy host.

The selection is process-local. Legacy and desktop-broker interpreters can run
at the same time without sharing Python client state.

## Launch environment

Rust supplies all six variables to the selected WebUI task:

```text
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRANSPORT_MODE=desktop_broker
SD_WEBUI_ALL_IN_ONE_RUNTIME_BROKER_URL=http://127.0.0.1:<port>
SD_WEBUI_ALL_IN_ONE_RUNTIME_SESSION_ID=<session-id>
SD_WEBUI_ALL_IN_ONE_RUNTIME_TOKEN=<unpredictable-session-token>
SD_WEBUI_ALL_IN_ONE_RUNTIME_IDENTITY=<runtime-identity>
SD_WEBUI_ALL_IN_ONE_RUNTIME_PROTOCOL_VERSION=2
```

The URL must be an `http` literal loopback origin with an explicit port and no user
information, path, query, or fragment. Session IDs, tokens, and runtime
identities are non-empty and bounded to 256 characters. These variables are
read only after explicit desktop selection. Legacy `HOST`, `PORT`, and `TOKEN`
variables are neither required nor used by the desktop client.

The standard-library HTTP opener has proxy handling disabled, so session
credentials cannot follow ambient `HTTP_PROXY` settings and no hostname lookup
is needed for the broker connection. Protocol v2 defines no redirects. The
client replaces urllib's redirect handler with a terminal `redirect_rejected`
failure before any redirected request is created, so `Authorization` and
session identity headers cannot be forwarded to a `Location` target.

Desktop launch also supplies `CONFIG_SOURCE=env` and `CONFIG_JSON`. Remote
configuration over the legacy runtime API is not part of this protocol.

## Authentication and identity

Every request carries the complete session binding in headers:

```http
Authorization: Bearer <session-token>
X-Runtime-Protocol-Version: 2
X-Runtime-Session-Id: <session-id>
X-Runtime-Identity: <runtime-identity>
```

The Rust broker validates all four values before reading or mutating session
state. HTTP 401/403 is classified as `authentication_rejected`; HTTP 409/426 is
classified as `protocol_mismatch`. The client remains in desktop mode and
retries with bounded backoff; it never attempts a legacy connection.

Timestamps are finite, non-negative Unix epoch seconds. Field names are
camelCase. Request and response bodies are JSON objects.

Protocol v2 separates an unresolved `activeDiagnostic` from acknowledged
diagnostic history. A historical failure never becomes active merely because
it is the newest retained item. The `/v1/runtime/*` route namespace remains
unchanged; the required environment value and request header select protocol
version 2 explicitly. Version 1 and unknown versions fail with the existing
explicit protocol-mismatch response.

## Endpoints

### Connect

```http
POST /v1/runtime/connect
{}
```

Response:

```json
{"status":"connected","acknowledgedSequence":0,"acknowledgedDiagnosticSequence":0}
```

The acknowledgements let a reconnecting client discard events and diagnostic
history already accepted by Rust. A session recovering from
degraded/disconnected health may return `status: "reconnecting"`; that is also
a successful authenticated attach. The successful authenticated connect clears
the Python client's active transport diagnostic, but not unacknowledged
historical entries. The worker resumes replay and reports its local transport
as connected, then the next heartbeat lets Rust complete its authoritative
health transition.

### Events

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

Response:

```json
{"acknowledgedSequence":1}
```

Sequences start at 1. Rust acknowledges the highest contiguous accepted
sequence. Events at or below that value are duplicate retries: they do not
create duplicate retained state but remain acknowledged. If a batch contains a
gap, Rust returns HTTP 200 with the unchanged highest contiguous
`acknowledgedSequence`; no event at or after the gap mutates broker state. The
client keeps its unacknowledged prefix and retries from the last
acknowledgement. Unknown event types consume their contiguous sequence and
become bounded `unknown_event_type` diagnostics instead of typed event state.

`browser.open` requires an object payload with a string `url`. Runtime identity
is carried by the authenticated request binding, rather than trusted from the
event payload.

Existing feature producers keep their legacy public event names. Only the
desktop client maps `log.*` to `runtime.log`, `error.*` to `runtime.error`, and
`progress.*` to `runtime.progress`; it adds the exact original name as reserved
payload field `sourceEventType` without mutating the caller's object. Rust can
therefore retain those canonical event families without changing legacy TCP
messages. `browser.open` and unknown event types are not rewritten.

### Heartbeat

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

Response:

```json
{
  "status": "connected",
  "acknowledgedSequence": 1,
  "acknowledgedDiagnosticSequence": 1
}
```

`activeDiagnostic` is either `null` or the complete diagnostic envelope
`{sequence, code, message, createdAt, occurrences}` for the currently unresolved
transport failure episode. It is validated independently from history. A
successful reconnect sets it to `null`; successful event/result upload or
command polling does not infer recovery on its own.

`diagnostics` contains only the oldest unacknowledged history prefix, never a
repeated snapshot of the latest local entries. Diagnostic sequences start at 1
and are monotonic per runtime session. Rust acknowledges only the highest
contiguous accepted sequence. Duplicate sequences are idempotent; a retry may
carry a larger `occurrences`, which Rust merges using the maximum without
appending another history item. An undeclared gap leaves acknowledgement
unchanged.

`diagnosticsStartSequence` is the first locally available history sequence, or
the client's next diagnostic sequence when the queue is empty. If bounded local
retention evicts unacknowledged entries, `diagnosticsTruncated` becomes `true`
and remains observable. Rust records the truncation and may rebase its
acknowledgement baseline to `diagnosticsStartSequence - 1`; this is the only
exception to ordinary no-gap advancement. A lost heartbeat response leaves the
Python prefix queued, so the same sequences replay safely.

Rust owns the authoritative heartbeat receipt time, active session health, and
retained debug history. Invalid historical envelopes do not mutate active
transport state, and an invalid active envelope does not ingest history.
An authenticated heartbeat response may report `connected`, `degraded`,
`reconnecting`, or `disconnected`; Python accepts each nonterminal broker state
while preserving its own reconnect workflow.

### Commands

```http
GET /v1/runtime/commands?afterSequence=0&waitMs=100
```

Response:

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

The Python client accepts commands in strictly increasing sequence order; a gap
is allowed because Rust may expire an earlier command before delivery. It
executes a command ID at most once, caches its result, and requeues the cached
result when Rust redelivers the same ID and content. Expired commands return
`command_expired` without calling the handler. The current desktop command surface contains only
`config.apply`; it calls `services.apply_config()` with the selected desktop
event sink. Unknown commands return `unknown_command`. Legacy `services.*`
requests remain available on `ServiceControlChannel` in legacy mode.

### Results

```http
POST /v1/runtime/results
```

Success result:

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

Failure results use `ok: false` and an `error` object with stable `code` and
`message` fields. Rust returns:

```json
{"acceptedCommandIds":["command-uuid"]}
```

Accepted results are removed from the replay queue. Duplicate result delivery
is idempotent on the Rust side.

## Python bounds and retry policy

The desktop client uses only Python standard-library HTTP and threading APIs.
All network work is performed by one daemon worker, never by a patched target.

| State | Bound |
| --- | ---: |
| unacknowledged outbound events, hard limit | 256 events |
| ordinary-event admission | 240 queued events |
| capacity reserved for `browser.open` | 16 events |
| one event payload | 16 KiB encoded JSON |
| one event upload | 32 events / 256 KiB |
| HTTP response | 256 KiB |
| one Rust command response | 32 commands / 256 KiB |
| unacknowledged diagnostic history | 64 entries / 128 KiB |
| one diagnostic code | 128 bytes UTF-8 |
| one diagnostic message | 2 KiB UTF-8 |
| one heartbeat diagnostic batch | 8 entries / 64 KiB |
| pending command results | 128 results |
| one command result payload | 64 KiB encoded JSON |
| completed command ID history | 256 commands |
| one Python result batch | 32 items / 256 KiB |

Event enqueue snapshots a JSON-compatible payload under a lock and returns
without HTTP or reconnect work. Log, error, progress, and all other ordinary
events are admitted only while fewer than 240 events are queued. The remaining
16 slots are reserved for exact, normalized `browser.open` events. A queue made
only of browser events is still bounded by the 256-event hard limit.

Ordinary admission failure records the exact diagnostic
`ordinary_event_capacity_exhausted` with message `ordinary event queue reached
its 240-event admission limit; 16 slots are reserved for browser.open`.
Complete queue exhaustion rejects a browser event and records
`critical_event_capacity_exhausted` with message `outbound event queue reached
its 256-event hard limit; browser.open was rejected`.

Both rejection paths run before sequence assignment. The client never evicts a
sequenced unacknowledged event, so accepted ordinary and browser events share
one contiguous wire sequence. Upload batching, acknowledgement, reconnect
replay, and the final flush continue to consume that single ordered queue.

Connection failures retain unacknowledged events and move status through
`disconnected` or `reconnecting`. Retry starts at 100 ms and doubles to a
maximum of 5 seconds. A heartbeat is sent every 5 seconds while connected;
command long polling waits at most 100 ms per request. Process shutdown requests
a final event/result flush bounded to 500 ms by default. A stuck operating
system request cannot make `close()` wait without bound.

Transport failures create or update one active diagnostic episode and one
sequenced historical entry. Identical retries increment bounded `occurrences`
instead of allocating a sequence per attempt. A different code/message or a
later post-recovery failure starts a new sequence. `status()` exposes the
current `activeDiagnostic`, `unacknowledgedDiagnostics`, their count and encoded
bytes, `acknowledgedDiagnosticSequence`, `diagnosticsStartSequence`, and sticky
`diagnosticsTruncated` metadata. Acknowledged entries leave Python's outbound
replay queue; Rust's bounded retained session history remains the debug record.
If an identical unresolved failure repeats after its history envelope was
already acknowledged, only the detached active summary's `occurrences`
advances. Protocol v2 does not mutate or replay an acknowledged historical
envelope; a later post-recovery episode receives a new sequence.

## Browser behavior

Browser mode remains separate from transport selection:

- `host`: enqueue one `browser.open` event and suppress locally.
- `suppress`: suppress locally without an event.
- `passthrough`: call the original standard-library browser implementation.

In desktop `host` mode, `webbrowser.open()` performs no HTTP request and waits
for no worker state. A disconnected broker, even a completely full 256-event
queue, rejected credentials, or a protocol mismatch never falls through to the
operating-system browser. The failure appears in bounded transport diagnostics
instead.
