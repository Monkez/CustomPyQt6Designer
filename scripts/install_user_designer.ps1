param(
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot,
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot
)

$ErrorActionPreference = "Stop"

$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$SourceRoot = [System.IO.Path]::GetFullPath($SourceRoot)
$DesignerExecutable = Join-Path $InstallRoot "venv\Scripts\custom-pyqt6-designer.exe"
$GalleryExecutable = Join-Path $InstallRoot "venv\Scripts\monkez-gallery.exe"

if (-not (Test-Path -LiteralPath $DesignerExecutable)) {
    throw "Installed Designer launcher was not found: $DesignerExecutable"
}

$ToolsDirectory = Join-Path $InstallRoot "tools"
New-Item -ItemType Directory -Path $ToolsDirectory -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $SourceRoot "logo.ico") -Destination (Join-Path $InstallRoot "MonkezDesigner.ico") -Force
Copy-Item -LiteralPath (Join-Path $SourceRoot "uninstall_designer.bat") -Destination (Join-Path $InstallRoot "uninstall_designer.bat") -Force
Copy-Item -LiteralPath (Join-Path $SourceRoot "scripts\uninstall_user_designer.ps1") -Destination (Join-Path $ToolsDirectory "uninstall_user_designer.ps1") -Force

$Shell = New-Object -ComObject WScript.Shell
$ProgramsDirectory = [Environment]::GetFolderPath("Programs")
$DesktopDirectory = [Environment]::GetFolderPath("Desktop")
$StartMenuDirectory = Join-Path $ProgramsDirectory "Monkez Designer"
New-Item -ItemType Directory -Path $StartMenuDirectory -Force | Out-Null

function New-MonkezShortcut {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Target,
        [string]$Description = ""
    )

    $Shortcut = $Shell.CreateShortcut($Path)
    $Shortcut.TargetPath = $Target
    $Shortcut.WorkingDirectory = $InstallRoot
    $Shortcut.IconLocation = Join-Path $InstallRoot "MonkezDesigner.ico"
    $Shortcut.Description = $Description
    $Shortcut.Save()
}

New-MonkezShortcut `
    -Path (Join-Path $StartMenuDirectory "Monkez Designer.lnk") `
    -Target $DesignerExecutable `
    -Description "Open Qt Designer with Monkez custom widgets"
New-MonkezShortcut `
    -Path (Join-Path $DesktopDirectory "Monkez Designer.lnk") `
    -Target $DesignerExecutable `
    -Description "Open Qt Designer with Monkez custom widgets"

if (Test-Path -LiteralPath $GalleryExecutable) {
    New-MonkezShortcut `
        -Path (Join-Path $StartMenuDirectory "Monkez Docs Lab.lnk") `
        -Target $GalleryExecutable `
        -Description "Browse Monkez widgets and runtime methods"
}

New-MonkezShortcut `
    -Path (Join-Path $StartMenuDirectory "Uninstall Monkez Designer.lnk") `
    -Target (Join-Path $InstallRoot "uninstall_designer.bat") `
    -Description "Remove the per-user Monkez Designer installation"

Write-Host "Shortcuts created in: $StartMenuDirectory"
