"""Persistent object storage for Liegenschafts Mailer."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import CONF_BERTHS, DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN


def _normalize_objects(raw_objects: Any) -> list[dict[str, Any]]:
    """Validate and detach objects loaded from or written to storage."""
    if not isinstance(raw_objects, list):
        raise ValueError("The Liegenschafts Mailer storage field 'objects' must be a list")

    objects: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_object in enumerate(raw_objects):
        if not isinstance(raw_object, dict):
            raise ValueError(f"Object at index {index} must be a dictionary")
        item = deepcopy(raw_object)
        object_id = str(item.get("berth_id", "")).strip()
        if not object_id:
            raise ValueError(f"Object at index {index} has no berth_id")
        if object_id in seen_ids:
            raise ValueError(f"Duplicate berth_id in storage: {object_id}")
        item["berth_id"] = object_id
        seen_ids.add(object_id)
        objects.append(item)
    return objects


class LiegenschaftsMailerObjectStore:
    """Own the Home Assistant Store file .storage/liegenschafts_mailer."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._objects: list[dict[str, Any]] = []

    @property
    def objects(self) -> list[dict[str, Any]]:
        """Return a detached snapshot so callers cannot mutate the cache."""
        return deepcopy(self._objects)

    async def async_load(self, legacy_objects: Any) -> list[dict[str, Any]]:
        """Load the dedicated file or migrate legacy config-entry objects once."""
        stored = await self._store.async_load()
        if stored is None:
            self._objects = _normalize_objects(legacy_objects or [])
            await self._store.async_save({"objects": self._objects})
        else:
            if not isinstance(stored, dict):
                raise ValueError("Invalid Liegenschafts Mailer storage payload")
            self._objects = _normalize_objects(stored.get("objects", []))
        return self.objects

    async def async_save(self, objects: Any) -> None:
        """Validate and atomically persist a complete object snapshot."""
        normalized = _normalize_objects(objects)
        await self._store.async_save({"objects": normalized})
        self._objects = normalized


def get_objects(entry: ConfigEntry) -> list[dict[str, Any]]:
    """Return objects from the dedicated store, with a legacy fallback."""
    store = getattr(entry, "runtime_data", None)
    if isinstance(store, LiegenschaftsMailerObjectStore):
        return store.objects
    return _normalize_objects(deepcopy(dict(entry.options or {})).get(CONF_BERTHS, []))


async def async_save_objects(entry: ConfigEntry, objects: Any) -> None:
    """Persist objects through the initialized dedicated store."""
    store = getattr(entry, "runtime_data", None)
    if not isinstance(store, LiegenschaftsMailerObjectStore):
        raise RuntimeError("Liegenschafts Mailer object storage is not initialized")
    await store.async_save(objects)


async def async_initialize_object_store(
    hass: HomeAssistant, entry: ConfigEntry
) -> LiegenschaftsMailerObjectStore:
    """Initialize storage and remove migrated object data from config entries."""
    legacy_options = deepcopy(dict(entry.options or {}))
    store = LiegenschaftsMailerObjectStore(hass)
    await store.async_load(legacy_options.get(CONF_BERTHS, []))
    entry.runtime_data = store

    if CONF_BERTHS in legacy_options:
        legacy_options.pop(CONF_BERTHS, None)
        hass.config_entries.async_update_entry(entry, options=legacy_options)
    return store
