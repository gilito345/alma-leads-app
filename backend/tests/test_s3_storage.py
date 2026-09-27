import io
from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

from app.services.storage import ObjectNotFoundError, S3ObjectStorage


@pytest.fixture
def storage() -> Iterator[S3ObjectStorage]:
    with mock_aws():
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",  # noqa: S106
        )
        yield S3ObjectStorage(client, "resumes", "us-east-1")


def test_round_trip(storage: S3ObjectStorage) -> None:
    storage.ensure_bucket()
    storage.ensure_bucket()  # second call is a no-op

    storage.put("leads/1/a.pdf", io.BytesIO(b"%PDF-data"), content_type="application/pdf", size=9)
    assert b"".join(storage.stream("leads/1/a.pdf")) == b"%PDF-data"

    storage.delete("leads/1/a.pdf")
    with pytest.raises(ObjectNotFoundError):
        storage.stream("leads/1/a.pdf")


def test_missing_object_raises_before_iteration(storage: S3ObjectStorage) -> None:
    storage.ensure_bucket()
    with pytest.raises(ObjectNotFoundError):
        storage.stream("does/not/exist")
