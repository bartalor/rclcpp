$ErrorActionPreference = "Stop"

$required = @(
  "src\bartalor\rclcpp",
  "src\ros2\system_tests"
)

foreach ($p in $required) {
  if (-not (Test-Path $p)) { throw "Required source path missing: $p" }
  if (-not (Test-Path (Join-Path $p ".git"))) { throw "Not a git checkout: $p" }
}

Write-Host "Source paths OK:"
foreach ($p in $required) { Write-Host "  $p" }
