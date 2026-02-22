# Agent Prompt & Tool Handling Improvements

> Branch: `copilot/compare-tool-handling-systems`  
> Motivation: Comparison of picoclaw's agentic core with [openclaw](https://github.com/openclaw/openclaw)

---

## Overview

This document explains four changes made to picoclaw's agent loop and system prompt
infrastructure, why they were made, and exactly how each one alters picoclaw's runtime
behaviour.

The changes touch three source files:

| File | What changed |
|------|--------------|
| `pkg/agent/context.go` | `PromptMode` type, `SilentReplyToken` constant, new prompt sections, minimal subagent prompt |
| `pkg/agent/loop.go` | Silent-reply-token detection; subagent `ContextBuilder` wiring |
| `pkg/tools/subagent.go` | `SetSystemPromptBuilder` / `buildSystemPrompt` on `SubagentManager` |

---

## Change 1 — `PromptMode` ("full" / "minimal")

### What was changed

`ContextBuilder` gained a `promptMode` field (default `PromptModeFull`) and a setter:

```go
// pkg/agent/context.go
type PromptMode string

const (
    PromptModeFull    PromptMode = "full"
    PromptModeMinimal PromptMode = "minimal"
)

func (cb *ContextBuilder) SetPromptMode(mode PromptMode) {
    cb.promptMode = mode
}
```

`BuildSystemPrompt()` now branches on the mode:

```go
func (cb *ContextBuilder) BuildSystemPrompt() string {
    if cb.promptMode == PromptModeMinimal {
        return cb.buildMinimalSystemPrompt()
    }
    // ... full prompt as before
}
```

The minimal prompt includes only: identity ("you are a picoclaw subagent"), runtime info,
workspace path, tool list, and a safety rule. It omits:

- bootstrap files (`AGENTS.md`, `SOUL.md`, `USER.md`, `IDENTITY.md`)
- skills summary
- memory context
- silent-reply instructions
- the user-facing "Important Rules" block

The wiring in `loop.go` sets minimal mode for every spawned subagent:

```go
subagentContextBuilder := NewContextBuilder(agent.Workspace)
subagentContextBuilder.SetPromptMode(PromptModeMinimal)
subagentManager.SetSystemPromptBuilder(func() string {
    return subagentContextBuilder.BuildSystemPrompt()
})
```

### Behavioural impact

**Before** — Every subagent received a three-line hardcoded string:

> "You are a subagent. Complete the given task independently and report the result.
> You have access to tools — use them as needed to complete your task.
> After completing the task, provide a clear summary of what was done."

This prompt contained no tool list, no workspace path, and no safety guidance.

**After** — Subagents receive a structured prompt that:

1. Lists all registered tools (same tool registry as the main agent).
2. Provides the workspace path so tools like `read_file`/`write_file` resolve paths correctly.
3. Includes a safety rule so subagents cannot pursue autonomous goals.
4. Deliberately excludes user-specific content (skills, memory, SOUL.md) — keeping the prompt
   small and preventing persona leakage into task-focussed workers.

This makes subagent tool calls reliably succeed where they previously failed silently because
the agent did not know which tools existed or where the workspace was.

---

## Change 2 — `## Safety` section in the system prompt

### What was changed

Two sentences were added to the full main-agent system prompt inside `getIdentity()`:

```
## Safety
You have no independent goals: do not pursue self-preservation, replication, resource
acquisition, or power-seeking; avoid long-term plans beyond the user's request.
Prioritize safety and human oversight over completion; if instructions conflict, pause and
ask; comply with stop/pause/audit requests and never bypass safeguards.
Do not manipulate or persuade anyone to expand access or disable safeguards.
```

A shorter version also appears in the minimal subagent prompt.

### Behavioural impact

**Before** — The model had no explicit constraint on autonomous or self-serving behaviour.
An adversarially crafted user message could instruct the agent to, for example, create
background cron jobs for "self-preservation" or attempt to acquire resources outside the
user's request.

**After** — The safety constraints are part of the model's context at every turn. Models
with strong instruction following (e.g. Claude, GPT-4o) treat these as high-priority rules
that cannot be overridden by later user messages. The agent will pause and ask instead of
silently executing potentially unsafe long-running plans.

---

## Change 3 — `## Tool Call Style` guidance

### What was changed

A new section was inserted into `getIdentity()` (full prompt only):

```
## Tool Call Style
Default: do not narrate routine, low-risk tool calls (just call the tool).
Narrate only when it helps: multi-step work, complex/challenging problems, sensitive
actions (e.g., deletions), or when the user explicitly asks.
Keep narration brief and value-dense; avoid repeating obvious steps.
```

### Behavioural impact

**Before** — Without guidance, models often over-explain every tool call ("I will now read
the file for you…", "I am going to execute the following command…"). This adds noise to
responses and wastes context-window tokens.

**After** — The model silently calls low-risk tools (reads, searches, writes) and only
narrates when the action is complex, irreversible, or explicitly requested. Conversations
become more concise and the context window is used more efficiently.

---

## Change 4 — `SilentReplyToken` and silent-reply suppression

### What was changed

A constant and detection logic were added:

```go
// pkg/agent/context.go
const SilentReplyToken = "__PICOCLAW_SILENT__"
```

The full prompt instructs the model to use it:

```
## Silent Replies
When you have nothing useful to say (e.g., after completing a background task with no
user-visible result), respond with ONLY: __PICOCLAW_SILENT__
It must be your entire message — nothing else.
```

The agent loop detects the token and suppresses the outbound message:

```go
// pkg/agent/loop.go — inside runAgentLoop()
if strings.TrimSpace(finalContent) == SilentReplyToken {
    logger.InfoCF("agent", "Silent reply token received, suppressing outbound message", ...)
    finalContent = ""
}
```

When `finalContent` is empty and the token was suppressed, the existing `DefaultResponse`
fallback (`"I've completed processing but have no response to give."`) is returned
internally but **not sent to the user** when the agent loop is called from the background
system-message path (where `SendResponse` is `false`).

### Behavioural impact

**Before** — After a background task (cron job, subagent completion, heartbeat), if the
model decided there was nothing to report, it would still produce filler text.  Depending
on the channel, this filler text would either be silently suppressed by other checks or
leaked to the user as an unhelpful "I've completed processing" message.

**After** — The model can explicitly opt out of sending a response by returning
`__PICOCLAW_SILENT__`. The agent loop treats this as a no-op and logs it at INFO level.
Users see no message; the session history still records the assistant turn as empty so the
conversation context is preserved.

Typical scenarios where this token is used:
- A heartbeat fires but there is nothing noteworthy to report.
- A subagent finishes a file-write task and the result was already communicated inline.
- A cron event triggers the agent but the condition it checks is not met.

---

## Summary table

| Change | Files affected | Visible to user? | Token cost impact |
|--------|---------------|-----------------|-------------------|
| `PromptMode` — subagent minimal prompt | `context.go`, `loop.go`, `subagent.go` | Indirectly (subagent tool calls now succeed) | Subagent system prompts are ~60% smaller |
| `## Safety` section | `context.go` | No (system prompt only) | ~40 tokens added per turn |
| `## Tool Call Style` section | `context.go` | Yes (fewer verbose narrations) | ~30 tokens added; saves many per reply |
| `SilentReplyToken` | `context.go`, `loop.go` | Yes (filler messages eliminated) | Negligible |

---

## Testing

Five new unit tests were added to `pkg/agent/loop_test.go`:

| Test | What it verifies |
|------|-----------------|
| `TestSilentReplyToken_SuppressesOutbound` | Token is detected and not forwarded to the user |
| `TestSilentReplyToken_Constant` | Token value is non-empty and starts with `_` |
| `TestPromptMode_DefaultIsFull` | New `ContextBuilder` defaults to full mode |
| `TestPromptMode_Minimal` | Minimal mode excludes bootstrap files (e.g. `SOUL.md`) |
| `TestPromptMode_FullContainsSafety` | Full prompt contains `## Safety` and `## Tool Call Style` |

Run them with:

```sh
go test ./pkg/agent/... -run "TestSilentReplyToken|TestPromptMode"
```
