# memory-mcp conventions (rclcpp)

Long-lived project notes for this repo live in memory-mcp, not in files. Do
not create `.claude/design_decisions/` or similar note trees.

## Required metadata on every store

Every memory written from this repo MUST carry:

- `tags`: comma-separated string, starting with **`rclcpp`** as the first
  tag, followed by topic tags (e.g.
  `rclcpp,issue-2876,parameters,deadlock`). The leading `rclcpp` tag is the
  project scope filter — without it, recall across multiple projects
  becomes impossible.
- `type`: pick from the ontology — typically `decision` (why we chose an
  approach), `learning` (a gotcha / non-obvious fact discovered), `bug` (a
  recorded defect + root cause), `reference` (durable factual lookup), or
  `convention` (a repo rule).

When the note concerns a specific source file, anchor it by **fully
qualified symbol name** in the content (e.g.
`NodeParameters::declare_parameter`,
`rclcpp::detail::declare_parameter_or_get`) — never by line number, which
rots on the first edit above it. Include the relative path once so future
searches on the path also hit.

## Content shape

Write the **why**, not the what — the diff already shows what changed.
Capture reasoning, constraints, alternatives considered and rejected,
non-obvious tradeoffs or invariants.

One memory per coherent decision/fact. Do not concatenate unrelated notes
into one blob; small memories search better and update cleanly.

## Issue / PR linkage

If the note is tied to an upstream issue or PR, include the URL in the
content (e.g. `https://github.com/ros2/rclcpp/issues/2876`) AND add the
`issue-<number>` tag (e.g. `issue-2876`). This makes "what do we know
about 2876?" a one-query recall.

## Linking memories to each other

Memories can reference each other; this is what turns isolated notes into a
graph (e.g. a `bug` memory linked to the `decision` that resolved it,
linked to the `learning` extracted from the fix). Memories are identified
by their `content_hash` — capture the hash returned by `memory_store` when
you intend to link later.

Two complementary mechanisms:

1. **Inline cross-reference in content.** When a note relies on another,
   name the other memory by a stable, searchable handle in the content —
   its `content_hash`, or a unique phrase that `memory_search` will
   reliably hit. Cheap, no extra tool call, survives if the graph is
   unavailable.

2. **Graph traversal via `mcp__memory__memory_graph`.** To explore
   relationships, use `action: "connected"` (BFS), `"path"` (shortest
   path between two hashes), `"subgraph"` (neighbourhood), `"infer"`
   (transitive), or `"suggest"` (proposed links from shared neighbours).
   Use this when answering "what else do we know about the same area?" —
   start from one known hash and walk out.

When you store a memory that is the direct consequence or counterpart of
another (e.g. the decision that fixed a recorded bug), include the other
memory's `content_hash` in the new memory's content so the link is
discoverable both by graph traversal and by plain search.

## Correcting or removing memories

Default preference: **update over delete.** A wrong-but-related memory is
more useful corrected than gone — its `content_hash` may already be
referenced by other memories, and deleting it silently breaks those
links.

- **Small fix (typo, missing tag, wrong type, added cross-ref):**
  `mcp__memory__memory_update { content_hash, updates: { ... } }`.
  Replaces the listed fields in place; preserves the original `created_at`
  by default.
- **Substantive correction where the old wording was actually wrong and
  should be retained as history:** same call with `versioned: true` and
  the corrected text in `updates.content`. The old memory is marked
  *superseded* (hidden from search by default; re-include with
  `include_superseded: true`). Use this when a future reader benefits
  from seeing the wrong claim and its replacement together — e.g. a
  root-cause note that was diagnosed wrong the first pass.
- **Two memories that genuinely contradict each other** (e.g. the same
  fact stored two ways in two sessions): check
  `mcp__memory__memory_conflicts`, then
  `mcp__memory__memory_resolve { winner_hash, loser_hash }`. Don't
  blind-delete one — let the conflict tool record the resolution.
- **Delete only when the memory has no enduring value** — pure noise,
  accidental capture, test/scratch content, or a duplicate of a memory
  you prefer to keep. Always preview with `dry_run: true` first; never
  delete by tag alone without inspecting which hashes will go. Filter as
  narrowly as possible (specific `content_hash`, or `tags` + time bound).

When you correct a memory that other memories cite by `content_hash`,
remember that `versioned: true` changes the hash. If the old hash was
referenced inline elsewhere, either update those references or prefer
in-place (`versioned: false`) when the change is small enough that
history isn't worth keeping.

## Anti-patterns

- Writing project notes to `.claude/design_decisions/*.md` or any other
  file tree. Memory-mcp is the store; files are not.
- Memories without the `rclcpp` tag (unfindable when filtering by
  project).
- Anchoring notes to line numbers instead of fully qualified symbol
  names.
- One giant "everything about #2876" memory instead of several focused
  ones.
- Storing related memories without any cross-reference, so a future
  search surfaces one but not the other half of the same story.
- Deleting a wrong memory instead of updating it — orphans inbound
  `content_hash` references and erases context a future reader would
  need to understand why the wrong belief existed.
- Bulk `memory_delete` by tag without a `dry_run` preview.
