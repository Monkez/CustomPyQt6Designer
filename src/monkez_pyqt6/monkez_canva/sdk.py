"""Public, Qt-free component-plugin SDK for MonkezCanva.

Applications explicitly import trusted plugin code and pass a
``ComponentPlugin`` to a canvas or registry. Documents never name or import
Python modules, preserving the safe document boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .registry import ElementDefinition, ElementRegistry


COMPONENT_SDK_VERSION = 1


def _plugin_id(value: str) -> str:
    result = str(value).strip().lower()
    if not result:
        raise ValueError("Component plugin ID cannot be empty")
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in result):
        raise ValueError(
            "Component plugin ID may contain only lowercase letters, digits, '.', '_' and '-'"
        )
    return result


@dataclass(frozen=True, slots=True)
class ComponentPlugin:
    """Validated manifest for one explicitly loaded component plugin.

    Renderer and Inspector callbacks remain on each :class:`ElementDefinition`.
    The manifest adds an atomic ownership/install boundary and metadata suitable
    for host plugin managers without importing Qt into the document layer.
    """

    plugin_id: str
    label: str
    version: str
    definitions: tuple[ElementDefinition, ...]
    description: str = ""
    minimum_sdk: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        plugin_id = _plugin_id(self.plugin_id)
        definitions = tuple(self.definitions)
        if not definitions:
            raise ValueError(f"Component plugin {plugin_id!r} must define at least one component")
        if int(self.minimum_sdk) < 1:
            raise ValueError("Component plugin minimum SDK must be >= 1")
        if int(self.minimum_sdk) > COMPONENT_SDK_VERSION:
            raise ValueError(
                f"Component plugin {plugin_id!r} requires SDK {self.minimum_sdk}; "
                f"runtime provides {COMPONENT_SDK_VERSION}"
            )
        mismatched = [
            definition.type_id
            for definition in definitions
            if definition.plugin_id != plugin_id
        ]
        if mismatched:
            raise ValueError(
                f"Component definitions must be owned by {plugin_id!r}: {mismatched}"
            )
        type_ids = [definition.type_id for definition in definitions]
        duplicates = sorted({type_id for type_id in type_ids if type_ids.count(type_id) > 1})
        if duplicates:
            raise ValueError(f"Duplicate component types in plugin {plugin_id!r}: {duplicates}")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("Component plugin metadata must be a mapping")
        object.__setattr__(self, "plugin_id", plugin_id)
        object.__setattr__(self, "label", str(self.label).strip() or plugin_id)
        object.__setattr__(self, "version", str(self.version).strip())
        object.__setattr__(self, "description", str(self.description).strip())
        object.__setattr__(self, "minimum_sdk", int(self.minimum_sdk))
        object.__setattr__(self, "definitions", definitions)
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType({str(key): value for key, value in self.metadata.items()}),
        )

    @property
    def type_ids(self) -> tuple[str, ...]:
        return tuple(definition.type_id for definition in self.definitions)


def component_plugin(
    plugin_id: str,
    label: str,
    version: str,
    definitions: Iterable[ElementDefinition],
    *,
    description: str = "",
    minimum_sdk: int = 1,
    metadata: Mapping[str, Any] | None = None,
) -> ComponentPlugin:
    """Construct a validated component-plugin manifest from any iterable."""

    return ComponentPlugin(
        plugin_id,
        label,
        version,
        tuple(definitions),
        description,
        minimum_sdk,
        {} if metadata is None else metadata,
    )


def install_component_plugin(
    registry: ElementRegistry,
    plugin: ComponentPlugin,
    *,
    replace_existing: bool = False,
) -> tuple[str, ...]:
    """Atomically install or upgrade a trusted plugin in one registry.

    Existing definitions owned by the same plugin and safe missing-component
    placeholders are replaceable. Another owner's type is rejected unless the
    host explicitly opts into ``replace_existing``.
    """

    if not isinstance(registry, ElementRegistry):
        raise TypeError("install_component_plugin expects an ElementRegistry")
    if not isinstance(plugin, ComponentPlugin):
        raise TypeError("install_component_plugin expects a ComponentPlugin")

    replacements: dict[str, bool] = {}
    conflicts: list[tuple[str, str]] = []
    for definition in plugin.definitions:
        existing = registry.definition(definition.type_id)
        replace = existing is not None
        replacements[definition.type_id] = replace
        if (
            existing is not None
            and existing.plugin_id not in (plugin.plugin_id, "__missing__")
            and not replace_existing
        ):
            conflicts.append((definition.type_id, existing.plugin_id))
    if conflicts:
        type_id, owner = conflicts[0]
        raise ValueError(
            f"Component plugin {plugin.plugin_id!r} conflicts with {type_id!r} "
            f"owned by {owner!r}"
        )

    # Validate the complete install against a clone before mutating the caller.
    preview = registry.clone()
    for definition in plugin.definitions:
        preview.register(definition, replace_existing=replacements[definition.type_id])
    for definition in plugin.definitions:
        registry.register(definition, replace_existing=replacements[definition.type_id])
    return plugin.type_ids


def uninstall_component_plugin(
    registry: ElementRegistry, plugin: ComponentPlugin | str
) -> tuple[str, ...]:
    """Unload one plugin's definitions without touching document records."""

    if not isinstance(registry, ElementRegistry):
        raise TypeError("uninstall_component_plugin expects an ElementRegistry")
    plugin_id = plugin.plugin_id if isinstance(plugin, ComponentPlugin) else _plugin_id(plugin)
    removed = registry.unregister_owner(plugin_id)
    if isinstance(plugin, ComponentPlugin):
        order = {type_id: index for index, type_id in enumerate(plugin.type_ids)}
        removed = tuple(
            sorted(removed, key=lambda definition: order.get(definition.type_id, len(order)))
        )
    return tuple(definition.type_id for definition in removed)
