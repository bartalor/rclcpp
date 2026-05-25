$ErrorActionPreference = "Stop"

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"

cmd /c "call `"$vcvars`" && colcon build --base-paths src --event-handlers console_cohesion+ console_package_list+ --packages-up-to rclcpp test_rosidl_buffer --cmake-args -DBUILD_TESTING=ON -DINSTALL_EXAMPLES=OFF -DSECURITY=ON -DAPPEND_PROJECT_NAME_TO_INCLUDEDIR=ON -DCMAKE_BUILD_TYPE=None"
if ($LASTEXITCODE -ne 0) { throw "colcon build failed with exit code $LASTEXITCODE" }
