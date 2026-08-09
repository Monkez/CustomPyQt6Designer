"""One visibility-aware animation clock shared by a MonkezCanva scene."""

from __future__ import annotations

import time
import weakref
from typing import Any

from PyQt6.QtCore import QObject, QPropertyAnimation, QTimer, Qt


class CanvasAnimationScheduler(QObject):
    """Drive all animated graphics through one bounded Qt timer.

    Targets implement ``_animation_active()``, ``_animation_has_packets()`` and
    ``_animation_tick(...)``. Purely visual effects pause with the canvas;
    explicit in-flight packets keep progressing so ``wait_to_end`` cannot hang.
    """

    def __init__(self, canvas: Any, interval_ms: int = 40) -> None:
        super().__init__(canvas)
        self.canvas = canvas
        self._targets: weakref.WeakSet[Any] = weakref.WeakSet()
        self._timer = QTimer(self)
        self._timer.setInterval(max(16, int(interval_ms)))
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._last_tick = time.monotonic()
        self._tick_count = 0
        self._repaint_count = 0

    @property
    def timer(self) -> QTimer:
        return self._timer

    def register(self, target: Any) -> None:
        self._targets.add(target)
        self.refresh()

    def unregister(self, target: Any) -> None:
        self._targets.discard(target)
        self.refresh()

    def refresh(self) -> None:
        active = [target for target in tuple(self._targets) if target._animation_active()]
        visible = self._is_visible()
        critical = any(target._animation_has_packets() for target in active)
        should_run = bool(active) and (visible or critical)
        if should_run and not self._timer.isActive():
            self._last_tick = time.monotonic()
            self._timer.start()
        elif not should_run and self._timer.isActive():
            self._timer.stop()

    def visibility_changed(self) -> None:
        self.refresh()

    def stats(self) -> dict[str, int | bool]:
        targets = tuple(self._targets)
        active = tuple(target for target in targets if target._animation_active())
        return {
            "registeredTargets": len(targets),
            "activeTargets": len(active),
            "inFlightPacketTargets": sum(target._animation_has_packets() for target in active),
            "timerActive": self._timer.isActive(),
            "intervalMs": self._timer.interval(),
            "tickCount": self._tick_count,
            "repaintCount": self._repaint_count,
        }

    def _is_visible(self) -> bool:
        return bool(self.canvas.isVisible() and self.canvas.view().isVisible())

    def _tick(self) -> None:
        now = time.monotonic()
        delta = max(0.0, min(0.25, now - self._last_tick))
        self._last_tick = now
        self._tick_count += 1
        visible = self._is_visible()
        visible_rect = None
        if visible:
            view = self.canvas.view()
            visible_rect = view.mapToScene(view.viewport().rect()).boundingRect()
        for target in tuple(self._targets):
            if not target._animation_active():
                self._targets.discard(target)
                continue
            has_packets = target._animation_has_packets()
            if not visible and not has_packets:
                continue
            repaint = bool(
                visible_rect is not None
                and target.isVisible()
                and target.scene() is not None
                and target.sceneBoundingRect().intersects(visible_rect)
            )
            target._animation_tick(
                now,
                delta,
                advance_visuals=visible,
                allow_loop=visible,
                repaint=repaint,
            )
            if repaint:
                self._repaint_count += 1
        self.refresh()


class ScheduledPropertyAnimation(QPropertyAnimation):
    """A QPropertyAnimation-compatible tween advanced by the canvas clock."""

    def __init__(self, canvas: Any, target: Any, property_name: bytes) -> None:
        super().__init__(target, property_name, canvas)
        self.canvas = canvas
        self.target_item = target
        self._scheduled_active = False
        self._elapsed_ms = 0.0

    def start(self, policy=QPropertyAnimation.DeletionPolicy.KeepWhenStopped) -> None:
        self._elapsed_ms = 0.0
        self._scheduled_active = True
        super().start(policy)
        super().pause()
        self.setCurrentTime(0)
        self.canvas._animation_scheduler.register(self)

    def stop(self) -> None:
        self._scheduled_active = False
        self.canvas._animation_scheduler.unregister(self)
        super().stop()

    def _animation_active(self) -> bool:
        return self._scheduled_active

    @staticmethod
    def _animation_has_packets() -> bool:
        return False

    def _animation_tick(
        self,
        _now: float,
        delta: float,
        *,
        advance_visuals: bool,
        allow_loop: bool,
        repaint: bool,
    ) -> None:
        del allow_loop, repaint
        if not advance_visuals or not self._scheduled_active:
            return
        self._elapsed_ms += max(0.0, delta * 1000.0)
        duration = max(1, self.duration())
        self.setCurrentTime(min(duration, int(self._elapsed_ms)))
        if self._elapsed_ms >= duration:
            self._scheduled_active = False
            self.canvas._animation_scheduler.unregister(self)
            super().stop()
            self.finished.emit()

    def isVisible(self) -> bool:
        return self.target_item.isVisible()

    def scene(self):
        return self.target_item.scene()

    def sceneBoundingRect(self):
        return self.target_item.sceneBoundingRect()
