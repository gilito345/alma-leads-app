from collections.abc import Iterator
from typing import BinaryIO

from app.services.storage.base import ObjectNotFoundError


class InMemoryObjectStorage:
    """Keeps objects in a dict. For tests and quick local experiments only."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def ensure_bucket(self) -> None:
        return None

    def put(self, key: str, data: BinaryIO, *, content_type: str, size: int) -> None:
        self.objects[key] = (data.read(), content_type)

    def stream(self, key: str) -> Iterator[bytes]:
        if key not in self.objects:
            raise ObjectNotFoundError(key)
        return iter([self.objects[key][0]])

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)
