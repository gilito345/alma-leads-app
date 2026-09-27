import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmailKind, EmailOutbox, EmailStatus, Lead, LeadState, User
from app.services.storage import InMemoryObjectStorage
from tests.helpers import PDF_BYTES, lead_form, resume_file

DOCX_BYTES = b"PK\x03\x04" + b"\x00" * 64


def submit(client: TestClient, **overrides: str):
    return client.post("/api/v1/leads", data=lead_form(**overrides), files=resume_file())


class TestCreateLead:
    def test_creates_pending_lead_and_stores_resume(
        self, client: TestClient, db: Session, storage: InMemoryObjectStorage
    ) -> None:
        response = submit(client, email="Ada@Example.com")

        assert response.status_code == 201, response.text
        body = response.json()
        assert set(body) == {"id", "created_at"}

        lead = db.get(Lead, uuid.UUID(body["id"]))
        assert lead is not None
        assert lead.state is LeadState.PENDING
        assert lead.email == "ada@example.com"
        assert lead.resume_filename == "resume.pdf"
        assert lead.resume_content_type == "application/pdf"
        assert lead.resume_size_bytes == len(PDF_BYTES)
        assert lead.resume_object_key.startswith(f"leads/{lead.id}/")
        assert storage.objects[lead.resume_object_key][0] == PDF_BYTES

    def test_queues_prospect_and_attorney_emails(self, client: TestClient, db: Session) -> None:
        lead_id = uuid.UUID(submit(client).json()["id"])

        rows = db.scalars(select(EmailOutbox).where(EmailOutbox.lead_id == lead_id)).all()
        by_kind = {row.kind: row for row in rows}
        assert set(by_kind) == {EmailKind.PROSPECT_CONFIRMATION, EmailKind.ATTORNEY_NOTIFICATION}
        assert by_kind[EmailKind.PROSPECT_CONFIRMATION].recipient == "ada@example.com"
        assert by_kind[EmailKind.ATTORNEY_NOTIFICATION].recipient == "intake@firm.test"
        assert all(row.status is EmailStatus.PENDING for row in rows)

    def test_accepts_docx(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/leads",
            data=lead_form(),
            files=resume_file(DOCX_BYTES, "cv.docx", "application/octet-stream"),
        )
        assert response.status_code == 201, response.text

    def test_trims_names(self, client: TestClient, db: Session) -> None:
        lead_id = submit(client, first_name="  Ada ", last_name=" Lovelace  ").json()["id"]
        lead = db.get(Lead, uuid.UUID(lead_id))
        assert lead is not None
        assert (lead.first_name, lead.last_name) == ("Ada", "Lovelace")

    def test_rejects_invalid_email(self, client: TestClient) -> None:
        response = submit(client, email="not-an-email")
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert error["details"][0]["field"] == "email"

    def test_rejects_blank_name(self, client: TestClient) -> None:
        response = submit(client, first_name="   ")
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["field"] == "first_name"

    def test_rejects_missing_resume(self, client: TestClient) -> None:
        response = client.post("/api/v1/leads", data=lead_form())
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["field"] == "resume"

    def test_rejects_unsupported_extension(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/leads", data=lead_form(), files=resume_file(PDF_BYTES, "resume.exe")
        )
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["field"] == "resume"

    def test_rejects_content_that_does_not_match_extension(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/leads", data=lead_form(), files=resume_file(b"MZ\x90\x00 not a pdf")
        )
        assert response.status_code == 422

    def test_rejects_empty_file(self, client: TestClient) -> None:
        response = client.post("/api/v1/leads", data=lead_form(), files=resume_file(b""))
        assert response.status_code == 422

    def test_rejects_body_over_size_limit(self, client: TestClient, settings, db: Session) -> None:
        too_big = PDF_BYTES + b"0" * (settings.max_request_body_bytes + 1)
        response = client.post("/api/v1/leads", data=lead_form(), files=resume_file(too_big))
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "payload_too_large"
        assert db.scalar(select(Lead)) is None

    def test_rejects_resume_over_file_limit(self, client: TestClient, settings) -> None:
        # Under the request cap but over the per-file cap.
        big = PDF_BYTES + b"0" * (settings.max_resume_bytes + 1 - len(PDF_BYTES))
        response = client.post("/api/v1/leads", data=lead_form(), files=resume_file(big))
        assert response.status_code == 422

    def test_honeypot_submission_is_dropped_silently(
        self, client: TestClient, db: Session, storage: InMemoryObjectStorage
    ) -> None:
        response = client.post(
            "/api/v1/leads", data=lead_form(website="http://spam.test"), files=resume_file()
        )
        assert response.status_code == 201
        assert db.scalar(select(Lead)) is None
        assert storage.objects == {}

    def test_removes_uploaded_file_when_database_write_fails(
        self, app, storage: InMemoryObjectStorage, monkeypatch
    ) -> None:
        def fail(*_args, **_kwargs):
            raise RuntimeError("database is down")

        monkeypatch.setattr("app.repositories.leads.LeadRepository.add", fail)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = submit(client)
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "internal_error"
        assert storage.objects == {}


class TestListLeads:
    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/api/v1/leads")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "not_authenticated"

    def test_rejects_bad_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/leads", headers={"Authorization": "Bearer nope"})
        assert response.status_code == 401

    def test_lists_newest_first_with_all_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        first = submit(client, first_name="First").json()["id"]
        second = submit(client, first_name="Second").json()["id"]

        response = client.get("/api/v1/leads", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert [item["id"] for item in body["items"]] == [second, first]
        item = body["items"][0]
        assert item["first_name"] == "Second"
        assert item["last_name"] == "Lovelace"
        assert item["email"] == "ada@example.com"
        assert item["state"] == "PENDING"
        assert item["resume"] == {
            "filename": "resume.pdf",
            "content_type": "application/pdf",
            "size_bytes": len(PDF_BYTES),
        }
        assert item["reached_out_at"] is None
        assert item["reached_out_by"] is None

    def test_filters_by_state_and_paginates(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        ids = [submit(client, first_name=f"Lead{i}").json()["id"] for i in range(3)]
        client.patch(f"/api/v1/leads/{ids[0]}", json={"state": "REACHED_OUT"}, headers=auth_headers)

        pending = client.get("/api/v1/leads?state=PENDING", headers=auth_headers).json()
        assert pending["total"] == 2
        reached = client.get("/api/v1/leads?state=REACHED_OUT", headers=auth_headers).json()
        assert [item["id"] for item in reached["items"]] == [ids[0]]

        page = client.get("/api/v1/leads?page=2&page_size=2", headers=auth_headers).json()
        assert page["total"] == 3
        assert len(page["items"]) == 1
        assert page["page"] == 2

    def test_rejects_invalid_page_size(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        assert client.get("/api/v1/leads?page_size=500", headers=auth_headers).status_code == 422


class TestGetLead:
    def test_returns_lead(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        lead_id = submit(client).json()["id"]
        response = client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == lead_id

    def test_unknown_lead_is_404(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        response = client.get(f"/api/v1/leads/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestUpdateLeadState:
    def test_marks_reached_out_and_records_who(
        self, client: TestClient, auth_headers: dict[str, str], attorney: User
    ) -> None:
        lead_id = submit(client).json()["id"]

        response = client.patch(
            f"/api/v1/leads/{lead_id}", json={"state": "REACHED_OUT"}, headers=auth_headers
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["state"] == "REACHED_OUT"
        assert body["reached_out_at"] is not None
        assert body["reached_out_by"] == {
            "id": str(attorney.id),
            "full_name": "Jane Attorney",
            "email": "jane@firm.test",
        }

    def test_is_idempotent(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        lead_id = submit(client).json()["id"]
        first = client.patch(
            f"/api/v1/leads/{lead_id}", json={"state": "REACHED_OUT"}, headers=auth_headers
        ).json()
        second = client.patch(
            f"/api/v1/leads/{lead_id}", json={"state": "REACHED_OUT"}, headers=auth_headers
        )
        assert second.status_code == 200
        assert second.json()["reached_out_at"] == first["reached_out_at"]

    def test_cannot_move_back_to_pending(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        lead_id = submit(client).json()["id"]
        client.patch(
            f"/api/v1/leads/{lead_id}", json={"state": "REACHED_OUT"}, headers=auth_headers
        )

        response = client.patch(
            f"/api/v1/leads/{lead_id}", json={"state": "PENDING"}, headers=auth_headers
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "invalid_state_transition"

    def test_rejects_unknown_state(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        lead_id = submit(client).json()["id"]
        response = client.patch(
            f"/api/v1/leads/{lead_id}", json={"state": "ARCHIVED"}, headers=auth_headers
        )
        assert response.status_code == 422

    def test_requires_authentication(self, client: TestClient) -> None:
        lead_id = submit(client).json()["id"]
        response = client.patch(f"/api/v1/leads/{lead_id}", json={"state": "REACHED_OUT"})
        assert response.status_code == 401


class TestDownloadResume:
    def test_streams_file_as_attachment(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        lead_id = client.post(
            "/api/v1/leads", data=lead_form(), files=resume_file(filename="Ada Résumé.pdf")
        ).json()["id"]

        response = client.get(f"/api/v1/leads/{lead_id}/resume", headers=auth_headers)

        assert response.status_code == 200
        assert response.content == PDF_BYTES
        assert response.headers["content-type"] == "application/pdf"
        disposition = response.headers["content-disposition"]
        assert disposition.startswith("attachment;")
        assert "filename*=UTF-8''Ada%20R%C3%A9sum%C3%A9.pdf" in disposition
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_requires_authentication(self, client: TestClient) -> None:
        lead_id = submit(client).json()["id"]
        assert client.get(f"/api/v1/leads/{lead_id}/resume").status_code == 401

    def test_missing_object_is_404(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        storage: InMemoryObjectStorage,
    ) -> None:
        lead_id = submit(client).json()["id"]
        storage.objects.clear()
        response = client.get(f"/api/v1/leads/{lead_id}/resume", headers=auth_headers)
        assert response.status_code == 404
