import io

import pytest

from app.services.storage import LocalFileStorage, ObjectNotFoundError


def test_round_trip(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path / "resumes")
    storage.ensure_bucket()

    storage.put("leads/1/a.pdf", io.BytesIO(b"%PDF-data"), content_type="application/pdf", size=9)
    assert b"".join(storage.stream("leads/1/a.pdf")) == b"%PDF-data"
    assert not list((tmp_path / "resumes" / "leads" / "1").glob(".*.tmp"))

    storage.delete("leads/1/a.pdf")
    storage.delete("leads/1/a.pdf")  # deleting twice is fine
    with pytest.raises(ObjectNotFoundError):
        storage.stream("leads/1/a.pdf")


def test_rejects_keys_outside_root(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path / "resumes")
    with pytest.raises(ValueError, match="Invalid object key"):
        storage.put("../escape.pdf", io.BytesIO(b"x"), content_type="application/pdf", size=1)
