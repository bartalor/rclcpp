---
name: memory-refactor
description: Use when the user asks for a deliberate refactor, cleanup, or audit of an issue's memory ("refactor notes for <issue>", "clean up notes", "audit memory", "memory got messy", "prune stale"). Distinct from the incremental fixes memory-write does on the fly — this is an intentional pass over one issue's whole note set. ALWAYS audit-then-report first; never edit or delete in the audit phase.
disable-model-invocation: true
---

# Project memory — REFACTOR (rclcpp)

Before doing anything: read `../memory-conventions.md` for the shared
data model. This skill operates on top of `memory-read` and
`memory-write` — it does not replace them.

## Scope

One issue at a time. Infer the issue from the current branch (e.g.
`bar/issue-2876-dev` → `issue-2876`). If the branch doesn't name an
issue and no issue is otherwise in scope, ask the user which one —
do not sweep the whole project. Utility notes are out of scope for
this skill unless the user names one explicitly.

## Two phases — strict

### Phase 1: audit and report. NO writes, NO deletes.

1. Pull every note tagged `issue-<N>` (use `memory-read`).
2. For each note, check against the conventions:
   - Does line 1 hold a scope sentence? Does it still match the body?
   - Is the kind right for the content? (e.g. running log of learnings
     filed under `fix-plan` belongs in `findings`.)
   - Is an editable kind (`status`, `reproduction`, `callflow`,
     `fix-plan`, `open-questions`) stale vs. current code or vs.
     newer findings/decisions?
   - Are append-only kinds (`findings`, `decisions`) actually
     append-only, or did someone overwrite history?
   - Do `[[wikilinks]]` resolve? Does `status` link to every existing
     child, and only to children that exist?
   - Are there duplicates (two notes of the same kind, or two notes
     covering the same scope under different titles)?
   - Are there orphans (notes not reachable from `status`)?
   - Verbatim code dumps, generic ROS 2 knowledge, multi-page debug
     output — anything the conventions say not to store?
   - `open-questions` entries that have actually been answered
     elsewhere?
3. Cross-check against current code where a note makes a code claim
   (`file:line — function — …`). If the file no longer has that
   symbol at that line, flag.
4. Produce a report — grouped by proposed action. Each entry names
   the note, cites the specific convention or contradiction, and
   proposes one action. Categories:
   - **edit-in-place** — editable kind drifted; propose the fix
   - **supersede** — append-only entry now wrong; propose the new
     superseding entry's gist
   - **delete** — obsolete and not historically interesting;
     justify why deletion is safe
   - **snapshot-then-delete** — historically interesting but no
     longer true; propose the one-line summary to land in `findings`
     before deletion
   - **split** — note's scope sentence doesn't cover its body;
     propose the split boundary
   - **merge** — two notes cover the same scope; propose which
     wins and what content moves
   - **relink** — `status` wikilinks out of sync; list adds/removes
   - **leave-alone** — flagged but on inspection is fine; say why

5. **Stop. Hand the report to the user. Do not proceed to Phase 2
   without explicit per-item or batch approval.**

### Phase 2: execute approved changes only.

- For each approved item, perform the action via `memory-write`
  (which knows the supersede/edit/delete rules).
- After every delete or new child, update `status`'s `[[wikilinks]]`
  so it remains an accurate directory.
- Group writes by kind to keep diffs reviewable.
- When done, re-read `status` and confirm the tree is consistent
  (every link resolves, every existing child is linked from status).
- Report back: a short list of what actually changed (note → action).
  No re-justification — that happened in Phase 1.

## Report format

Keep it scannable. Markdown, one section per action category, one
bullet per note. For each bullet:

- **note title** — one-sentence finding — proposed action
- (if non-obvious) one-line justification citing the convention
  ("scope sentence rule", "append-only", etc.) or the contradiction
  ("claims `executor.cpp:412 spin_some`, current file has no such
  symbol at that line").

Don't paste full note bodies into the report. Cite by title and the
specific phrase or section that's the problem.

## Don't

- Don't edit or delete in Phase 1. Ever.
- Don't expand scope to other issues mid-cleanup. If you spot a
  cross-issue problem, note it in the report and stop there.
- Don't reformat notes for cosmetic reasons — only act on convention
  violations or staleness.
- Don't silently rewrite an append-only entry. If it's wrong,
  supersede it; if Phase 1 missed it, surface it now and re-enter
  Phase 1 for that item.
- Don't run this skill as part of normal write traffic. The
  incremental drift-fixes belong in `memory-write`. This skill is
  for intentional passes only.
