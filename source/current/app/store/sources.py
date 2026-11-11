import time
from uuid import uuid4

from .db import get_db

SOURCE_KINDS = {"book", "article", "legislation", "case_law", "website", "other"}
MAX_NOTES_LENGTH = 5000


def create_source(account_id: str, title: str, author: str, kind: str, reference: str, notes: str) -> str:
    source_id = str(uuid4())
    now = int(time.time())
    get_db().execute(
        """INSERT INTO sources (id, account_id, title, author, kind, reference, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            source_id,
            account_id,
            str(title or "").strip()[:240],
            str(author or "").strip()[:240],
            kind if kind in SOURCE_KINDS else "other",
            str(reference or "").strip()[:500],
            str(notes or "").strip()[:MAX_NOTES_LENGTH],
            now,
            now,
        ),
    )
    get_db().commit()
    return source_id


def list_sources(account_id: str):
    rows = get_db().execute(
        """SELECT id, title, author, kind, reference, notes, created_at, updated_at
           FROM sources WHERE account_id = ? ORDER BY updated_at DESC, title COLLATE NOCASE""",
        (account_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def update_source(
    account_id: str,
    source_id: str,
    title: str,
    author: str,
    kind: str,
    reference: str,
    notes: str,
) -> bool:
    """Atualiza somente uma fonte pertencente à conta informada."""
    result = get_db().execute(
        """UPDATE sources
           SET title = ?, author = ?, kind = ?, reference = ?, notes = ?, updated_at = ?
           WHERE id = ? AND account_id = ?""",
        (
            str(title or "").strip()[:240],
            str(author or "").strip()[:240],
            kind if kind in SOURCE_KINDS else "other",
            str(reference or "").strip()[:500],
            str(notes or "").strip()[:MAX_NOTES_LENGTH],
            int(time.time()),
            source_id,
            account_id,
        ),
    )
    get_db().commit()
    return result.rowcount == 1


def delete_source(account_id: str, source_id: str) -> bool:
    """Exclui uma fonte somente quando ela pertence à conta atual."""
    result = get_db().execute(
        "DELETE FROM sources WHERE id = ? AND account_id = ?",
        (source_id, account_id),
    )
    get_db().commit()
    return result.rowcount == 1


def owned_source_ids(account_id: str, source_ids: list[str]) -> set[str]:
    clean = {str(source_id) for source_id in source_ids if isinstance(source_id, str) and source_id}
    if not clean:
        return set()
    placeholders = ",".join("?" for _ in clean)
    query = "SELECT id FROM sources WHERE account_id = ? AND id IN (" + placeholders + ")"
    rows = get_db().execute(
        query,
        (account_id, *clean),
    ).fetchall()
    return {row["id"] for row in rows}
