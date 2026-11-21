"""Reading an image's file: which of its copies the app can actually read.

A location row says where a copy was when a scan found it. The file can
still refuse the app afterwards — a share whose ACL changed, another
tool rewriting its permissions, an NFS client answering EACCES. One such
copy must not hide a readable one, and it must be reported, not raised
into a 500.
"""

import errno
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field

from thalimage.services.locations import resolve_paths

logger = logging.getLogger(__name__)

# The file is not there, which the next scan settles: not a refusal.
MISSING_ERRNOS = frozenset({errno.ENOENT, errno.ENOTDIR, errno.ELOOP, errno.EBADF})

# A refusal can be momentary — a share rewriting its ACLs, a stale NFS
# file handle — so it is tried once more before it is reported.
TRANSIENT_ERRNOS = frozenset({errno.EACCES, errno.EPERM, errno.ESTALE})
RETRY_SECONDS = 0.2


@dataclass
class FileLookup:
    """Where an image's file is, as far as the app can read it."""

    path: str | None = None
    indexed: int = 0  # copies the index holds, readable or not
    missing: list[str] = field(default_factory=list)
    refused: list[tuple[str, str]] = field(default_factory=list)  # (path, why)


def find_file(conn: sqlite3.Connection, content_hash: str) -> FileLookup:
    """The first of the image's copies the app can read, primary first.

    A copy that refuses is logged and passed over, so one unreadable copy
    does not hide a readable one; `refused` names them, with the reason,
    when none can be read. `indexed` is 0 for an unknown or deleted image.
    """
    lookup = FileLookup()
    for path in resolve_paths(conn, content_hash):
        lookup.indexed += 1
        error = read_error(path)
        if error is None:
            if lookup.refused or lookup.missing:
                logger.warning(
                    "Reading %s for %s, after %d unusable copies",
                    path, content_hash, len(lookup.refused) + len(lookup.missing),
                )
            lookup.path = path
            return lookup
        if error.errno in MISSING_ERRNOS:
            logger.debug("No file at %s, a copy of %s", path, content_hash)
            lookup.missing.append(path)
        else:
            reason = describe(error)
            logger.warning("Cannot read %s, a copy of %s: %s", path, content_hash, reason)
            lookup.refused.append((path, reason))
    return lookup


def read_error(path: str) -> OSError | None:
    """Why the app cannot read the file, or None when it can.

    Opening the file and reading a byte is the test, not a stat: a
    location the app can see but not open is exactly what a share's ACLs
    do. A refusal that may be momentary is retried once first.
    """
    error = _open_error(path)
    if error is not None and error.errno in TRANSIENT_ERRNOS:
        time.sleep(RETRY_SECONDS)
        error = _open_error(path)
    return error


def _open_error(path: str) -> OSError | None:
    try:
        with open(path, "rb") as opened:
            opened.read(1)
    except OSError as exc:
        return exc
    return None


def describe(error: OSError) -> str:
    """What went wrong, and the errno's name, for a line in a log or a
    response: "Permission denied (EACCES)"."""
    if error.errno is None:
        return str(error)
    name = errno.errorcode.get(error.errno, str(error.errno))
    return f"{os.strerror(error.errno)} ({name})"
