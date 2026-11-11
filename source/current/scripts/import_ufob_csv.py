"""Importa metadados bibliográficos MB Jurídica do CSV público da UFOB.

Descrições editoriais, artigos e conteúdo de livros não entram no catálogo.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.research_catalog import write_catalog_file  # noqa: E402

SOURCE_URL = "https://ufob.edu.br/acesso-a-informacao/dados-abertos/api/2021/acervo-da-plataforma-minha-biblioteca-2021.csv/@@download/file/ACERVO-DA-PLATAFORMA-MINHA-BIBLIOTECA-2021.csv"
SOURCE = "UFOB — Acervo da Plataforma Minha Biblioteca 2021 (snapshot modificado em 2022)"


def _key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _value(row: Mapping[str, str], *names: str) -> str:
    wanted = {_key(name) for name in names}
    for key, value in row.items():
        if _key(key) in wanted:
            return " ".join((value or "").replace("\x00", " ").split())
    return ""


def _csv_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _records_from_rows(rows: Iterable[Mapping[str, str]]) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        category = _value(row, "MB JURÍDICA", "MB JURDICA", "MB JURIDICA")
        title = _value(row, "Título", "Ttulo", "Titulo")
        if not category or not title:
            continue
        isbn = _value(row, "ISBN")
        author = _value(row, "Autor")
        identity = "|".join((_key(isbn), _key(title), _key(author)))
        identifier = "ufob-mb:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        records.setdefault(
            identifier,
            {
                "id": identifier,
                "kind": "book",
                "title": title,
                "author": author,
                "source_year": 2021,
                "source": SOURCE,
                "link": SOURCE_URL,
                "isbn": isbn,
                "categories": ["MB Jurídica"],
            },
        )
    return [records[key] for key in sorted(records)]


def read_csv_records(csv_path_or_url: str | os.PathLike[str]) -> list[dict[str, Any]]:
    value = str(csv_path_or_url)
    if re.match(r"^https?://", value, re.IGNORECASE):
        with urllib.request.urlopen(value, timeout=60) as response:
            raw = response.read()
    else:
        raw = Path(value).read_bytes()
    text = _csv_text(raw)
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames:
        raise ValueError("CSV sem cabeçalho")
    return _records_from_rows(reader)


def import_ufob(csv_path_or_url: str | os.PathLike[str], output_dir: str | os.PathLike[str]) -> dict[str, Any]:
    entries = read_csv_records(csv_path_or_url)
    return write_catalog_file(
        output_dir,
        "ufob_mb_juridica.jsonl",
        entries,
        metadata={
            "ufob_entry_count": len(entries),
            "ufob_source_url": SOURCE_URL,
            "ufob_snapshot_year": 2021,
            "ufob_snapshot_modified_year": 2022,
            "ufob_categories": ["MB Jurídica"],
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", default=SOURCE_URL, help="caminho local ou URL do CSV")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("ASSISTENTE_PRIVATE_CATALOG_DIR", "/home/ubuntu/assistente-private-catalogs")),
    )
    args = parser.parse_args(argv)
    result = import_ufob(args.csv, args.output_dir)
    print(f"UFOB: {result['ufob_entry_count']} livros MB Jurídica; índice total: {result['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
