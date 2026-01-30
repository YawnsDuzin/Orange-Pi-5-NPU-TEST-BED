"""
Configuration Persistence Service

Generic, reusable service for persisting runtime configurations to JSON files.
Supports any Pydantic models, automatic backups, and version management.
"""

import asyncio
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar, get_args

from pydantic import BaseModel, ValidationError

from app.config import DATA_DIR

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class PersistenceConfig(BaseModel):
    """Configuration for a persistence store."""
    name: str
    filename: str
    version: str = "1.0"
    max_backups: int = 5


class ConfigPersistence(Generic[T]):
    """
    Generic configuration persistence manager.

    Handles saving/loading configurations with:
    - Pydantic model validation
    - Automatic backups
    - Version management
    - Atomic writes
    - Thread-safe operations

    Example:
        camera_store = ConfigPersistence[CameraConfig](
            PersistenceConfig(name="cameras", filename="cameras.json")
        )
        await camera_store.save_all(camera_configs)
        configs = await camera_store.load_all(CameraConfig)
    """

    def __init__(self, config: PersistenceConfig, data_dir: Path = DATA_DIR):
        self.config = config
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.file_path = self.data_dir / config.filename
        self.backup_dir = self.data_dir / "backups" / config.name
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._lock = asyncio.Lock()

    async def save_all(self, items: list[T]) -> None:
        """
        Save list of Pydantic models to JSON file.

        Creates backup of existing file before overwriting.
        Uses atomic write to prevent corruption.
        """
        async with self._lock:
            try:
                # Create backup if file exists
                if self.file_path.exists():
                    await self._create_backup()

                # Serialize to JSON
                data = {
                    "version": self.config.version,
                    "timestamp": datetime.utcnow().isoformat(),
                    "count": len(items),
                    "items": [item.model_dump(mode='json') for item in items],
                }

                # Atomic write: write to temp file, then rename
                temp_path = self.file_path.with_suffix('.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                temp_path.replace(self.file_path)

                logger.info(
                    f"Saved {len(items)} {self.config.name} to {self.file_path}"
                )

            except Exception as e:
                logger.error(f"Failed to save {self.config.name}: {e}")
                raise

    async def load_all(self, model_class: type[T]) -> list[T]:
        """
        Load list of Pydantic models from JSON file.

        Validates each item against the model schema.
        Returns empty list if file doesn't exist or is invalid.
        """
        async with self._lock:
            if not self.file_path.exists():
                logger.info(f"No saved {self.config.name} found")
                return []

            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Version check (future: migration logic here)
                file_version = data.get("version", "1.0")
                if file_version != self.config.version:
                    logger.warning(
                        f"{self.config.name} version mismatch: "
                        f"file={file_version}, expected={self.config.version}"
                    )

                # Validate and deserialize
                items = []
                for item_data in data.get("items", []):
                    try:
                        items.append(model_class.model_validate(item_data))
                    except ValidationError as e:
                        logger.error(
                            f"Validation error for {self.config.name} item: {e}"
                        )
                        # Skip invalid items instead of failing entirely
                        continue

                logger.info(
                    f"Loaded {len(items)} {self.config.name} from {self.file_path}"
                )
                return items

            except Exception as e:
                logger.error(f"Failed to load {self.config.name}: {e}")
                # Try to restore from backup
                if await self._restore_from_backup():
                    return await self.load_all(model_class)
                return []

    async def save_one(self, item_id: str, item: T, id_field: str = "id") -> None:
        """
        Save or update a single item.

        Loads existing items, updates/adds the item, and saves back.
        """
        # Get model class from item
        model_class = type(item)

        items = await self.load_all(model_class)

        # Update existing or append new
        updated = False
        for i, existing in enumerate(items):
            if getattr(existing, id_field) == item_id:
                items[i] = item
                updated = True
                break

        if not updated:
            items.append(item)

        await self.save_all(items)

    async def delete_one(
        self, item_id: str, model_class: type[T], id_field: str = "id"
    ) -> bool:
        """Delete a single item by ID."""
        items = await self.load_all(model_class)
        original_count = len(items)

        items = [
            item for item in items if getattr(item, id_field) != item_id
        ]

        if len(items) < original_count:
            await self.save_all(items)
            return True
        return False

    async def clear_all(self) -> None:
        """Delete the configuration file."""
        async with self._lock:
            if self.file_path.exists():
                await self._create_backup()
                self.file_path.unlink()
                logger.info(f"Cleared {self.config.name}")

    async def _create_backup(self) -> None:
        """Create timestamped backup of current file."""
        if not self.file_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{self.config.filename}.{timestamp}"

        shutil.copy2(self.file_path, backup_path)
        logger.debug(f"Created backup: {backup_path}")

        # Cleanup old backups
        await self._cleanup_old_backups()

    async def _cleanup_old_backups(self) -> None:
        """Keep only the most recent N backups."""
        backups = sorted(
            self.backup_dir.glob(f"{self.config.filename}.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for old_backup in backups[self.config.max_backups :]:
            old_backup.unlink()
            logger.debug(f"Removed old backup: {old_backup}")

    async def _restore_from_backup(self) -> bool:
        """Restore from the most recent backup."""
        backups = sorted(
            self.backup_dir.glob(f"{self.config.filename}.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not backups:
            logger.error(f"No backups available for {self.config.name}")
            return False

        latest_backup = backups[0]
        shutil.copy2(latest_backup, self.file_path)
        logger.warning(
            f"Restored {self.config.name} from backup: {latest_backup}"
        )
        return True


class SimplePersistence:
    """
    Simple key-value persistence for non-model data.

    Use this for storing simple dictionaries or lists without Pydantic validation.
    """

    def __init__(self, filename: str, data_dir: Path = DATA_DIR):
        self.file_path = data_dir / filename
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def save(self, data: Any) -> None:
        """Save data to JSON file."""
        async with self._lock:
            try:
                temp_path = self.file_path.with_suffix('.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                temp_path.replace(self.file_path)
            except Exception as e:
                logger.error(f"Failed to save to {self.file_path}: {e}")
                raise

    async def load(self, default: Any = None) -> Any:
        """Load data from JSON file."""
        async with self._lock:
            if not self.file_path.exists():
                return default

            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load from {self.file_path}: {e}")
                return default
