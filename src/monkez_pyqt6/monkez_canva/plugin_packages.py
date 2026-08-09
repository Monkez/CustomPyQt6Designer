"""Safe discovery and explicit-trust loading for project-local component plugins.

Discovery never imports Python. A host must trust the exact package SHA-256
fingerprint before :func:`load_trusted_plugin_package` executes its entry file.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .sdk import COMPONENT_SDK_VERSION, ComponentPlugin


PLUGIN_PACKAGE_FORMAT = "monkez-canva-plugin"
PLUGIN_PACKAGE_VERSION = 1
PLUGIN_MANIFEST_NAME = "plugin.json"
MAX_PLUGIN_MANIFEST_BYTES = 128 * 1024
MAX_PLUGIN_PACKAGE_BYTES = 10 * 1024 * 1024
MAX_PLUGIN_PACKAGE_FILES = 256
MAX_PLUGIN_PACKAGES = 128
PLUGIN_PACKAGE_STATES = ("invalid", "untrusted", "trusted", "loaded")


def normalize_plugin_id(value: str) -> str:
    result = str(value).strip().lower()
    if not result:
        raise ValueError("Component plugin ID cannot be empty")
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in result):
        raise ValueError(
            "Component plugin ID may contain only lowercase letters, digits, '.', '_' and '-'"
        )
    return result


def _safe_relative_file(value: str, *, suffix: str = "") -> str:
    text = str(value).strip().replace("\\", "/")
    path = Path(text)
    if (
        not text
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
        or suffix and path.suffix.lower() != suffix
    ):
        raise ValueError(f"Unsafe plugin package file path: {value!r}")
    return path.as_posix()


def _json_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    try:
        detached = json.loads(
            json.dumps(dict(value or {}), ensure_ascii=False, allow_nan=False)
        )
    except (TypeError, ValueError) as error:
        raise TypeError("Plugin package metadata must be finite JSON data") from error
    return MappingProxyType(detached)


@dataclass(frozen=True, slots=True)
class PluginPackageManifest:
    plugin_id: str
    label: str
    plugin_version: str
    entry_file: str = "plugin.py"
    entry_symbol: str = "PLUGIN"
    description: str = ""
    author: str = ""
    homepage: str = ""
    minimum_sdk: int = 1
    component_types: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        plugin_id = normalize_plugin_id(self.plugin_id)
        minimum_sdk = int(self.minimum_sdk)
        if minimum_sdk < 1:
            raise ValueError("Plugin package minimum SDK must be >= 1")
        entry_symbol = str(self.entry_symbol).strip()
        if not entry_symbol.isidentifier():
            raise ValueError("Plugin package entry symbol must be a Python identifier")
        component_types = tuple(
            dict.fromkeys(str(value).strip().lower() for value in self.component_types)
        )
        if any(not value for value in component_types):
            raise ValueError("Plugin package component type cannot be empty")
        object.__setattr__(self, "plugin_id", plugin_id)
        object.__setattr__(self, "label", str(self.label).strip() or plugin_id)
        object.__setattr__(self, "plugin_version", str(self.plugin_version).strip())
        object.__setattr__(self, "entry_file", _safe_relative_file(self.entry_file, suffix=".py"))
        object.__setattr__(self, "entry_symbol", entry_symbol)
        object.__setattr__(self, "description", str(self.description).strip())
        object.__setattr__(self, "author", str(self.author).strip())
        object.__setattr__(self, "homepage", str(self.homepage).strip())
        object.__setattr__(self, "minimum_sdk", minimum_sdk)
        object.__setattr__(self, "component_types", component_types)
        object.__setattr__(self, "metadata", _json_mapping(self.metadata))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PluginPackageManifest":
        if str(payload.get("format", "")) != PLUGIN_PACKAGE_FORMAT:
            raise ValueError("Unsupported MonkezCanva plugin package format")
        version = int(payload.get("version", 0))
        if version != PLUGIN_PACKAGE_VERSION:
            raise ValueError(f"Unsupported plugin package manifest version: {version}")
        entry = payload.get("entryPoint", {})
        if not isinstance(entry, Mapping):
            raise TypeError("Plugin package entryPoint must be an object")
        component_types = payload.get("componentTypes", ())
        if not isinstance(component_types, (list, tuple)):
            raise TypeError("Plugin package componentTypes must be an array")
        return cls(
            str(payload.get("pluginId", "")),
            str(payload.get("label", "")),
            str(payload.get("pluginVersion", "")),
            str(entry.get("file", "plugin.py")),
            str(entry.get("symbol", "PLUGIN")),
            str(payload.get("description", "")),
            str(payload.get("author", "")),
            str(payload.get("homepage", "")),
            int(payload.get("minimumSdk", 1)),
            tuple(str(value) for value in component_types),
            payload.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": PLUGIN_PACKAGE_FORMAT,
            "version": PLUGIN_PACKAGE_VERSION,
            "pluginId": self.plugin_id,
            "label": self.label,
            "pluginVersion": self.plugin_version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "minimumSdk": self.minimum_sdk,
            "entryPoint": {"file": self.entry_file, "symbol": self.entry_symbol},
            "componentTypes": list(self.component_types),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class PluginPackageCandidate:
    package_dir: Path
    manifest: PluginPackageManifest | None
    fingerprint: str = ""
    state: str = "invalid"
    errors: tuple[str, ...] = ()
    file_count: int = 0
    total_bytes: int = 0

    @property
    def plugin_id(self) -> str:
        return self.manifest.plugin_id if self.manifest is not None else self.package_dir.name

    @property
    def loadable(self) -> bool:
        return self.manifest is not None and not self.errors and self.state in ("trusted", "loaded")

    def to_dict(self) -> dict[str, Any]:
        return {
            "pluginId": self.plugin_id,
            "label": self.manifest.label if self.manifest is not None else self.package_dir.name,
            "pluginVersion": self.manifest.plugin_version if self.manifest is not None else "",
            "description": self.manifest.description if self.manifest is not None else "",
            "author": self.manifest.author if self.manifest is not None else "",
            "homepage": self.manifest.homepage if self.manifest is not None else "",
            "minimumSdk": self.manifest.minimum_sdk if self.manifest is not None else 0,
            "componentTypes": list(self.manifest.component_types) if self.manifest is not None else [],
            "packageDirectory": str(self.package_dir),
            "fingerprint": self.fingerprint,
            "state": self.state,
            "loadable": self.loadable,
            "errors": list(self.errors),
            "fileCount": self.file_count,
            "totalBytes": self.total_bytes,
        }


@dataclass(frozen=True, slots=True)
class PluginDiscoveryReport:
    directory: Path
    candidates: tuple[PluginPackageCandidate, ...]
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "directory": str(self.directory),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "errors": list(self.errors),
        }


class PluginTrustStore:
    """In-memory exact-fingerprint trust decisions owned by the host session."""

    def __init__(self, records: Mapping[str, str] | None = None) -> None:
        self._records: dict[str, str] = {}
        for plugin_id, fingerprint in dict(records or {}).items():
            self.trust(plugin_id, fingerprint)

    def trust(self, plugin: PluginPackageCandidate | str, fingerprint: str = "") -> str:
        if isinstance(plugin, PluginPackageCandidate):
            plugin_id = normalize_plugin_id(plugin.plugin_id)
            value = plugin.fingerprint
            if plugin.errors or not value:
                raise ValueError(f"Cannot trust invalid plugin package {plugin_id!r}")
        else:
            plugin_id = normalize_plugin_id(plugin)
            value = str(fingerprint).strip().lower()
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("Plugin trust requires an exact SHA-256 fingerprint")
        self._records[plugin_id] = value
        return value

    def revoke(self, plugin_id: str) -> bool:
        return self._records.pop(normalize_plugin_id(plugin_id), None) is not None

    def is_trusted(self, plugin: PluginPackageCandidate | str, fingerprint: str = "") -> bool:
        if isinstance(plugin, PluginPackageCandidate):
            plugin_id, value = plugin.plugin_id, plugin.fingerprint
        else:
            plugin_id, value = normalize_plugin_id(plugin), str(fingerprint).strip().lower()
        return bool(value) and self._records.get(plugin_id) == value

    def records(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self._records))


def _package_files(package_dir: Path) -> tuple[tuple[Path, ...], int]:
    files: list[Path] = []
    total_bytes = 0
    for candidate in sorted(package_dir.rglob("*"), key=lambda path: path.as_posix().casefold()):
        if candidate.is_symlink():
            raise ValueError(f"Plugin package cannot contain symbolic links: {candidate.name}")
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(package_dir)
        if "__pycache__" in relative.parts or candidate.suffix.lower() in (".pyc", ".pyo"):
            # CPython may create these after an explicitly trusted load. They are
            # derived caches, never entry points, and must not invalidate source trust.
            continue
        files.append(candidate)
        if len(files) > MAX_PLUGIN_PACKAGE_FILES:
            raise ValueError(f"Plugin package exceeds {MAX_PLUGIN_PACKAGE_FILES} files")
        total_bytes += candidate.stat().st_size
        if total_bytes > MAX_PLUGIN_PACKAGE_BYTES:
            raise ValueError(f"Plugin package exceeds {MAX_PLUGIN_PACKAGE_BYTES} bytes")
    return tuple(files), total_bytes


def _fingerprint(package_dir: Path, files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(package_dir).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _scan_package(package_dir: Path, trust_store: PluginTrustStore) -> PluginPackageCandidate:
    errors: list[str] = []
    manifest: PluginPackageManifest | None = None
    files: tuple[Path, ...] = ()
    total_bytes = 0
    fingerprint = ""
    try:
        if package_dir.is_symlink():
            raise ValueError("Plugin package directory cannot be a symbolic link")
        files, total_bytes = _package_files(package_dir)
        manifest_path = package_dir / PLUGIN_MANIFEST_NAME
        if not manifest_path.is_file():
            raise ValueError(f"Plugin package has no {PLUGIN_MANIFEST_NAME}")
        if manifest_path.stat().st_size > MAX_PLUGIN_MANIFEST_BYTES:
            raise ValueError("Plugin package manifest is too large")
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise TypeError("Plugin package manifest root must be an object")
        manifest = PluginPackageManifest.from_dict(payload)
        entry = (package_dir / manifest.entry_file).resolve()
        entry.relative_to(package_dir.resolve())
        if not entry.is_file() or entry.is_symlink():
            raise ValueError(f"Plugin entry file is missing or unsafe: {manifest.entry_file}")
        fingerprint = _fingerprint(package_dir, files)
        if manifest.minimum_sdk > COMPONENT_SDK_VERSION:
            raise ValueError(
                f"Plugin package requires SDK {manifest.minimum_sdk}; "
                f"runtime provides {COMPONENT_SDK_VERSION}"
            )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        errors.append(f"{type(error).__name__}: {error}")
    state = "invalid" if errors else "trusted" if trust_store.is_trusted(
        manifest.plugin_id, fingerprint
    ) else "untrusted"
    return PluginPackageCandidate(
        package_dir, manifest, fingerprint, state, tuple(errors), len(files), total_bytes
    )


def discover_plugin_packages(
    directory: str | Path,
    *,
    trust_store: PluginTrustStore | None = None,
) -> PluginDiscoveryReport:
    """Read and fingerprint project plugin packages without importing code."""

    root = Path(directory).expanduser().resolve()
    store = trust_store or PluginTrustStore()
    if not root.exists():
        return PluginDiscoveryReport(root, ())
    if not root.is_dir():
        return PluginDiscoveryReport(root, (), ("Plugin discovery path is not a directory",))
    children = sorted(
        (path for path in root.iterdir() if path.is_dir() or path.is_symlink()),
        key=lambda path: path.name.casefold(),
    )
    errors: list[str] = []
    if len(children) > MAX_PLUGIN_PACKAGES:
        errors.append(f"Only the first {MAX_PLUGIN_PACKAGES} plugin packages were scanned")
        children = children[:MAX_PLUGIN_PACKAGES]
    candidates = tuple(_scan_package(path, store) for path in children)
    seen: set[str] = set()
    normalized: list[PluginPackageCandidate] = []
    for candidate in candidates:
        if candidate.manifest is not None and candidate.plugin_id in seen:
            normalized.append(
                PluginPackageCandidate(
                    candidate.package_dir,
                    candidate.manifest,
                    candidate.fingerprint,
                    "invalid",
                    (*candidate.errors, f"Duplicate discovered plugin ID: {candidate.plugin_id}"),
                    candidate.file_count,
                    candidate.total_bytes,
                )
            )
        else:
            normalized.append(candidate)
            if candidate.manifest is not None:
                seen.add(candidate.plugin_id)
    return PluginDiscoveryReport(root, tuple(normalized), tuple(errors))


@dataclass(frozen=True, slots=True)
class LoadedPluginPackage:
    candidate: PluginPackageCandidate
    plugin: ComponentPlugin
    module_name: str


def load_trusted_plugin_package(
    candidate: PluginPackageCandidate,
    trust_store: PluginTrustStore,
) -> LoadedPluginPackage:
    """Re-scan and execute one package only when its exact fingerprint is trusted."""

    if not isinstance(candidate, PluginPackageCandidate):
        raise TypeError("load_trusted_plugin_package expects a PluginPackageCandidate")
    if not isinstance(trust_store, PluginTrustStore):
        raise TypeError("load_trusted_plugin_package expects a PluginTrustStore")
    current = _scan_package(candidate.package_dir.resolve(), trust_store)
    if current.errors or current.manifest is None:
        raise ValueError(f"Invalid plugin package {candidate.plugin_id!r}: {'; '.join(current.errors)}")
    if current.fingerprint != candidate.fingerprint:
        raise PermissionError(f"Plugin package {candidate.plugin_id!r} changed after discovery")
    if not trust_store.is_trusted(current):
        raise PermissionError(
            f"Plugin package {current.plugin_id!r} is not trusted for fingerprint {current.fingerprint}"
        )
    if current.manifest.minimum_sdk > COMPONENT_SDK_VERSION:
        raise ValueError(
            f"Plugin package {current.plugin_id!r} requires SDK {current.manifest.minimum_sdk}; "
            f"runtime provides {COMPONENT_SDK_VERSION}"
        )
    entry = current.package_dir / current.manifest.entry_file
    module_name = f"_monkez_canvas_plugin_{current.fingerprint[:20]}"
    spec = importlib.util.spec_from_file_location(module_name, entry)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create loader for plugin package {current.plugin_id!r}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        plugin = getattr(module, current.manifest.entry_symbol)
        if not isinstance(plugin, ComponentPlugin):
            raise TypeError(
                f"Plugin entry {current.manifest.entry_symbol!r} must be a ComponentPlugin"
            )
        if plugin.plugin_id != current.manifest.plugin_id:
            raise ValueError("Loaded plugin ID does not match package manifest")
        if plugin.version != current.manifest.plugin_version:
            raise ValueError("Loaded plugin version does not match package manifest")
        if current.manifest.component_types and plugin.type_ids != current.manifest.component_types:
            raise ValueError("Loaded component types do not match package manifest")
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    loaded_candidate = PluginPackageCandidate(
        current.package_dir,
        current.manifest,
        current.fingerprint,
        "loaded",
        (),
        current.file_count,
        current.total_bytes,
    )
    return LoadedPluginPackage(loaded_candidate, plugin, module_name)


def unload_plugin_package(package: LoadedPluginPackage) -> None:
    """Release the dynamically loaded module after registry callbacks are removed."""

    if not isinstance(package, LoadedPluginPackage):
        raise TypeError("unload_plugin_package expects a LoadedPluginPackage")
    sys.modules.pop(package.module_name, None)
