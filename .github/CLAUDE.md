# `.github/` — instructions for Claude

Read this before touching anything under `.github/` or proposing CI changes for this branch.

This file holds rules and pointers that survive across sessions. It complements the top-level `CLAUDE.md` (branching strategy, persistence, colcon) and the skill at `.claude/skills/replicate-ros2-ci-build/SKILL.md` (reproducing ci.ros2.org builds in GHA).

---

## What we're trying to reproduce — and what we are NOT

**The repro target is PR #3143's CI failures, not #27999's baseline failures.**

- PR #3143 (`bar/issue-2898`): "node_parameters: reject non-finite values in floating-point range check". A one-function source change in rclcpp.
- ci.ros2.org Windows #27999 ran against rolling and produced 9 failing tests in `test_rosidl_buffer` under `rmw_fastrtps_cpp`. **Those same failures also showed up on the PR #3143 build (#27970).** Per `ci-flake-analysis.md`, every PR-#3143 failure was classified as flake / infra / environmental — none caused by the PR's changes.
- So #27999 is our **reference environment**, not the failure cause. We are trying to reproduce the *environment* in which the same tests fail regardless of branch.

This matters for diagnosing the GHA run: success = the 9 `test_rosidl_buffer` tests fail the same way they do on ci.ros2.org. The **job** is expected to succeed (it runs tests and uploads results); what we're watching is the **test outcomes** inside the artifact. If those 9 tests pass (or don't run), we failed to reproduce the env — not "the PR is safe to merge". The biggest known env deltas are in `windows-repro.md`'s rationale section.

---

## Build artifacts and other downloads

**Never invent a path or "convention" on the fly.** Before downloading anything (GHA artifacts, run logs, release tarballs, anything), ask the user where it should go. One pre-existing file in `/tmp/` is not a convention — it's one file. Do not generalize from it.

### Established locations

- **GHA run artifacts** (`gh run download <id>`): `/tmp/gha-artifact-<run-id>/`
- **GHA run logs** (`gh run view --log`): `/tmp/gh-cli-cache/run-log-<run-id>-*.zip` (gh's own cache dir)

If you need to download something not listed above, ask the user where it goes, then add the location here in the same commit.

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
