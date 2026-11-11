"""Catálogo local determinístico para pistas de pesquisa acadêmica.

Os arquivos de dados são deliberadamente externos ao repositório.  Este
módulo só lê metadados e índices locais; não baixa fontes durante uma busca e
não chama modelos de linguagem.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import Any, Iterable, Mapping

KINDS = frozenset({"legislation", "book", "case-law"})
_INDEX_NAME = "catalog.sqlite3"
_META_NAME = "catalog_meta.json"
_WORD_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
_CACHE: dict[str, tuple[tuple[Any, ...], sqlite3.Connection]] = {}
_CACHE_LOCK = threading.RLock()


def default_catalog_dir() -> Path:
    """Retorna o diretório de dados conforme o contrato, fora do repositório."""
    explicit = os.environ.get("ASSISTENTE_CATALOG_DIR")
    if explicit:
        return Path(explicit).expanduser()
    data_dir = os.environ.get("ASSISTENTE_DATA_DIR")
    return (Path(data_dir).expanduser() if data_dir else Path("data")) / "catalogs"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "; ".join(_clean(item) for item in value if _clean(item))
    return " ".join(str(value).replace("\x00", " ").split())


def _entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Normaliza um registro sem eliminar campos oficiais específicos do STJ."""
    result: dict[str, Any] = {}
    for key, value in entry.items():
        if value is None or value == "" or value == []:
            continue
        if key in {"id", "kind", "title", "reference", "author", "abstract", "source", "link"}:
            if isinstance(value, (dict, list)):
                result[key] = value
            else:
                result[key] = _clean(value)
        elif key == "source_year":
            try:
                result[key] = int(value)
            except (TypeError, ValueError):
                continue
        else:
            result[key] = value
    if not result.get("id") or result.get("kind") not in KINDS or not result.get("title"):
        raise ValueError("cada entrada precisa de id, kind válido e title")
    return result


def _record_files(catalog_dir: Path) -> list[Path]:
    return sorted(
        (path for path in catalog_dir.glob("*.jsonl") if path.is_file()),
        key=lambda path: path.name,
    )


def _read_records(catalog_dir: Path) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in _record_files(catalog_dir):
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    value = _entry(json.loads(line))
                except (json.JSONDecodeError, OSError, ValueError) as exc:
                    raise ValueError(f"registro inválido em {path}:{line_number}: {exc}") from exc
                # A ordem dos arquivos é estável: o primeiro registro é a fonte
                # vencedora em caso de ID repetido.
                records.setdefault(str(value["id"]), value)
    return list(records.values())


def _search_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_search_text(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_search_text(item) for item in value)
    return _clean(value)


def _signature(catalog_dir: Path) -> tuple[Any, ...]:
    paths = [catalog_dir / _INDEX_NAME, catalog_dir / _META_NAME, *_record_files(catalog_dir)]
    signature: list[Any] = []
    for path in paths:
        try:
            stat = path.stat()
        except FileNotFoundError:
            signature.append((str(path), None))
        else:
            signature.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(signature)


def _create_schema(connection: sqlite3.Connection, use_fts: bool) -> None:
    connection.execute(
        """CREATE TABLE entries (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            reference TEXT,
            author TEXT,
            abstract TEXT,
            source_year INTEGER,
            source TEXT,
            search_text TEXT NOT NULL,
            payload TEXT NOT NULL
        )"""
    )
    if use_fts:
        connection.execute(
            """CREATE VIRTUAL TABLE entries_fts USING fts5(
                id UNINDEXED, kind UNINDEXED, title, reference, author,
                abstract, search_text, tokenize='unicode61 remove_diacritics 2'
            )"""
        )


def _fill_schema(connection: sqlite3.Connection, records: Iterable[Mapping[str, Any]], use_fts: bool) -> int:
    count = 0
    for raw in records:
        value = _entry(raw)
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        search_text = _search_text(value)
        connection.execute(
            """INSERT OR IGNORE INTO entries
               (id, kind, title, reference, author, abstract, source_year, source, search_text, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(value["id"]), value["kind"], value["title"], value.get("reference"),
                value.get("author"), value.get("abstract"), value.get("source_year"),
                value.get("source"), search_text, payload,
            ),
        )
        if use_fts:
            connection.execute(
                """INSERT OR IGNORE INTO entries_fts
                   (id, kind, title, reference, author, abstract, search_text)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(value["id"]), value["kind"], value.get("title", ""),
                    _search_text(value.get("reference")), _search_text(value.get("author")),
                    _search_text(value.get("abstract")), search_text,
                ),
            )
        count += 1
    return count


def _fts_available(connection: sqlite3.Connection) -> bool:
    try:
        return bool(connection.execute("SELECT sqlite_compileoption_used('ENABLE_FTS5')").fetchone()[0])
    except sqlite3.DatabaseError:
        return False


def build_catalog(catalog_dir: str | os.PathLike[str], metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Reconstrói atomicamente o índice a partir dos JSONL privados do diretório."""
    directory = Path(catalog_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    records = _read_records(directory)
    fd, temporary = tempfile.mkstemp(prefix="catalog-", suffix=".sqlite3", dir=directory)
    os.close(fd)
    try:
        connection = sqlite3.connect(temporary)
        use_fts = _fts_available(connection)
        _create_schema(connection, use_fts)
        count = _fill_schema(connection, records, use_fts)
        connection.execute("CREATE INDEX entries_kind ON entries(kind)")
        connection.commit()
        connection.close()
        os.replace(temporary, directory / _INDEX_NAME)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    sources = sorted({str(row.get("source")) for row in records if row.get("source")})
    years = sorted({int(row["source_year"]) for row in records if row.get("source_year") is not None})
    result: dict[str, Any] = {}
    meta_path = directory / _META_NAME
    if meta_path.exists():
        try:
            previous = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(previous, dict):
                result.update(previous)
        except (OSError, json.JSONDecodeError):
            pass
    result.update({
        "count": count,
        "kinds": sorted({row["kind"] for row in records}),
        "source_years": years,
        "sources": sources,
        "fts5": use_fts,
    })
    if metadata:
        result.update(dict(metadata))
    (directory / _META_NAME).write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    with _CACHE_LOCK:
        old = _CACHE.pop(str(directory.resolve()), None)
        if old:
            old[1].close()
    return result


def write_catalog_file(
    catalog_dir: str | os.PathLike[str],
    filename: str,
    records: Iterable[Mapping[str, Any]],
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Grava um JSONL de fonte e atualiza o índice combinado do diretório."""
    if not filename.endswith(".jsonl") or Path(filename).name != filename:
        raise ValueError("filename deve ser um nome JSONL simples")
    directory = Path(catalog_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    normalized = [_entry(record) for record in records]
    temporary = directory / f".{filename}.tmp"
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in normalized:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    os.replace(temporary, directory / filename)
    return build_catalog(directory, metadata=metadata)


def _open_index(directory: Path) -> sqlite3.Connection:
    """Abre índice existente; sem índice, constrói uma vez a partir de JSONL."""
    directory.mkdir(parents=True, exist_ok=True)
    index = directory / _INDEX_NAME
    index_mtime = index.stat().st_mtime_ns if index.exists() else -1
    source_changed = any(path.stat().st_mtime_ns > index_mtime for path in _record_files(directory))
    if not index.exists() or source_changed:
        build_catalog(directory)
    uri = f"file:{index.resolve()}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def _connection(directory: Path) -> sqlite3.Connection:
    key = str(directory.resolve())
    signature = _signature(directory)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and cached[0] == signature:
            return cached[1]
        if cached:
            cached[1].close()
        connection = _open_index(directory)
        _CACHE[key] = (_signature(directory), connection)
        return connection


def _fts_query(query: str) -> str:
    # Tokens próprios, entre aspas, evitam que a consulta do usuário injete a
    # sintaxe MATCH. O prefixo permite buscar flexões sem gerar termos amplos.
    tokens = [_clean(token).replace('"', "") for token in _WORD_RE.findall(query)]
    return " AND ".join(f'"{token}"*' for token in tokens if token)


def _public_payload(payload: str) -> dict[str, Any]:
    value = json.loads(payload)
    # Não vazamos colunas internas; os campos extras oficiais (p.ex. ementa e
    # numeroProcesso) continuam disponíveis para a etapa JEV selecionar IDs.
    return value


def search_catalog(
    query: str,
    kind: str | None = None,
    limit: int = 12,
    catalog_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Busca metadados locais conforme o contrato Corpus API."""
    if kind is not None and kind not in KINDS:
        raise ValueError(f"kind inválido: {kind!r}")
    try:
        amount = int(limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit deve ser inteiro") from exc
    if amount <= 0:
        return {"entries": [], "metadata": {"count": 0, "limit": amount}}
    amount = min(amount, 100)
    directory = Path(catalog_dir).expanduser() if catalog_dir is not None else default_catalog_dir()
    directory = directory.resolve()
    if not directory.exists():
        return {"entries": [], "metadata": {"count": 0, "catalog_dir": str(directory), "limit": amount}}
    connection = _connection(directory)
    terms = _fts_query(query or "")
    params: list[Any] = []
    where = []
    if kind:
        where.append("e.kind = ?")
        params.append(kind)
    if terms:
        where.append("entries_fts MATCH ?")
        params.append(terms)
    clause = " WHERE " + " AND ".join(where) if where else ""
    if terms:
        sql = (
            "SELECT e.payload FROM entries_fts f JOIN entries e ON e.id = f.id"
            f"{clause} ORDER BY bm25(entries_fts), e.title COLLATE NOCASE, e.id LIMIT ?"
        )
    else:
        sql = "SELECT e.payload FROM entries e" + clause + " ORDER BY e.title COLLATE NOCASE, e.id LIMIT ?"
    params.append(amount)
    try:
        rows = connection.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        # Índices criados sem FTS5 continuam utilizáveis como busca leve, sem
        # reprocessar JSON por requisição.
        if terms and "no such table: entries_fts" in str(exc):
            like = "%" + "%".join(_clean(query).split()) + "%"
            fallback_where = []
            fallback_params: list[Any] = []
            if kind:
                fallback_where.append("e.kind = ?")
                fallback_params.append(kind)
            fallback_where.append("e.search_text LIKE ?")
            fallback_params.append(like)
            fallback_sql = "SELECT e.payload FROM entries e WHERE " + " AND ".join(fallback_where) + " ORDER BY e.title COLLATE NOCASE, e.id LIMIT ?"
            fallback_params.append(amount)
            rows = connection.execute(fallback_sql, fallback_params).fetchall()
        else:
            raise
    entries = [_public_payload(row[0]) for row in rows]
    meta_path = directory / _META_NAME
    metadata: dict[str, Any] = {}
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            metadata = {}
    metadata.update({"catalog_dir": str(directory), "query": query or "", "limit": amount, "returned": len(entries)})
    return {"entries": entries, "metadata": metadata}


__all__ = ["KINDS", "build_catalog", "default_catalog_dir", "search_catalog", "write_catalog_file"]
