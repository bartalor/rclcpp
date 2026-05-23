$ErrorActionPreference = "Stop"

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw "vswhere.exe not found at $vswhere" }

$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) { throw "No VS installation with VC tools found" }

$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvars)) { throw "vcvars64.bat not found at $vcvars" }

cmd /c "call `"$vcvars`" && call install\local_setup.bat && colcon test --event-handlers console_cohesion+ --packages-select rclcpp test_rosidl_buffer --retest-until-pass 2 --ctest-args -LE xfail --pytest-args -m `"not xfail`" --executor sequential"
if ($LASTEXITCODE -ne 0) { throw "colcon test failed with exit code $LASTEXITCODE" }
