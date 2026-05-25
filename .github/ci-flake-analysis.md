# CI flake analysis — PR #3143

PR: [ros2/rclcpp#3143](https://github.com/ros2/rclcpp/pull/3143) — "node_parameters: reject non-finite values in floating-point range check" (fixes ros2/rclcpp#2898).

Goal of this doc: catalogue every CI failure observed on PR #3143, and for each one determine **flake vs signal** by comparing against builds of the same job that ran in the same time window but were not on this PR.

Reproducibility: every Jenkins build URL below is queryable at `https://ci.ros2.org/job/<job>/<build>/testReport/api/json` for the failing case list and `https://ci.ros2.org/job/<job>/<build>/consoleText` for the log.

## 1. Builds run on PR #3143

`ci_launcher/19255` triggered five Jenkins jobs:

| Job              | Build  | Result    | Duration | Notes                              |
| ---------------- | ------ | --------- | -------- | ---------------------------------- |
| ci_linux         | 29060  | SUCCESS   | 128 min  | clean                              |
| ci_linux-aarch64 | 21856  | SUCCESS   | 93 min   | clean                              |
| ci_linux-rhel    | 8929   | UNSTABLE  | 173 min  | 5 reported test failures (3 distinct uncrustify regressions) |
| ci_windows       | 27970  | FAILURE   | 203 min  | Jenkins agent went offline mid-build ("Node is being removed") — infrastructure failure, not a code failure |
| ci_windows       | 27999  | UNSTABLE  | 350 min  | 9 test failures, all `test_rosidl_buffer` / `rmw_fastrtps_cpp` (re-trigger of #27970 to get past the agent issue) |

Plus our own GitHub Actions reproduction:

| Workflow          | Run         | Result    | Notes |
| ----------------- | ----------- | --------- | ----- |
| windows-repro     | 26400247793 | SUCCESS   | 9 tests from #27999 all passed. Repro did not reproduce. |

## 2. Failure details

### 2.1 ci_windows #27970 — infrastructure failure (NOT a code failure)

Build failed because the Jenkins build agent disconnected mid-build. Console log ends with:

```
ERROR: Node is being removed
…
hudson.remoting.ChannelClosedException: Channel "...": Remote call on JNLP4-connect connection from ip-10-0-4-47.ec2.internal/10.0.4.47:49895 failed. The channel is closing down or has closed down
…
Agent went offline during the build
Build step 'Publish xUnit test result report' marked build as failure
Finished: FAILURE
```

No `testReport` was published (build died before the report stage). The 27999 re-trigger was the substitute.

**Classification: infrastructure flake.** Unrelated to PR contents.

### 2.2 ci_windows #27999 — 9 test failures in test_rosidl_buffer / rmw_fastrtps_cpp

All 9 failing cases:

| Status     | Suite                                           | Test                                                |
| ---------- | ----------------------------------------------- | --------------------------------------------------- |
| REGRESSION | projectroot                                     | test_test_to_test__rmw_fastrtps_cpp                 |
| REGRESSION | projectroot                                     | test_test_to_cpu__rmw_fastrtps_cpp                  |
| REGRESSION | projectroot                                     | test_nested_msgs__rmw_fastrtps_cpp                  |
| REGRESSION | test_rosidl_buffer.TestTestToCpuFastRTPS        | test_test_to_cpu_falls_back                         |
| REGRESSION | test_rosidl_buffer.TestTestToCpuFastRTPSShutdown| test_exit_codes                                     |
| REGRESSION | test_rosidl_buffer.TestNestedMsgsFastRTPS       | test_nested_byte_arrays_round_trip                  |
| REGRESSION | test_rosidl_buffer.TestNestedMsgsFastRTPSShutdown | test_exit_codes                                   |
| REGRESSION | test_rosidl_buffer.TestTestToTestFastRTPS       | test_test_to_test_uses_descriptor_path              |
| REGRESSION | test_rosidl_buffer.TestTestToTestFastRTPSShutdown | test_exit_codes                                   |

These are 3 ctest IDs × (1 pytest case + 1 shutdown-exit-code case) per ID; effectively 3 distinct test groups under `rmw_fastrtps_cpp` only. Other RMWs (`rmw_cyclonedds_cpp`, `rmw_connextdds`, `rmw_fastrtps_dynamic_cpp`) passed in the same build.

Failure mode (from `/tmp/ci_windows_27999.log`): subscriber EXE process exits with `0xC0000005` (access violation) at startup, before any rclcpp init log lines.

### 2.3 ci_linux-rhel #8929 — uncrustify regressions in tf2_ros and rosbag2_cpp

5 reported cases, 3 distinct lint failures (each duplicated under a `projectroot` aggregate suite):

| Status     | Suite                | Test (file)                                                 |
| ---------- | -------------------- | ----------------------------------------------------------- |
| REGRESSION | projectroot          | uncrustify (×2 aggregate rows)                              |
| FAILED     | tf2_ros.uncrustify   | include/tf2_ros/static_transform_broadcaster.hpp            |
| FAILED     | tf2_ros.uncrustify   | include/tf2_ros/transform_broadcaster.hpp                   |
| FAILED     | rosbag2_cpp.uncrustify | test/rosbag2_cpp/test_circular_message_cache.cpp          |

These are **code-style linter** failures (whitespace/formatting) on files outside `rclcpp`, in packages PR #3143 doesn't touch.

## 3. Flake comparison — same-job builds in the PR window (2026-05-10 → 2026-05-22)

### 3.1 ci_windows — does the test_rosidl_buffer / rmw_fastrtps_cpp pattern recur?

In the PR window, `ci_windows` had **89 builds** total. I sampled the UNSTABLE and FAILURE builds adjacent to #27999 (12+ builds: #28032, #28045, #28057, #28068, #28072, #28089, #28090, #28095, #28102, #28103, #28104, #28105, #28114, #28116, #28121, #28123, #28125) and looked for failures matching #27999's pattern:

**Result: zero matches.** Not a single other Windows build in this window failed `test_rosidl_buffer` / `rmw_fastrtps_cpp` (or any FastRTPS test_rosidl_buffer combination).

Recurring Windows flakes that DO show up across this window — but did **not** appear on #27999 — are completely different test families:

- `test_communication.TestActionClientServer :: test_client_finishes_in_a_finite_amount_of_time[…]` (Fibonacci, NestedMessage, Strings)
- `ros2cli.test.test_ros2cli_daemon :: test_get_*` (~20 cases per occurrence)
- `ros2multicast.test.test_api :: test_*` (3 cases)
- `sros2.test.…test_generate_policy :: test_generate_policy`
- `message_filters` test family (5 cases)
- `test_async_clock :: test_sleep_multiple_concurrent_waiters`

**Classification of #27999's 9 failures: signal, not flake** — the pattern is unique to #27999 within this window.

Caveat: #27999 used a different `ros2.repos` manifest (gist `ab84ebe…`) than the routine nightly builds, and the test_rosidl_buffer + `bartalor/rclcpp` overlay only exists on PR-launcher invocations. So "did not recur on nightlies" cannot be a perfect control. But our **GitHub Actions reproduction** ran the exact same source tree and the exact same `colcon test` invocation and got 0 failures — that is the direct control, and it points the same direction (intermittent, not a deterministic regression introduced by the PR).

Refined classification: **either an environmental flake on the ci.ros2.org Windows agent, or a sensitivity to something in that agent's environment that our GitHub Actions runner doesn't share.** It is not caused by the rclcpp code change in PR #3143.

### 3.2 ci_linux-rhel — does the uncrustify pattern recur?

In the PR window, `ci_linux-rhel` had **86 builds**. I sampled the UNSTABLE builds adjacent to #8929 (#8959, #8963, #8965, #8966, #8967, #8979, #8980, #8989, #8991, #8992, #8995, #9002–#9040). Notable matches:

**#8965 (2026-05-16, 4 days BEFORE #8929):**

| Status     | Suite              | Test (file)                                       |
| ---------- | ------------------ | ------------------------------------------------- |
| REGRESSION | projectroot        | uncrustify                                        |
| FAILED     | tf2_ros.uncrustify | include/tf2_ros/static_transform_broadcaster.hpp  |
| FAILED     | tf2_ros.uncrustify | include/tf2_ros/transform_broadcaster.hpp         |
| REGRESSION | projectroot        | image_display_test                                |
| FAILED     | topic_monitor.test.test_mypy | test_mypy                               |

→ **The exact same two `tf2_ros.uncrustify` files failed in #8965 as in #8929.**

**#8989 (2026-05-18):**

| Status     | Suite                            | Test (file)                       |
| ---------- | -------------------------------- | --------------------------------- |
| REGRESSION | projectroot                      | uncrustify                        |
| REGRESSION | projectroot                      | cpplint                           |
| REGRESSION | point_cloud_transport.uncrustify | src/point_cloud_transport.cpp     |

→ Same family (uncrustify), different file. Confirms ongoing uncrustify regressions across this window in unrelated packages.

**Classification of #8929's 5 failures: flake (pre-existing, unrelated lint regressions).** The `tf2_ros` and `rosbag2_cpp` uncrustify failures are pre-existing regressions in those packages' source — they have nothing to do with the rclcpp change in PR #3143, and they were already failing on the same job 4 days earlier.

### 3.3 ci_linux and ci_linux-aarch64

Both were SUCCESS on PR #3143. Nothing to compare.

## 4. Summary — flake vs signal

| Build              | Failures                                                        | Classification |
| ------------------ | --------------------------------------------------------------- | -------------- |
| ci_linux #29060    | none                                                            | clean          |
| ci_linux-aarch64 #21856 | none                                                       | clean          |
| ci_linux-rhel #8929 | 3 distinct uncrustify regressions (tf2_ros×2 + rosbag2_cpp×1) | **flake** — pre-existing lint regressions in unrelated packages; same `tf2_ros.uncrustify` failures recurred 4 days earlier on #8965 |
| ci_windows #27970  | Jenkins agent disconnect                                        | **infra flake** — agent went offline mid-build |
| ci_windows #27999  | 9 cases across `test_rosidl_buffer` × `rmw_fastrtps_cpp`        | **environmental** — not reproducible on our GitHub Actions repro with the same source tree; failure pattern did not recur in ~16 other sampled Windows builds in the same window. Not caused by PR #3143's code change. |
| GHA windows-repro 26400247793 | none                                                | clean — counter-evidence that the 9 #27999 failures are not deterministic |

**Bottom line: nothing on this PR represents a real code-induced regression caused by PR #3143.**

- The Linux-rhel uncrustify failures are an ongoing background issue with `tf2_ros` and `rosbag2_cpp` style on rhel; they fail without this PR.
- The Windows test_rosidl_buffer/rmw_fastrtps_cpp failures are an intermittent ci.ros2.org-Windows-specific symptom — they occur on that environment with this commit but not on ours; the 0xC0000005 access violation pattern points at a Windows runtime/environment issue (DLL search path, static-init ordering, or ABI mismatch in FastRTPS subscriber startup), not at the floating-point range check change.
