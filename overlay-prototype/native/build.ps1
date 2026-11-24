$ErrorActionPreference = "Stop"
$nativeDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildDir = Join-Path $nativeDir "build"
cmake -S $nativeDir -B $buildDir -A x64
cmake --build $buildDir --config Release
