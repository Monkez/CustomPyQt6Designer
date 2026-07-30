# Heavy startup executable demo

This Windows demo proves that the splash animation remains responsive while the
application performs expensive initialization on a background thread.

## Run the prepared executable

Double-click:

```text
run_splash_exe_demo.bat
```

The executable is located at:

```text
dist\SplashHeavyDemo\SplashHeavyDemo.exe
```

No Python installation is needed when the complete `SplashHeavyDemo` directory
or its ZIP archive is copied to another Windows x64 machine.

## Demonstrated workload

The worker performs these tasks outside Qt's GUI thread:

- creates and parses 16,000 configuration records;
- generates, validates and hashes 48 MB of asset data;
- builds and sorts a 320,000-item search index;
- runs 2.4 million calculation-engine iterations;
- restores a simulated workspace.

The splash receives queued progress updates from the worker. The resulting main
window reports total startup time, processed data and the largest observed GUI
heartbeat gap.

On the release workstation, the complete workload takes approximately 13
seconds. The measured duration is intentionally long enough to observe the
spinner, progress animation and responsive GUI behavior.

## Rebuild

Double-click:

```text
build_splash_demo.bat
```

The build intentionally uses PyInstaller `onedir`. A `onefile` executable must
extract its embedded runtime before Python and Qt can show the splash, which
would make the first visible frame slower.

The build script runs the packaged app in a short verification mode before
creating `dist\SplashHeavyDemo-windows-x64.zip`.
