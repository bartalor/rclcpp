---
name: basic-memory-write
description: Use AFTER a meaningful investigation step, AFTER a decision, AFTER learning something non-obvious, BEFORE context grows long, or when the user says "save that", "note that", "remember", "record this decision", "update status". Also use to fix wrong/stale memory, supersede a finding or decision, delete obsolete notes, or close out a finished issue. Always defer to basic-memory-read first to avoid duplicates.
disable-model-invocation: true
---

# Project memory — WRITE side (rclcpp)

Before doing anything: read `../basic-memory-conventions.md` for the shared
data model (tree shape, note kinds, tagging, scope rule, mutability,
deletion, close-out). This skill only adds the write-side workflow on
top.

Backend: `basic-memory` MCP — tools `mcp__basic-memory__write_note`,
`edit_note`, `move_note`, `delete_note`. See
`.claude/skills/basic-memory-tool-guide.md` for known tool quirks — consult
on first unexpected failure, do not retry the same payload.

## Always read before write

Invoke the `basic-memory-read` skill first to:

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

All kinds are `edit_note` (overwrite). Keep them current; staleness
is a bug. When a fact is wrong, fix it in place — no supersede
chains, no append-only history.

- **status** — one short paragraph: scope, current state, next step.
  Plus `[[wikilinks]]` down to whichever children exist. Update
  every time progress changes.
- **reproduction**, **callflow**, **fix-plan**, **open-questions** —
  keep current. Callflow stays in the bulleted
  `file:line — function — desc` form, not prose.
- **findings**, **decisions** — current understanding / current
  rationale. When you learn the prior take was wrong, rewrite it.
  Split into `issue-<N>-finding-<slug>` / `issue-<N>-decision-<slug>`
  standalone notes only when one note gets too large to scan.

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

## Audit the whole note before every write

Applies to **every** write: `write_note`, `edit_note`, `append`,
`prepend`. Applies to **every** kind, append-only included. "I'm
only adding a paragraph" is when most bloat accumulates — the rule
exists specifically to catch that.

- **These notes are your working memory, not the user's documentation.**
  The user doesn't read them. They exist so a fresh Claude instance
  can pick up the thread without re-deriving everything. Optimize for
  *your* re-read, not for completeness.

- **Read the whole target note first, with intent to cut.** Before
  the write, list every section that no longer earns its context
  cost in *this* note, and cut them in the same write that adds new
  content. Specifically look for:
  - Sections motivating an approach that has since been rejected
    (e.g. infrastructure facts gathered for a path you decided
    against — gtest-timeout semantics, `try_lock` UB, leaked-process
    counts when staged-deadlock testing was abandoned). When a
    `decision` records a rejection, the `findings` paragraphs that
    motivated the rejected approach usually go with it.
  - Bullets advocating *for* the current approach when the current
    approach is flagged unsatisfactory. A `findings` note should
    record neutral facts, not arguments for code that may be
    replaced.
  - Reasoning duplicated between `findings` and `decisions` — pick
    one home; the other gets a `[[wikilink]]`.
  - Verification recipes that are mechanically re-derivable from the
    code in under a minute. Keep the gotcha, drop the recipe.
  - Scope-sentence drift: if line 1 no longer matches the body,
    re-scope or split.

- **Verify before you touch.** Adds, edits, and deletes all have to
  clear the same bar: 100% confidence the claim is true *right now*
  against the current code. A hasty add poisons memory with a
  half-verified fact; a hasty delete loses the one bullet the next
  instance needed. If you can't verify it this turn — by reading the
  code, running it, or asking the user — leave the note alone. "I
  think this is probably stale" is not grounds to delete. "This
  sounds right" is not grounds to add. Slower is safer; the cost of
  a wrong write is paid by every future instance.

## Fixing wrong / stale memory

- **Fact is wrong** → overwrite in place. Every kind.
- **Two notes contradict, neither obviously stale** → do not write
  a fix unilaterally. Surface to the user (via `basic-memory-read`'s
  conflict handling), get a resolution, then overwrite the loser.

## Deleting

Use `delete_note` when:

- An `open-question` is answered — delete it and append the answer
  to `findings`.
- A `reproduction` / `callflow` / `fix-plan` is no longer true and
  not historically interesting. If the historical version matters,
  snapshot a one-line summary into `findings` before deleting.
- Issue close-out (below).

Never delete `status` mid-issue. After deleting, update `status`'s
`[[wikilinks]]` so it stays accurate.

## Issue close-out

When the PR ships or the issue closes:

1. Write `issue-<N>-postmortem`, tagged
   `ros2, rclcpp, issue-<N>, postmortem`. Contents: one-paragraph
   summary, the fix in one paragraph, plus whatever from
   `findings`/`decisions` is worth keeping (merged in or linked).
2. `delete_note` on every other note for that issue.

## Multi-issue care

A note belongs to exactly one issue (tag-wise). If during issue-1234
work you produce a finding that's really about issue-5678, write it
under `issue-5678` tags and link from `issue-1234` via `[[wikilink]]`.
Do not double-tag — it pollutes tag queries on both sides.

## Pacing memory writes

No parallel writes (serialize them — each write's server result
may inform the next: new permalink, conflict, error). Otherwise,
just do the work: once the user has authorized a memory task
(audit, cut, append, supersede plan), execute all the writes in
one response. Do not stop between writes, do not narrate "next
I'll…", do not summarize what's left. These are your notes — the
user does not want to be the gate between each one.

## Don't

- Don't write without first invoking `basic-memory-read`.
- Don't skip the scope sentence on line 1.
- Don't paste verbatim code from the repo. Link to `file:line`.
- Don't store commit hashes — they rot when branches are amended,
  rebased onto upstream, or squashed. Reference changes by file +
  symbol + behaviour. (See `basic-memory-conventions.md` "What NOT to store".)
- Don't hand-stamp dates. The server tracks `created_at` /
  `updated_at`.
- Don't leave `status`'s `[[wikilinks]]` stale after creating or
  deleting a child.
