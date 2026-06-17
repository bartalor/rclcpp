---
name: code-walkthrough
description: Use when walking the user through a code path step by step — tracing how execution reaches a point, how a bug propagates, how a feature wires up. Forbids teleporting between locations and bare file references.
disable-model-invocation: true
---

# Code walkthrough

Three rules. All three apply on every step. No exceptions.

## 1. One step at a time

A step is one location in the code. Explain it, then **stop and wait** for the user to say "next" (or equivalent). Never chain steps in a single message. Never preview later steps. The user drives the pace.

A "location" is a contiguous block — usually 1 to ~20 lines — that does one conceptual thing. If you find yourself wanting to explain two things, that's two steps.

## 2. Every code reference is a line-numbered link

Never write a bare file path. Never write a symbol name without a link to its definition or call site. Every reference must be a markdown link to a specific line:

- `[node_parameters.cpp:762](rclcpp/src/rclcpp/node_interfaces/node_parameters.cpp#L762)` ✓
- `node_parameters.cpp` ✗
- `NodeParameters::set_parameters_atomically` (no link) ✗

When mentioning a function, link to the **actual implementation that gets called**, not just the public declaration. If both are worth pointing at, link both and say which is which.

## 3. Every transition shows the actual call

When moving from step N to step N+1, the first thing in step N+1 is a "how we got here" paragraph that:

- Names the location step N ended at, with a line-numbered link.
- Shows the literal call site that connects N to N+1 — the line of code that does the call, with a line-numbered link.
- Names the function that line lands in — with a line-numbered link to that function's definition (the implementation, not the interface).

If the transition is not a function call — e.g. "the function returns, then later the user calls a different entry point on a fresh stack" — say so explicitly. Don't pretend a non-call is a call.

If you're tempted to skip a frame because it's "obvious," don't. The user is walking the path to understand it; skipped frames are exactly where confusion lives.

## What this skill forbids

- Teleporting: jumping to a new location without showing the call that connects it to the previous one.
- Bare references: any file path, function name, or symbol mentioned without a line-numbered link.
- Batching: explaining multiple steps in one message.
- Previewing: "in the next step we'll see..." — let the next step speak for itself when the user asks for it.
- Faking the chain: describing a transition as a function call when it isn't, or vice versa.
