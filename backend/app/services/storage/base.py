from collections.abc import Iterator
from typing import BinaryIO, Protocol


class ObjectNotFoundError(Exception):
    pass


class ObjectStorage(Protocol):
    """Where resume files live. Implementations: S3, local files, and in-memory for tests."""

    def ensure_bucket(self) -> None: ...

    def put(self, key: str, data: BinaryIO, *, content_type: str, size: int) -> None: ...

    def stream(self, key: str) -> Iterator[bytes]:
        """Yield the object's bytes in chunks. Raises ObjectNotFoundError."""
        ...

    def delete(self, key: str) -> None: ...
