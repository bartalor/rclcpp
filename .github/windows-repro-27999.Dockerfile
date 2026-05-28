# escape=`
# Mirrors ci.ros2.org Windows build #27999's Dockerfile.
# Deviations (documented, intentional):
#   - Base image: mcr.microsoft.com/windows/server:ltsc2022 (was :2009).
#     Windows containers require host/image kernel match under
#     --isolation=process; GHA windows-2022 runners are ltsc2022 and the
#     only isolation available is process. :2009 image will not start.
#   - Skip VS BuildTools 2019 install (#27999 Steps 8-9). #27999 builds with
#     --visual-studio-version 2022; 2019 is dead weight here.
#   - Skip RTI Connext install (#27999 Steps 25-30). The 9 failing tests
#     all run under rmw_fastrtps_cpp; Connext is not exercised.

ARG ROS_DISTRO=rolling
FROM mcr.microsoft.com/windows/server:ltsc2022

ARG ROS_DISTRO
ARG PIXI_VERSION
ARG PIXI_ZIP_SHA256
ARG PIXI_TOML_SHA
ARG PIXI_TOML_URL=https://raw.githubusercontent.com/ros2/ros2/${PIXI_TOML_SHA}/pixi.toml

# Promote ARGs to ENV so RUN lines see them. Per Docker docs, the builder
# does NOT substitute ${VAR} inside RUN -- substitution there is the shell's
# job. ENV makes them available to PowerShell as $env:VAR.
ENV PIXI_VERSION=${PIXI_VERSION}
ENV PIXI_ZIP_SHA256=${PIXI_ZIP_SHA256}

RUN powershell -noexit "New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force"

RUN powershell -noexit irm https://aka.ms/vs/17/release/vs_buildtools.exe -OutFile vs_buildtools_2022.exe
RUN vs_buildtools_2022.exe --quiet --wait --norestart `
    --add Microsoft.Component.MSBuild `
    --add Microsoft.Net.Component.4.6.1.TargetingPack `
    --add Microsoft.Net.Component.4.8.SDK `
    --add Microsoft.VisualStudio.Component.CoreBuildTools `
    --add Microsoft.VisualStudio.Component.Roslyn.Compiler `
    --add Microsoft.VisualStudio.Component.TextTemplating `
    --add Microsoft.VisualStudio.Component.VC.CLI.Support `
    --add Microsoft.VisualStudio.Component.VC.CoreBuildTools `
    --add Microsoft.VisualStudio.Component.VC.CoreIde `
    --add Microsoft.VisualStudio.Component.VC.Redist.14.Latest `
    --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    --add Microsoft.VisualStudio.Component.Windows10SDK `
    --add Microsoft.VisualStudio.Component.Windows10SDK.19041 `
    --add Microsoft.VisualStudio.ComponentGroup.NativeDesktop.Core `
    --add Microsoft.VisualStudio.Workload.MSBuildTools `
    --add Microsoft.VisualStudio.Workload.VCTools

RUN powershell -noexit "irm https://github.com/prefix-dev/pixi/releases/download/$env:PIXI_VERSION/pixi-x86_64-pc-windows-msvc.zip -OutFile pixi-x86_64-pc-windows-msvc.zip"
RUN powershell -noexit "if ((get-filehash pixi-x86_64-pc-windows-msvc.zip -Algorithm SHA256).hash -ne $env:PIXI_ZIP_SHA256) { exit 1 }"
RUN powershell -noexit "Expand-Archive -Path pixi-x86_64-pc-windows-msvc.zip -DestinationPath (Join-Path $Env:USERPROFILE\.pixi 'bin') -Force"
RUN powershell -noexit "$bindir = Join-Path $Env:USERPROFILE\.pixi 'bin' ; $pathkey = (Get-Item -Path 'HKCU:').OpenSubKey('Environment', $true) ; $oldpath = $pathkey.GetValue('PATH', $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) ; $newpath = \"$bindir;$oldpath\" ; $pathkey.SetValue('PATH', $newpath, [Microsoft.Win32.RegistryValueKind]::String)"

WORKDIR C:\pixi_ws
ADD ${PIXI_TOML_URL} pixi.toml
RUN powershell -Command "(Get-Item pixi.toml).LastWriteTime = Get-Date"
RUN pixi --color never --no-progress -q install
RUN pixi --color never --no-progress -q list
RUN pixi --color never --no-progress -q run "pip install 'colcon-ros-domain-id-coordinator >= 0.2.3'"

ENV ROS_DISTRO=${ROS_DISTRO}
WORKDIR C:\ci
