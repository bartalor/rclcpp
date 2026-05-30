---
name: memory-read
description: Use BEFORE diagnosing a bug, explaining behaviour in a sensitive area, proposing a fix, or writing a new note — to check what we already know about this repo via memory-mcp. Also triggers on phrases like "do we have notes on", "what do we know about", "recall", "what did we decide about", "did we hit this before", "search memories". Always read before write (see also memory-write).
---

# Project memory — READ side (rclcpp)

Before doing anything: read `.claude/memory-mcp.md` for the conventions
(required tags incl. leading `rclcpp`, ontology types, symbol anchoring,
linking via `content_hash`, anti-patterns). This skill only adds the
read-side workflow on top.

## When to invoke

- Before proposing a fix or explaining behaviour in code you have not
  recently touched.
- Before writing a new memory (the write skill MUST defer to this skill
  first to avoid duplicates).
- When the user references an issue / PR / area we may have notes on
  ("did we hit this before?", "what did we decide about X?").
- When `understanding-before-proposing` would already require you to
  investigate — search memory as part of that investigation.

## Workflow

1. **Always filter by the project tag.** Every query must include
   `tags: "rclcpp"` so cross-project memories don't pollute results.
2. **Start with `mcp__memory__memory_search`** (semantic):

   ```
   memory_search { query: "<topic or symbol>", tags: "rclcpp", limit: 10 }
   ```

   For an issue/PR, include the `issue-<N>` tag:

   ```
   memory_search { query: "<topic>", tags: "rclcpp,issue-2876",
                   tag_match: "all", limit: 10 }
   ```

3. **Fall back to `mcp__memory__memory_list`** for categorical browsing
   when you want everything of a given type/tag rather than the most
   semantically similar hits (e.g. all `decision` memories tagged
   `parameters`).
4. **Walk the graph from a known hit.** Once `memory_search` returns a
   relevant `content_hash`, use `mcp__memory__memory_graph`
   (`action: "connected"` or `"subgraph"`) to surface linked memories
   (e.g. the `decision` paired with a found `bug`, the `learning`
   extracted from a fix).
5. **Check superseded versions only when the current memory looks
   stale or you're tracing a past wrong belief:**
   `memory_search { ..., include_superseded: true }`. Default off —
   superseded entries are hidden because they were corrected for a
   reason.

## What to do with what you find

- Cite the memory's `content_hash` (or a unique phrase from it) when you
  use it in your reply, so the user can audit the source.
- If recall surfaces a memory that is now **wrong or incomplete**, do
  not silently work around it — hand off to `memory-write` to
  update or version it.
- If recall surfaces **two memories that contradict**, that is a
  conflict: surface both to the user and use `memory_conflicts` /
  `memory_resolve` (write side) to resolve it.

## Don't

- Don't query without the `rclcpp` tag.
- Don't trust a single semantic hit blindly; if a memory will drive a
  non-trivial decision, walk its graph for context.
- Don't paste memory content verbatim into code or commits without
  reviewing it — memories capture past reasoning, which may be partly
  out of date even when not formally superseded.
