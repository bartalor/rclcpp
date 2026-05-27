# `.github/` — instructions for Claude

Read this before touching anything under `.github/` or proposing CI changes for this branch.

This file holds rules and pointers that survive across sessions. It complements the top-level `CLAUDE.md` (branching strategy, persistence, colcon) and the skill at `.claude/skills/replicate-ros2-ci-build/SKILL.md` (reproducing ci.ros2.org builds in GHA).

---

## What we're trying to reproduce — and what we are NOT

**The repro target is PR #3143's CI failures, not #27999's baseline failures.** PR #3143 (`bar/issue-2898`) is a one-function source change; ci.ros2.org Windows #27999 (against rolling) produced 9 failing tests in `test_rosidl_buffer` under `rmw_fastrtps_cpp`, and the same failures also appeared on the PR's own build (#27970). Per `ci-flake-analysis.md`, every PR-#3143 failure was classified as flake / infra / environmental — none caused by the PR. So #27999 is our **reference environment**, not the failure cause: we're reproducing the *environment* in which those tests fail regardless of branch.

For diagnosing the GHA run: success = the 9 `test_rosidl_buffer` tests fail the same way they do on ci.ros2.org. The **job** is expected to succeed (it runs tests and uploads results); what we watch is the **test outcomes** inside the artifact. If those 9 tests pass (or don't run), we failed to reproduce the env — not "the PR is safe to merge". Biggest known env deltas: see `windows-repro.md`'s rationale section.

Use common sense about what PR #3143 could plausibly have caused. Look at its actual changes and reason about whether they can reach the failing test at all.

---

## Build artifacts and other downloads

See [`.github/download-locations.md`](download-locations.md) for the rule (ask before downloading) and the established `/tmp/` paths.

---

## File map

See [`.github/file-map.md`](file-map.md) for what each file under `.github/` is for.

---

### GHA builds

**NEVER start, dispatch, or cancel a GHA workflow run on your own without explicit permission.** This includes `gh workflow run`, `gh run cancel`, re-dispatching after an amend, etc. Always ask first.

### Branch discipline

Per the top-level `CLAUDE.md`: `bar/devcontainer` is the personal-preferences root (`.devcontainer/`, `.vscode/`, `CLAUDE.md`, skills under `.claude/skills/`). Everything CI- or PR-related (anything under `.github/workflows/`, `.github/ci-flake-analysis.md`, this file) lives on the working branch (currently `bar/issue-2898-test`).

When you stage changes that touch both areas, **commit them on separate branches**. Check `git ls-files -- <path>` to see which branch a file lives on if uncertain.

---

## Tagging milestones

When a workflow file reaches a meaningful state (last commit that triggered an end-to-end successful run, last commit of a now-replaced approach, etc.), annotate-tag it: `git tag -a vN.MM <SHA> -m "milestone: ..."` then `git push origin vN.MM`.

---

## additional reminders

Keep `windows-repro.md` up to date with `windows-repro.yml`.
