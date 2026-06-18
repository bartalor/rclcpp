---
name: memory-read

description: Memory is a fallback for fresh sessions and post-compaction amnesia, not a per-question reflex. Use at session start when an issue is in scope, after a /compact when state may be lost, when the user explicitly asks ("do we have notes on", "recall", "search memories", "continue <issue>"), or before writing a note (memory-write defers here to dedupe). When the live conversation already has the answer, trust it — do not re-read memory to restate things the user just said.
disable-model-invocation: true
---

# Project memory — READ side (rclcpp)

Before doing anything: read `../memory-conventions.md` for the shared
data model (tree shape, note kinds, tagging, scope rule, mutability,
deletion, close-out). This skill only adds the read-side workflow on
top.

Backend: `basic-memory` MCP — tools `mcp__basic-memory__search_notes`,
`read_note`, `build_context`, `recent_activity`.

## When to invoke

Memory exists for two situations:
1. **Cold start.** New session, or post-`/compact` amnesia where you've lost
   context the live conversation no longer carries.
2. **Explicit user request.** "Do we have notes on…", "what did we decide
   about…", "search memories", "continue <issue>".

Plus one mechanical case: **before writing a note** (memory-write defers
here to avoid duplicates).

That's it. When the live conversation already has the answer — including
"where are we", "what's next", "what did we just decide" — answer from
session context. Do **not** re-read `status` to recite things the user
just told you in this session. Memory is not a script to run at the user.

## Workflow

1. **Infer the issue from context — do not ask the user for it.**
   The current branch name (e.g. `bar/issue-2876-dev` → tag
   `issue-2876`), mentioned file paths, the active diff,
   `ide_selection`, and recent commit subjects are enough to form a
   first query. Asking "what should I search for?" when the branch
   already answers it is the wrong move. Only ask if context is
   genuinely ambiguous.

2. **When invoking, read `status` first.** It is the entry point —
   current state plus next step plus `[[wikilinks]]` down to whichever
   children exist.

   ```
   search_notes { query: "status", tags: ["issue-<N>", "status"],
                  tag_match: "all" }
   ```

   Then `read_note` on the hit. If zero hits → this is a brand-new
   issue. Hand off to `memory-write` to seed `status` (ask the user
   for a one-liner first).

3. **Pull other notes lazily, only what the current question needs and
   only when the session doesn't already have the answer.** Do not
   pre-load callflow + findings + decisions "just in case" — that wastes
   context. Map question → note (each conditional on cold-start or
   explicit request):

   - "remind me how to reproduce" → `reproduction`.
   - "why did we choose X" / "should we do Y" → `decisions`
     (and `open-questions` if proposing a fix).
   - "walk me through the code path" → `callflow`.
   - "what have we learned" / explaining behaviour in code you have not
     recently touched → `findings`.
   - "what's the current plan" → `fix-plan`.

   "Where were we / what's next" mid-session is answered from the live
   conversation, not from `status`.

4. **Follow `[[wikilinks]]` deliberately.** `status` links down to
   the children that actually exist. Resolve a link by reading the
   linked note directly (`read_note`) — faster and more precise than
   another tag search. `build_context` is useful when you want the
   whole reachable subgraph from one anchor in one call.

5. **Cross-issue context.** If a finding here references a
   `[[wikilink]]` into another issue's notes, follow it only when
   the current question genuinely depends on that other issue.
   Don't drag in adjacent issues by reflex.

## Handling conflicts and stale memory

- If a note contradicts current code or another note, the note is
  wrong. All kinds are edit-in-place — hand off to `memory-write` to
  overwrite. Do **not** silently work around stale memory.

- If two notes contradict and neither is obviously stale, surface
  both to the user — do not pick silently. The user resolves; the
  write skill records the resolution.

- Notes whose scope sentence (line 1) no longer matches their body
  are drift. Flag and hand off to `memory-write` to re-scope or
  split.

## Citing what you read

When a note drives a non-trivial reply, cite it by title (and a
unique phrase or section header) so the user can audit. Don't paste
note content verbatim into code or commits without reviewing it —
notes capture past reasoning, which may be partly out of date even
when not formally superseded.

## Don't

- Don't query without an `issue-<N>` tag when an issue is in scope.
- Don't pre-load every child of `status`. Read lazily.
- Don't trust a single semantic hit blindly for a high-stakes
  decision — follow its links for context.
- Don't paste note content verbatim into code or commits without
  reviewing it.
