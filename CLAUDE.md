# Branching

`bar/devcontainer` is the personal-preferences root: `.devcontainer/`, `.vscode/`, `CLAUDE.md`, etc.

# C++ navigation

For navigating rclcpp C++ — finding symbol definitions, callers, types,
inheritance — prefer the `cpp` MCP server (`mcp__cpp__search_symbols`,
`mcp__cpp__analyze_symbol_context`, `mcp__cpp__get_project_details`)
over grep/Read. It is clangd-backed against the overlay build and
resolves overloads, templates, and macros correctly. Fall back to
grep/Read only when the symbol isn't indexed (third-party headers,
generated code) or for non-code files.
