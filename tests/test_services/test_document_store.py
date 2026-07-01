from pathlib import Path

from apps.api.app.services.document_store import DocumentStore
from packages.agent_core.tools import builtin
from packages.schemas.document import Document


def test_document_store_persists_documents(tmp_path):
    storage_path = tmp_path / "documents.json"
    store = DocumentStore(storage_path=storage_path)

    created = store.create(
        Document(
            session_id="session-1",
            title="draft",
            content="hello",
        )
    )
    store.upsert_file_document(
        session_id="session-1",
        title="report",
        content="preview",
        content_type="docx",
        output_format="docx",
        file_path=str(tmp_path / "report.docx"),
    )

    reloaded = DocumentStore(storage_path=storage_path)
    assert reloaded.get(created.id) is not None
    assert len(reloaded.list_by_session("session-1")) == 2


def test_upsert_file_document_updates_same_path(tmp_path):
    storage_path = tmp_path / "documents.json"
    store = DocumentStore(storage_path=storage_path)
    file_path = tmp_path / "deck.pptx"

    first = store.upsert_file_document(
        session_id="session-1",
        title="deck",
        content="v1",
        content_type="pptx",
        output_format="pptx",
        file_path=str(file_path),
    )
    second = store.upsert_file_document(
        session_id="session-1",
        title="deck",
        content="v2",
        content_type="pptx",
        output_format="pptx",
        file_path=str(file_path),
    )

    assert first.id == second.id
    assert len(store.list_by_session("session-1")) == 1
    assert store.get(first.id).content == "v2"


def test_office_wrapper_syncs_created_file_into_document_store(tmp_path, monkeypatch):
    storage_path = tmp_path / "documents.json"
    store = DocumentStore(storage_path=storage_path)

    monkeypatch.setattr(builtin, "get_document_store", lambda: store)
    monkeypatch.setattr(
        builtin,
        "view_docx",
        lambda file_path, mode="text": {"success": True, "data": "generated body"},
    )

    def fake_create(path: str):
        return {"success": True, "data": f"Created: {path}"}

    wrapped = builtin._wrap_office_tool(fake_create, path_param="path")
    target_path = tmp_path / "brief.docx"

    token = builtin.set_current_session_id("session-1")
    try:
        wrapped(path=str(target_path))
    finally:
        builtin.reset_current_session_id(token)

    documents = store.list_by_session("session-1")
    assert len(documents) == 1
    assert documents[0].title == "brief"
    assert documents[0].content == "generated body"
    assert documents[0].file_path == str(Path(target_path).resolve())
