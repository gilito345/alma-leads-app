from app.core.config import Settings
from app.services.storage.base import ObjectNotFoundError, ObjectStorage
from app.services.storage.local import LocalFileStorage
from app.services.storage.memory import InMemoryObjectStorage
from app.services.storage.s3 import S3ObjectStorage


def build_storage(settings: Settings) -> ObjectStorage:
    if settings.storage_backend == "s3":
        return S3ObjectStorage.from_settings(settings)
    return LocalFileStorage(settings.local_storage_dir)


__all__ = [
    "InMemoryObjectStorage",
    "LocalFileStorage",
    "ObjectNotFoundError",
    "ObjectStorage",
    "S3ObjectStorage",
    "build_storage",
]
