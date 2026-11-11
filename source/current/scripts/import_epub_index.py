"""Importa somente o índice alfabético remissivo autorizado do Vade Mecum.

Uso: python3 scripts/import_epub_index.py caminho.epub --output-dir /home/ubuntu/assistente-private-catalogs
"""
from __future__ import annotations

import argparse
import hashlib
import html
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.research_catalog import write_catalog_file  # noqa: E402

ALLOWED_PATHS = (
    "OEBPS/Text/bm01.xhtml",
    "OEBPS/Text/bm01a.xhtml",
    "OEBPS/Text/bm01b.xhtml",
)
SOURCE = "Vade Mecum Método, 16ª edição (2023)"


def _text(value: str) -> str:
    value = html.unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


class _IndexParser(HTMLParser):
    """Extrai relações h4_b -> h4_col -> p.index, sem navegar capítulos."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.term = ""
        self.norma = ""
        self.in_linebox = 0
        self.capture: tuple[str, str] | None = None
        self.buffer: list[str] = []
        self.rows: list[tuple[str, str, str]] = []

    @staticmethod
    def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
        raw = dict(attrs).get("class") or ""
        return set(raw.split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = self._classes(attrs)
        if tag == "div" and "linebx" in classes:
            self.in_linebox += 1
            self.norma = ""
        if tag == "h4" and "h4_b" in classes:
            self.capture = ("h4", "term")
            self.buffer = []
        elif tag == "h4" and self.in_linebox and classes.intersection({"h4_col", "h4_col2", "h4_col3"}):
            self.capture = ("h4", "norma")
            self.buffer = []
        elif tag == "p" and self.in_linebox and "index" in classes:
            self.capture = ("p", "remissao")
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture and self.capture[0] == tag:
            field = self.capture[1]
            value = _text("".join(self.buffer))
            self.capture = None
            self.buffer = []
            if field == "term":
                self.term = value
            elif field == "norma":
                self.norma = value
            elif field == "remissao":
                value = re.sub(r"^[-–—]\s*", "", value).strip()
                if self.term and self.norma and value:
                    self.rows.append((self.term, self.norma, value))
        if tag == "div" and self.in_linebox:
            self.in_linebox -= 1
            if self.in_linebox == 0:
                self.norma = ""


def extract_index(epub_path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    """Lê apenas bm01/bm01a/bm01b e retorna metadados de remissões."""
    rows: dict[str, dict[str, Any]] = {}
    with ZipFile(epub_path) as archive:
        names = set(archive.namelist())
        missing = [name for name in ALLOWED_PATHS if name not in names]
        if missing:
            raise ValueError("EPUB sem índice autorizado: " + ", ".join(missing))
        for name in ALLOWED_PATHS:
            parser = _IndexParser()
            with archive.open(name) as handle:
                parser.feed(handle.read().decode("utf-8", errors="replace"))
            for term, norma, remissao in parser.rows:
                key = "\x00".join((term, norma, remissao))
                identifier = "vademecum-2023:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
                rows.setdefault(
                    identifier,
                    {
                        "id": identifier,
                        "kind": "legislation",
                        "title": term,
                        "reference": f"{norma} — {remissao}",
                        "source_year": 2023,
                        "source": SOURCE,
                        "term": term,
                        "norma": norma,
                        "remissao": remissao,
                    },
                )
    return [rows[key] for key in sorted(rows)]


def import_epub(epub_path: str | os.PathLike[str], output_dir: str | os.PathLike[str]) -> dict[str, Any]:
    entries = extract_index(epub_path)
    return write_catalog_file(
        output_dir,
        "vademecum_index.jsonl",
        entries,
        metadata={
            "vademecum_paths": list(ALLOWED_PATHS),
            "vademecum_entry_count": len(entries),
            "reference_year": 2023,
            "source_book": "Vade Mecum Método",
            "source_book_edition": 16,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("epub", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("ASSISTENTE_PRIVATE_CATALOG_DIR", "/home/ubuntu/assistente-private-catalogs")),
    )
    args = parser.parse_args(argv)
    result = import_epub(args.epub, args.output_dir)
    print(f"EPUB: {result['vademecum_entry_count']} entradas; índice total: {result['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
