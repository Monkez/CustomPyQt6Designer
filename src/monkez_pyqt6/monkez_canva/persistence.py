"""Crash-safe JSON and managed-asset persistence for MonkezCanva."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


ASSET_MANIFEST_KEY = "assetManifest"


@dataclass(frozen=True, slots=True)
class RecoveryLoadResult:
    payload: dict[str, Any]
    source: Path
    recovered_from_backup: bool = False
    primary_error: str = ""


@dataclass(frozen=True, slots=True)
class AssetIntegrityIssue:
    path: str
    reason: str
    expected: str = ""
    actual: str = ""

    def message(self) -> str:
        detail = f" (expected {self.expected}, got {self.actual})" if self.expected or self.actual else ""
        return f"Asset {self.path!r}: {self.reason}{detail}"


def backup_path(path: str | Path) -> Path:
    target = Path(path)
    return target.with_suffix(target.suffix + ".bak")


def _write_bytes_atomically(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            raise


def atomic_write_json(
    path: str | Path,
    payload: Mapping[str, Any],
    *,
    create_backup: bool = True,
    indent: int | None = 2,
) -> Path:
    """Write valid UTF-8 JSON through a same-directory atomic replace.

    A valid previous primary is copied to ``.bak`` before replacement. An
    already-valid backup is deliberately retained when the primary is corrupt.
    """

    target = Path(path)
    serialized = json.dumps(
        dict(payload), ensure_ascii=False, indent=indent, allow_nan=False
    ).encode("utf-8")
    json.loads(serialized.decode("utf-8"))
    target.parent.mkdir(parents=True, exist_ok=True)
    if create_backup and target.is_file():
        try:
            previous = target.read_bytes()
            json.loads(previous.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            previous = b""
        if previous:
            _write_bytes_atomically(backup_path(target), previous)
    _write_bytes_atomically(target, serialized)
    return target


def load_json_with_recovery(path: str | Path) -> RecoveryLoadResult:
    """Load the primary JSON, falling back to its last valid backup."""

    target = Path(path)
    primary_error = ""
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("document root is not a JSON object")
        return RecoveryLoadResult(payload, target)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        primary_error = f"{type(error).__name__}: {error}"
    backup = backup_path(target)
    try:
        payload = json.loads(backup.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("backup root is not a JSON object")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as backup_error:
        raise ValueError(
            f"Cannot load MonkezCanva document {target}: {primary_error}; "
            f"backup failed: {type(backup_error).__name__}: {backup_error}"
        ) from backup_error
    return RecoveryLoadResult(payload, backup, True, primary_error)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative_asset_paths(document: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()

    def add(value: Any) -> None:
        text = str(value or "").strip().replace("\\", "/")
        if (
            text
            and "://" not in text
            and not text.lower().startswith(("data:", "qrc:"))
            and not Path(text).is_absolute()
        ):
            values.add(text)

    scene = document.get("scene", {})
    if isinstance(scene, Mapping):
        add(scene.get("backgroundImage"))
    for record in document.get("elements", []):
        if isinstance(record, Mapping):
            add(record.get("source"))
            add(record.get("packetIcon"))
    for record in document.get("connectors", []):
        if isinstance(record, Mapping):
            add(record.get("packetIcon"))
    for resource in document.get("resources", []):
        if isinstance(resource, Mapping):
            add(resource.get("uri"))
    return values


def _safe_asset(root: Path, relative: str) -> Path | None:
    try:
        candidate = (root / Path(relative)).resolve()
        candidate.relative_to(root.resolve())
        return candidate
    except (OSError, ValueError):
        return None


def build_asset_manifest(
    document: Mapping[str, Any], root: str | Path
) -> dict[str, dict[str, Any]]:
    base = Path(root)
    manifest: dict[str, dict[str, Any]] = {}
    for relative in sorted(_relative_asset_paths(document)):
        candidate = _safe_asset(base, relative)
        if candidate is None or not candidate.is_file():
            continue
        manifest[relative] = {
            "sha256": sha256_file(candidate),
            "size": candidate.stat().st_size,
        }
    return manifest


def verify_asset_manifest(
    document: Mapping[str, Any], root: str | Path
) -> tuple[AssetIntegrityIssue, ...]:
    base = Path(root)
    if ASSET_MANIFEST_KEY not in document:
        return ()
    manifest = document.get(ASSET_MANIFEST_KEY, {})
    if not isinstance(manifest, Mapping):
        return (AssetIntegrityIssue("", "asset manifest is not a JSON object"),)
    issues: list[AssetIntegrityIssue] = []
    referenced = _relative_asset_paths(document)
    for relative in sorted(referenced):
        candidate = _safe_asset(base, relative)
        if candidate is None:
            issues.append(AssetIntegrityIssue(relative, "path escapes the project workspace"))
            continue
        expected = manifest.get(relative)
        if not candidate.is_file():
            issues.append(AssetIntegrityIssue(relative, "file is missing"))
            continue
        if not isinstance(expected, Mapping):
            issues.append(AssetIntegrityIssue(relative, "checksum is not recorded"))
            continue
        expected_hash = str(expected.get("sha256", ""))
        actual_hash = sha256_file(candidate)
        if not expected_hash or actual_hash.lower() != expected_hash.lower():
            issues.append(
                AssetIntegrityIssue(relative, "checksum mismatch", expected_hash, actual_hash)
            )
            continue
        expected_size = expected.get("size")
        if isinstance(expected_size, int) and candidate.stat().st_size != expected_size:
            issues.append(
                AssetIntegrityIssue(
                    relative,
                    "size mismatch",
                    str(expected_size),
                    str(candidate.stat().st_size),
                )
            )
    for relative in sorted(set(manifest) - referenced):
        issues.append(AssetIntegrityIssue(str(relative), "manifest entry is not referenced"))
    return tuple(issues)


def copy_asset_atomically(source: str | Path, destination: str | Path) -> Path:
    """Copy one managed asset without exposing a partially written file."""

    source_path = Path(source)
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source_path, temporary)
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return target
