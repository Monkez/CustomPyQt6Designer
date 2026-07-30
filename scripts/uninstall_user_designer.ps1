param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "MonkezDesigner")
)

$ErrorActionPreference = "Stop"

$ExpectedRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $env:LOCALAPPDATA "MonkezDesigner")
).TrimEnd("\")
$ResolvedRoot = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd("\")
if (-not $ResolvedRoot.Equals($ExpectedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove unexpected install directory: $ResolvedRoot"
}

$StartMenuDirectory = Join-Path ([Environment]::GetFolderPath("Programs")) "Monkez Designer"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "Monkez Designer.lnk"

if (Test-Path -LiteralPath $DesktopShortcut) {
    Remove-Item -LiteralPath $DesktopShortcut -Force
}
if (Test-Path -LiteralPath $StartMenuDirectory) {
    Remove-Item -LiteralPath $StartMenuDirectory -Recurse -Force
}
if (Test-Path -LiteralPath $ResolvedRoot) {
    Remove-Item -LiteralPath $ResolvedRoot -Recurse -Force
}

Write-Host "Monkez Designer was removed from this Windows account."
