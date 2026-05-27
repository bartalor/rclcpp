# File map: what each thing is for

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
