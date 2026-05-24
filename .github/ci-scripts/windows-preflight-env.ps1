$ErrorActionPreference = "Stop"

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw "vswhere.exe not found at $vswhere" }

$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) { throw "No VS installation with VC tools found" }

$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvars)) { throw "vcvars64.bat not found at $vcvars" }

if (-not (Get-Command colcon -ErrorAction SilentlyContinue)) { throw "colcon not on PATH" }
if (-not (Get-Command vcs -ErrorAction SilentlyContinue)) { throw "vcs not on PATH" }

Write-Host "vswhere : $vswhere"
Write-Host "vsPath  : $vsPath"
Write-Host "vcvars  : $vcvars"
Write-Host "colcon  : $((Get-Command colcon).Source)"
Write-Host "vcs     : $((Get-Command vcs).Source)"
