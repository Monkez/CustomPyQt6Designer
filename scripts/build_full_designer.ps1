$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = ".\.venv311\Scripts\python.exe"
$PyInstaller = ".\.venv311\Scripts\pyinstaller.exe"
$PyInstallerVersion = "6.21.0"

if (-not (Test-Path $Python)) {
    throw "Python 3.11 environment not found. Run setup.bat first."
}

$Version = & $Python -c "from monkez_pyqt6 import __version__; print(__version__)"
$PythonHome = & $Python -c "import sys; print(sys.base_prefix)"
$PortableBuildRoot = "dist\portable\$Version"
$OutputDirectory = Join-Path $PortableBuildRoot "MonkezDesigner"
$ArchivePath = "dist\MonkezDesigner-$Version-windows-x64.zip"

& $Python -m pip install "pyinstaller==$PyInstallerVersion"
if ($LASTEXITCODE -ne 0) {
    throw "Could not install PyInstaller $PyInstallerVersion."
}

& $PyInstaller `
    --clean `
    --noconfirm `
    --onedir `
    --windowed `
    --name MonkezDesigner `
    --distpath $PortableBuildRoot `
    --icon "logo.ico" `
    --paths src `
    --add-data "logo.png;." `
    --add-data "logo.ico;." `
    --add-data "src\monkez_pyqt6;monkez_pyqt6" `
    --add-data ".venv311\Lib\site-packages\PyQt6;PyQt6" `
    --add-data ".venv311\Lib\site-packages\pyqt6_plugins;pyqt6_plugins" `
    --add-data ".venv311\Lib\site-packages\qt6_applications;qt6_applications" `
    --add-data ".venv311\Lib\site-packages\qt6_tools;qt6_tools" `
    --add-data ".venv311\Lib\site-packages\pyqt6_tools;pyqt6_tools" `
    --add-data ".venv311\Lib\site-packages\cv2;cv2" `
    --add-data ".venv311\Lib\site-packages\numpy;numpy" `
    --add-data ".venv311\Lib\site-packages\numpy.libs;numpy.libs" `
    --collect-all qfluentwidgets `
    --collect-all qframelesswindow `
    --add-data "$PythonHome\Lib;python_runtime\Lib" `
    --add-data "$PythonHome\DLLs;python_runtime\DLLs" `
    --add-binary "$PythonHome\python3.dll;python_runtime" `
    --add-binary "$PythonHome\python311.dll;python_runtime" `
    --add-binary "$PythonHome\vcruntime140.dll;python_runtime" `
    --add-binary "$PythonHome\vcruntime140_1.dll;python_runtime" `
    src\monkez_pyqt6\exe_entry.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$PortableFiles = @(
    "packaging\portable\New Splash Screen.bat",
    "packaging\portable\Open Monkez Designer.bat",
    "packaging\portable\START_HERE.txt"
)
foreach ($PortableFile in $PortableFiles) {
    Copy-Item -LiteralPath $PortableFile -Destination $OutputDirectory -Force
}

$VerificationUi = (Resolve-Path "src\monkez_pyqt6\templates\monkez_splash_screen.ui").Path
$Verification = Start-Process `
    -FilePath "$OutputDirectory\MonkezDesigner.exe" `
    -ArgumentList "--verify-plugins `"$VerificationUi`"" `
    -Wait `
    -PassThru
if ($Verification.ExitCode -ne 0) {
    throw "Bundled Designer plugin verification failed."
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
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    (Resolve-Path $OutputDirectory).Path,
    (Join-Path $Root $ArchivePath),
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

Write-Host "Built: $OutputDirectory\MonkezDesigner.exe"
Write-Host "Archive: $ArchivePath"
