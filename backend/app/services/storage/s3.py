import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.services.storage.base import ObjectNotFoundError

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 64 * 1024


class S3ObjectStorage:
    """S3 or any S3-compatible service (R2, MinIO, ...). Used in production."""

    def __init__(self, client: "S3Client", bucket: str, region: str) -> None:
        self._client = client
        self._bucket = bucket
        self._region = region

    @classmethod
    def from_settings(cls, settings: Settings) -> "S3ObjectStorage":
        secret = settings.s3_secret_access_key
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=secret.get_secret_value() if secret else None,
            region_name=settings.s3_region,
            # Path-style addressing works with S3-compatible services and with AWS.
            config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
        )
        return cls(client, settings.s3_bucket, settings.s3_region)

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
            return
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in ("404", "NoSuchBucket"):
                raise
        logger.info("Creating bucket %s", self._bucket)
        if self._region == "us-east-1":
            self._client.create_bucket(Bucket=self._bucket)
        else:
            # The stubs type LocationConstraint as a Literal of known regions.
            location: Any = {"LocationConstraint": self._region}
            self._client.create_bucket(Bucket=self._bucket, CreateBucketConfiguration=location)

    def put(self, key: str, data: BinaryIO, *, content_type: str, size: int) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ContentLength=size,
        )

    def stream(self, key: str) -> Iterator[bytes]:
        # Fetch eagerly (not inside the generator) so a missing object raises here, before
        # the caller has started sending a response.
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                raise ObjectNotFoundError(key) from exc
            raise
        body = obj["Body"]

        def chunks() -> Iterator[bytes]:
            try:
                yield from body.iter_chunks(_CHUNK_SIZE)
            finally:
                body.close()

        return chunks()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
