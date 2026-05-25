# `windows-repro.yml` — line-by-line research notes

This document explains every meaningful line in `.github/workflows/windows-repro.yml`. For every value, flag, arg, and step it answers:

1. **What it does.**
2. **Why it's there** — what choice in ci.ros2.org Windows Jenkins build #27999 (the reference) it mirrors, or what upstream tool constraint forces it.
3. **The evidence** — log line citations from `/tmp/ci_windows_27999.log` (cited as `log:NNNN`), or the upstream URL / docs page.

Citations like `windows-repro.yml:NN` refer to the workflow file. Citations like `log:NNNN` refer to `/tmp/ci_windows_27999.log` (use `sed -n 'NNNNp' /tmp/ci_windows_27999.log` to look them up).

Items I could not justify are flagged inline with **⚠ UNJUSTIFIED** and gathered at the end.

---

## Reference build context (for grounding)

- Jenkins job: `ci_windows` build **#27999**. Triggered by user "Tomoya Fujita" (`log:3-4`), rebuild of #27970 (`log:5`). Build directory timestamp: `build_2026-05-14_22-52-35` (`log:127113`) — i.e. the build started 2026-05-14 ~22:52 UTC. The workflow's header comment (`windows-repro.yml:5`) says `2026-05-14T22:49:27Z` (the Jenkins queue time); the docker step that builds the image bakes in `"Thursday, May 14, 2026"` (`log:182`) so both numbers are on the same UTC day.
- The 9 failing tests (from `/tmp/ci_windows_27999_testreport.json`, `failCount: 9`): all in `test_rosidl_buffer` under `rmw_fastrtps_cpp` — three ctest-level tests (`test_test_to_test__rmw_fastrtps_cpp`, `test_test_to_cpu__rmw_fastrtps_cpp`, `test_nested_msgs__rmw_fastrtps_cpp`) plus their pytest cases.
- Reference build image: `mcr.microsoft.com/windows/server:10.0.26100.32690` (`log:147, log:138`) — Windows Server 2025 base. Installs **both** VS 2019 BuildTools (`log:158-161`) and VS 2022 BuildTools (`log:164-167`), with VS 2022 selected at runtime via `--visual-studio-version 2022` (`log:290`).
- Reference build CI_ARGS (the load-bearing single line for build/test args): `log:290` and (duplicated) `log:308`, `log:337`.

---

## `name: windows-repro` (`windows-repro.yml:1`)

Cosmetic workflow display name. No upstream pin. Just a label so the run shows up usefully in the GitHub Actions UI.

## Top-of-file comment (`windows-repro.yml:3-5`)

> `# Replicates ci.ros2.org Windows build #27999 environment using pixi.`
> `# pixi.toml is pinned to the commit of ros2/ros2@rolling that was HEAD when`
> `# build #27999 started (2026-05-14T22:49:27Z).`

Documents intent and the pin selection rule from `.claude/skills/replicate-ros2-ci-build/SKILL.md` "Windows pins to extract from the log" table: `PIXI_TOML_SHA` is reconstructed from `ros2/ros2@rolling` HEAD at the build start time because the Dockerfile uses a branch ref, not a SHA (`log:152`: `ARG PIXI_TOML_URL=https://raw.githubusercontent.com/ros2/ros2/refs/heads/${ROS_DISTRO}/pixi.toml`).

## `on:` trigger (`windows-repro.yml:7-11`)

```
on:
  workflow_dispatch:
    inputs:
      matrix:
        description: "JSON matrix (built by .github/windows-repro-run.py)"
        required: true
```

- `workflow_dispatch` — manual-only trigger; matches the SKILL.md layout pattern ("A workflow file under `.github/workflows/` with a `workflow_dispatch` matrix input"). No automatic triggers; user always launches via the Python wrapper.
- `inputs.matrix: required: true` — the launch wrapper (`.github/windows-repro-run.py`, per the description) builds a JSON matrix from a gitignored local config and passes it. Matches SKILL.md "Layout pattern (reusable across repos)".

## `concurrency:` block (`windows-repro.yml:14-16`)

```
concurrency:
  group: windows-repro-${{ github.event.inputs.matrix }}
  cancel-in-progress: true
```

- `group: windows-repro-${{ github.event.inputs.matrix }}` — keys the concurrency group on the **input matrix JSON**, so two dispatches with the *same* matrix collide but different matrices don't. Mentioned in commit subject `ci(windows-repro): add concurrency group keyed on matrix input` (commit 745056c4).
- `cancel-in-progress: true` — **tension with the rule** in SKILL.md "What we considered and rejected (generic)":
  > "Auto-cancelling in-flight runs on a new dispatch. Cancellation must be a deliberate manual action by the user, never workflow-driven. Don't propose `cancel-in-progress: true` without checking."

  The user has the value set to `true` anyway. The grouping by-matrix narrows the blast radius (only collisions on the same matrix self-cancel), but it still violates the no-auto-cancel rule for any duplicate dispatch. Recording the tension as the prompt requested; not changing it.

## `env:` (workflow-level) (`windows-repro.yml:18-21`)

```
env:
  CI_REPOS_URL: https://gist.githubusercontent.com/fujitatomoya/e96e535bdc812744725b6237e9eb22e6/raw/ab84ebe82133d581d33d732a722c20660dfc487c/ros2.repos
  PIXI_VERSION: v0.41.0
  PIXI_TOML_SHA: a22d7b50717dad7c8b3b2bfb36055684600925a5
```

### `CI_REPOS_URL` (`windows-repro.yml:19`)

The exact `--repo-file-url` from the reference build's CI_ARGS. Verbatim cite:
- `log:290`: `... --repo-file-url https://gist.githubusercontent.com/fujitatomoya/e96e535bdc812744725b6237e9eb22e6/raw/ab84ebe82133d581d33d732a722c20660dfc487c/ros2.repos ...`
- The same URL appears in the `docker run -e CI_ARGS=...` invocation (`log:308`), in `run_ros2_batch.py`'s parsed args (`log:312`), and in the `curl -skL` that fetches it inside the container (`log:661`).

Per SKILL.md "Windows pins to extract from the log" → "`CI_REPOS_URL`: the build's `--repo-file-url` arg, search for it in the ros2_batch CI_ARGS line." Matches.

The gist is also why we have `bartalor/rclcpp` checked in the manifest-verify step (the gist's manifest pins a fork): `log:693-696` shows `bartalor/rclcpp: ... url: https://github.com/bartalor/rclcpp.git, version: bar/issue-2898`.

### `PIXI_VERSION: v0.41.0` (`windows-repro.yml:20`)

Pin from the Dockerfile `Step 12/32`:
- `log:170`: `Step 12/32 : RUN powershell -noexit irm https://github.com/prefix-dev/pixi/releases/download/v0.41.0/pixi-x86_64-pc-windows-msvc.zip -OutFile pixi-x86_64-pc-windows-msvc.zip`

Per SKILL.md "Windows pins to extract from the log" → "`PIXI_VERSION`: the Dockerfile `Step N/M : RUN ... pixi-...zip` line — the URL has the version." Matches.

The reference also pins the zip SHA256 in step 13 (`log:173`: `16b1b83f2d6f04a990ef7c6eea2bb45d2e846d122be312ca3f5f1b14be7cdc6d`); our workflow delegates that integrity check to `prefix-dev/setup-pixi@v0.8.1` which downloads from the GitHub release tag.

### `PIXI_TOML_SHA: a22d7b50717dad7c8b3b2bfb36055684600925a5` (`windows-repro.yml:21`)

The `ros2/ros2@rolling` HEAD commit at build-start time. Not in the log directly — the Dockerfile uses `refs/heads/rolling`, not a SHA (`log:152`):
- `log:152`: `Step 6/32 : ARG PIXI_TOML_URL=https://raw.githubusercontent.com/ros2/ros2/refs/heads/${ROS_DISTRO}/pixi.toml`
- `log:191`: `Step 19/32 : ADD ${PIXI_TOML_URL} pixi.toml`

Per SKILL.md "Windows pins to extract from the log" → "`PIXI_TOML_SHA`: ros2/ros2 HEAD SHA at build start time — find a commit on the `<distro>` branch with a timestamp at-or-just-before the build's start; the Dockerfile uses a ref like `refs/heads/<distro>`, NOT a SHA, so you must reconstruct."

The reconstruction was done by the user when they wrote the file; the SHA itself isn't independently verifiable from the cached log. **⚠ The SHA's link to the build-start timestamp is by external reconstruction** — I can't cross-check it from the cached log alone. (It is a plausible 40-char hex commit SHA on `ros2/ros2` `rolling`; would need a GitHub API call against `ros2/ros2` history filtered by date to confirm. The user prefers we not chase that.)

---

## `jobs.windows-rolling-source-build:` (`windows-repro.yml:23-24`)

Job ID = `windows-rolling-source-build`. The "rolling" identifies the ROS distro mirrored (matches `ROS_DISTRO=rolling` in the reference: `log:142` `--build-arg ROS_DISTRO=rolling`, `log:207` `ENV ROS_DISTRO=${ROS_DISTRO}`). "source-build" distinguishes from a binary-overlay job.

### `runs-on: windows-2022` (`windows-repro.yml:25`)

A GitHub-hosted runner image with VS 2022 BuildTools preinstalled. Why this and not `windows-latest` or `windows-2019`:

- The reference build sets `--visual-studio-version 2022` in CI_ARGS (`log:290`) and resolves to VS 2022 BuildTools at runtime: `log:2263`: `call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86_amd64`. Even though the Dockerfile installs both 2019 and 2022 toolsets (`log:158-167`), only 2022 is exercised.
- `windows-2022` is the named GitHub Actions runner image whose toolchain matches; `windows-latest` is a moving target (currently still maps to `windows-2022` but could shift), and `windows-2019` would be a different toolset.

### `timeout-minutes: 350` (`windows-repro.yml:26`)

5h 50min ceiling. **⚠ Source not in the log directly.** The reference Jenkins build doesn't advertise its timeout in the cached log. I searched for `timeout` / minutes-style numbers but nothing emerged. Possible justifications: GitHub Actions caps a single job at 6h (360 min) on hosted runners, so 350 is just-under-cap; an order-of-magnitude check: in the log `Finished <<< rclcpp [28min 25s]` (`log:42627`) plus the full build tree took several hours. The value is in the right ballpark but no upstream pin forces 350. **⚠ UNJUSTIFIED** flag retained — the specific number 350 is a heuristic, not a mirror.

### `strategy:` (`windows-repro.yml:28-30`)

```
strategy:
  fail-fast: false
  matrix: ${{ fromJSON(inputs.matrix) }}
```

- `fail-fast: false` — keep other matrix legs running when one fails. Standard for multi-RMW debug matrices; SKILL.md "RMW matrix" knob assumes legs run independently.
- `matrix: ${{ fromJSON(inputs.matrix) }}` — pulls the JSON matrix straight from the dispatch input. Matches SKILL.md "Layout pattern" recommendation.

### `env:` (job-level) (`windows-repro.yml:32-34`)

```
env:
  RMW_IMPLEMENTATION: ${{ matrix.rmw }}
  ROS_DOMAIN_ID: 1
```

#### `RMW_IMPLEMENTATION: ${{ matrix.rmw }}`

Per-leg RMW selection. The matrix entry's `rmw` key supplies values like `rmw_fastrtps_cpp` (since the failing tests are only in that RMW). This is the SKILL.md "RMW matrix" knob.

#### `ROS_DOMAIN_ID: 1`

Mirrors the Docker invocation:
- `log:308`: `docker run --isolation=process --rm --net=isolated_network -e ROS_DOMAIN_ID=1 ...`
- `log:381`: `ROS_DOMAIN_ID=1` (printed by `set` inside the container)

Per SKILL.md "What to mirror" → "`ROS_DOMAIN_ID`. Grep the log for `ROS_DOMAIN_ID=` to see what the docker/CI env sets ... Add the same value to the workflow env block. Mirror at every layer." Matches. Commit ea513c0a (`ci(windows-repro): set ROS_DOMAIN_ID=1 to match ci.ros2.org #27999`) is the direct trace.

(Aside: `log:104318` shows `1: ROS_DOMAIN_ID 61` inside one test's stdout — a per-test override that doesn't change the env we set.)

---

## Steps

### Step: Configure git long paths (`windows-repro.yml:37-39`)

```
- name: Configure git long paths
  shell: pwsh
  run: git config --global core.longpaths true
```

Windows ships with a default Win32 `MAX_PATH` of 260 chars; ROS 2 source paths plus colcon build directories regularly exceed that. The reference build addresses this at the OS level via the Dockerfile `Step 7/32`:
- `log:155`: `RUN powershell -noexit "New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force"`

We can't set the registry on GitHub-hosted runners (no admin guarantee for arbitrary registry writes is part of the contract worth relying on), so we mirror it at the git layer with `core.longpaths true`, which lets git itself handle long paths during `vcs import` / clone. Necessary because `vcs import` later in the workflow will fail otherwise on packages with deep tree paths.

### Step: Checkout repo (`windows-repro.yml:41-42`)

```
- name: Checkout repo
  uses: actions/checkout@v4
```

Brings the workflow repo into the runner workspace (so `pixi.toml` & friends end up alongside the workflow file). `actions/checkout@v4` is the current major version recommended by GitHub. The workflow itself doesn't use the checkout for source code (the source tree comes from `vcs import`); it just needs the workflow's own working directory present.

### Step: Check manifest URL reachable (`windows-repro.yml:44-46`)

```
- name: Check manifest URL reachable
  shell: pwsh
  run: Invoke-WebRequest -Method Head -Uri $env:CI_REPOS_URL -UseBasicParsing | Out-Null
```

Cheap preflight: HEAD the `CI_REPOS_URL` gist before doing tens of minutes of env install. Fails fast if the gist URL is wrong or temporarily down. No direct upstream mirror — this is purely defensive (the reference build doesn't preflight either, it just goes for it via `curl -skL` at `log:661`).

### Step: Install pixi (`windows-repro.yml:48-54`)

```
- name: Install pixi
  uses: prefix-dev/setup-pixi@v0.8.1
  with:
    pixi-version: ${{ env.PIXI_VERSION }}
    run-install: false
    cache: true
    cache-key: pixi-${{ env.PIXI_VERSION }}-${{ env.PIXI_TOML_SHA }}
```

- `prefix-dev/setup-pixi@v0.8.1` — official pixi installer action. Pinned to a specific minor version (per `https://github.com/prefix-dev/setup-pixi` README) instead of `@v0` or `latest` to keep behavior identical across runs.
- `pixi-version: ${{ env.PIXI_VERSION }}` — pins the pixi binary to `v0.41.0` (the reference's pinned version). Per the action's docs: "Specifies which version of pixi to install. You can provide a specific release version (e.g., `v0.66.0`) or use `latest`."
- `run-install: false` — tells the action **not** to run `pixi install` itself. We do that in a separate step against the fetched `pixi.toml` (the action expects a `pixi.toml` alongside the workflow checkout; ours arrives in a later step). Per action docs: "Controls whether the action installs the current project. When set to `false`, 'you only want to install pixi and not install the current project.'"
- `cache: true` — enables pixi's environment cache; per action docs, caches the resolved env keyed by `pixi.lock` (we have a `pixi.toml` without a `lock`, so the action falls back to the cache-key prefix).
- `cache-key: pixi-${{ env.PIXI_VERSION }}-${{ env.PIXI_TOML_SHA }}` — explicit prefix so the cache invalidates whenever either the pixi binary version *or* the pinned `pixi.toml` SHA changes. This is the cheapest setting of SKILL.md's "Env source" knob ("cheapest: cache the env across runs.") — the env-source faithful alternative would be `cache: false` per run.

### Step: Fetch pinned pixi.toml from ros2/ros2 (`windows-repro.yml:56-61`)

```
- name: Fetch pinned pixi.toml from ros2/ros2
  shell: pwsh
  run: |
    $url = "https://raw.githubusercontent.com/ros2/ros2/$env:PIXI_TOML_SHA/pixi.toml"
    Invoke-WebRequest -Uri $url -OutFile pixi.toml
    Get-Content pixi.toml | Select-Object -First 8
```

Fetches `pixi.toml` from the pinned SHA so the resolved env mirrors what `Step 19/32` of the reference Dockerfile downloads (`log:152, log:191`). Critical difference: the reference uses `refs/heads/rolling` (a moving ref), we substitute the **frozen SHA** so the env is reproducible after `ros2/ros2@rolling` advances. `Get-Content ... -First 8` dumps the file's first 8 lines into the log for debug parity.

### Step: pixi install (frozen) (`windows-repro.yml:63-65`)

```
- name: pixi install (frozen)
  shell: pwsh
  run: pixi install
```

Resolves and installs the pixi env into `.pixi/`. Mirrors the reference Dockerfile `Step 21/32`:
- `log:198`: `Step 21/32 : RUN pixi --color never --no-progress -q install`

**Note on the step name:** It says "frozen" but the command is plain `pixi install`, not `pixi install --frozen`. Per SKILL.md "Windows-specific checks":
> "Dockerfile uses plain `pixi install` (no `--frozen`) at build time, then runtime uses `pixi run --frozen` (asserts env unchanged). On GitHub Actions we do `pixi install` fresh per run — *cannot* use `--frozen` at runtime if the workflow does any `pip install` step, because pip adds packages outside pixi's conda-meta tracking and invalidates the lock. Accept the drift; it's small."

So the step name is misleading — there is no `--frozen` because we have a later `pip install` step (line 69). The step name should arguably be `pixi install` without "(frozen)". **⚠ Minor naming inconsistency, not a divergence in behavior.**

### Step: Bump colcon-ros-domain-id-coordinator (`windows-repro.yml:67-69`)

```
- name: Bump colcon-ros-domain-id-coordinator (mirrors ci.ros2.org Dockerfile step 23)
  shell: pwsh
  run: pixi run pip install "colcon-ros-domain-id-coordinator >= 0.2.3"
```

Direct mirror of `Step 23/32` of the reference Dockerfile:
- `log:204`: `Step 23/32 : RUN pixi --color never --no-progress -q run "pip install 'colcon-ros-domain-id-coordinator >= 0.2.3'"`

The step name's comment "mirrors Dockerfile step 23" is **verified** — same package name, same `>= 0.2.3` constraint, same `pixi run pip install` form.

This is also the pip-install step that breaks `pixi run --frozen` purity (see preceding step). Per SKILL.md generic "What to mirror": "pip-install steps (any colcon plugin or other dep). Look for `pip install` invocations in the build setup phase — these are easy to miss because they happen before the colcon command line, not in it. Replicate each as a separate workflow step."

I grepped for other `pip install` lines in the setup phase; only this one appears in the Dockerfile (other `pip` invocations later in the log are setuptools internal calls from colcon's package builds, not env-setup pip installs).

### Step: pixi list (`windows-repro.yml:71-73`)

```
- name: pixi list (record exact resolved versions)
  shell: pwsh
  run: pixi list
```

Mirrors `Step 22/32` of the reference Dockerfile:
- `log:201`: `Step 22/32 : RUN pixi --color never --no-progress -q list`

Records the resolved package versions in the GH Actions log for debugging / drift analysis. Position ordering note: in the reference Dockerfile `pixi list` is **before** the `pip install colcon-ros-domain-id-coordinator` (step 22 vs step 23). Our workflow has them swapped (`pip install` is the step immediately before `pixi list`). The swap doesn't change behavior — both `pixi list` outputs cover the post-`pixi install` env state — but it is a tiny ordering divergence. **⚠ Minor ordering divergence vs reference Dockerfile.**

### Step: Fetch pinned ros2.repos manifest (`windows-repro.yml:75-80`)

```
- name: Fetch pinned ros2.repos manifest
  shell: pwsh
  run: |
    New-Item -ItemType Directory -Force -Path src | Out-Null
    Invoke-WebRequest -Uri $env:CI_REPOS_URL -OutFile ros2.repos
    Get-Content ros2.repos | Select-Object -First 5
```

Pulls the gist `ros2.repos` so `vcs import` later has its input. Mirrors what the reference does inside the container:
- `log:661`: `==> curl -skL https://gist.githubusercontent.com/fujitatomoya/e96e535bdc812744725b6237e9eb22e6/raw/ab84ebe82133d581d33d732a722c20660dfc487c/ros2.repos -o 00-ros2.repos`

(Filename differs — reference saves to `00-ros2.repos`, we save to `ros2.repos`. Functionally identical; both feed the same content into `vcs import`.)

`New-Item ... -Path src` pre-creates `src/` so the `vcs import src --input ...` step has its target tree.

`Get-Content ... -First 5` prints the first 5 lines for debug parity (the reference also dumps the file in the log via `vcs validate` / etc.).

### Step: Verify manifest has required entries (`windows-repro.yml:82-88`)

```
- name: Verify manifest has required entries
  shell: pwsh
  run: |
    $manifest = Get-Content ros2.repos -Raw
    foreach ($entry in @("bartalor/rclcpp", "ros2/system_tests")) {
      if ($manifest -notmatch [regex]::Escape($entry)) { throw "Manifest missing entry: $entry" }
    }
```

Defensive guard: if the gist gets edited and one of the entries we depend on disappears, fail before doing tens of minutes of pointless build. The two entries are verified to be in the reference manifest:
- `log:693`: `bartalor/rclcpp:` (the fork providing the rclcpp under test, with branch `bar/issue-2898` at `log:696`)
- `log:1061`: `ros2/system_tests:` (provides `test_rosidl_buffer`, which the SKILL.md-style scope chase needs in src/)

`bartalor/rclcpp` matters because the issue under reproduction is `bar/issue-2898`; `ros2/system_tests` matters because `test_rosidl_buffer` is one of the packages in it (`log:2519`: `- test_rosidl_buffer (ros.ament_cmake)`).

### Step: Set up colcon mixins (`windows-repro.yml:90-95`)

```
- name: Set up colcon mixins (mirrors ci.ros2.org)
  shell: pwsh
  run: |
    pixi run colcon mixin remove default 2>$null
    pixi run colcon mixin add default https://raw.githubusercontent.com/colcon/colcon-mixin-repository/master/index.yaml
    pixi run colcon mixin update default
```

Mirrors the three-line mixin sequence in the reference build (in the same order):
- `log:503`: `==> C:\pixi_ws\.pixi\envs\default\Scripts\colcon.EXE mixin remove default || VER>NUL`
- `log:506`: `==> C:\pixi_ws\.pixi\envs\default\Scripts\colcon.EXE mixin add default https://raw.githubusercontent.com/colcon/colcon-mixin-repository/master/index.yaml`
- `log:508`: `==> C:\pixi_ws\.pixi\envs\default\Scripts\colcon.EXE mixin update default`

The URL is the reference's `--colcon-mixin-url` from CI_ARGS (`log:290`). The `remove` swallows "no such mixin set" errors via `2>$null` (PowerShell's analogue of the reference's `|| VER>NUL`).

**Are the mixins actually consumed?** Per SKILL.md "Windows-specific checks": "Grep the log for `--mixin ` (space-suffixed) — if no hits, no command consumes them and the setup is cosmetic." I grepped:
```
grep -n -- "--mixin " /tmp/ci_windows_27999.log
```
returns **zero hits**. So in the reference, no `colcon build` or `colcon test` line consumes a `--mixin foo` arg. The setup is cosmetic. We mirror it anyway "for parity (the step is cheap and keeps step-by-step diff clean)" per SKILL.md.

### Step: vcs import sources (`windows-repro.yml:97-99`)

```
- name: vcs import sources
  shell: pwsh
  run: pixi run vcs import --force --retry 5 src --input ros2.repos
```

Direct verbatim mirror of `log:1086`:
> `==> vcs import "src" --force --retry 5 --input 00-ros2.repos`

Flags:
- `--force` — overwrite existing checkouts (idempotent re-runs in a non-cached `src/` work).
- `--retry 5` — retry git fetches up to 5 times on transient network failures. Value comes directly from the reference; no need to derive it. Per SKILL.md "Windows-specific checks": "expect the wrapper to add `vcs import --force --retry 5` ... before the build."
- `src --input ros2.repos` — positional target (`src/`) + manifest path. Mirrors the reference (modulo the filename `ros2.repos` vs `00-ros2.repos`).

This is the SKILL.md "`src/` tree" knob in its faithful setting (no cache lookup before this step).

### Step: Show all imported package commits (`windows-repro.yml:101-103`)

```
- name: Show all imported package commits
  shell: pwsh
  run: pixi run vcs log -l1 src
```

Records the resolved per-package commits in the log. Mirrors the reference's `==> vcs log -l1 "src"`:
- `log:1305`: `==> vcs log -l1 "src"`

(`-l1` is `--limit-tag-history 1` → one log entry per repo.) Plain debug parity; not load-bearing for the actual build.

### Step: Restore build/install cache (`windows-repro.yml:105-112`)

```
- name: Restore build/install cache (keyed on pinned manifest)
  id: build-cache
  uses: actions/cache@v4
  with:
    path: |
      build
      install
    key: build-${{ matrix.rmw }}-${{ hashFiles('ros2.repos') }}
```

- `actions/cache@v4` — current major version of the official cache action.
- `path: build / install` — preserves colcon's build artifacts (`build/`) and merged install tree (`install/`) across runs. SKILL.md "What we considered and rejected (generic)" warns about caching as a silent default: "A cache hit at any of those layers means we no longer test the question 'did something change upstream between the reference build and now.'" The mitigation is the key:
- `key: build-${{ matrix.rmw }}-${{ hashFiles('ros2.repos') }}` — the cache scopes per-RMW (so `rmw_fastrtps_cpp`'s artifacts don't trample `rmw_cyclonedds_cpp`'s) **and** invalidates whenever the `ros2.repos` content hash changes (a manifest edit forces a fresh build). So the cache is intentionally narrow.
- Behavior on miss: this is a "restore-and-save" action (default for `actions/cache@v4`); on miss, `build/` and `install/` start empty and the post-step writes them at job-end.

No upstream mirror — the reference Jenkins job runs in a fresh container every time. This is purely an iteration-speed optimization scoped by per-RMW key + manifest hash.

### Step: Resolve vcvarsall.bat path (`windows-repro.yml:114-120`)

```
- name: Resolve vcvarsall.bat path (mirrors ci.ros2.org x86_amd64 cross-toolchain)
  shell: pwsh
  run: |
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    $vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    $vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvarsall.bat"
    "VCVARS=$vcvars" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
```

Finds VS 2022's `vcvarsall.bat` on the runner image and exports its path as `$env:VCVARS` for later steps. `vswhere.exe` is Microsoft's official VS-locator (lives in the `Installer` directory regardless of which VS edition is installed).

Args to `vswhere`:
- `-latest` — pick the newest installed VS instance.
- `-products *` — match any product (BuildTools, Community, Professional, …) — the runner image might use any.
- `-requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64` — must have the **x86 → x64 cross toolchain** component installed. This is the same component the reference Dockerfile installs (`log:161` and `log:167`: `--add Microsoft.VisualStudio.Component.VC.Tools.x86.x64`). Picking exactly the component the toolchain target needs guards against a VS install that lacks it.
- `-property installationPath` — print the install path only.

`Join-Path ... "VC\Auxiliary\Build\vcvarsall.bat"` — the official location of `vcvarsall.bat` for VS 2017+ per Microsoft docs (`https://learn.microsoft.com/en-us/cpp/build/building-on-the-command-line`): "In Visual Studio 2017 and Visual Studio 2019, you'll find them in the `VC\Auxiliary\Build` subdirectory." (Same path applies to VS 2022.) Matches the reference path:
- `log:2263`: `call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86_amd64`

`Out-File ... $env:GITHUB_ENV -Append` — GitHub Actions' mechanism for persisting an env var across subsequent steps in the same job.

### Step: colcon build (`windows-repro.yml:122-124`)

```
- name: colcon build (mirrors ci.ros2.org build #27999 invocation)
  shell: cmd
  run: call "%VCVARS%" x86_amd64 && pixi run colcon build --base-paths src --merge-install --event-handlers console_cohesion+ console_package_list+ --packages-above-and-dependencies rclcpp --cmake-args -DBUILD_TESTING=ON --no-warn-unused-cli -DINSTALL_EXAMPLES=OFF -DSECURITY=ON -DAPPEND_PROJECT_NAME_TO_INCLUDEDIR=ON
```

Reference invocation (verbatim, the one to compare against):
- `log:2275`: `==> env.bat C:\pixi_ws\.pixi\envs\default\Scripts\colcon.EXE build --base-paths "src" --build-base "build" --install-base "install" --merge-install --event-handlers console_cohesion+ console_package_list+ --cmake-args -DBUILD_TESTING=ON --no-warn-unused-cli -DINSTALL_EXAMPLES=OFF -DSECURITY=ON -DAPPEND_PROJECT_NAME_TO_INCLUDEDIR=ON --packages-above-and-dependencies rclcpp`

(`env.bat` wraps `colcon.EXE` with `call vcvarsall.bat x86_amd64`, per `log:2261-2265`.)

Going through every piece of our line:

- `shell: cmd` — required because `vcvarsall.bat` sets env vars in the current cmd.exe; pwsh would lose them. The reference invokes via `env.bat` which is also cmd.
- `call "%VCVARS%" x86_amd64` — sets up VS 2022 env. `x86_amd64` argument: per Microsoft docs on `vcvarsall.bat`, the table reads:
  > `x86_amd64` or `x86_x64` — x64 on x86 cross — Host x86/x64 → Build x64
  
  i.e. "Use the 32-bit x86-native cross tools to build 64-bit x64 code." This is what the reference picks (`log:2263`: `... vcvarsall.bat x86_amd64`); the reference's confirmation message also reads `[vcvarsall.bat] Environment initialized for: 'x86_x64'` (`log:2280, 53605, 125613, 127095`) — `x86_amd64` and `x86_x64` are aliases per the docs.

  Why **not** `x64` or `amd64`? Those would use the 64-bit-native compiler (Hostx64). The reference deliberately uses the 32-bit cross-toolchain. Commit bfd79f27 (`ci(windows-repro): use vcvarsall.bat x86_amd64 to match ci.ros2.org #27999`) records the move.
- `&&` — chain so colcon only runs if vcvars succeeded.
- `pixi run colcon build` — invokes the colcon binary from the pixi env. Reference uses the direct path `C:\pixi_ws\.pixi\envs\default\Scripts\colcon.EXE`; `pixi run` is the public-API equivalent (per SKILL.md "PATH / wrappers" note: "We use `pixi run colcon`").
- `--base-paths src` — root of the source tree. Reference: `--base-paths "src"` (`log:2275`). Match.
- `--merge-install` — single merged `install/` tree (not isolated per-package). Reference: `--merge-install` (`log:2275`). Match.
- `--event-handlers console_cohesion+ console_package_list+` — colcon event handler flags. `console_cohesion+` interleaves per-package stdout into coherent blocks; `console_package_list+` prints a topological package list. Reference: same two flags in the same order (`log:2275`). Match.
- `--packages-above-and-dependencies rclcpp` — build `rclcpp`, every package that **depends on** rclcpp (transitively), **and** the dependencies of those — i.e., everything needed to build rclcpp's reverse-dep closure. Reference: same flag, same arg (`log:2275`). Match.
  - **Note re: prompt's claim "Medium scope, not faithful to the reference":** Looking at `log:2275`, the reference build flag is identical: `--packages-above-and-dependencies rclcpp`. The build-time scope is faithful. (The test-time scope is the one with a meaningful difference — see test step.)
- `--cmake-args` (rest of the line) — args passed to cmake for each package:
  - `-DBUILD_TESTING=ON` — enable tests. Reference: `-DBUILD_TESTING=ON` (`log:2275`). Match. Note this is **not** in `CI_ARGS` from `log:290` — `run_ros2_batch.py` injects it automatically when tests will be run.
  - `--no-warn-unused-cli` — suppress cmake's warning for unused CLI variables. Reference: `--no-warn-unused-cli` (`log:2275`). Match. Same provenance — injected by `run_ros2_batch.py`, not user-specified.
  - `-DINSTALL_EXAMPLES=OFF` — skip example installation. Reference: `log:2275`, also originally in `CI_ARGS` (`log:290`). Match.
  - `-DSECURITY=ON` — enable DDS security plugin builds. Reference: `log:2275, log:290`. Match.
  - `-DAPPEND_PROJECT_NAME_TO_INCLUDEDIR=ON` — install headers under `include/<pkg>/...` (newer ament_cmake convention). Reference: `log:2275, log:290`. Match.

**Build-base / install-base path divergence:** the reference passes `--build-base "build" --install-base "install"` explicitly (`log:2275`). Our line **does not pass them** — but the colcon defaults are `build` and `install` (relative to CWD), so the resolved behavior is identical assuming CWD is the workflow checkout root (which it is). Functional match; flag-list cosmetic divergence.

### Step: colcon test (`windows-repro.yml:126-128`)

```
- name: colcon test (focused on rclcpp + test_rosidl_buffer)
  shell: cmd
  run: call "%VCVARS%" x86_amd64 && call install\local_setup.bat && pixi run colcon test --base-paths src --merge-install --event-handlers console_cohesion+ --packages-select rclcpp test_rosidl_buffer --retest-until-pass 2 --ctest-args -LE xfail --pytest-args -m "not xfail" --executor sequential
```

Reference test invocation (the one to compare against):
- `log:53600`: `==> env.bat C:\pixi_ws\.pixi\envs\default\Scripts\colcon.EXE test --base-paths "src" --build-base "build" --install-base "install" --merge-install --event-handlers console_cohesion+ --retest-until-pass 2 --ctest-args -LE xfail --pytest-args -m "not xfail" --executor sequential --packages-above rclcpp`

Pieces:
- `shell: cmd` — same reason as build step.
- `call "%VCVARS%" x86_amd64` — same reason; reference's `env.bat` does the same (`log:2263`).
- `call install\local_setup.bat` — overlay the just-built install tree into PATH/PYTHONPATH/etc. Required so tests can `import` / `find_package` the packages we just built. The reference does this implicitly via `env.bat` + ROS-distro `local_setup`; matching it explicitly. **⚠ Note**: I did not see an explicit `local_setup.bat` invocation in the reference test stage of the log — the colcon test invocation is on the next line at `log:53600`. The reference may rely on colcon's automatic local_setup chaining. Our explicit call is a belt-and-braces safety net; behavior should match either way. **Mark as a cosmetic divergence, not load-bearing.**
- `pixi run colcon test` — pixi-env colcon, same as build step.
- `--base-paths src` — match (reference: `--base-paths "src"`, `log:53600`).
- `--merge-install` — match (reference, `log:53600`).
- `--event-handlers console_cohesion+` — match (reference: `--event-handlers console_cohesion+`, `log:53600`). Note: build-step has `console_package_list+` too, test-step does not — same as reference.
- `--packages-select rclcpp test_rosidl_buffer` — **🚨 DIVERGENCE from reference**. Reference is `--packages-above rclcpp` (`log:53600`, `log:325`'s parsed test_args). `--packages-above rclcpp` tests rclcpp plus everything that depends on it (transitively) — a much wider scope including `rclcpp_action`, `rclcpp_components`, `rclcpp_lifecycle`, and dozens of downstream packages. `--packages-select rclcpp test_rosidl_buffer` restricts to exactly those two packages.

  This is the SKILL.md "Test selection" knob at its cheapest setting: "cheapest: `--packages-select <failing-test-pkg>`, no retries, parallel executor." We extended it slightly (also include `rclcpp` so any rclcpp-internal tests participate) but the test scope is narrower than the reference. The failing tests we care about all live in `test_rosidl_buffer`, so this is intentional.
- `--retest-until-pass 2` — re-run failing tests up to 2 times before declaring them failed. Reference: `--retest-until-pass 2` (`log:53600`). Match.
- `--ctest-args -LE xfail` — pass `-LE xfail` to ctest, which **excludes** tests labeled `xfail`. (`-LE` = label exclude regex.) Reference: `--ctest-args -LE xfail` (`log:53600`). Match.
- `--pytest-args -m "not xfail"` — pass `-m "not xfail"` to pytest, **excludes** pytest tests marked `xfail`. Reference: `--pytest-args -m "not xfail"` (`log:53600`). Match.
- `--executor sequential` — run packages serially. Reference: `--executor sequential` (`log:53600`). Match. Important: this is contrary to SKILL.md "cheapest: parallel executor" — we picked the faithful setting here for determinism, on the assumption that the failures are timing-sensitive.

### Step: colcon test-result (`windows-repro.yml:130-133`)

```
- name: colcon test-result
  if: always()
  shell: cmd
  run: pixi run colcon test-result --all --verbose
```

Aggregates per-package test results into a summary. `if: always()` ensures it runs even when `colcon test` fails (which it should, since we're reproducing failures).

Reference equivalents:
- `log:125608`: `==> env.bat ... colcon.EXE test-result --test-result-base "build" --all`
- `log:127090`: `==> env.bat ... colcon.EXE test-result --test-result-base "build"`

The reference invokes it twice (once with `--all` for the full dump, once without for a summary). We do it once with `--all --verbose`. `--verbose` adds per-test detail beyond what the reference's `--all` shows. Cosmetic divergence (more output, not less).

### Step: Upload test results (`windows-repro.yml:135-143`)

```
- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-results-${{ matrix.rmw }}
    path: |
      build/**/test_results/**/*.xml
      log/**/*
    retention-days: 7
```

- `actions/upload-artifact@v4` — current major version. Required for `path: |` multi-line lists.
- `name: test-results-${{ matrix.rmw }}` — per-RMW artifact name so multi-RMW matrix runs don't clash.
- `path: build/**/test_results/**/*.xml` — the per-package gtest/junit XMLs colcon produces. These are the load-bearing artifacts (CI test report consumes them).
- `path: log/**/*` — colcon's `log/` directory (per-package stdout/stderr, build/test session logs). Useful for diagnosing failures.
- `retention-days: 7` — keep for 7 days. **⚠ Number choice not pinned to any reference value.** GitHub Actions' default is 90 days; 7 is a reasonable short-retention choice for debug-iteration runs. No upstream mirror — this is a local convention. **⚠ UNJUSTIFIED** for the specific `7`.
- `if: always()` — upload artifacts even when prior steps failed.

---

## What I couldn't justify

Items marked **⚠ UNJUSTIFIED** above, gathered:

1. **`PIXI_TOML_SHA: a22d7b50717dad7c8b3b2bfb36055684600925a5`** (`windows-repro.yml:21`). The Dockerfile in the cached log uses `refs/heads/rolling` (`log:152`), not a SHA, so the link from the SHA to "ros2/ros2@rolling HEAD at 2026-05-14T22:49:27Z" must be reconstructed externally (e.g., via GitHub commit history). I cannot verify it from the cached log alone. The value is in the right shape (40-char hex), the workflow comment claims the right rule, and the SKILL.md table prescribes exactly this reconstruction — but the SHA-vs-timestamp correspondence is taken on trust.

2. **`timeout-minutes: 350`** (`windows-repro.yml:26`). No Jenkins-side timeout appears in the cached log. The value sits just under GitHub Actions' 360-minute hard cap on hosted runners, and is consistent with order-of-magnitude expectations from per-package timings in the log (`rclcpp` alone took 28min on the build side, `log:42627`), but the specific number 350 is a heuristic with no upstream pin.

3. **Step ordering: `pixi list` after `pip install`** vs. reference Dockerfile order (steps 22 then 23). Functionally inconsequential, but a divergence from "verbatim mirror." Logged in main text, called out here for completeness.

4. **Step name says "pixi install (frozen)"** but the command is plain `pixi install` (`windows-repro.yml:63-65`). The "(frozen)" label is left over from an earlier draft and is misleading per SKILL.md "Windows-specific checks" (we cannot use `--frozen` because the later pip install invalidates the lock).

5. **`call install\local_setup.bat`** before colcon test (`windows-repro.yml:128`). I didn't find an explicit equivalent invocation in the reference test stage of the log; the reference may rely on `env.bat`'s default chaining. Our explicit call is safe (idempotent) but not a strict mirror.

6. **`--verbose`** on `colcon test-result` (`windows-repro.yml:133`). Reference does not use `--verbose` (`log:125608, log:127090`). Cosmetic; produces more diagnostic output, not less.

7. **`retention-days: 7`** on artifact upload (`windows-repro.yml:143`). No reference. Local convention.

8. **`--build-base "build" --install-base "install"`** flags missing from our `colcon build`/`colcon test` lines vs the reference (`log:2275`, `log:53600`). The colcon defaults match the reference's explicit values, so behavior is identical; only the flag-list shape differs. Cosmetic.

9. **`cancel-in-progress: true`** in concurrency block (`windows-repro.yml:16`). Tension with SKILL.md "What we considered and rejected (generic)" rule "never auto-cancel". The user has flagged this and kept the value; recorded as ongoing tension per the prompt.

---

## Cross-check tallies (for future iteration)

- Reference build's `^Finished <<<` count: **412** (every package built). When our workflow runs with `--packages-above-and-dependencies rclcpp` (the build-scope faithful setting), this is the number to compare against. A mismatch implies the manifest resolution gave a different graph.
- Reference build's failure count: **9** (all `test_rosidl_buffer` × `rmw_fastrtps_cpp`). When reproducing, this is the target.
- Reference build's `--ignore-rmw`: only `rmw_fastrtps_dynamic_cpp` (`log:290`). Our matrix should not include that RMW; if reproducing the full RMW matrix, mirror this exclusion.
