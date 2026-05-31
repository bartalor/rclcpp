---
name: memory-read
description: Use BEFORE diagnosing a bug, explaining behaviour in a sensitive area, proposing a fix, or writing a new note — to check what we already know about this issue via the basic-memory MCP server. Also triggers on phrases like "do we have notes on", "what do we know about", "recall", "what did we decide about", "did we hit this before", "search memories", "continue <issue>", "where were we". Always read before write (see also memory-write).
---

# Project memory — READ side (rclcpp)

Before doing anything: read `../memory-conventions.md` for the shared
data model (tree shape, note kinds, tagging, scope rule, mutability,
deletion, close-out). This skill only adds the read-side workflow on
top.

Backend: `basic-memory` MCP — tools `mcp__basic-memory__search_notes`,
`read_note`, `build_context`, `recent_activity`.

## When to invoke

- Session start when an issue is in scope (branch name, file paths,
  `ide_selection`, or recent commits make the issue obvious).
- Before proposing a fix or explaining behaviour in code you have not
  recently touched.
- Before writing a new note (the write skill MUST defer here first to
  avoid duplicates).
- When the user references an issue / PR / area we may have notes on
  ("did we hit this before?", "what did we decide about X?",
  "continue 1234", "where were we").

## Workflow

1. **Infer the issue from context — do not ask the user for it.**
   The current branch name (e.g. `bar/issue-2876-dev` → tag
   `issue-2876`), mentioned file paths, the active diff,
   `ide_selection`, and recent commit subjects are enough to form a
   first query. Asking "what should I search for?" when the branch
   already answers it is the wrong move. Only ask if context is
   genuinely ambiguous.

2. **Read `status` first.** It is the entry point — current state
   plus next step plus `[[wikilinks]]` down to whichever children
   exist.

   ```
   search_notes { query: "status", tags: ["issue-<N>", "status"],
                  tag_match: "all" }
   ```

   Then `read_note` on the hit. If zero hits → this is a brand-new
   issue. Hand off to `memory-write` to seed `status` (ask the user
   for a one-liner first).

3. **Pull other notes lazily, only what the current question needs.**
   Do not pre-load callflow + findings + decisions "just in case" —
   that wastes context. Map question → note:

   - "where were we / what's next" → `status` alone.
   - "remind me how to reproduce" → `reproduction`.
   - "why did we choose X" / "should we do Y" → `decisions`
     (and `open-questions` if proposing a fix).
   - "walk me through the code path" → `callflow`.
   - "what have we learned" / explaining behaviour → `findings`.
   - "what's the current plan" → `fix-plan`.

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
  wrong. Editable kinds (status, reproduction, callflow, fix-plan,
  open-questions): hand off to `memory-write` to overwrite. Append-only
  kinds (findings, decisions): hand off to `memory-write` to add a
  superseding entry. Do **not** silently work around stale memory.

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
