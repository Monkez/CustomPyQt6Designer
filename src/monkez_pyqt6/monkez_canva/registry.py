"""Public component metadata registry for MonkezCanva."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class ElementDefinition:
    """Declarative metadata shared by documents, palettes and future plugins."""

    type_id: str
    label: str
    category: str
    default_width: float
    default_height: float
    icon: str = ""
    defaults: Mapping[str, Any] = field(default_factory=dict)
    media_picker: bool = False

    def __post_init__(self) -> None:
        type_id = str(self.type_id).strip().lower()
        if not type_id:
            raise ValueError("MonkezCanva element type ID cannot be empty")
        if float(self.default_width) <= 0 or float(self.default_height) <= 0:
            raise ValueError(f"Element {type_id!r} must have a positive default size")
        object.__setattr__(self, "type_id", type_id)
        object.__setattr__(self, "label", str(self.label).strip() or type_id.replace("_", " ").title())
        object.__setattr__(self, "category", str(self.category).strip() or "Custom")
        object.__setattr__(self, "icon", str(self.icon).strip() or type_id)
        object.__setattr__(self, "defaults", MappingProxyType(dict(self.defaults)))

    @property
    def default_size(self) -> tuple[float, float]:
        return float(self.default_width), float(self.default_height)


class ElementRegistry:
    """Ordered, cloneable registry with explicit duplicate handling."""

    def __init__(self, definitions: Iterable[ElementDefinition] = ()) -> None:
        self._definitions: dict[str, ElementDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: ElementDefinition, *, replace_existing: bool = False) -> None:
        if not isinstance(definition, ElementDefinition):
            raise TypeError("ElementRegistry.register expects an ElementDefinition")
        if definition.type_id in self._definitions and not replace_existing:
            raise ValueError(f"Duplicate MonkezCanva element type: {definition.type_id}")
        self._definitions[definition.type_id] = definition

    def unregister(self, type_id: str) -> ElementDefinition:
        key = str(type_id).strip().lower()
        try:
            return self._definitions.pop(key)
        except KeyError as error:
            raise KeyError(f"Unknown MonkezCanva element type: {key}") from error

    def definition(self, type_id: str) -> ElementDefinition | None:
        return self._definitions.get(str(type_id).strip().lower())

    def require(self, type_id: str) -> ElementDefinition:
        definition = self.definition(type_id)
        if definition is None:
            raise KeyError(f"Unknown MonkezCanva element type: {type_id}")
        return definition

    def definitions(self) -> tuple[ElementDefinition, ...]:
        return tuple(self._definitions.values())

    def categories(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.category for item in self._definitions.values()))

    def in_category(self, category: str) -> tuple[ElementDefinition, ...]:
        return tuple(item for item in self._definitions.values() if item.category == category)

    def clone(self) -> "ElementRegistry":
        return ElementRegistry(replace(item) for item in self._definitions.values())


BUILTIN_ELEMENT_DEFINITIONS = (
    ElementDefinition("text", "Text", "Shapes", 160, 48),
    ElementDefinition("rectangle", "Rectangle", "Shapes", 140, 80),
    ElementDefinition("ellipse", "Ellipse", "Shapes", 120, 80),
    ElementDefinition("button", "Button", "Shapes", 120, 42),
    ElementDefinition("diamond", "Diamond", "Shapes", 120, 100),
    ElementDefinition("triangle", "Triangle", "Shapes", 120, 100),
    ElementDefinition("node", "Node", "Diagram & data", 180, 96),
    ElementDefinition("splitter", "Splitter", "Diagram & data", 72, 72),
    ElementDefinition("line", "Line / arrow", "Diagram & data", 220, 40),
    ElementDefinition("bar_chart", "Bar chart", "Diagram & data", 260, 160),
    ElementDefinition("line_chart", "Line chart", "Diagram & data", 260, 160),
    ElementDefinition("image", "Image", "Media", 280, 180, media_picker=True),
    ElementDefinition("animated_image", "Animated GIF", "Media", 280, 180, icon="gif", media_picker=True),
)


def create_default_element_registry() -> ElementRegistry:
    return ElementRegistry(BUILTIN_ELEMENT_DEFINITIONS)

