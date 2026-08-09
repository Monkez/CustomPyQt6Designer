"""Minimal reversible document patches backed by Qt's undo framework."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Iterable

from PyQt6.QtGui import QUndoCommand

from monkez_pyqt6.monkez_canva import CanvasDocument


_RECORD_COLLECTIONS = ("elements", "connectors", "groups", "resources")


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


@dataclass(frozen=True, slots=True)
class DocumentPatch:
    collection: str
    record_id: str
    before: Any
    after: Any
    before_index: int = -1
    after_index: int = -1


def patches_from_documents(
    before: dict[str, Any], after: dict[str, Any]
) -> tuple[DocumentPatch, ...]:
    """Return only changed scene/records, never a whole-document snapshot."""
    patches: list[DocumentPatch] = []
    if before.get("scene", {}) != after.get("scene", {}):
        patches.append(
            DocumentPatch("scene", "scene", _copy(before.get("scene", {})), _copy(after.get("scene", {})))
        )
    for collection in _RECORD_COLLECTIONS:
        previous_records = before.get(collection, [])
        current_records = after.get(collection, [])
        previous = {str(item["id"]): item for item in previous_records}
        current = {str(item["id"]): item for item in current_records}
        previous_indexes = {str(item["id"]): index for index, item in enumerate(previous_records)}
        current_indexes = {str(item["id"]): index for index, item in enumerate(current_records)}
        for record_id in dict.fromkeys((*previous, *current)):
            old = previous.get(record_id)
            new = current.get(record_id)
            if old != new:
                patches.append(
                    DocumentPatch(
                        collection,
                        record_id,
                        _copy(old),
                        _copy(new),
                        previous_indexes.get(record_id, -1),
                        current_indexes.get(record_id, -1),
                    )
                )
    known = {"format", "version", "scene", *_RECORD_COLLECTIONS}
    previous_metadata = {key: value for key, value in before.items() if key not in known}
    current_metadata = {key: value for key, value in after.items() if key not in known}
    if previous_metadata != current_metadata:
        patches.append(
            DocumentPatch("metadata", "document", _copy(previous_metadata), _copy(current_metadata))
        )
    return tuple(patches)


def apply_patches(
    document: CanvasDocument,
    patches: Iterable[DocumentPatch],
    *,
    forward: bool,
    origin: Any = None,
) -> None:
    payload = document.to_dict()
    for patch in patches:
        value = patch.after if forward else patch.before
        if patch.collection == "scene":
            payload["scene"] = _copy(value)
            continue
        if patch.collection == "metadata":
            known = {"format", "version", "scene", *_RECORD_COLLECTIONS}
            for key in tuple(payload):
                if key not in known:
                    payload.pop(key)
            payload.update(_copy(value))
            continue
        records = payload.setdefault(patch.collection, [])
        index = next(
            (position for position, item in enumerate(records) if str(item["id"]) == patch.record_id),
            -1,
        )
        if value is None:
            if index >= 0:
                records.pop(index)
        elif index >= 0:
            records[index] = _copy(value)
            target_index = patch.after_index if forward else patch.before_index
            if target_index >= 0 and target_index != index:
                record = records.pop(index)
                records.insert(min(target_index, len(records)), record)
        else:
            target_index = patch.after_index if forward else patch.before_index
            if target_index < 0:
                records.append(_copy(value))
            else:
                records.insert(min(target_index, len(records)), _copy(value))
    document.reconcile(payload, origin=origin)


class CanvasDocumentCommand(QUndoCommand):
    """A mergeable command containing only changed record pairs."""

    MERGE_ID = 0x4D43

    def __init__(
        self,
        document: CanvasDocument,
        patches: Iterable[DocumentPatch],
        text: str,
        *,
        merge_key: str = "",
        already_applied: bool = False,
        origin: Any = None,
    ) -> None:
        super().__init__(str(text))
        self.document = document
        self.patches = tuple(patches)
        self.merge_key = str(merge_key)
        self.origin = origin
        self._skip_first_redo = bool(already_applied)
        self._updated_at = time.monotonic()

    def id(self) -> int:
        return self.MERGE_ID if self.merge_key else -1

    def redo(self) -> None:
        if self._skip_first_redo:
            self._skip_first_redo = False
            return
        apply_patches(self.document, self.patches, forward=True, origin=self.origin)

    def undo(self) -> None:
        apply_patches(self.document, self.patches, forward=False, origin=self.origin)

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, CanvasDocumentCommand):
            return False
        if not self.merge_key or self.merge_key != other.merge_key:
            return False
        if self.document is not other.document or time.monotonic() - self._updated_at > 0.8:
            return False
        own = {(patch.collection, patch.record_id): patch for patch in self.patches}
        incoming = {(patch.collection, patch.record_id): patch for patch in other.patches}
        if own.keys() != incoming.keys():
            return False
        self.patches = tuple(
            DocumentPatch(
                key[0], key[1], own[key].before, incoming[key].after,
                own[key].before_index, incoming[key].after_index,
            )
            for key in own
        )
        self._updated_at = time.monotonic()
        return True


class CanvasRenameCommand(QUndoCommand):
    """Preserve graphics/model identity by using explicit rename operations."""

    def __init__(
        self,
        document: CanvasDocument,
        old_id: str,
        new_id: str,
        *,
        connector: bool = False,
    ) -> None:
        super().__init__("Rename connector" if connector else "Rename element")
        self.document = document
        self.old_id = str(old_id)
        self.new_id = str(new_id)
        self.connector = bool(connector)

    def _rename(self, old_id: str, new_id: str) -> None:
        if self.connector:
            self.document.rename_connector(old_id, new_id)
        else:
            self.document.rename_element(old_id, new_id)

    def redo(self) -> None:
        self._rename(self.old_id, self.new_id)

    def undo(self) -> None:
        self._rename(self.new_id, self.old_id)
