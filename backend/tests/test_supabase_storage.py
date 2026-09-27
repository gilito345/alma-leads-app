import io
import json

import httpx
import pytest
import respx

from app.services.storage import ObjectNotFoundError, SupabaseObjectStorage

BASE = "http://supabase.test"
STORAGE = f"{BASE}/storage/v1"


@pytest.fixture
def storage() -> SupabaseObjectStorage:
    return SupabaseObjectStorage(BASE, "sb_secret_y", "resumes", max_file_bytes=10 * 1024 * 1024)


@respx.mock
def test_put_uploads_with_secret_key(storage: SupabaseObjectStorage) -> None:
    route = respx.post(f"{STORAGE}/object/resumes/leads/1/a.pdf").mock(
        return_value=httpx.Response(200, json={"Key": "resumes/leads/1/a.pdf"})
    )

    storage.put("leads/1/a.pdf", io.BytesIO(b"%PDF-data"), content_type="application/pdf", size=9)

    request = route.calls.last.request
    assert request.headers["apikey"] == "sb_secret_y"
    assert request.headers["content-type"] == "application/pdf"
    assert request.headers["x-upsert"] == "false"
    assert request.read() == b"%PDF-data"


@respx.mock
def test_stream_returns_content(storage: SupabaseObjectStorage) -> None:
    respx.get(f"{STORAGE}/object/resumes/leads/1/a.pdf").mock(
        return_value=httpx.Response(200, content=b"%PDF-data")
    )
    assert b"".join(storage.stream("leads/1/a.pdf")) == b"%PDF-data"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404, json={"error": "not_found"}),
        httpx.Response(400, json={"statusCode": "404", "error": "not_found", "message": "x"}),
    ],
)
@respx.mock
def test_missing_object(storage: SupabaseObjectStorage, response: httpx.Response) -> None:
    respx.get(f"{STORAGE}/object/resumes/missing.pdf").mock(return_value=response)
    with pytest.raises(ObjectNotFoundError):
        storage.stream("missing.pdf")


@respx.mock
def test_delete(storage: SupabaseObjectStorage) -> None:
    route = respx.delete(f"{STORAGE}/object/resumes").mock(
        return_value=httpx.Response(200, json=[])
    )
    storage.delete("leads/1/a.pdf")
    assert json.loads(route.calls.last.request.content) == {"prefixes": ["leads/1/a.pdf"]}


@respx.mock
def test_ensure_bucket_creates_private_bucket(storage: SupabaseObjectStorage) -> None:
    respx.get(f"{STORAGE}/bucket/resumes").mock(return_value=httpx.Response(404))
    create = respx.post(f"{STORAGE}/bucket").mock(return_value=httpx.Response(200, json={}))

    storage.ensure_bucket()

    body = json.loads(create.calls.last.request.content)
    assert body["id"] == "resumes"
    assert body["public"] is False


@respx.mock
def test_ensure_bucket_noop_when_present(storage: SupabaseObjectStorage) -> None:
    respx.get(f"{STORAGE}/bucket/resumes").mock(return_value=httpx.Response(200, json={}))
    create = respx.post(f"{STORAGE}/bucket")
    storage.ensure_bucket()
    assert not create.called
