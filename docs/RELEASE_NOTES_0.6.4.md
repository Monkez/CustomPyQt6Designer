# Monkez PyQt6 0.6.4

- Added runtime viewport lock (`viewLocked`) for zoom and pan.
- Added runtime interaction lock (`interactionLocked`) for selection, drag,
  connection, delete, clipboard editing and undo/redo.
- Both locks are available as Python methods, Qt properties/signals and View
  pane controls, with edit mode as an explicit override.
