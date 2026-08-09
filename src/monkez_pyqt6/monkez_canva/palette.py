"""Qt-free search and preference helpers for the MonkezCanva component palette."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


PALETTE_FAVORITES_KEY = "paletteFavorites"
PALETTE_RECENT_KEY = "paletteRecent"
MAX_RECENT_COMPONENTS = 12


@dataclass(frozen=True, slots=True)
class PaletteEntry:
    type_id: str
    label: str
    category: str
    icon: str = ""
    keywords: tuple[str, ...] = ()

    @property
    def searchable_text(self) -> str:
        return " ".join(
            (self.label, self.type_id.replace("_", " "), self.category, *self.keywords)
        ).casefold()


def normalize_component_ids(
    values: Iterable[object], *, limit: int | None = None
) -> tuple[str, ...]:
    """Normalize ordered component IDs while removing blanks and duplicates."""

    result: list[str] = []
    for value in values:
        type_id = str(value).strip().lower()
        if type_id and type_id not in result:
            result.append(type_id)
        if limit is not None and len(result) >= max(0, int(limit)):
            break
    return tuple(result)


def record_recent_component(
    current: Iterable[object], type_id: str, *, limit: int = MAX_RECENT_COMPONENTS
) -> tuple[str, ...]:
    normalized = str(type_id).strip().lower()
    return normalize_component_ids((normalized, *current), limit=limit)


def search_palette(
    entries: Iterable[PaletteEntry],
    query: str = "",
    *,
    category: str = "",
    favorites: Iterable[object] = (),
    recent: Iterable[object] = (),
) -> tuple[PaletteEntry, ...]:
    """Rank registry entries deterministically for category/search palette views."""

    source = tuple(entries)
    favorite_ids = normalize_component_ids(favorites)
    recent_ids = normalize_component_ids(recent)
    favorite_set = set(favorite_ids)
    recent_set = set(recent_ids)
    category_key = str(category).strip().casefold()
    words = tuple(word for word in str(query).casefold().split() if word)
    ranked: list[tuple[tuple[int, ...], int, PaletteEntry]] = []
    for index, entry in enumerate(source):
        if category_key == "favorites" and entry.type_id not in favorite_set:
            continue
        if category_key == "recent" and entry.type_id not in recent_set:
            continue
        if (
            category_key not in ("", "all", "favorites", "recent")
            and entry.category.casefold() != category_key
        ):
            continue
        text = entry.searchable_text
        if any(word not in text for word in words):
            continue
        label = entry.label.casefold()
        type_id = entry.type_id.casefold()
        query_key = " ".join(words)
        match_rank = (
            0 if query_key and query_key in (label, type_id)
            else 1 if query_key and (label.startswith(query_key) or type_id.startswith(query_key))
            else 2 if words
            else 3
        )
        if category_key == "recent":
            preference_rank = recent_ids.index(entry.type_id)
        elif category_key == "favorites":
            preference_rank = favorite_ids.index(entry.type_id)
        else:
            preference_rank = 0 if entry.type_id in favorite_set else 1
        ranked.append(((match_rank, preference_rank), index, entry))
    ranked.sort(key=lambda item: (*item[0], item[1]))
    return tuple(item[2] for item in ranked)
