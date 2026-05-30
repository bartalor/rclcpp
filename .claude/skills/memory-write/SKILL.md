---
name: memory-write
description: Use whenever storing, updating, correcting, or deleting long-lived notes about this repo via memory-mcp — design decisions, bug root causes, ROS/build gotchas, conventions. Also triggers on phrases like "remember this", "note this for next time", "save that", "store this fact", "update that memory", "we know this now". Do not write project notes to files under .claude/ (e.g. .claude/design_decisions/); use memory-mcp instead.
---

# Project memory — WRITE side (rclcpp)

Before doing anything: read `.claude/memory-mcp.md` for the conventions
(required tags incl. leading `rclcpp`, ontology types, symbol anchoring,
issue/PR linkage, linking via `content_hash`, update vs delete rules,
anti-patterns). This skill only adds the write-side workflow on top.

## Workflow when storing a new memory

1. **Search first.** Always invoke the read side first
   (`memory-read` / `mcp__memory__memory_search`) to see whether a
   relevant memory already exists.
   - If yes and still correct: do nothing — don't store a duplicate.
   - If yes but now wrong/incomplete: **update** it instead of storing a
     new one (see `.claude/memory-mcp.md` "Correcting or removing
     memories").
   - If no: proceed to store.
2. **Store with full metadata.** Use `mcp__memory__memory_store` with the
   required tags (leading `rclcpp`) and `type` per the shared doc.
3. **Capture the returned `content_hash`** if the memory is likely to be
   linked to from a future note (e.g. a `bug` that will be paired with a
   `decision`). Include the hash inline in the linked memory's content
   when you store it.

## When to use which write tool

- `mcp__memory__memory_store` — new memory.
- `mcp__memory__memory_update` — fix metadata or content on an existing
  memory (in place, or `versioned: true` to keep the wrong version as
  superseded history). Default to in-place; see shared doc for when
  versioning is worth the hash change.
- `mcp__memory__memory_resolve` — pick a winner between two memories
  flagged by `mcp__memory__memory_conflicts`. Don't blind-delete the
  loser.
- `mcp__memory__memory_delete` — only for pure noise / accidental
  captures, and always with `dry_run: true` first.

## Confirm before destructive operations

`memory_delete` (especially by tag) and `memory_update` with
`versioned: true` change recall behaviour for future sessions. State what
you're about to do and confirm with the user before running them, unless
the user has already authorized the specific operation in this turn.
