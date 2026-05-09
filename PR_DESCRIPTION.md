## Description

Fixes #2898. `__check_double_range` accepted `+inf`, `-inf`, and `NaN` for parameters declared with a `floating_point_range`. Fix guards `__are_doubles_equal` against non-finite operands and rewrites the bound check so `NaN` is rejected.

### Is this user-facing behavior change?

Yes. `set_parameter` with `+inf`, `-inf`, or `NaN` on a parameter with a `floating_point_range` now returns `successful=false`.

### Did you use Generative AI?

Yes — Claude Opus 4.7.

### Additional Information

Adds a regression test in `test_node.cpp` for the three non-finite cases. The new scope block pushes the existing `TEST_F` over cpplint's 800-line limit, so a `// NOLINT(readability/fn_size)` is added on its closing brace — same pattern other ROS 2 packages use for this case.
