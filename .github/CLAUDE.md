# `.github/` — instructions for Claude

Read this before touching anything under `.github/` or proposing CI changes for this branch.

This file holds rules and pointers that survive across sessions. It complements the top-level `CLAUDE.md` (branching strategy, persistence, colcon) and the skill at `.claude/skills/replicate-ros2-ci-build/SKILL.md` (reproducing ci.ros2.org builds in GHA).

---

## What we're trying to reproduce — and what we are NOT

**The repro target is PR #3143's CI failures, not #27999's baseline failures.**

- PR #3143 (`bar/issue-2898`): "node_parameters: reject non-finite values in floating-point range check". A one-function source change in rclcpp.
- ci.ros2.org Windows #27999 ran against rolling and produced 9 failing tests in `test_rosidl_buffer` under `rmw_fastrtps_cpp`. **Those same failures also showed up on the PR #3143 build (#27970).** Per `ci-flake-analysis.md`, every PR-#3143 failure was classified as flake / infra / environmental — none caused by the PR's changes.
- So #27999 is our **reference environment**, not the failure cause. We are trying to reproduce the *environment* in which the same tests fail regardless of branch.

This matters for diagnosing why our GHA run goes green: if the failures are environmental (FastRTPS discovery, network setup, race conditions), then matching the test scope is not enough — we have to match the environment. The biggest known env deltas are in `windows-repro.md`'s rationale section.

If a future session sees a green run and concludes "PR is safe to merge", **that's wrong**. A green run means we failed to reproduce the env, not that the failures are gone.

---

## File map: what each thing is for

### `.github/workflows/windows-repro.yml`

The live workflow. **Rebuilds ci.ros2.org Windows build #27999's docker image and runs the reference's own `docker run` invocation on a GHA `windows-2022` host.** Three intentional deviations from #27999's Dockerfile (base image kernel bump, drop VS 2019, drop Connext) — each one explained in `.github/windows-repro.Dockerfile`'s header comment and in `windows-repro.md`.

If you change this file, **also update `windows-repro.md`** in the same commit. The two are a pair.

### `.github/windows-repro.Dockerfile`

The actual Dockerfile that `windows-repro.yml` builds. **Pins (`PIXI_VERSION`, `PIXI_ZIP_SHA256`, `PIXI_TOML_SHA`) are passed in via `--build-arg`** from the workflow's `env:` block — the workflow stays the single source of truth for pin values. Header comment documents the three deviations from #27999.

Previously this content was emitted by a PowerShell heredoc inside the workflow's "Write Dockerfile" step. That approach died on Step 11 in run `26443931213` because the backtick Dockerfile-escape and PowerShell's own backtick-escape collided on the one RUN line that embeds quotes. The extraction also makes the file diffable against #27999's Dockerfile (recoverable from `/tmp/ci_windows_27999.log` Step lines) and locally buildable without GHA.

If you change this file, **also update `windows-repro.md`** in the same commit (it's part of the pair with the workflow).

### `.github/workflows/windows-repro.md`

Line-by-line walkthrough of `windows-repro.yml`. Every meaningful line in the workflow is justified against:
- A specific line number in `/tmp/ci_windows_27999.log` (the cached console log of build #27999), or
- An upstream docs URL, or
- A SKILL.md rule, or
- Flagged as **⚠ UNJUSTIFIED** with the reason.

When you change `windows-repro.yml`, walk through the changed lines and update the matching sections of `windows-repro.md`. If you can't justify a line, mark it `⚠ UNJUSTIFIED` rather than guessing.

### `.github/windows-repro-run.py`

A Python wrapper that reads `.github/windows-repro.local.json` (gitignored) and invokes `gh workflow run` with a JSON matrix.

**Status: stale from the pre-v1.01 bare-runner approach** (when `windows-repro.yml` had a matrix input across RMWs). The current workflow takes no input. **Do not delete it yet** — when we raise the RMW-matrix fidelity knob it'll come back into use. Don't fix it for the current workflow either; the current workflow is single-RMW deliberately.

### `.github/windows-repro.local.json`

Local config consumed by `windows-repro-run.py`. **Gitignored via `.git/info/exclude`** (NOT `.gitignore`) so per-developer settings don't pollute the repo. Same stale-status as the script above.

### `.github/ci-flake-analysis.md`

Frozen report classifying every CI failure observed on PR #3143 across the five Jenkins jobs (linux, linux-aarch64, linux-rhel, windows #27970, windows #27999) plus the GHA windows-repro run. Every failure was classified as flake / infra / environmental — nothing PR-caused.

**Don't edit this file lightly.** It's a point-in-time analysis tied to specific build numbers. If you're doing a fresh analysis, create a new file, don't overwrite.

---

## Cached external data (not in this repo)

Three files in `/tmp/` are referenced throughout `windows-repro.md` and `ci-flake-analysis.md`. They're transient — `/tmp/` doesn't survive a reboot — so if you start a session and these are missing, ask the user to refetch with `curl --netrc` (see "Auth tokens" below).

- `/tmp/ci_windows_27999.log` — console log of ci.ros2.org Windows build #27999. Fetched from `https://ci.ros2.org/job/ci_windows/27999/consoleText`. Authoritative source for all `log:NNNN` citations in `windows-repro.md`.
- `/tmp/ci_windows_27999_testreport.json` — Jenkins testReport JSON for the same build. Fetched from `https://ci.ros2.org/job/ci_windows/27999/testReport/api/json` (plain URL — do NOT use `?tree=...` filters, they return 503 / empty data).
- `/tmp/win_27970_report.json` — testReport for the related #27970 build (also referenced in `ci-flake-analysis.md`).

**Do NOT recreate `.ci-cache/` or similar persistent caches in the repo.** A previous session created `.ci-cache/` with 134M of Jenkins JSON; it had to be deleted manually. `/tmp/` is sufficient — same-session cache, dies between sessions, doesn't clutter the working tree. If you find yourself reaching for a persistent cache, you're solving the wrong problem.

---

## Auth tokens

The ci.ros2.org auth token **must NEVER enter Claude's context**.

- The user has it in `~/.netrc`. That file is on Claude's settings.json deny list (Read/Write/Edit blocked).
- **Do not** try to `cat` it, ask the user for it, or suggest where it might be.
- Use `curl --netrc <URL>` so the token stays out of arguments and output. The flag tells curl to read `~/.netrc` itself.
- For private API calls (`gh api ...`), use `gh` — it manages its own token. Don't read `~/.config/gh/hosts.yml`.

---

## Rules I have repeatedly broken — and what to do instead

### Never dispatch a new workflow run when an equivalent one is in flight

If the user asks for "a fresh run" after you just amended a workflow, **ask first** whether to cancel the old one or wait. The old run snapshotted the workflow file at dispatch time and keeps running even after you force-push a new commit. Dispatching a new run on top burns a second runner for identical output.

If you already dispatched and it's redundant, point that out immediately — don't quietly let two parallel runs burn ~2h30m of runner time each.

### Never cancel a running workflow run on your own

This is non-negotiable. The user's exact words: "don't fucking dare cancel, even by mistake a running job". Cancellation is always the user's call. You can:
- Tell them a run is redundant and offer to cancel.
- Mention that a stuck run could be cancelled.

But never `gh run cancel` without an explicit `yes` to that specific question.

### Never propose `cancel-in-progress: true`

The workflow's concurrency block must have `cancel-in-progress: false`. Commit `ac1c4305` (`ci(windows-repro): never auto-cancel in-flight runs`) established this. The skill at `.claude/skills/replicate-ros2-ci-build/SKILL.md` lists it under "What we considered and rejected (generic)". Don't reintroduce it.

### Never propose `--no-verify` or skipping hooks

If a hook fails, fix the underlying issue. Don't bypass.

### Never propose force-push proactively

If you've amended a commit that's already pushed, **wait for the user to ask** about the force-push. Don't volunteer "should I force-push?" — the user's instruction: "you piss me off stop asking if to force push if I want I'll ask."

If the user explicitly directs the amend and the consequence is obviously a force-push, you can do the push without re-asking — but in any other case, hands off.

### Never stash

The user does not stash. If you need to switch branches with uncommitted changes, either:
- Commit on the current branch first, then switch.
- Carry the changes across the switch (git allows this when the changes don't conflict).
- Ask the user how to proceed.

### Branch discipline

Per the top-level `CLAUDE.md`: `bar/devcontainer` is the personal-preferences root (`.devcontainer/`, `.vscode/`, `CLAUDE.md`, skills under `.claude/skills/`). Everything CI- or PR-related (anything under `.github/workflows/`, `.github/ci-flake-analysis.md`, this file) lives on the working branch (currently `bar/issue-2898-test`).

When you stage changes that touch both areas, **commit them on separate branches**. Check `git ls-files -- <path>` to see which branch a file lives on if uncertain.

### One question at a time

Never batch clarification questions. One yes/no question per turn, phrased so "yes" and "no" each map to a single concrete action. If you have three things to ask, ask the most blocking one and hold the rest. See `~/.claude/skills/one-question-at-a-time/SKILL.md`.

### Don't ask questions whose answer is obvious from context

If the user just said "go" or "yes" to a specific plan, execute that plan. Don't follow up with "should I really do step 3 of the plan I just proposed?" — they already said yes.

### Don't create files without permission

Even for an "obvious" parent directory. Show the plan first, get a `yes`, then write.

### Don't make up the user's intent

If a CLAUDE.md, workflow comment, or skill text seems to say something different from what the user just told you, **the user is authoritative**. Don't argue from stale docs.

---

## Tagging milestones

When a workflow file reaches a meaningful state (last commit that triggered an end-to-end successful run, last commit of a now-replaced approach, etc.), annotate-tag it: `git tag -a vN.MM <SHA> -m "milestone: ..."` then `git push origin vN.MM`.

Current tags:
- `v1.01` → `f2d3bfe7` — last commit of the bare-runner + pixi approach (triggered the only successful end-to-end run, `26400247793`, before we pivoted to the container approach).

When proposing a tag, **verify the SHA against actual data first** (e.g. `gh run view <RUN_ID> --json headSha`), not just commit-message similarity. A force-pushed branch may have rebased the original dispatch SHA into oblivion, in which case the tag should point at the post-rebase equivalent and the tag message must note the original orphan SHA.

---

## Process for changing the workflow

1. **Identify the fidelity layer being raised** (see SKILL.md "Fidelity layers"). State it explicitly in the commit message: "build scope: cheapest → faithful", "RMW matrix: single → full", etc.
2. **Update `windows-repro.yml`** with the change.
3. **Update `windows-repro.md`** to justify every changed line with `log:NNNN` citations or mark them `⚠ UNJUSTIFIED`.
4. **Don't auto-dispatch** the workflow after committing. Tell the user the change is ready; they'll dispatch when they want.
5. **If the change required rewriting history** (e.g. amending a pushed commit), wait for the user to authorize the force-push.
