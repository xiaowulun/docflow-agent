# DocFlow Agent Architecture

## 1. Goal

DocFlow Agent is a local-first office assistant agent for structured document workflows.

Its core goals are:

- Process `Word`, `Excel`, and `PDF`
- Analyze input automatically
- Generate a structured execution plan
- Require human confirmation for risky or write actions
- Execute through deterministic tools
- Verify outputs after execution
- Track the full execution trail with audit events
- Extend capabilities later through native tools and MCP integrations

This project does not use a free-form autonomous agent loop as the primary runtime.
The primary runtime is a controlled state machine.

## 2. Design Principles

- State machine first: task flow must be explicit, inspectable, and interruptible
- Human gate first: write operations and risky actions must pause for confirmation
- Deterministic execution: models propose plans, tools perform concrete actions
- Capability abstraction: planner sees stable capabilities, not raw tool internals
- Audit by default: every major transition and tool call becomes an event
- Native-first core: local document workflows stay in-process and strongly controlled
- MCP as extension: external systems are connected through adapters, not embedded in the core

## 3. Final Architecture

```text
                +-----------------------------------+
                |           API / Channel           |
                | FastAPI / Web / future Bot layer  |
                +------------------+----------------+
                                   |
                +------------------v----------------+
                |        Runtime Orchestrator       |
                |   task lifecycle + state machine  |
                +--------+---------------+----------+
                         |               |
              +----------v-----+   +-----v----------+
              | Analyzer/Router |   | Confirmation   |
              | classify intent |   | Human Gate     |
              | inspect files   |   | policy checks  |
              +----------+------+   +-----+----------+
                         |                |
                         +--------+-------+
                                  |
                       +----------v----------+
                       | Planner             |
                       | structured plan     |
                       | uncertainty output  |
                       +----------+----------+
                                  |
                       +----------v----------+
                       | Executor            |
                       | capability calls    |
                       +----------+----------+
                                  |
                       +----------v----------+
                       | Verifier            |
                       | output checks       |
                       +----------+----------+
                                  |
                +-----------------v------------------+
                |        Capability Registry         |
                | schema + policy + routing metadata |
                +-------------+-------------+--------+
                              |             |
                +-------------v--+   +------v---------------+
                | Native Adapters |   | MCP Client Adapters |
                | office/pdf/ocr  |   | email/web/db/etc.   |
                +-------------+---+   +------+--------------+
                              |              |
                    +---------v----+   +-----v--------------+
                    | OfficeCLI     |   | External MCP       |
                    | PDF / OCR     |   | servers/services   |
                    +---------------+   +--------------------+

                +-------------------------------------------+
                | Audit/Event Store + Artifact/Task Store   |
                +-------------------------------------------+
```

## 4. Layer Responsibilities

### 4.1 API / Channel Layer

Responsibilities:

- Receive task requests
- Upload and download files
- Show plan previews
- Accept confirmation or rejection
- Query task status and audit trail

Examples:

- `apps/api/app/main.py`
- `apps/api/app/routers/tasks.py`
- `apps/api/app/routers/files.py`
- `apps/web/`

This layer should not contain business workflow logic.

### 4.2 Runtime Orchestrator

Responsibilities:

- Own task lifecycle
- Enforce valid state transitions
- Trigger analysis, planning, execution, and verification
- Pause on confirmation-required states
- Emit audit events on every major step

This is the true system core.

Recommended runtime flow:

`created -> analyzing -> planned -> awaiting_confirm -> executing -> verifying -> done/failed`

`awaiting_confirm` subtypes:

- `plan_review` — 首次执行前审阅 plan，确认后 → `executing`
- `risky_action` — 执行中遇到高风险写操作（删除、覆盖等），暂停后 → 继续当前 step 或 abort
- `ambiguity_resolution` — 分析或规划阶段发现歧义，需用户补充决定，响应后 → 回退到 `analyzing` 或 `planned` 重新处理

Current alignment:

- `packages/agent_core/orchestrator.py`
- `packages/agent_core/state_machine.py`

### 4.3 Analyzer / Router

Responsibilities:

- Detect file type and document subtype
- Classify task intent
- Extract enough context to plan safely
- Mark risky or ambiguous cases early

Typical outputs:

- input summary
- document structure
- field candidates
- OCR requirement
- task class
- risk level

This should remain mostly read-only.

### 4.4 Planner

Responsibilities:

- Convert user intent plus analysis into a structured plan
- Select capabilities, not raw shell commands
- Emit uncertainties explicitly
- Mark actions that require confirmation

The planner should output a stable schema, for example:

- `intent`
- `input_artifacts`
- `actions`
- `uncertainties`
- `requires_confirmation`
- `expected_outputs`
- `verification_checks`

Important boundary:

- The planner proposes
- The runtime decides
- The tool executes

### 4.5 Confirmation Gate

Responsibilities:

- Enforce write policies
- Stop on ambiguous operations
- Surface a human-readable plan summary
- Record approval or rejection decisions

This should be a first-class module, not a boolean hidden inside planner output.

### 4.6 Executor

Responsibilities:

- Resolve capabilities from the registry
- Execute deterministic tool calls
- Normalize outputs and errors
- Persist generated artifacts
- Emit per-action audit events

The executor should never let the model improvise arbitrary writes at runtime.

### 4.7 Verifier

Responsibilities:

- Re-read output artifacts
- Validate structural correctness
- Check whether expected content exists
- Detect partial failures and malformed outputs

Examples:

- Can the generated docx open successfully
- Was the expected worksheet updated
- Did exported PDF text contain required fields

### 4.8 Capability Registry

Responsibilities:

- Expose the system's usable capabilities
- Store capability metadata, schema, risk class, and adapter binding
- Hide whether an ability is native or MCP-backed

The planner and executor should work with `CapabilitySpec`, not implementation details.

Suggested capability fields:

- `name`
- `kind` (`native` or `mcp`)
- `description`
- `input_schema`
- `output_schema`
- `risk_level`
- `requires_confirmation`
- `adapter`
- `tags`

This is an evolution of the current `ToolRegistry`.

### 4.9 Native Adapters

Responsibilities:

- Wrap local deterministic tools
- Normalize parameter validation
- Provide stable outputs to the executor

First native adapters:

- `officecli` for `docx/xlsx/pptx`
- local PDF parsing
- OCR pipeline
- file storage
- task storage
- audit storage

### 4.10 MCP Client Adapters

Responsibilities:

- Connect to external MCP servers
- Discover and map external tools into internal `CapabilitySpec`
- Apply local policy before use
- Normalize errors and result payloads

Good MCP targets later:

- `email`
- `web search`
- `database query`
- `knowledge base`
- `calendar`

MCP is an extension surface, not the state machine core.

## 5. Native Tools vs MCP Tools

Conceptually:

- Native tools are your agent's in-process or directly managed abilities
- MCP tools are external abilities connected through an MCP client

Inside the runtime, both should look the same:

```text
Planner -> Capability Registry -> Executor
```

The planner should request capabilities such as:

- `fill_excel_template`
- `extract_pdf_text`
- `send_email_with_attachment`

It should not care whether the capability comes from:

- local `officecli`
- local PDF/OCR code
- an external MCP server

That distinction belongs in the adapter layer.

## 6. Data and Audit Model

The system needs two persistent stores.

### 6.1 Task and Artifact Store

Stores:

- task metadata
- task state
- input file paths
- output artifact paths
- plan snapshots
- confirmation records

Suggested storage:

- `SQLite` for metadata
- local filesystem for artifacts

### 6.2 Audit/Event Store

Stores:

- state transitions
- planner decisions
- confirmation requests
- tool execution events
- verification results
- failure reasons

Suggested event shape:

- `event_id`
- `task_id`
- `event_type`
- `timestamp`
- `actor`
- `step`
- `payload`

Audit must be append-only in normal operation.

## 7. Recommended Runtime Contract

Each task should move through this contract:

1. Accept input and create a task
2. Analyze artifacts and classify intent
3. Generate a structured plan
4. Pause if any action requires confirmation
5. Execute approved actions via capabilities
6. Verify outputs
7. Persist artifacts, status, and audit events

Recommended failure policy:

- fail fast on invalid plan or missing capability
- pause instead of guessing when intent is ambiguous
- keep partial artifacts traceable
- never hide tool errors behind generic summaries

## 8. Recommended Repo Shape

Target structure based on the current repository:

```text
apps/
  api/
  web/

packages/
  agent_core/
    orchestrator.py
    state_machine.py
    analyzer.py
    router.py
    planner.py
    confirmation_gate.py
    executor.py
    verifier.py
    capability_registry.py
    policy.py
  tooling/
    officecli/
    pdf/
    ocr/
    storage/
    mcp_client/
  schemas/
    task.py
    plan.py
    events.py
    capability.py
    artifact.py

storage/
  artifacts/
  sessions/
  audit/
  db/

tests/
  test_agent_core/
  test_tooling/
  fixtures/
```

Notes:

- `capability_registry.py` should gradually replace the current `packages/tooling/registry.py`
- `packages/tooling/mcp_client/` should contain MCP connection, discovery, mapping, and execution adapters
- `packages/schemas/capability.py` should define the unified capability contract

## 9. Phased Delivery Plan

### Phase 1: Stabilize the Core

Goal:

- make the current state-machine runtime explicit and persistent

Work:

- separate orchestrator responsibilities more clearly
- persist tasks, plans, confirmations, and audit events
- normalize executor and verifier result schemas

### Phase 2: Lock the Capability Contract

Goal:

- stop exposing raw tools directly to planning logic

Work:

- introduce `CapabilitySpec`
- upgrade `ToolRegistry` into a capability registry
- mark risk level and confirmation policy per capability

### Phase 3: Solidify Office Assistant Features

Goal:

- make Word/Excel/PDF the first reliable vertical

Work:

- keep `officecli` as the native adapter for `docx/xlsx/pptx`
- build PDF text extraction, classification, and OCR fallback
- build verification rules per document type

### Phase 4: Add MCP Extension Layer

Goal:

- allow controlled external capability expansion

Work:

- add MCP client connection management
- map external tools to internal capability specs
- add allowlist and risk policy before exposing external capabilities

### Phase 5: Add Better Human-in-the-Loop UX

Goal:

- make confirmation and audit usable in the Web UI

Work:

- show plan preview and uncertainty list
- show approval checkpoints
- show full audit timeline

## 10. What MCP Is Good For Here

MCP is a good fit for:

- connecting external capability providers without hard-coding each integration
- reusing existing tool ecosystems
- exposing DocFlow Agent itself as a higher-level MCP server later

MCP is not the right place for:

- core state transitions
- confirmation policy ownership
- audit truth source
- local document execution control

Practical rule:

- local document operations stay native first
- external systems enter through MCP adapters

## 11. Final Recommendation

The correct base for this project is:

`state machine runtime + capability registry + native document adapters + MCP extension adapters + persistent audit`

Not:

- a free-form ReAct loop
- a chat shell as the main runtime
- a tool system that exposes raw external tools directly to the planner

If implemented this way, the project stays stable for office-document workflows now and remains extensible for email, web, database, and future skills later.
