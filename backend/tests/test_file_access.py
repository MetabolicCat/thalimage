"""Reading an image's file: a copy the app cannot read is reported and
skipped, never raised into a 500, and one bad copy does not hide a good
one."""

import errno
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.helpers import scan_source
from thalimage.services import file_access


def _permission_denied(path: str) -> PermissionError:
    return PermissionError(errno.EACCES, "Permission denied", path)


def _refusing(monkeypatch: pytest.MonkeyPatch, *paths: str) -> None:
    """Make reading these paths fail with EACCES, as a share can."""
    original = file_access.read_error

    def read_error(path: str) -> OSError | None:
        if str(path) in paths:
            return _permission_denied(path)
        return original(path)

    monkeypatch.setattr(file_access, "read_error", read_error)


def _hash(client: TestClient, source_id: int, relative_path: str = "a.png") -> str:
    items = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
    [image] = [i for i in items if i["relative_path"] == relative_path]
    return str(image["content_hash"])


def test_a_transient_refusal_is_tried_once_more(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(file_access, "RETRY_SECONDS", 0)
    answers = [_permission_denied("a.png"), None]
    monkeypatch.setattr(file_access, "_open_error", lambda path: answers.pop(0))

    assert file_access.read_error("a.png") is None
    assert answers == []


def test_a_refusal_that_stays_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(file_access, "RETRY_SECONDS", 0)
    calls = []

    def open_error(path: str) -> PermissionError:
        calls.append(path)
        return _permission_denied(path)

    monkeypatch.setattr(file_access, "_open_error", open_error)

    error = file_access.read_error("a.png")

    assert isinstance(error, PermissionError)
    assert len(calls) == 2


def test_a_missing_file_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def open_error(path: str) -> FileNotFoundError:
        calls.append(path)
        return FileNotFoundError(errno.ENOENT, "No such file or directory", path)

    monkeypatch.setattr(file_access, "_open_error", open_error)

    assert isinstance(file_access.read_error("a.png"), FileNotFoundError)
    assert len(calls) == 1


def test_a_readable_file_is_found(client: TestClient, image_dir: Path, db: sqlite3.Connection) -> None:
    source_id, _ = scan_source(client, image_dir)
    content_hash = _hash(client, source_id)

    lookup = file_access.find_file(db, content_hash)

    assert lookup.path is not None and Path(lookup.path).is_file()
    assert lookup.refused == [] and lookup.indexed >= 1


def test_an_unreadable_copy_is_skipped_for_a_readable_one(
    client: TestClient, image_dir: Path, tmp_path: Path, db: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    shutil.copy(image_dir / "a.png", other / "a.png")
    source_id, _ = scan_source(client, image_dir)
    to_source_id, _ = scan_source(client, other)
    content_hash = _hash(client, to_source_id)
    paths = [c["source_path"] + "/" + c["relative_path"] for c in client.get(
        f"/api/v1/images/{content_hash}/copies"
    ).json()]
    assert len(paths) == 2
    _refusing(monkeypatch, paths[0])

    lookup = file_access.find_file(db, content_hash)

    assert lookup.path == paths[1]
    assert [p for p, _ in lookup.refused] == [paths[0]]


def test_every_copy_refused_leaves_no_path(
    client: TestClient, image_dir: Path, db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_id, _ = scan_source(client, image_dir)
    content_hash = _hash(client, source_id)
    [copy] = client.get(f"/api/v1/images/{content_hash}/copies").json()
    _refusing(monkeypatch, copy["source_path"] + "/" + copy["relative_path"])

    lookup = file_access.find_file(db, content_hash)

    assert lookup.path is None
    assert len(lookup.refused) == 1 and "Permission denied" in lookup.refused[0][1]


def test_the_preview_of_an_unreadable_file_says_so(
    client: TestClient, image_dir: Path, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source_id, _ = scan_source(client, image_dir)
    content_hash = _hash(client, source_id)
    [copy] = client.get(f"/api/v1/images/{content_hash}/copies").json()
    path = copy["source_path"] + "/" + copy["relative_path"]
    _refusing(monkeypatch, path)

    resp = client.get(f"/api/v1/images/{content_hash}/preview?size=2560")

    assert resp.status_code == 409
    assert path in resp.json()["detail"]
    assert "Permission denied" in resp.json()["detail"]
    assert any("Cannot read" in r.message and path in r.getMessage() for r in caplog.records)


def test_a_readable_copy_is_served_when_another_is_refused(
    client: TestClient, image_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    shutil.copy(image_dir / "a.png", other / "a.png")
    source_id, _ = scan_source(client, image_dir)
    to_source_id, _ = scan_source(client, other)
    content_hash = _hash(client, to_source_id)
    copies = client.get(f"/api/v1/images/{content_hash}/copies").json()
    paths = [c["source_path"] + "/" + c["relative_path"] for c in copies]
    _refusing(monkeypatch, paths[0])

    assert client.get(f"/api/v1/images/{content_hash}/file").status_code == 200
    assert client.get(f"/api/v1/images/{content_hash}/preview?size=2560").status_code == 200


def test_a_file_gone_from_disk_is_a_404(client: TestClient, image_dir: Path) -> None:
    source_id, _ = scan_source(client, image_dir)
    content_hash = _hash(client, source_id)
    [copy] = client.get(f"/api/v1/images/{content_hash}/copies").json()
    (Path(copy["source_path"]) / copy["relative_path"]).unlink()

    resp = client.get(f"/api/v1/images/{content_hash}/file")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "File not found on disk"


def test_an_unknown_image_is_a_404(client: TestClient) -> None:
    unknown = "0" * 64

    resp = client.get(f"/api/v1/images/{unknown}/file")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Image not found"
