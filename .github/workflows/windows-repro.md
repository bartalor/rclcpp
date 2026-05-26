# `windows-repro.yml` — line-by-line research notes

This document explains every meaningful line in `.github/workflows/windows-repro.yml`. For every value, flag, arg, and step it answers:

1. **What it does.**
2. **Why it's there** — what choice in ci.ros2.org Windows Jenkins build #27999 (the reference) it mirrors, or what upstream tool constraint forces it.
3. **The evidence** — log line citations from `/tmp/ci_windows_27999.log` (cited as `log:NNNN`), or the upstream URL / docs page.

Citations like `windows-repro.yml:NN` refer to the workflow file. Citations like `log:NNNN` refer to `/tmp/ci_windows_27999.log` (use `sed -n 'NNNNp' /tmp/ci_windows_27999.log` to look them up).

Items I could not justify are flagged inline with **⚠ UNJUSTIFIED** and gathered at the end.

> **Approach history:** tag `v1.01` marks the last commit of the previous **bare-runner + pixi** approach (the workflow that triggered run `26400247793` — the only end-to-end build+test cycle of that path). The workflow on `HEAD` is a **pivot**: rebuild #27999's docker image and run the reference's own `docker run` invocation on a GHA `windows-2022` host. Closer to the reference because the test code now runs inside a Windows Server container with `--isolation=process` matching #27999's runtime.

---

## Reference build context (for grounding)

- Jenkins job: `ci_windows` build **#27999**. Triggered by user "Tomoya Fujita" (`log:3-4`), rebuild of #27970 (`log:5`). Build directory timestamp: `build_2026-05-14_22-52-35` (`log:127113`) — i.e. the build started 2026-05-14 ~22:52 UTC.
- The 9 failing tests (from `/tmp/ci_windows_27999_testreport.json`, `failCount: 9`): all in `test_rosidl_buffer` under `rmw_fastrtps_cpp` — three ctest-level tests (`test_test_to_test__rmw_fastrtps_cpp`, `test_test_to_cpu__rmw_fastrtps_cpp`, `test_nested_msgs__rmw_fastrtps_cpp`) plus their pytest cases.
- Reference Dockerfile base: `mcr.microsoft.com/windows/server:$WINDOWS_RELEASE_VERSION` with `WINDOWS_RELEASE_ID=2009` (`log:144-147`). Installs **both** VS 2019 BuildTools (`log:158-161`) and VS 2022 BuildTools (`log:164-167`), with VS 2022 selected at runtime via `--visual-studio-version 2022` (`log:290`).
- Reference docker run invocation: `log:308` (the load-bearing line for everything below).

---

## Intentional deviations from #27999 (header comment, `windows-repro.yml:3-14`)

Three deviations are documented at the top of the workflow file. Each has a reason that has been verified against the cached log:

### Deviation 1: base image `:ltsc2022` instead of `:2009`

`log:144-147` shows #27999's Dockerfile pinning `WINDOWS_RELEASE_ID=2009` (Windows Server 20H2, build 19042). GitHub Actions' `windows-2022` runners are Windows Server 2022 (ltsc2022, build 20348). Windows containers require the host/image kernel versions to match when running with `--isolation=process` — and process isolation is the only mode GHA hosts support (Hyper-V isolation needs nested virtualization that GHA runners don't expose).

So `:2009` would fail to start on a `windows-2022` host. We bump to `:ltsc2022` to match the host. This is the largest single drift from the reference; everything else about the docker run is faithful.

### Deviation 2: skip VS 2019 BuildTools

`log:290` shows `--visual-studio-version 2022` in CI_ARGS, and `log:2263` confirms VS 2022 is the toolchain actually invoked. The Dockerfile installs 2019 (`log:158-161`) only because the same image template historically served older ROS distros; for rolling on this build the 2019 toolchain is never exercised. Dropping it shaves ~10-15min off the image build.

### Deviation 3: skip RTI Connext install (Steps 25-30)

`/tmp/ci_windows_27999_testreport.json` shows every one of the 9 failing tests under `rmw_fastrtps_cpp` (or its `FastRTPS` pytest aliases). Connext is not exercised by any of the failing tests. The Connext install in #27999 (Steps 25-30, `log:210-225`) copies proprietary RTI binaries from a private path — we can't reproduce it on GHA anyway, and it's not load-bearing for this repro.

---

## `name: windows-repro` (`windows-repro.yml:1`)

Cosmetic workflow display name. No upstream pin. Just a label so the run shows up usefully in the GitHub Actions UI.

## `on:` trigger (`windows-repro.yml:16-17`)

```
on:
  workflow_dispatch: {}
```

Manual-only trigger. No inputs (this revision intentionally simpler than the pre-v1.01 matrix-input version — we no longer matrix across RMWs because all 9 failing tests are FastRTPS-only). Matches SKILL.md "Layout pattern" recommendation for `workflow_dispatch` plus the "RMW matrix: cheapest" knob narrowed to a single RMW.

## `concurrency:` block (`windows-repro.yml:19-21`)

```
concurrency:
  group: windows-repro
  cancel-in-progress: false
```

- `group: windows-repro` — single group name; all dispatches go through the same queue.
- `cancel-in-progress: false` — **never** auto-cancel an in-flight run. Matches SKILL.md "What we considered and rejected (generic)" rule: "Auto-cancelling in-flight runs on a new dispatch. Cancellation must be a deliberate manual action by the user, never workflow-driven."

Commit `ac1c4305` (`ci(windows-repro): never auto-cancel in-flight runs`) carries this rule forward from the pre-v1.01 workflow.

## `env:` (workflow-level) (`windows-repro.yml:23-28`)

```
env:
  CI_REPOS_URL: https://gist.githubusercontent.com/fujitatomoya/e96e535bdc812744725b6237e9eb22e6/raw/ab84ebe82133d581d33d732a722c20660dfc487c/ros2.repos
  PIXI_VERSION: v0.41.0
  PIXI_ZIP_SHA256: 16b1b83f2d6f04a990ef7c6eea2bb45d2e846d122be312ca3f5f1b14be7cdc6d
  PIXI_TOML_SHA: a22d7b50717dad7c8b3b2bfb36055684600925a5
  IMAGE_TAG: ros2_windows_ci_rolling_repro
```

### `CI_REPOS_URL` (`windows-repro.yml:24`)

The exact `--repo-file-url` from the reference build's CI_ARGS:
- `log:290`: `... --repo-file-url https://gist.githubusercontent.com/fujitatomoya/e96e535bdc812744725b6237e9eb22e6/raw/ab84ebe82133d581d33d732a722c20660dfc487c/ros2.repos ...`
- Same URL in the `docker run -e CI_ARGS=...` invocation (`log:308`) and in `run_ros2_batch.py`'s parsed args (`log:312`).

Per SKILL.md "Windows pins to extract from the log" → "`CI_REPOS_URL`: the build's `--repo-file-url` arg, search for it in the ros2_batch CI_ARGS line." Matches.

The gist pins `bartalor/rclcpp@bar/issue-2898` (`log:693-696`), which is the fork providing the rclcpp under test.

### `PIXI_VERSION: v0.41.0` (`windows-repro.yml:25`)

Pin from the Dockerfile `Step 12/32`:
- `log:170`: `Step 12/32 : RUN powershell -noexit irm https://github.com/prefix-dev/pixi/releases/download/v0.41.0/pixi-x86_64-pc-windows-msvc.zip -OutFile pixi-x86_64-pc-windows-msvc.zip`

Per SKILL.md "Windows pins to extract from the log" → "`PIXI_VERSION`: the Dockerfile `Step N/M : RUN ... pixi-...zip` line — the URL has the version." Matches.

### `PIXI_ZIP_SHA256` (`windows-repro.yml:26`)

The SHA-256 integrity check that #27999's Dockerfile pins in Step 13:
- `log:173`: `Step 13/32 : RUN powershell -noexit "if ((get-filehash pixi-x86_64-pc-windows-msvc.zip -Algorithm SHA256).hash -ne '16b1b83f2d6f04a990ef7c6eea2bb45d2e846d122be312ca3f5f1b14be7cdc6d') { exit 1 }"`

Verbatim mirror — the value is interpolated into the Dockerfile we generate so the integrity check runs identically inside our image build.

### `PIXI_TOML_SHA: a22d7b50717dad7c8b3b2bfb36055684600925a5` (`windows-repro.yml:27`)

The `ros2/ros2@rolling` HEAD commit at build-start time. Not in the cached log directly — the reference Dockerfile uses `refs/heads/rolling`, not a SHA (`log:152`):
- `log:152`: `Step 6/32 : ARG PIXI_TOML_URL=https://raw.githubusercontent.com/ros2/ros2/refs/heads/${ROS_DISTRO}/pixi.toml`
- `log:191`: `Step 19/32 : ADD ${PIXI_TOML_URL} pixi.toml`

Per SKILL.md "Windows pins to extract from the log" → "`PIXI_TOML_SHA`: ros2/ros2 HEAD SHA at build start time — find a commit on the `<distro>` branch with a timestamp at-or-just-before the build's start." We pin a SHA where the reference used a moving ref so our image is reproducible after `ros2/ros2@rolling` advances. **⚠ The SHA's link to the build-start timestamp is by external reconstruction** — not independently verifiable from the cached log alone.

### `IMAGE_TAG: ros2_windows_ci_rolling_repro` (`windows-repro.yml:28`)

Local docker image tag. Mirrors #27999's tag pattern `ros2_windows_ci_rolling` (`log:308`) with `_repro` suffix so we don't accidentally collide if you ever build #27999's actual image locally.

---

## `jobs.build-and-test:` (`windows-repro.yml:30-31`)

Single job, no matrix. Pre-v1.01 had a per-RMW matrix; this revision drops it because all 9 failing tests are FastRTPS only, so the RMW knob's cheapest setting is exactly one RMW.

### `runs-on: windows-2022` (`windows-repro.yml:32`)

A GitHub-hosted runner image whose host OS is Windows Server 2022 (ltsc2022). This is the kernel-match constraint driving Deviation 1 above. `windows-latest` currently aliases to `windows-2022` but could shift; we pin the explicit name.

### `timeout-minutes: 350` (`windows-repro.yml:33`)

5h 50min ceiling. **⚠ Source not in the log directly.** GitHub Actions caps a single job at 360 min on hosted runners; 350 is just-under-cap. The reference Jenkins build doesn't advertise its timeout in the log. Heuristic, not a mirror. **⚠ UNJUSTIFIED** as a specific number.

---

## Steps

### Step: Checkout repo (`windows-repro.yml:36-37`)

```
- name: Checkout repo
  uses: actions/checkout@v4
```

Brings the workflow repo into the runner workspace so `.github/windows-repro.Dockerfile` is on disk for the next step, and so subsequent steps have a CWD with write access for the `workspace/` mount target.

### Dockerfile: `.github/windows-repro.Dockerfile`

The Dockerfile lives in its own file, **not** generated by a heredoc in the workflow. (Previous revisions emitted it from a PowerShell heredoc; that approach died on Step 11 in run `26443931213` because the backtick Dockerfile-escape and PowerShell's own backtick-escape collided on the one RUN line that embeds quotes. See commit history for the pivot.)

Why a checked-in file beats a generated heredoc:
- One syntax layer instead of three (PowerShell heredoc → Dockerfile → CMD/PowerShell-in-RUN).
- IDE/linter/diff tooling treats it as a real Dockerfile.
- Diffing against #27999's Dockerfile (extractable from `/tmp/ci_windows_27999.log` Step lines) is a real text diff.
- Locally reproducible: `docker build -f .github/windows-repro.Dockerfile --build-arg PIXI_VERSION=v0.41.0 ...` runs without the workflow.

Pins are passed via `--build-arg` from the workflow's `env:` block so the workflow remains the single source of truth.

Going line by line through `.github/windows-repro.Dockerfile`:

- `# escape=`` ` — Dockerfile escape directive. Backtick is the standard Windows-Dockerfile choice (Microsoft's own docs and samples) because `\` would collide with Windows path separators in RUN/COPY lines.
- `ARG ROS_DISTRO=rolling` (before `FROM`) — mirrors `log:146` `Step 3/32 : ARG ROS_DISTRO=rolling`.
- `FROM mcr.microsoft.com/windows/server:ltsc2022` — **Deviation 1**. Reference at `log:147` is `mcr.microsoft.com/windows/server:$WINDOWS_RELEASE_VERSION` resolved to `:2009`.
- `ARG ROS_DISTRO` (after `FROM`) — re-declares so the value crosses the `FROM` boundary into this stage. Mirrors `log:149` `Step 5/32 : ARG ROS_DISTRO`.
- `ARG PIXI_VERSION`, `ARG PIXI_ZIP_SHA256`, `ARG PIXI_TOML_SHA` — no defaults; missing `--build-arg` is a hard error. The workflow's `env:` block supplies all three (`windows-repro.yml:43-45`).
- `ARG PIXI_TOML_URL=https://raw.githubusercontent.com/ros2/ros2/${PIXI_TOML_SHA}/pixi.toml` — **deliberate divergence from `log:152`**: reference uses `refs/heads/${ROS_DISTRO}`, we substitute the frozen `PIXI_TOML_SHA` so the env is reproducible after `ros2/ros2@rolling` advances.
- `RUN powershell ... LongPathsEnabled` — mirrors `log:155` `Step 7/32` verbatim. Sets the Windows registry key so long source paths work during the build (ROS 2 trees blow past the default 260-char Win32 `MAX_PATH`).
- `RUN powershell -noexit irm .../vs_buildtools.exe ...` — mirrors `log:164` (`Step 10/32`). **Deviation 2**: we skip `log:158-161` (`Steps 8-9`, VS 2019 BuildTools download + install).
- `RUN vs_buildtools_2022.exe --quiet --wait --norestart --add ...` (continued with backticks) — verbatim mirror of `log:167` (`Step 11/32`), same component list. The component set matters because:
  - `Microsoft.VisualStudio.Component.VC.Tools.x86.x64` is the **x86 → x64 cross toolchain** the reference's `vcvarsall.bat x86_amd64` invocation depends on (`log:2263`).
  - `Microsoft.VisualStudio.Component.Windows10SDK.19041` pins the SDK version (matches between #27999 and our container).
- `RUN powershell -noexit "irm .../pixi-...${PIXI_VERSION}.../pixi-...zip ..."` — mirrors `log:170` (`Step 12/32`). `${PIXI_VERSION}` is expanded by the Dockerfile parser from the build-arg.
- `RUN powershell -noexit "if ((get-filehash ...).hash -ne '${PIXI_ZIP_SHA256}') { exit 1 }"` — mirrors `log:173` (`Step 13/32`). SHA-256 integrity check; `${PIXI_ZIP_SHA256}` expanded from build-arg.
- `RUN powershell -noexit "Expand-Archive ..."` — mirrors `log:176` (`Step 14/32`). Unzips pixi into `%USERPROFILE%\.pixi\bin`.
- `RUN powershell -noexit "$bindir = ... ; $newpath = \"$bindir;$oldpath\" ; $pathkey.SetValue('PATH', $newpath, ...)"` — mirrors `log:179` (`Step 15/32`). Prepends pixi's bin dir to the persistent registry PATH.
  - **Critical detail (the bug from run `26443931213`):** the embedded quotes around `$bindir;$oldpath` are written as `\"...\"` so they survive CMD's argv parsing (the `docker build` invocation goes through cmd.exe via `shell: cmd`) and reach PowerShell as real quotes. The reference assigns the joined string to a `$newpath` variable first, then passes the variable bare to `SetValue` — same shape adopted here for clarity.
- `WORKDIR C:\pixi_ws` — mirrors `log:185` (`Step 17/32`). The pixi project root for the env install.
- `ADD ${PIXI_TOML_URL} pixi.toml` — mirrors `log:191` (`Step 19/32`). Downloads our pinned `pixi.toml`. We **skip** `log:188` (`Step 18/32`, the HTTPS-protocol check on `$PIXI_TOML_URL`) because our URL is fixed at workflow-write time, not user-controlled.
- `RUN powershell -Command "(Get-Item pixi.toml).LastWriteTime = Get-Date"` — mirrors `log:195` (`Step 20/32`). Touches `pixi.toml` so pixi doesn't think the cache is stale.
- `RUN pixi --color never --no-progress -q install` — mirrors `log:198` (`Step 21/32`). Resolves and installs the env.
- `RUN pixi --color never --no-progress -q list` — mirrors `log:201` (`Step 22/32`). Records resolved package versions in the build log.
- `RUN pixi --color never --no-progress -q run "pip install 'colcon-ros-domain-id-coordinator >= 0.2.3'"` — mirrors `log:204` (`Step 23/32`). The one pip install in the env setup.
- `ENV ROS_DISTRO=${ROS_DISTRO}` — mirrors `log:207` (`Step 24/32`). Persists the distro env var for the container runtime.
- **Skipped:** `log:210-225` (`Steps 25-30`, RTI Connext install — **Deviation 3**).
- `WORKDIR C:\ci` — mirrors `log:228` (`Step 31/32`). The CWD inside the container at run time; the mount point for the host workspace.
- **Skipped:** `log:231` (`Step 32/32`, the `CMD` that runs `pixi run ... python run_ros2_batch.py %CI_ARGS%`). We invoke this manually via `docker run` instead so we control the args from outside.

### Step: docker build image (`windows-repro.yml:39-47`)

```
- name: docker build image
  shell: cmd
  run: |
    docker build --isolation=process ^
      --build-arg PIXI_VERSION=%PIXI_VERSION% ^
      --build-arg PIXI_ZIP_SHA256=%PIXI_ZIP_SHA256% ^
      --build-arg PIXI_TOML_SHA=%PIXI_TOML_SHA% ^
      -f .github/windows-repro.Dockerfile ^
      -t %IMAGE_TAG% .
```

- `shell: cmd` — `%VAR%` syntax for env-var interpolation is cmd.exe.
- `--isolation=process` — matches `log:308` `docker run --isolation=process`. At build time, `--isolation=process` requires the base image kernel to match the host kernel — that's Deviation 1's whole reason.
- `--build-arg PIXI_VERSION=%PIXI_VERSION%` (and the same for `PIXI_ZIP_SHA256`, `PIXI_TOML_SHA`) — passes pins from the workflow's `env:` block to the Dockerfile's `ARG`s. Single source of truth: change a pin in `env:` and both build and runtime see the new value.
- `-f .github/windows-repro.Dockerfile` — explicit path to the checked-in Dockerfile.
- `-t %IMAGE_TAG%` — tag the built image so the subsequent `docker run` references it by name.
- `.` — build context = repo root (`checkout@v4` puts us there). The Dockerfile only `ADD`s a remote URL, so build context contents aren't actually used; we still need a context arg.

### Step: Clone ros2/ci into workspace (`windows-repro.yml:49-56`)

```
- name: Clone ros2/ci into workspace (provides run_ros2_batch.py)
  shell: pwsh
  run: |
    New-Item -ItemType Directory -Force -Path workspace | Out-Null
    git clone --depth 1 https://github.com/ros2/ci.git workspace_tmp
    Copy-Item -Recurse -Force workspace_tmp\* workspace\
    Remove-Item -Recurse -Force workspace_tmp
```

This is the critical bridge step — without it the container's `python run_ros2_batch.py` would fail with "file not found." Background:

`run_ros2_batch.py` is the entry point #27999 invokes via the container's CMD (`log:231`):
> `Step 32/32 : CMD "pixi run --manifest-path C:\pixi_ws\pixi.toml --frozen python run_ros2_batch.py %CI_ARGS%"`

It is **not** in the docker image — only in the **Jenkins workspace** mounted at `C:\ci` via `-v "C:\J\workspace\ci_windows":"C:\ci"` (`log:308`). On Jenkins, the workspace is automatically populated with the `ros2/ci` checkout. On GHA, we don't get that for free.

The fix: clone `https://github.com/ros2/ci` (which has `run_ros2_batch.py` at its top level plus the `ros2_batch_job/` package) into a local `workspace/` directory, then mount **that** to `C:\ci` inside the container.

- `New-Item ... -Path workspace` — pre-create the mount target.
- `git clone --depth 1 ros2/ci workspace_tmp` — shallow clone for speed.
- `Copy-Item -Recurse -Force workspace_tmp\* workspace\` — copy contents (not the directory itself) so `workspace/run_ros2_batch.py` is at the right level.
- `Remove-Item -Recurse -Force workspace_tmp` — cleanup.

Per SKILL.md "Windows-specific" → "**It IS in a public repo: `https://github.com/ros2/ci`**. To invoke it directly, clone `ros2/ci` into the host-side workspace dir before `docker run` so the mount surfaces the script at `C:\ci\run_ros2_batch.py`."

### Step: docker run (`windows-repro.yml:58-66`)

```
- name: docker run (mirrors ci.ros2.org #27999 invocation, scoped to failing tests)
  shell: cmd
  run: |
    docker run --isolation=process --rm ^
      -e ROS_DOMAIN_ID=1 ^
      -e CI_ARGS="--force-ansi-color --workspace-path C:\ci --ignore-rmw rmw_fastrtps_dynamic_cpp --ignore-rmw rmw_connextdds --ignore-rmw rmw_cyclonedds_cpp --repo-file-url ... --packages-up-to test_rosidl_buffer --test-args ... --packages-select test_rosidl_buffer" ^
      -v "%CD%\workspace":"C:\ci" ^
      %IMAGE_TAG% ^
      cmd /c "pixi run --manifest-path C:\pixi_ws\pixi.toml --frozen python run_ros2_batch.py %CI_ARGS%"
```

Reference invocation (verbatim):
- `log:308`: `docker run --isolation=process --rm --net=isolated_network -e ROS_DOMAIN_ID=1 -e CI_ARGS="..." -v "C:\J\workspace\ci_windows":"C:\ci" ros2_windows_ci_rolling ...`

Going through every piece:

- `--isolation=process` — matches reference. Required by Deviation 1's kernel constraint.
- `--rm` — auto-cleanup the container on exit. Matches reference.
- `-e ROS_DOMAIN_ID=1` — matches reference. Per SKILL.md "ROS_DOMAIN_ID. Mirror at every layer."
- **`--net=isolated_network` not mirrored.** Reference uses a custom docker bridge (`log:308`); we run on GHA's default network. This is a **⚠ KNOWN DIVERGENCE** — FastRTPS discovery is multicast-based and the network topology can matter. Not addressed in this revision.
- `-e CI_ARGS="..."` — the args string is mostly verbatim from `log:290`, with these targeted changes:
  - `--workspace-path C:\J\workspace\ci_windows` → `--workspace-path C:\ci`. Reference uses the host-side path which gets mounted to `C:\ci`; we pass `C:\ci` directly since that's what `run_ros2_batch.py` actually sees inside the container.
  - Added `--ignore-rmw rmw_connextdds --ignore-rmw rmw_cyclonedds_cpp` (reference only ignores `rmw_fastrtps_dynamic_cpp`). We narrow to `rmw_fastrtps_cpp` only — the SKILL.md "RMW matrix" knob at its cheapest setting. The failing tests are all on `rmw_fastrtps_cpp`.
  - Changed `--packages-above-and-dependencies rclcpp` → `--packages-up-to test_rosidl_buffer` (build scope) and `--packages-above rclcpp` → `--packages-select test_rosidl_buffer` (test scope). SKILL.md "Build scope" + "Test selection" knobs at their cheapest settings — narrow to just the package whose tests fail.
  - Everything else verbatim: `--force-ansi-color`, the `--repo-file-url` URL, `--colcon-mixin-url`, `--visual-studio-version 2022`, `--build-args --event-handlers console_cohesion+ console_package_list+`, `--cmake-args -DINSTALL_EXAMPLES=OFF -DSECURITY=ON -DAPPEND_PROJECT_NAME_TO_INCLUDEDIR=ON`, `--test-args --event-handlers console_cohesion+ --retest-until-pass 2 --ctest-args -LE xfail --pytest-args -m "not xfail" --executor sequential`.
- `-v "%CD%\workspace":"C:\ci"` — mount the host's `workspace/` (with `ros2/ci` cloned into it) at `C:\ci` inside the container. Matches the reference's `-v "C:\J\workspace\ci_windows":"C:\ci"` mount target; only the host source path differs.
- `%IMAGE_TAG%` — our locally-built image (vs reference's `ros2_windows_ci_rolling`).
- `cmd /c "pixi run --manifest-path C:\pixi_ws\pixi.toml --frozen python run_ros2_batch.py %CI_ARGS%"` — the entry command. Verbatim mirror of `log:231` (`Step 32/32` CMD). Since we **skipped** the Dockerfile CMD (Step 32/32) when writing our Dockerfile, we re-supply it here on the docker run command line so the container has something to execute.

### Step: Upload test results (`windows-repro.yml:68-76`)

```
- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: |
      workspace/**/test_results/**/*.xml
      workspace/**/log/**/*
    retention-days: 7
```

- `actions/upload-artifact@v4` — current major version.
- `name: test-results` — single artifact name. Pre-v1.01 had `test-results-${{ matrix.rmw }}` because of the RMW matrix; this revision is single-RMW.
- `path: workspace/**/test_results/**/*.xml` — the per-package gtest/junit XMLs. Note the `workspace/` prefix: the container writes its output into `C:\ci` which is mounted to host `%CD%\workspace`, so the artifacts surface there.
- `path: workspace/**/log/**/*` — colcon's `log/` directory inside the same mount.
- `retention-days: 7` — **⚠ UNJUSTIFIED** (no upstream pin; local convention).
- `if: always()` — upload even on failure (which is the expected case here since we're reproducing failures).

---

## What I couldn't justify

Items marked **⚠ UNJUSTIFIED** above, gathered:

1. **`PIXI_TOML_SHA: a22d7b50717dad7c8b3b2bfb36055684600925a5`** (`windows-repro.yml:27`). The Dockerfile in the cached log uses `refs/heads/rolling` (`log:152`), so the link from this SHA to "ros2/ros2@rolling HEAD at 2026-05-14T22:49:27Z" must be reconstructed externally. Not verifiable from the cached log alone.

2. **`timeout-minutes: 350`** (`windows-repro.yml:33`). No Jenkins-side timeout in the cached log. Sits just under GitHub Actions' 360-min hard cap on hosted runners. Heuristic, no upstream pin.

3. **`retention-days: 7`** on artifact upload (`windows-repro.yml:76`). No reference. Local convention.

## Known divergences from the reference (not mistakes — design choices)

These are intentional and documented; listing for completeness:

1. **Base image `:ltsc2022` instead of `:2009`** (Deviation 1). The largest single drift. Forced by GHA's host kernel.

2. **VS 2019 BuildTools install skipped** (Deviation 2). Reference's `log:158-161` (Steps 8-9). VS 2022 is the actual toolchain at runtime; 2019 is dead weight.

3. **RTI Connext install skipped** (Deviation 3). Reference's `log:210-225` (Steps 25-30). Connext is not exercised by the failing tests; the install also can't be reproduced on GHA (proprietary).

4. **`--net=isolated_network` not mirrored.** Reference's `log:308`. GHA default network instead. **Suspect this matters for FastRTPS discovery** — flagged as a future fidelity-raise candidate.

5. **`PIXI_TOML_URL` uses frozen SHA instead of `refs/heads/rolling`.** Reference's `log:152`. Reproducibility after `ros2/ros2@rolling` advances.

6. **Build scope `--packages-up-to test_rosidl_buffer`** vs reference's `--packages-above-and-dependencies rclcpp`. SKILL.md "Build scope" knob at cheapest setting.

7. **Test scope `--packages-select test_rosidl_buffer`** vs reference's `--packages-above rclcpp`. SKILL.md "Test selection" knob at cheapest setting.

8. **Two extra `--ignore-rmw` flags** (`rmw_connextdds`, `rmw_cyclonedds_cpp`). SKILL.md "RMW matrix" knob narrowed to `rmw_fastrtps_cpp` only since all 9 failing tests are on that RMW.

9. **Skip Dockerfile Step 18/32 (HTTPS-protocol check on `$PIXI_TOML_URL`).** The URL is fixed at workflow-write time, not user-controlled.

---

## Cross-check tallies (for future iteration)

- Reference build's failure count: **9** (all `test_rosidl_buffer` × `rmw_fastrtps_cpp`). When reproducing, this is the target.
- Reference build's `--ignore-rmw`: only `rmw_fastrtps_dynamic_cpp` (`log:290`). If you ever raise the RMW matrix knob toward faithful, mirror this exclusion (do not include `rmw_fastrtps_dynamic_cpp`).
- Reference build's `^Finished <<<` count: **412** (every package built). Only applicable if you raise the build-scope knob to `--packages-above-and-dependencies rclcpp`.
