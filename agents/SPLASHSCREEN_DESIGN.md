# Splash screen design

## Goals

- Show useful application identity and startup progress as early as possible.
- Keep startup overhead low by using only PyQt6 modules already required at runtime.
- Accept transparent PNG backgrounds and smooth fade/progress/spinner animation.
- Allow progress updates from the GUI thread or worker threads.
- Let users redesign the splash in Qt Designer and load the resulting `.ui`.

## Components

### `MonkezSplashScreen`

A lightweight `QWidget` container. When top-level it uses splash/frameless window
flags; when embedded in Qt Designer it behaves like a regular container.

It provides a default layout and Designer properties for:

- application name, version and status text;
- progress value and visibility;
- background image, colors, radius and padding;
- spinner visibility, color and speed;
- transparent background and window behavior.

Named child widgets in a custom `.ui` override the default presentation:

- `splashAppNameLabel`
- `splashVersionLabel`
- `splashStatusLabel`
- `splashProgressBar`

### `SplashController`

Owns a `MonkezSplashScreen` loaded directly or through `PyQt6.uic.loadUi()`.
Signal-based commands make `set_progress()` and `set_status()` safe to call from
worker threads. The controller handles fade in/out, minimum visible duration,
event processing and transition to the main window.

### `SplashConfig`

A dataclass containing app identity, image, initial message, timing, animation and
window options. `SplashController.create()` and `SplashController.from_ui()` are
the two primary constructors.

## Performance policy

- No OpenCV, QFluentWidgets, C++ or Rust runtime dependency.
- No image decoding until a configured image path is present.
- No busy loop and no blocking sleep in the GUI thread.
- Spinner uses one timer and direct painting.
- Progress animation reuses one `QVariantAnimation`.

C++ or Rust should only be considered after profiling proves the Python/PyQt
implementation misses a measurable startup target. Native FFI would add loading,
packaging and ABI cost without improving Qt's own image decoding or painting.
