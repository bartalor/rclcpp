---
name: replicate-ros2-ci-build
description: Use when the user wants to reproduce a specific ci.ros2.org build (Windows, Linux, etc.) in GitHub Actions to debug a failing test or rebuild a known reference. Generic guidance below; Windows specifics are fleshed out, Linux is not yet documented.
---

# Replicating a ci.ros2.org build in GitHub Actions

> **Maintenance rule:** every time you learn something new while doing this work — a new gotcha, a new check, a Dockerfile detail that changed, a tool that moved — update this file before the session ends. The whole point of this skill is to accumulate that knowledge so the next session doesn't re-learn it. If you don't write it down, it's lost.
>
> **When you add knowledge, do NOT hardcode build-specific values (version numbers, SHAs, step numbers, RMW names, env values, URLs, file paths inside the image, etc.). Those will be wrong by the next build. Instead write *where to look*: "grep the log for X", "find the setup step that does Y", "check the `--foo` arg in the invocation line." The skill must stay useful when the specifics change.
>
> **When you add knowledge, put it in the right section.** Generic findings (apply to any platform) go in the Generic section; platform-tied findings go under that platform. If you're tempted to add a Linux note, start a Linux section rather than smuggling it into Windows.

---

# Generic (applies to any ci.ros2.org build)

## When this applies

The user wants to debug a failing upstream CI test by re-running the same build in their own GitHub Actions workflow. The goal is **bit-faithful reproduction of a single build number** — not "a ROS2 CI" in general.

## Capturing the reference build log

You need the full ci.ros2.org build log cached locally before any checks work. The URL pattern is `https://ci.ros2.org/job/<job_name>/<build_number>/consoleText`. Some jobs need credentials.

**Hard rule:** the ci.ros2.org auth token must NEVER enter Claude's context. The user has it in `~/.netrc` (which is on Claude's settings.json deny list — don't try to read it, don't ask the user to share it, don't suggest where it might be). The user fetches the log themselves; you work from the cached file (e.g. `/tmp/ci_<job>_<NNNNN>.log`).

## What we mirror (and how)

A GitHub Actions workflow that pins everything the upstream build pinned. Extract pin values from the build's log; do not invent or "tidy up". The set of pins is platform-specific (see platform sections below).

The build/test colcon invocations come **verbatim** from the cached log — search for `==>` markers around `colcon build` and `colcon test` lines. The bug class we're trying to avoid is exactly the silent divergence from hand-written args.

## Generic checks (run for any build)

Each check exists to catch the same class of bug: **a silent divergence that explodes tens of minutes into the build**.

- **Mirror every colcon invocation verbatim.** Grep the log for `==>` markers to find every colcon invocation. Mirror each one's flags exactly. Do not hand-edit.

- **`ROS_DOMAIN_ID`.** Grep the log for `ROS_DOMAIN_ID=` to see what the docker/CI env sets (a non-zero value avoids cross-job interference on shared CI). Add the same value to the workflow env block. Even if no test you care about asserts on it, mirror anyway — discovery-test fixtures can pick it up implicitly.

- **`--ignore-rmw` flags.** Grep the log for `--ignore-rmw` to see which RMWs the build excludes. Your matrix must not include any RMW in the ignore list, or your build is testing something ros2.org isn't and has no reference to compare to.

- **pip-install steps (any colcon plugin or other dep).** Look for `pip install` invocations in the build setup phase — these are easy to miss because they happen before the colcon command line, not in it. Replicate each as a separate workflow step.

- **Package set comparison.** `grep -c '^Finished <<<' <log>` gives the count of packages built. After your workflow runs, compare that count. A mismatch means your `ros2.repos` resolution gave a different graph (missing repo, extra repo, divergent commit). Manual check at log review time; not worth automating.

## Layout pattern (reusable across repos)

A useful structure for the replication workflow:

- A workflow file under `.github/workflows/` with a `workflow_dispatch` matrix input.
- A small Python wrapper checked into `.github/` that reads a gitignored local JSON config (e.g. RMW list) and invokes `gh workflow run` with a JSON-encoded matrix.
- The local config goes in `.git/info/exclude` (not `.gitignore`) so per-developer settings don't pollute the repo.

This pattern (matrix input from local config + Python wrapper) is reusable for any "run workflow with my chosen matrix" use case.

## What we considered and rejected (generic)

- **Configure-only preflight** (`colcon build --cmake-force-configure` or similar). Doesn't work cleanly because each package's configure needs upstream packages' install trees; `find_package` failures during preflight aren't real errors.
- **Drift-detection assertion step** (compare our cmake-args to expected). Premature abstraction with one consumer; user pushed back hard.

## Process notes for working this with the user

- **One check at a time.** Don't batch. Explain what you'll do and why *before* running each check. The user will say `go` or `yes` to proceed.
- **Address each gap before the next check.** Don't pile up findings — fix as you find.
- **Never offer to push or force-push proactively.** The user will initiate if they want it.
- **No mkdir / file creation without permission.** Even for an "obvious" parent directory.
- **The `colcon build` failure mode you're racing against:** tens of minutes of work that explodes on the first non-matching arg. Each check is cheap; the alternative is another full-build round-trip.

---

# Windows-specific

## The Windows core architecture

ci.ros2.org's Windows builds run inside a docker image built per build. The general shape (verify against the specific build's log — versions, step numbers, and even the broad sequence can change):

1. Installs VS BuildTools, pixi, downloads `pixi.toml` from `ros2/ros2@<distro>`, runs `pixi install`. **Look up the exact pixi version and pixi.toml SHA in the log's `Step N/M` Dockerfile lines.**
2. Runs `pip install` for any colcon plugins or other deps. The exact package set and step number is build-specific — grep the log for `pip install`.
3. Installs RTI Connext DDS (proprietary, copied from a private path).
4. CMD invokes ros2_batch via `pixi run --frozen python run_ros2_batch.py %CI_ARGS%`.

`run_ros2_batch.py` lives in the **Jenkins workspace**, mounted at `C:\ci` via `-v "C:\J\workspace\ci_windows":"C:\ci"`. It is NOT in the docker image. It's NOT in any single public repo we could find — chasing it down was a dead end. Don't try to invoke `run_ros2_batch.py` directly.

## Windows pins to extract from the log

The mirror runs on a `windows-2022` GitHub Actions runner. Pins to extract:

| Pin | Where to find it in the log |
|---|---|
| `PIXI_VERSION` | the Dockerfile `Step N/M : RUN ... pixi-...zip` line — the URL has the version |
| `PIXI_TOML_SHA` | `ros2/ros2` HEAD SHA at build start time — find a commit on the `<distro>` branch with a timestamp at-or-just-before the build's start; the Dockerfile uses a ref like `refs/heads/<distro>`, NOT a SHA, so you must reconstruct |
| `CI_REPOS_URL` | the build's `--repo-file-url` arg, search for it in the ros2_batch CI_ARGS line |

## Windows-specific checks

- **PATH / wrappers (env.bat vs pixi run).** ros2_batch wraps colcon with `env.bat C:\pixi_ws\.pixi\envs\default\Scripts\colcon.EXE`. We use `pixi run colcon`. When mirroring the `==>` invocations, expect the wrapper to add `vcs import --force --retry 5` and `colcon mixin remove/add/update default` before the build.

- **pixi install vs pixi run --frozen.** Dockerfile uses plain `pixi install` (no `--frozen`) at build time, then runtime uses `pixi run --frozen` (asserts env unchanged). On GitHub Actions we do `pixi install` fresh per run — *cannot* use `--frozen` at runtime if the workflow does any `pip install` step, because pip adds packages outside pixi's conda-meta tracking and invalidates the lock. Accept the drift; it's small.

- **colcon mixin usage.** ros2_batch sets up `~/.colcon/mixin/default/` with mixin files. Grep the log for `--mixin ` (space-suffixed) — if no hits, no command consumes them and the setup is cosmetic. Mirror it anyway for parity (the step is cheap and keeps step-by-step diff clean).

- **vcvars script.** Grep the log for `vcvars` to see which variant the build used (`vcvarsall.bat <target>` vs `vcvars64.bat` vs `vcvars32.bat` — each sets up a different Hostx* toolchain). The naive default of `vcvars64.bat` may not match. Mirror exactly what's in the log.

## What we considered and rejected (Windows-specific)

- **Run ros2_batch directly.** Would eliminate all hand-typed args. Rejected because (a) `run_ros2_batch.py` is in a non-obvious Jenkins location, (b) RTI Connext is proprietary, (c) ros2_batch assumes mount paths `C:\ci` / `C:\pixi_ws` that we can't easily fake.
- **Pure Docker** (build the actual ci.ros2.org image and run it). Would be most faithful but needs Windows + Docker locally. Out of scope if the user wants GH Actions.
