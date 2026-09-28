import logging
from collections.abc import Iterator
from typing import BinaryIO
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.services.storage.base import ObjectNotFoundError
from app.services.supabase_auth import key_headers

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 64 * 1024
_ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]


class SupabaseObjectStorage:
    """Supabase Storage via its REST API, authenticated with the project's secret key.

    The bucket is private: only this backend (holding the secret key) can read or write it,
    and attorneys view or download resumes through the authenticated API.
    """

    def __init__(
        self,
        base_url: str,
        secret_key: str,
        bucket: str,
        *,
        max_file_bytes: int,
        client: httpx.Client | None = None,
    ) -> None:
        self._storage_url = f"{base_url.rstrip('/')}/storage/v1"
        self._headers = key_headers(secret_key)
        self._bucket = bucket
        self._max_file_bytes = max_file_bytes
        self._client = client or httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0))

    @classmethod
    def from_settings(cls, settings: Settings) -> "SupabaseObjectStorage":
        return cls(
            settings.supabase_api_url,
            settings.supabase_secret_key.get_secret_value(),
            settings.supabase_storage_bucket,
            max_file_bytes=settings.max_resume_bytes,
        )

    def _object_url(self, key: str) -> str:
        return f"{self._storage_url}/object/{self._bucket}/{quote(key)}"

    def ensure_bucket(self) -> None:
        response = self._client.get(
            f"{self._storage_url}/bucket/{self._bucket}", headers=self._headers
        )
        if response.is_success:
            return
        logger.info("Creating Supabase Storage bucket %s", self._bucket)
        created = self._client.post(
            f"{self._storage_url}/bucket",
            headers=self._headers,
            json={
                "id": self._bucket,
                "name": self._bucket,
                "public": False,
                "file_size_limit": self._max_file_bytes,
                "allowed_mime_types": _ALLOWED_MIME_TYPES,
            },
        )
        # 409/400 "already exists" can happen if another instance created it first.
        if not created.is_success and "already exists" not in created.text.lower():
            created.raise_for_status()

    def put(self, key: str, data: BinaryIO, *, content_type: str, size: int) -> None:
        response = self._client.post(
            self._object_url(key),
            headers={
                **self._headers,
                "Content-Type": content_type,
                "Content-Length": str(size),
                "x-upsert": "false",
                "cache-control": "no-store",
            },
            content=_chunks(data),
        )
        response.raise_for_status()

    def stream(self, key: str) -> Iterator[bytes]:
        request = self._client.build_request("GET", self._object_url(key), headers=self._headers)
        response = self._client.send(request, stream=True)
        if not response.is_success:
            body = response.read().decode(errors="replace").lower()
            response.close()
            # Storage reports a missing object as 400 or 404 with "not_found" in the body.
            if response.status_code == 404 or "not_found" in body or "not found" in body:
                raise ObjectNotFoundError(key)
            response.raise_for_status()

        def chunks() -> Iterator[bytes]:
            try:
                yield from response.iter_bytes(_CHUNK_SIZE)
            finally:
                response.close()

        return chunks()

    def delete(self, key: str) -> None:
        response = self._client.request(
            "DELETE",
            f"{self._storage_url}/object/{self._bucket}",
            headers=self._headers,
            json={"prefixes": [key]},
        )
        response.raise_for_status()


def _chunks(data: BinaryIO) -> Iterator[bytes]:
    while chunk := data.read(_CHUNK_SIZE):
        yield chunk
