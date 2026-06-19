# basic-memory tool guide

How to drive the basic-memory MCP tools around known footguns.

## `edit_note` fails with "Missing required argument: content"

If `edit_note` returns a Pydantic error about missing `content`, the
target note is probably **poisoned** — not your payload. A previous
write left a line with long prose around an inline `[[wikilink]]`,
and re-indexing now fails on that line for every subsequent edit
(basic-memory issue #721).

Do this:

1. `read_note` the target. Find any bullet/paragraph with prose
   around `[[wikilinks]]` longer than ~200 chars **before** the
   `[[`.
2. Open the file directly (bypassing MCP) and shorten that line —
   either move the wikilink to the start (`- [[Foo]] — long
   description...`) or break the prose up.
3. Retry the `edit_note`.

Do NOT just retry the same `edit_note` payload — it will fail again.

## Parameter naming

`edit_note` accepts these aliases (basic-memory issue #690), so any
of these work:

- replacement text: `content` | `new_content` | `replacement` | `replace_with`
- search text: `find_text` | `find` | `old_text` | `old_content` | `search`

## XML parameter ordering workaround for "Missing required argument: content"

Separate from the poisoned-note failure mode above: the
Claude-Code-side XML→JSON converter sometimes drops the `content`
parameter when the XML places `<parameter name="find_text">` (with a
long body) **before** `<parameter name="content">`. The exact same
payload with `content` placed first parses fine. Observed on
multi-line `find_text` ~500+ chars with backticks and `[[wikilinks]]`.

If `edit_note` returns `Missing required argument: content` and the
target note is NOT poisoned (test by trying a tiny throwaway edit
first), re-send with `<parameter name="content">` ordered **before**
`<parameter name="find_text">`. Do not retry the same XML ordering.
