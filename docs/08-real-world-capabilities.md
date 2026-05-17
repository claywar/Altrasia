# 08 — Real-World Capabilities

Selected characters—typically **Architect**-class builders—may interact with the host environment: **filesystem**, **scheduled tasks**, and **character administration**. These capabilities are gated by role, config, and [07-approvals.md](07-approvals.md).

## 1. Filesystem agent

### 1.1 Purpose

Allow authorized agents to read and propose changes to files within **allowed roots** (project dirs, user data, designated workspaces)—not the entire OS.

### 1.2 Configuration

| Key | Description |
|-----|-------------|
| `enabled` | Master switch |
| `allowedRoots` | Resolved paths (userData, serverRoot, custom) |
| `maxReadChars` | Pagination limit per read |
| `maxWriteBytes` | Max write payload |
| `maxListEntries` | Directory listing cap |
| `requireApprovalForWrites` | Queue writes (default true) |
| `unattendedWrites` | Allow headless apply (default false) |
| `backupBeforeDestructive` | Copy before delete/overwrite |

### 1.3 Tools

| Tool | Approval |
|------|----------|
| `fs_read` | No |
| `fs_list` | No |
| `fs_write` | Yes |
| `fs_patch` | Yes |
| `fs_delete` | Yes |

### 1.4 Read behavior

- Paginated line ranges
- Return `mtime`; warn if file changed on disk since last read in session
- Reject paths outside roots or on denylist

### 1.5 Write behavior

1. Classify operation (write/destructive)
2. If approval required → enqueue, return `pending`
3. On approve → apply, backup if destructive, set state `applied`
4. On deny → no mutation

### 1.6 Denylist (non-exhaustive)

- Path traversal outside roots
- `.ssh`, credential stores, env secrets
- Character card binaries (`characters/*.png`)
- Approval metadata directories

### 1.7 Character records vs files

Agents MUST use **character admin tools** for persona definitions. Filesystem tools MUST NOT target character PNG/card binaries even if roots overlap.

## 2. Scheduled tasks

### 2.1 Purpose

Run recurring or one-shot jobs in the server process: HTTP **webhooks**, log lines, or future `architect_fs` maintenance—while server is up.

### 2.2 Configuration

```yaml
scheduledTasks:
  enabled: true
  tickIntervalSeconds: 60      # minimum 5
  maxConcurrentRunsPerUser: 2
  webhookRequestTimeoutMs: 30000
```

Storage per operator: `data/<operator>/schedules/jobs.json`

### 2.3 Job shape

| Field | Description |
|-------|-------------|
| `name` | Required label |
| `kind` | `webhook` \| `log` \| `architect_fs` (extensible) |
| `schedule` | `interval`, `cron` (5-field), or `once` (ISO) |
| `webhook` | URL, method, headers |
| `log.line` | Text for log kind |
| `repeat.times` | Stop after N successes |
| `enabled` | Boolean |

Max jobs per operator: e.g. 50.

### 2.4 Webhook payload

POST JSON including job id, name, timestamp, operator id—exact schema implementation-defined.

### 2.5 Agent tools

When enabled:

- `scheduled_task_list`
- `scheduled_task_create`
- `scheduled_task_run`
- `scheduled_task_pause` / `resume`
- `scheduled_task_delete`

Same REST API as operator UI. Architect prompts SHOULD document when to schedule vs execute immediately.

### 2.6 Architect FS jobs

`kind: architect_fs` runs read/list headless; writes need `preApproved` or `unattendedWrites` or they return pending approval ids.

## 3. Character administration

Tools (no approval):

| Tool | Action |
|------|--------|
| `character_list` | Enumerate characters |
| `character_create` | Create record |
| `character_update` | Patch fields |

Forbidden: writing card binaries via `fs_write`.

## 4. Architect role

**Architect** (configurable allowlist of `characterId`s):

- Filesystem tools when server FS enabled
- Scheduled task tools when scheduler enabled
- Often same allowlist as **diary admin** and **observer** sync

`architectSyncObserverList` SHOULD merge diary admins into FS allowlist when enabled.

Operator MUST paste **Architect system prompt** fragment covering: mandatory recall, diary_read_other, tool budgets, approval waiting, no character PNG writes.

## 5. Security

| Control | Application |
|---------|-------------|
| Session auth | All mutating APIs |
| CSRF | Browser POSTs |
| Path allowlist | FS |
| Approval queue | Writes + risky web |
| Rate limits | Webhooks, concurrent runs |

## 6. Requirements summary

| ID | Requirement |
|----|-------------|
| RW-1 | FS writes require approval unless unattended/preApproved. |
| RW-2 | FS reads respect roots and size limits. |
| RW-3 | Destructive FS ops backup when configured. |
| RW-4 | Scheduler disabled → API 404 or equivalent hide. |
| RW-5 | Character admin separate from FS binary writes. |
| RW-6 | Architect allowlist gates real-world tools. |

## 7. Commissions (post-v1)

Filesystem and web tools invoked during a **commission** ([23-in-world-work.md](23-in-world-work.md)) follow the same approval and allowlist rules. Commission completion MUST persist findings to assignee mind pool by default (COM-2), not transcript-only.

## 8. World heartbeat (v1.1)

Distinct from §2 **scheduled tasks** (webhooks, cron). World heartbeat runs **`idle_timer`** orchestration when no browser is connected.

### 8.1 Purpose

Allow background NPC rotation (`AO-4`) while the server process is up, without requiring an open Web UI tab. Tab-visible idle remains when heartbeat is off ([20-product-principles.md](20-product-principles.md)).

### 8.2 Configuration (global)

Stored in **server/operator settings** (e.g. `~/.altrasia/config.yaml`), not per-world `configJson`:

```yaml
heartbeat:
  enabled: false              # HB-5: default off at v1.1
  intervalSeconds: 60         # minimum 5
```

| Key | Description |
|-----|-------------|
| `heartbeat.enabled` | Master switch (HB-1) |
| `heartbeat.intervalSeconds` | Tick interval for eligible worlds |

Individual worlds MAY still be **paused** via operator UI (UI-C1); paused worlds MUST NOT receive heartbeat idle ticks.

### 8.3 Behavior

| ID | Requirement |
|----|-------------|
| HB-1 | When `heartbeat.enabled` is true and server is up, orchestrator MUST enqueue `idle_timer` jobs without any WebSocket client connected |
| HB-2 | Heartbeat MUST NOT bypass GpuResourceQueue or AO-11 (INF-5, AO-12) |
| HB-3 | Configuration is global only — not per-world flags |
| HB-4 | Web UI operator/server settings show enabled state, interval, `lastHeartbeatAt` |
| HB-5 | Default `enabled: false`; operator opts in |

Eligible worlds: all non-paused worlds in the operator database with at least one present NPC. Fairness across multiple worlds is implementation-defined; SHOULD round-robin worlds per tick cap.

Jobs MUST set idle metadata `source: server_heartbeat` (AO-5a). Queue strip shows heartbeat origin (UI-2).

### 8.4 Explicitly out of scope

- Webhooks and external scheduled tasks (§2)
- Commission ticks (post-v1)
- Running when server process is stopped

## Related documents

- [07-approvals.md](07-approvals.md)
- [23-in-world-work.md](23-in-world-work.md)
- [09-roles-and-privilege.md](09-roles-and-privilege.md)
- [05-tool-calling.md](05-tool-calling.md)
- [13-agent-orchestration.md](13-agent-orchestration.md)
- [20-product-principles.md](20-product-principles.md)
