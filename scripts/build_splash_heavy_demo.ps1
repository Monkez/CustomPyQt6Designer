$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = ".\.venv311\Scripts\python.exe"
$PyInstaller = ".\.venv311\Scripts\pyinstaller.exe"
$PyInstallerVersion = "6.21.0"
$OutputDirectory = "dist\SplashHeavyDemo"
$Executable = "$OutputDirectory\SplashHeavyDemo.exe"
$ArchivePath = "dist\SplashHeavyDemo-windows-x64.zip"

if (-not (Test-Path $Python)) {
    throw "Python 3.11 environment not found. Run setup.bat first."
}

& $Python -m pip install "pyinstaller==$PyInstallerVersion"
if ($LASTEXITCODE -ne 0) {
    throw "Could not install PyInstaller $PyInstallerVersion."
}

& $PyInstaller `
    --clean `
    --noconfirm `
    --onedir `
    --windowed `
    --name SplashHeavyDemo `
    --icon "logo.ico" `
    --paths src `
    --add-data "logo.png;." `
    --hidden-import "monkez_pyqt6.monkez_widgets.monkez_splash_screen" `
    splash_heavy_demo\launcher.py

if ($LASTEXITCODE -ne 0) {
    throw "Splash demo build failed."
}

$LockHolder = Start-Process `
    -FilePath $Executable `
    -ArgumentList "--verify-startup-lock" `
    -PassThru
$StartupLockPath = & $Python -c "from monkez_pyqt6.startup_guard import StartupInstanceGuard; print(StartupInstanceGuard('com.monkez.splash-heavy-demo').lock_path)"
$LockDeadline = (Get-Date).AddSeconds(10)
while (-not (Test-Path -LiteralPath $StartupLockPath)) {
    $LockHolder.Refresh()
    if ($LockHolder.HasExited) {
        throw "The startup-lock holder exited before acquiring its lock."
    }
    if ((Get-Date) -ge $LockDeadline) {
        $LockHolder.Kill()
        throw "Timed out waiting for the packaged startup lock."
    }
    Start-Sleep -Milliseconds 50
}
$BlockedDuplicate = Start-Process `
    -FilePath $Executable `
    -ArgumentList "--verify-startup-lock" `
    -Wait `
    -PassThru
if ($BlockedDuplicate.ExitCode -ne 73) {
    if (-not $LockHolder.HasExited) {
        $LockHolder.Kill()
    }
    throw "A concurrent startup was not blocked by the packaged executable."
}
$LockHolder.WaitForExit()
if ($LockHolder.ExitCode -ne 0) {
    throw "The packaged startup-lock holder failed."
}

$Verification = Start-Process `
    -FilePath $Executable `
    -ArgumentList "--verify" `
    -Wait `
    -PassThru
if ($Verification.ExitCode -ne 0) {
    throw "The packaged splash demo failed its startup verification."
}

function Wait-FileUnlocked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [int]$TimeoutSeconds = 30
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        try {
            $Stream = [System.IO.File]::Open(
                $Path,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::Read,
                [System.IO.FileShare]::None
            )
            $Stream.Dispose()
            return
        }
        catch [System.IO.IOException] {
            Start-Sleep -Milliseconds 250
        }
    }
    throw "Timed out waiting for release file to unlock: $Path"
}

$BaseLibrary = Join-Path $OutputDirectory "_internal\base_library.zip"
Wait-FileUnlocked -Path $BaseLibrary

if (Test-Path $ArchivePath) {
    Remove-Item -LiteralPath $ArchivePath -Force
}
Compress-Archive `
    -Path "$OutputDirectory\*" `
    -DestinationPath $ArchivePath `
    -CompressionLevel Optimal

Write-Host "Verified executable: $Executable"
Write-Host "Portable archive: $ArchivePath"
