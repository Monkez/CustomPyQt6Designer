$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = ".\.venv311\Scripts\python.exe"
$env:QT_QPA_PLATFORM = "offscreen"

if (-not (Test-Path $Python)) {
    throw "Python environment not found. Run setup.bat first."
}

$ImportSamples = @()
$PaintSamples = @()
for ($Index = 0; $Index -lt 7; $Index++) {
    $ImportSamples += [double](& $Python -c @"
from time import perf_counter
t = perf_counter()
from custom_pyqt6_designer.splash import show_splash
print((perf_counter() - t) * 1000)
"@)
    $PaintSamples += [double](& $Python -c @"
from time import perf_counter
t = perf_counter()
from PyQt6.QtWidgets import QApplication
from custom_pyqt6_designer.splash import show_splash
app = QApplication([])
splash = show_splash(animation_enabled=False, minimum_visible_ms=0)
app.processEvents()
print((perf_counter() - t) * 1000)
splash.widget.close()
"@)
}

function Write-Summary {
    param([string]$Label, [double[]]$Samples)
    $Sorted = $Samples | Sort-Object
    $Median = $Sorted[[math]::Floor($Sorted.Count / 2)]
    Write-Host ("{0}: min={1:N1} ms, median={2:N1} ms, max={3:N1} ms" -f `
        $Label, $Sorted[0], $Median, $Sorted[-1])
}

Write-Summary "Splash import" $ImportSamples
Write-Summary "First paint" $PaintSamples
