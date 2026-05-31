---
name: memory-write
description: Use AFTER a meaningful investigation step, AFTER a decision, AFTER learning something non-obvious, BEFORE context grows long, or when the user says "save that", "note that", "remember", "record this decision", "update status". Also use to fix wrong/stale memory, supersede a finding or decision, delete obsolete notes, or close out a finished issue. Always defer to memory-read first to avoid duplicates.
---

# Project memory — WRITE side (rclcpp)

Before doing anything: read `../memory-conventions.md` for the shared
data model (tree shape, note kinds, tagging, scope rule, mutability,
deletion, close-out). This skill only adds the write-side workflow on
top.

Backend: `basic-memory` MCP — tools `mcp__basic-memory__write_note`,
`edit_note`, `move_note`, `delete_note`.

## Always read before write

Invoke the `memory-read` skill first to:

- Find the existing `status` for this issue (and confirm whether
  this is a new issue or a continuation).
- Check whether a note of the same kind already exists — if it does,
  this is an `edit_note` operation, not a new `write_note`.
- Pull any note whose content the new write might contradict, so a
  supersede can be authored deliberately.

Skipping the read step produces duplicates and orphaned drift.

## When to invoke

- End of a meaningful investigation step.
- After any decision worth keeping ("we'll fix it in rcl, not rclcpp
  because …").
- After learning something non-obvious about the code or the bug.
- Before the chat context gets long enough to risk losing detail.
- When the user explicitly says save / note / remember / record /
  update.
- When a read surfaced a contradiction with current code or another
  note (this skill performs the fix).
- When an issue ships — perform close-out (see conventions).

Do **not** wait for "we're done." Save incrementally.

## Required fields on every write

- `title`: short, kebab-case, scoped. E.g. `issue-1234-status`,
  `issue-1234-callflow-executor`. The kind appears in the title so
  human listings are scannable.
- `folder`: `<issue-tag>` (e.g. `issue-1234`). Per conventions —
  retrieval ignores this, humans don't.
- `tags`: at minimum `ros2`, `rclcpp`, `issue-<N>`, `<kind>`.
- `content`: first line is the scope sentence. No exceptions.

## Write rules per note kind

- **status** — `edit_note` (overwrite). One short paragraph: scope,
  current state, next step. Plus `[[wikilinks]]` down to whichever
  children exist. Update every time progress changes.

- **reproduction**, **callflow**, **fix-plan**, **open-questions** —
  `edit_note` (overwrite). Keep current. Callflow stays in the
  bulleted `file:line — function — desc` form, not prose.

- **findings**, **decisions** — append-only. Either add a new
  section to the existing note with a header that the server's
  auto-managed timestamp will identify, **or** write a new
  standalone note `issue-<N>-finding-<slug>` that links back via
  `[[wikilink]]`. Pick standalone when the entry is large enough to
  scan on its own; otherwise append a section.

  **Never edit a prior finding or decision.** To correct one:
  append a new entry that says "supersedes [[prior-note-or-section]]
  because <reason>". The server's `created_at` orders them; do not
  hand-stamp dates.

## Linking when writing

- Every child note's body links up to `status` via `[[wikilink]]`.
- Update `status`'s `[[wikilinks]]` whenever a new child is created
  or an existing child is deleted. `status` must always be an
  accurate directory of what exists for this issue.
- Sideways links only on real dependency. A finding that pins to a
  specific `callflow` node links there. Two findings that merely
  share a tag do **not** link.
- Cross-issue `[[wikilinks]]` allowed when one issue's note informs
  another. The tag set still names exactly one issue per note.

## Fixing wrong / stale memory

- **Editable kind drifted from reality** → `edit_note` to overwrite.
  If the scope sentence no longer matches the body, either re-scope
  the sentence or split the note (move the off-scope content into a
  new child and link).

- **Append-only entry is now wrong** → append a superseding entry.
  Reference the prior entry by `[[wikilink]]` (or by its section
  header if same-note). State the reason for supersession.

- **Two notes contradict, neither obviously stale** → do not write
  a fix unilaterally. Surface to the user (via `memory-read`'s
  conflict handling), get a resolution, then record it as a new
  finding/decision and edit/supersede the loser.

## Deleting

Use `delete_note` when:

- An `open-question` is answered — delete it and append the answer
  to `findings`.
- A `reproduction` / `callflow` / `fix-plan` is no longer true and
  not historically interesting. If the historical version matters,
  snapshot a one-line summary into `findings` before deleting.
- Issue close-out (below).

Never delete `findings`, `decisions`, or `status` mid-issue.
After deleting, update `status`'s `[[wikilinks]]` so it stays
accurate.

## Issue close-out

When the PR ships or the issue closes:

1. Write `issue-<N>-postmortem`, tagged
   `ros2, rclcpp, issue-<N>, postmortem`. Contents: one-paragraph
   summary, the fix in one paragraph, `[[wikilinks]]` to the
   surviving `decisions` and `findings`.
2. `delete_note` on `status`, `reproduction`, `callflow`,
   `fix-plan`, `open-questions` for that issue.
3. Keep `decisions` and `findings` — audit trail.

## Multi-issue care

A note belongs to exactly one issue (tag-wise). If during issue-1234
work you produce a finding that's really about issue-5678, write it
under `issue-5678` tags and link from `issue-1234` via `[[wikilink]]`.
Do not double-tag — it pollutes tag queries on both sides.

## Don't

- Don't write without first invoking `memory-read`.
- Don't skip the scope sentence on line 1.
- Don't edit a past `finding` or `decision` — supersede instead.
- Don't paste verbatim code from the repo. Link to `file:line`.
- Don't hand-stamp dates. The server tracks `created_at` /
  `updated_at`.
- Don't leave `status`'s `[[wikilinks]]` stale after creating or
  deleting a child.
