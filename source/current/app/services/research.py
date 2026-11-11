"""Consulta segura do índice de pesquisa local montado fora do banco da aplicação."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import quote


RESEARCH_KINDS = frozenset({"legislation", "book", "case-law"})
_WORD_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


class ResearchUnavailable(RuntimeError):
    """O catálogo não está montado ou não pode ser consultado."""


def catalog_path(configured: str | os.PathLike[str] | None = None) -> Path:
    """Resolve o arquivo do catálogo sem criar diretórios ou tocar no banco de usuários.

    ``RESEARCH_CATALOG_PATH`` aponta para o arquivo montado em produção
    (normalmente ``/catalogs/catalog.sqlite3``). Os nomes antigos são somente
    fallbacks para desenvolvimento e testes de migração.
    """
    value = configured
    if value is None:
        try:
            from flask import current_app, has_app_context

            if has_app_context():
                value = current_app.config.get("RESEARCH_CATALOG_PATH")
        except ImportError:
            pass
    if not value:
        value = os.environ.get("RESEARCH_CATALOG_PATH")
    if value:
        path = Path(value).expanduser()
        if path.exists() and path.is_dir():
            path = path / "catalog.sqlite3"
        return path

    catalog_dir = os.environ.get("ASSISTENTE_CATALOG_DIR")
    if catalog_dir:
        return Path(catalog_dir).expanduser() / "catalog.sqlite3"
    data_dir = os.environ.get("ASSISTENTE_DATA_DIR")
    return (Path(data_dir).expanduser() if data_dir else Path("data")) / "catalogs" / "catalog.sqlite3"


def _fts_query(query: str) -> str:
    tokens = []
    for token in _WORD_RE.findall(query):
        clean = token.replace('"', "")
        if clean:
            tokens.append(f'"{clean}"*')
    return " AND ".join(tokens)


def _metadata(path: Path, query: str, limit: int, returned: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    metadata_path = path.with_name("catalog_meta.json")
    try:
        loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            result.update(loaded)
    except (OSError, json.JSONDecodeError):
        pass
    # Nunca retornamos o caminho físico do volume montado ao navegador.
    result.update(
        {
            "query": query,
            "limit": limit,
            "returned": returned,
            "scope": "Índice remissivo e metadados locais; pista inicial, não pesquisa concluída.",
        }
    )
    return result


def _entry_from_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = row[0]
    if payload:
        try:
            value = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            value = None
        if isinstance(value, dict):
            return value
    return {
        key: row[index]
        for index, key in enumerate(("id", "kind", "title", "reference", "author", "abstract", "source_year", "source"), 1)
        if len(row) > index and row[index] not in (None, "")
    }


def search_catalog(
    query: str,
    kind: str | None = None,
    limit: int = 12,
    catalog_file: str | os.PathLike[str] | None = None,
    catalog_dir: str | os.PathLike[str] | None = None,
    letter: str | None = None,
) -> dict[str, Any]:
    """Busca no índice legado sem abrir o banco de contas e sem executar o legado."""
    if letter is not None and (len(letter) != 1 or letter.upper() not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        raise ValueError("letra inicial inválida")
    if kind == "case_law":
        kind = "case-law"
    if kind is not None and kind not in RESEARCH_KINDS:
        raise ValueError("tipo de catálogo inválido")
    try:
        amount = int(limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("limite inválido") from exc
    if amount <= 0:
        return {"entries": [], "metadata": {"query": query or "", "limit": amount, "returned": 0}}
    amount = min(amount, 100)
    text = str(query or "").strip()
    path = catalog_path(catalog_file if catalog_file is not None else catalog_dir)
    if not path.is_file():
        raise ResearchUnavailable("catálogo local não montado")

    uri = f"file:{quote(str(path.resolve()), safe='/')}?mode=ro"
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        connection.create_function("initial", 1, lambda value: unicodedata.normalize("NFD", str(value or "").strip()).upper()[:1], deterministic=True)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            ).fetchall()
        }
        if "entries" not in tables:
            raise ResearchUnavailable("catálogo sem tabela de entradas")
        terms = _fts_query(text)
        params: list[Any] = []
        where: list[str] = []
        if letter:
            where.append("initial(e.title) = ?")
            params.append(letter.upper())
        if kind:
            where.append("e.kind = ?")
            params.append(kind)
        if terms and "entries_fts" in tables:
            where.append("entries_fts MATCH ?")
            params.append(terms)
            sql = (
                "SELECT e.payload, e.id, e.kind, e.title, e.reference, e.author, "
                "e.abstract, e.source_year, e.source FROM entries_fts AS f "
                "JOIN entries AS e ON e.id = f.id"
            )
        else:
            if terms:
                where.append("e.search_text LIKE ?")
                params.append("%" + "%".join(_WORD_RE.findall(text)) + "%")
            sql = (
                "SELECT e.payload, e.id, e.kind, e.title, e.reference, e.author, "
                "e.abstract, e.source_year, e.source FROM entries AS e"
            )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY e.title COLLATE NOCASE, e.id LIMIT ?"
        params.append(amount)
        try:
            rows = connection.execute(sql, params).fetchall()
        except sqlite3.OperationalError as exc:
            # Alguns índices antigos não têm FTS5; a coluna search_text é a
            # mesma usada pelo importador e permite fallback sem reindexar.
            if terms and "entries_fts" in tables and "no such table" not in str(exc).lower():
                raise
            fallback_where: list[str] = []
            fallback_params: list[Any] = []
            if kind:
                fallback_where.append("e.kind = ?")
                fallback_params.append(kind)
            fallback_where.append("e.search_text LIKE ?")
            fallback_params.append("%" + "%".join(_WORD_RE.findall(text)) + "%")
            fallback_params.append(amount)
            rows = connection.execute(
                "SELECT e.payload, e.id, e.kind, e.title, e.reference, e.author, "
                "e.abstract, e.source_year, e.source FROM entries AS e WHERE "
                + " AND ".join(fallback_where)
                + " ORDER BY e.title COLLATE NOCASE, e.id LIMIT ?",
                fallback_params,
            ).fetchall()
        entries = [_entry_from_row(row) for row in rows]
        return {
            "entries": entries,
            "metadata": _metadata(path, text, amount, len(entries)),
        }
    except ResearchUnavailable:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise ResearchUnavailable("catálogo local indisponível") from exc
    finally:
        if connection is not None:
            connection.close()


def entries_by_ids(source_ids: list[str], catalog_file: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    """Retorna somente registros canônicos do catálogo read-only."""
    ids = list(dict.fromkeys(value.strip() for value in source_ids if isinstance(value, str) and value.strip()))[:100]
    if not ids:
        return []
    path = catalog_path(catalog_file)
    if not path.is_file():
        raise ResearchUnavailable("catálogo local não montado")
    placeholders = ",".join("?" for _ in ids)
    connection = None
    try:
        uri = f"file:{quote(str(path.resolve()), safe='/')}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'entries'").fetchone()
        if row is None:
            raise ResearchUnavailable("catálogo sem tabela de entradas")
        rows = connection.execute(
            "SELECT payload, id, kind, title, reference, author, abstract, source_year, source FROM entries WHERE id IN (" + placeholders + ")",
            ids,
        ).fetchall()
        by_id = {_entry_from_row(row)["id"]: _entry_from_row(row) for row in rows}
        return [by_id[source_id] for source_id in ids if source_id in by_id]
    except ResearchUnavailable:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise ResearchUnavailable("catálogo local indisponível") from exc
    finally:
        if connection is not None:
            connection.close()


__all__ = ["RESEARCH_KINDS", "ResearchUnavailable", "catalog_path", "entries_by_ids", "search_catalog"]
