"""Moving files from one source to another (#180): only between writable
sources, never a file that changed since it was scanned, the same relative
path under the target, and every attempt recorded."""

import errno
import os
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from tests.helpers import scan_source

SUB_COPY = str(Path("sub") / "c.png")


@pytest.fixture
def two_sources(
    client: TestClient, image_dir: Path, tmp_path: Path
) -> tuple[int, int, Path]:
    """A scanned library and an empty target folder, both writable."""
    target = tmp_path / "incoming"
    target.mkdir()
    source_id, _ = scan_source(client, image_dir)
    to_source_id, _ = scan_source(client, target)
    for sid in (source_id, to_source_id):
        client.patch(f"/api/v1/sources/{sid}", json={"writable": True})
    return source_id, to_source_id, target


def _move(client: TestClient, source_id: int, to_source_id: int, *paths: str):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/sources/{source_id}/move-copies",
        json={"to_source_id": to_source_id, "paths": list(paths)},
    )


def _changes(db: sqlite3.Connection) -> list[tuple[str, str, str, str | None, int | None]]:
    return [
        tuple(r)
        for r in db.execute(
            "SELECT operation, path, outcome, target, target_source_id"
            " FROM file_changes ORDER BY id"
        )
    ]


def test_a_file_moves_to_the_other_source(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.status_code == 200
    assert resp.json() == {
        "moved": ["a.png"],
        "deleted": [],
        "sidecars": [],
        "kept_sidecars": [],
        "failed": [],
        "not_readable": [],
    }
    assert not (image_dir / "a.png").exists()
    assert (target / "a.png").exists()


def test_the_file_keeps_its_relative_path_under_the_target(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources

    resp = _move(client, source_id, to_source_id, SUB_COPY)

    assert resp.status_code == 200
    assert not (image_dir / SUB_COPY).exists()
    assert (target / SUB_COPY).exists()


def test_the_image_opens_from_the_target(
    client: TestClient, two_sources: tuple[int, int, Path], image_dir: Path
) -> None:
    source_id, to_source_id, target = two_sources
    items = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
    image = next(i for i in items if i["relative_path"] == SUB_COPY)
    content_hash = image["content_hash"]

    _move(client, source_id, to_source_id, SUB_COPY)

    detail = client.get(f"/api/v1/images/{content_hash}").json()
    assert detail["source_id"] == to_source_id
    assert detail["relative_path"] == SUB_COPY
    assert client.get(f"/api/v1/images/{content_hash}/file").status_code == 200
    [copy] = client.get(f"/api/v1/images/{content_hash}/copies").json()
    assert copy["source_id"] == to_source_id and copy["writable"] is True


def test_the_sources_count_the_images_they_hold(
    client: TestClient, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources
    before = client.get(f"/api/v1/sources/{source_id}/summary").json()

    _move(client, source_id, to_source_id, "a.png")

    assert client.get(f"/api/v1/sources/{source_id}/summary").json()["files"] == (
        before["files"] - 1
    )
    assert client.get(f"/api/v1/sources/{to_source_id}/summary").json()["files"] == 1


def test_every_moved_file_is_recorded(
    client: TestClient, db: sqlite3.Connection, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources

    _move(client, source_id, to_source_id, SUB_COPY)

    assert _changes(db) == [("move", SUB_COPY, "done", SUB_COPY, to_source_id)]


@pytest.fixture
def with_sidecars(
    client: TestClient, image_dir: Path, tmp_path: Path
) -> tuple[int, int, Path]:
    """a.png and sub/c.png, each with a .txt sidecar."""
    target = tmp_path / "incoming"
    target.mkdir()
    (image_dir / "a.txt").write_text("steps: 20")
    (image_dir / "sub" / "c.txt").write_text("steps: 30")
    source_id, _ = scan_source(client, image_dir)
    to_source_id, _ = scan_source(client, target)
    for sid in (source_id, to_source_id):
        client.patch(f"/api/v1/sources/{sid}", json={"writable": True})
    return source_id, to_source_id, target


def test_a_sidecar_moves_with_its_file(
    client: TestClient, db: sqlite3.Connection, with_sidecars: tuple[int, int, Path],
    image_dir: Path,
) -> None:
    source_id, to_source_id, target = with_sidecars

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.json()["sidecars"] == ["a.txt"]
    assert not (image_dir / "a.txt").exists()
    assert (target / "a.txt").read_text() == "steps: 20"
    assert ("move", "a.txt", "done", "a.txt", to_source_id) in _changes(db)
    assert db.execute(
        "SELECT source_id FROM sidecars WHERE relative_path = 'a.txt'"
    ).fetchone()[0] == to_source_id


def test_a_sidecar_another_file_is_named_after_stays(
    client: TestClient, with_sidecars: tuple[int, int, Path], image_dir: Path
) -> None:
    source_id, to_source_id, target = with_sidecars
    # a.jpg is named after a.txt too, so the sidecar belongs to the folder.
    Image.new("RGB", (12, 12), "yellow").save(image_dir / "a.jpg")

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.json()["sidecars"] == [] and resp.json()["kept_sidecars"] == []
    assert (image_dir / "a.txt").exists()
    assert not (target / "a.txt").exists()


def test_a_sidecar_the_target_holds_identically_is_dropped(
    client: TestClient, image_dir: Path, tmp_path: Path
) -> None:
    target = tmp_path / "incoming"
    target.mkdir()
    shutil.copy(image_dir / "a.png", target / "a.png")
    (image_dir / "a.txt").write_text("steps: 20")
    (target / "a.txt").write_text("steps: 20")
    source_id, _ = scan_source(client, image_dir)
    to_source_id, _ = scan_source(client, target)
    for sid in (source_id, to_source_id):
        client.patch(f"/api/v1/sources/{sid}", json={"writable": True})

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.json()["deleted"] == ["a.png"]
    assert resp.json()["sidecars"] == ["a.txt"]
    assert not (image_dir / "a.txt").exists()
    assert (target / "a.txt").read_text() == "steps: 20"


def test_a_sidecar_the_target_holds_differently_stays_as_an_orphan(
    client: TestClient, db: sqlite3.Connection, image_dir: Path, tmp_path: Path
) -> None:
    target = tmp_path / "incoming"
    target.mkdir()
    shutil.copy(image_dir / "a.png", target / "a.png")
    (image_dir / "a.txt").write_text("steps: 20")
    (target / "a.txt").write_text("steps: 40")
    source_id, _ = scan_source(client, image_dir)
    to_source_id, _ = scan_source(client, target)
    for sid in (source_id, to_source_id):
        client.patch(f"/api/v1/sources/{sid}", json={"writable": True})

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.json()["kept_sidecars"] == ["a.txt"]
    assert (image_dir / "a.txt").read_text() == "steps: 20"
    assert (target / "a.txt").read_text() == "steps: 40"
    orphan = db.execute(
        "SELECT orphan FROM sidecars WHERE source_id = ? AND relative_path = 'a.txt'",
        (source_id,),
    ).fetchone()
    assert orphan is not None and orphan[0] == 1


def test_a_name_the_target_uses_sends_the_file_to_its_hash_name(
    client: TestClient, image_dir: Path, tmp_path: Path
) -> None:
    target = tmp_path / "incoming"
    target.mkdir()
    Image.new("RGB", (30, 30), "purple").save(target / "a.png")
    source_id, _ = scan_source(client, image_dir)
    to_source_id, _ = scan_source(client, target)
    for sid in (source_id, to_source_id):
        client.patch(f"/api/v1/sources/{sid}", json={"writable": True})
    [image] = [
        i
        for i in client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
        if i["relative_path"] == "a.png"
    ]

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.status_code == 200
    assert resp.json()["moved"] == ["a.png"]
    assert (target / f"{image['content_hash']}.png").exists()
    assert (target / "a.png").exists()  # the file that was there stays
    assert client.get(f"/api/v1/images/{image['content_hash']}").json()["relative_path"] == (
        f"{image['content_hash']}.png"
    )


def test_a_target_using_the_hash_name_too_is_refused(
    client: TestClient, image_dir: Path, tmp_path: Path
) -> None:
    target = tmp_path / "incoming"
    target.mkdir()
    Image.new("RGB", (30, 30), "purple").save(target / "a.png")
    source_id, _ = scan_source(client, image_dir)
    to_source_id, _ = scan_source(client, target)
    for sid in (source_id, to_source_id):
        client.patch(f"/api/v1/sources/{sid}", json={"writable": True})
    [image] = [
        i
        for i in client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
        if i["relative_path"] == "a.png"
    ]
    Image.new("RGB", (30, 30), "orange").save(target / f"{image['content_hash']}.png")

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.status_code == 409
    assert "cannot move" in resp.json()["detail"]
    assert (image_dir / "a.png").exists()


def test_a_copy_the_target_already_holds_is_deleted(
    client: TestClient, db: sqlite3.Connection, image_dir: Path, tmp_path: Path
) -> None:
    target = tmp_path / "incoming"
    target.mkdir()
    shutil.copy(image_dir / "a.png", target / "a.png")
    source_id, _ = scan_source(client, image_dir)
    to_source_id, _ = scan_source(client, target)
    for sid in (source_id, to_source_id):
        client.patch(f"/api/v1/sources/{sid}", json={"writable": True})
    [image] = [
        i
        for i in client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
        if i["relative_path"] == "a.png"
    ]

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.status_code == 200
    assert resp.json()["moved"] == [] and resp.json()["deleted"] == ["a.png"]
    assert not (image_dir / "a.png").exists()
    assert (target / "a.png").exists()
    [copy] = client.get(f"/api/v1/images/{image['content_hash']}/copies").json()
    assert copy["source_id"] == to_source_id
    assert db.execute(
        "SELECT deleted FROM images WHERE content_hash = ?", (image["content_hash"],)
    ).fetchone()[0] == 0


def test_the_source_that_sends_must_be_writable(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": False})

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.status_code == 409
    assert "not marked writable" in resp.json()["detail"]
    assert (image_dir / "a.png").exists()


def test_the_source_that_receives_must_be_writable(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources
    client.patch(f"/api/v1/sources/{to_source_id}", json={"writable": False})

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.status_code == 409
    assert "not marked writable" in resp.json()["detail"]
    assert (image_dir / "a.png").exists()


def test_moving_to_its_own_source_is_refused(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, Path]
) -> None:
    source_id, _, target = two_sources

    resp = _move(client, source_id, source_id, "a.png")

    assert resp.status_code == 409
    assert "own source" in resp.json()["detail"]


def test_a_path_that_is_not_an_indexed_copy_is_refused(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources

    for path in ("readme.txt", "missing.png", "../images/a.png"):
        resp = _move(client, source_id, to_source_id, path)
        assert resp.status_code == 400, path
    assert (image_dir / "readme.txt").exists()


def test_a_file_changed_since_the_scan_is_refused_and_nothing_moves(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources
    st = (image_dir / "a.png").stat()
    os.utime(image_dir / "a.png", (st.st_atime, st.st_mtime + 60))

    resp = _move(client, source_id, to_source_id, "a.png", "b.jpg")

    assert resp.status_code == 409
    assert "rescan" in resp.json()["detail"]
    assert (image_dir / "a.png").exists() and (image_dir / "b.jpg").exists()
    assert not (target / "b.jpg").exists()


def test_an_unknown_source_is_a_404(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources

    assert _move(client, 999, to_source_id, "a.png").status_code == 404
    assert _move(client, source_id, 999, "a.png").status_code == 404
    assert (image_dir / "a.png").exists()


def test_a_removed_source_cannot_receive_files(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources
    client.delete(f"/api/v1/sources/{to_source_id}", params={"keep_data": True})

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.status_code == 404
    assert (image_dir / "a.png").exists()


def test_a_move_across_filesystems_copies_then_removes(
    client: TestClient,
    image_dir: Path,
    two_sources: tuple[int, int, Path],
    monkeypatch: pytest.MonkeyPatch,
    db: sqlite3.Connection,
) -> None:
    source_id, to_source_id, target = two_sources
    moved = image_dir / "a.png"
    modified = moved.stat().st_mtime

    def other_device(path: object, target_path: object) -> None:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(os, "rename", other_device)

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.status_code == 200
    assert resp.json()["moved"] == ["a.png"]
    assert not moved.exists()
    assert (target / "a.png").stat().st_mtime == modified
    assert [p.name for p in target.iterdir() if p.name.startswith(".")] == []


def test_a_failed_move_is_reported_and_the_rest_move(
    client: TestClient,
    db: sqlite3.Connection,
    image_dir: Path,
    two_sources: tuple[int, int, Path],
) -> None:
    source_id, to_source_id, target = two_sources
    (target / "sub").mkdir()
    (target / "sub").chmod(0o500)
    try:
        resp = _move(client, source_id, to_source_id, "a.png", SUB_COPY)

        assert resp.status_code == 200
        assert resp.json()["moved"] == ["a.png"]
        [failure] = resp.json()["failed"]
        assert failure["relative_path"] == SUB_COPY
        assert (target / "a.png").exists() and (image_dir / SUB_COPY).exists()
        assert _changes(db) == [
            ("move", "a.png", "done", "a.png", to_source_id),
            ("move", SUB_COPY, "failed", SUB_COPY, to_source_id),
        ]
    finally:
        (target / "sub").chmod(0o700)


def test_a_scan_after_the_move_finds_nothing_to_do(
    client: TestClient, db: sqlite3.Connection, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources
    [image] = [
        i
        for i in client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
        if i["relative_path"] == SUB_COPY
    ]
    _move(client, source_id, to_source_id, SUB_COPY)

    for sid in (source_id, to_source_id):
        client.post(f"/api/v1/sources/{sid}/scan")
        client.get(f"/api/v1/sources/{sid}/scan/status")

    summary = client.get(f"/api/v1/sources/{to_source_id}/summary").json()
    assert summary["files"] == 1 and summary["duplicates"] == summary["failures"] == []
    [copy] = client.get(f"/api/v1/images/{image['content_hash']}/copies").json()
    assert copy["source_id"] == to_source_id and copy["relative_path"] == SUB_COPY
    assert client.get(f"/api/v1/sources/{source_id}/summary").json()["files"] == 2


def test_the_moved_location_does_not_look_changed(
    client: TestClient, db: sqlite3.Connection, two_sources: tuple[int, int, Path]
) -> None:
    """A scan skips a file whose size and modification time its location
    row still records; the move must leave them as the scan wrote them."""
    source_id, to_source_id, target = two_sources
    [image] = [
        i
        for i in client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
        if i["relative_path"] == "a.png"
    ]
    before = db.execute(
        "SELECT file_size, file_modified FROM image_locations"
        " WHERE source_id = ? AND relative_path = 'a.png'",
        (source_id,),
    ).fetchone()

    _move(client, source_id, to_source_id, "a.png")

    after = db.execute(
        "SELECT file_size, file_modified FROM image_locations"
        " WHERE source_id = ? AND relative_path = 'a.png'",
        (to_source_id,),
    ).fetchone()
    assert tuple(after) == tuple(before)
    assert client.get(f"/api/v1/images/{image['content_hash']}").status_code == 200


def test_a_file_the_app_cannot_read_after_the_move_is_reported(
    client: TestClient,
    db: sqlite3.Connection,
    image_dir: Path,
    two_sources: tuple[int, int, Path],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A share can hand back a file the app may not open: the move happens,
    and the response says the file cannot be read there."""
    from thalimage.services import file_access

    source_id, to_source_id, target = two_sources
    moved = str(target / "a.png")
    original = file_access.read_error

    def read_error(path: str) -> OSError | None:
        if str(path) == moved:
            return PermissionError(errno.EACCES, "Permission denied", path)
        return original(path)

    # Patch where it is used: the service holds the name itself.
    monkeypatch.setattr("thalimage.services.file_moving.read_error", read_error)

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.status_code == 200
    assert resp.json()["moved"] == ["a.png"]
    [unreadable] = resp.json()["not_readable"]
    assert unreadable["relative_path"] == "a.png"
    assert "Permission denied" in unreadable["error"]
    assert (target / "a.png").exists() and not (image_dir / "a.png").exists()
    assert any("cannot read" in r.getMessage().lower() for r in caplog.records)


def test_a_file_the_app_can_read_after_the_move_is_not_reported(
    client: TestClient, two_sources: tuple[int, int, Path]
) -> None:
    source_id, to_source_id, target = two_sources

    resp = _move(client, source_id, to_source_id, "a.png")

    assert resp.json()["not_readable"] == []
