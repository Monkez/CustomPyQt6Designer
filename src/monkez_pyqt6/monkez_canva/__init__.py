"""Public document/runtime foundation for the MonkezCanva editor."""

from .models import (
    DOCUMENT_FORMAT,
    DOCUMENT_VERSION,
    CanvasDocument,
    ConnectorModel,
    ElementModel,
    GroupModel,
    PortModel,
    ResourceModel,
    SceneModel,
)
from .operations import OperationEvent
from .persistence import (
    ASSET_MANIFEST_KEY,
    AssetIntegrityIssue,
    RecoveryLoadResult,
    atomic_write_json,
    backup_path,
    build_asset_manifest,
    load_json_with_recovery,
    sha256_file,
    verify_asset_manifest,
)
from .registry import (
    BUILTIN_ELEMENT_DEFINITIONS,
    ElementDefinition,
    ElementRegistry,
    create_default_element_registry,
)
from .schema import DOCUMENT_JSON_SCHEMA, DocumentMigrationResult, migrate_document

__all__ = [
    "DOCUMENT_FORMAT",
    "DOCUMENT_VERSION",
    "DOCUMENT_JSON_SCHEMA",
    "ASSET_MANIFEST_KEY",
    "AssetIntegrityIssue",
    "CanvasDocument",
    "BUILTIN_ELEMENT_DEFINITIONS",
    "ConnectorModel",
    "ElementModel",
    "ElementDefinition",
    "ElementRegistry",
    "GroupModel",
    "OperationEvent",
    "RecoveryLoadResult",
    "PortModel",
    "ResourceModel",
    "SceneModel",
    "create_default_element_registry",
    "atomic_write_json",
    "backup_path",
    "build_asset_manifest",
    "load_json_with_recovery",
    "migrate_document",
    "DocumentMigrationResult",
    "sha256_file",
    "verify_asset_manifest",
]
