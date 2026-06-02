# Project memory — conventions (rclcpp)

Shared data model for the `memory-read` and `memory-write` skills.
**Not a skill itself.** Both skills' frontmatter requires reading this first.

Backend: `basic-memory` MCP server. Notes are markdown files on disk;
tags + `[[wikilinks]]` are the index. Folder layout is for humans only —
retrieval is by tag.

These conventions are guidance, not law. Deviate when the cost of
conforming outweighs the benefit — but say so in the note (one line:
"deviation: <what> because <why>") so the next reader knows it was
deliberate. When a deviation becomes a recurring pattern, update this
file rather than letting drift go undocumented.

Every note belongs to a category: either an issue (`issue-<N>`) or
`utility` (anything not tied to an issue — branch tooling, local
workflow, etc.). New categories may be added later. The tree shape
and note kinds below apply to the issue category. Utility notes are
flat and just need the scope sentence + tags `ros2`, `rclcpp`,
`utility`, `<topic>`.

All notes are edit-in-place. If a past entry is wrong, fix it
directly. No append-only kinds, no supersede chains.

## Tree shape (issue category)

Per issue, notes form a tree rooted at `status`.

- **status** is the root. One short paragraph: what the issue is, where
  we are, next step. Every other note for this issue is reachable from
  here, directly or transitively.
- **children** (`reproduction`, `callflow`, `fix-plan`, `decisions`,
  `findings`, `open-questions`) each link *up* to `status` and
  *sideways* only when a real dependency exists.
- **grandchildren** appear only when a child gets too large to scan.
  E.g. `callflow` may split into `callflow-executor` and
  `callflow-waitset`. Don't pre-split — split only when scanning fails.

## Scope sentence rule

Every note's first line states its scope in one sentence.
Example: *"This note covers the rcl→rmw boundary in issue-1234."*
If you cannot write that sentence, the note is too vague — fix the
scope or merge the note back into its parent. This is the single
most important discipline; without it notes drift into useless soup.

## Note kinds

| Kind            | Purpose                                                |
|-----------------|--------------------------------------------------------|
| `status`        | Where we are now + next step. Entry point for sessions.|
| `reproduction`  | Exact steps/commands/configs that trigger the bug.     |
| `callflow`      | The code path under investigation. See format below.   |
| `fix-plan`      | Current proposed change. Replaced wholesale on pivot.  |
| `open-questions`| Unknowns. Removed when answered (answer → findings).   |
| `findings`      | What we learned about the code/bug.                    |
| `decisions`     | Choices made and why.                                  |

All kinds are edit-in-place. Keep them current; staleness is a bug.

Not every issue needs all seven. `status` is mandatory; the rest grow
on demand.

## Callflow format

Prose call flows go stale fastest. Store as a bulleted tree of
`file:line — function — one-line description`, not paragraphs.
This lets a re-read grep the refs against current code in seconds
instead of re-parsing English.

## Tagging

Every note carries: `ros2`, `rclcpp`, `issue-<N>`, `<kind>`.
The `issue-<N>` tag is the join key — it pulls the whole issue back
in one query. Tag-wise each note belongs to **exactly one** issue,
even when content references another (see cross-issue links below).

## Linking

- `status` links down to whichever children exist via `[[wikilinks]]`.
- Children link up to `status` and sideways only on real dependency
  (e.g. a finding that pins to a specific callflow node).
- Cross-issue links are allowed via `[[wikilink]]` when one issue's
  finding informs another, but tagging stays single-issue. Otherwise
  tag queries get noisy.
- Links are deliberate. Don't link two notes just because they share
  a tag — only when one note actually depends on the other.

## What NOT to store

- Verbatim copies of code that lives in the repo. Link to `file:line`
  instead. Memory should be reasoning *about* the code, not a worse
  duplicate of it.
- Generic ROS 2 / rclcpp knowledge available in upstream docs. Store
  what is specific to *this* investigation.
- Transient debugging output longer than a few lines. Summarize it.
- **Commit hashes.** Branches get amended, rebased onto upstream, or
  squashed; SHAs rot and become orphan refs that mislead future reads.
  Reference changes by file + symbol + behaviour ("the `ignore_callbacks`
  flag on `NodeParameters::declare_parameter`"), not by hash.

## Fixing wrong memory

All kinds are edit-in-place. When a read surfaces a contradiction
with current code or another note, overwrite the wrong fact.
No background sweep — fix on-demand.

## Deletion

`status` lives forever. Everything else is disposable:

- `open-questions` entries: delete when answered (answer → findings).
- `reproduction`, `callflow`, `fix-plan`, `findings`, `decisions`:
  delete when no longer true *and* no longer historically interesting.

Without a deletion rule, the issue folder grows monotonically and
old context starts polluting new chats.

## Issue close-out

When an issue ships (PR merged / closed wontfix):

1. Write one final note: `issue-<N>-postmortem`, tagged
   `ros2, rclcpp, issue-<N>, postmortem`. Contents: one-paragraph
   summary, the fix in one paragraph, plus whatever from
   `findings`/`decisions` is worth keeping (merged in or linked).
2. Delete every other note for that issue.

You almost never need callflow for a closed issue; you do want one
searchable summary.

## Filesystem layout (humans only)

When calling `write_note`, set `folder` to `<issue-tag>`. Retrieval
does not depend on this — it's purely for human browsing and backup.
