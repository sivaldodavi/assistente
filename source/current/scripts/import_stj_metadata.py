"""Importa ementas/metadados identificáveis do espelho oficial CKAN do STJ.

Por padrão seleciona um único JSON mensal recente (até 10 MB), nunca todo o
histórico do pacote. Nenhuma teoria, decisão ou texto além de ementa é salvo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.research_catalog import write_catalog_file  # noqa: E402

PACKAGE_URL = "https://dadosabertos.web.stj.jus.br/api/3/action/package_show?id=espelhos-de-acordaos-quarta-turma"
PACKAGE_NAME = "espelhos-de-acordaos-quarta-turma"
COLLECTION = "Quarta Turma"
SOURCE = "STJ — Espelhos de acórdãos da Quarta Turma"
MAX_RESOURCE_BYTES = 10_000_000


def fetch_json(url: str, timeout: int = 60) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _resource_date(resource: Mapping[str, Any]) -> dt.date | None:
    name = str(resource.get("name") or resource.get("url") or "")
    found = re.search(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)", name)
    if found:
        try:
            return dt.date(int(found.group(1)), int(found.group(2)), int(found.group(3)))
        except ValueError:
            pass
    for key in ("last_modified", "metadata_modified", "created"):
        value = str(resource.get(key) or "")[:10]
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            continue
    return None


def _resource_size(resource: Mapping[str, Any]) -> int | None:
    try:
        return int(resource["size"])
    except (KeyError, TypeError, ValueError):
        return None


def select_recent_resource(resources: Iterable[Mapping[str, Any]], max_bytes: int = MAX_RESOURCE_BYTES) -> dict[str, Any]:
    """Escolhe um recurso JSON mensal, recente e pequeno; a seleção é única."""
    candidates: list[tuple[dt.date, int, Mapping[str, Any]]] = []
    for resource in resources:
        url = str(resource.get("url") or "")
        fmt = str(resource.get("format") or "").lower()
        name = str(resource.get("name") or url).lower()
        if not url.startswith(("http://", "https://")) or not (fmt == "json" or name.endswith(".json")):
            continue
        size = _resource_size(resource)
        if size is not None and size > max_bytes:
            continue
        candidates.append((_resource_date(resource) or dt.date.min, size if size is not None else max_bytes, resource))
    if not candidates:
        raise ValueError("pacote STJ não oferece recurso JSON mensal pequeno")
    # Data desc, depois tamanho asc e URL estável. Uma única data é baixada.
    candidates.sort(key=lambda item: (-item[0].toordinal(), item[1], str(item[2].get("url"))))
    return dict(candidates[0][2])


def _text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\x00", " ").split())


def _year(value: str) -> int | None:
    found = re.match(r"(20\d{2})", value)
    return int(found.group(1)) if found else None


def _record(entry: Mapping[str, Any], resource: Mapping[str, Any]) -> dict[str, Any] | None:
    # O ID numérico é a chave pública oficial do espelho; sem ele não há
    # candidato identificável e portanto não se cria um ID inventado.
    official_id = _text(entry.get("id"))
    ementa = _text(entry.get("ementa"))
    if not official_id or not ementa:
        return None
    processo = _text(entry.get("numeroProcesso"))
    registro = _text(entry.get("numeroRegistro"))
    orgao = _text(entry.get("nomeOrgaoJulgador")) or COLLECTION.upper()
    data_decisao = _text(entry.get("dataDecisao"))
    classe = _text(entry.get("siglaClasse"))
    title_prefix = classe or "Acórdão"
    title = f"{title_prefix} — Processo {processo}" if processo else f"{title_prefix} STJ — {official_id}"
    value: dict[str, Any] = {
        "id": official_id,
        "kind": "case-law",
        "title": title,
        "abstract": ementa,
        "ementa": ementa,
        "source": SOURCE,
        "license": "CC BY",
        "link": str(resource.get("url") or PACKAGE_URL),
        "numeroProcesso": processo,
        "numeroRegistro": registro,
        "nomeOrgaoJulgador": orgao,
        "dataDecisao": data_decisao,
        "termosAuxiliares": entry.get("termosAuxiliares"),
    }
    source_year = _year(data_decisao)
    if source_year is not None:
        value["source_year"] = source_year
    return value


def records_from_json(data: Any, resource: Mapping[str, Any]) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        for key in ("result", "records", "items", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError("recurso STJ não é uma lista JSON de acórdãos")
    dedup: dict[str, dict[str, Any]] = {}
    for item in data:
        if not isinstance(item, Mapping):
            continue
        value = _record(item, resource)
        if value:
            dedup.setdefault(value["id"], value)
    return [dedup[key] for key in sorted(dedup)]


def import_stj(output_dir: str | os.PathLike[str], package_url: str = PACKAGE_URL) -> dict[str, Any]:
    package = fetch_json(package_url)
    if not isinstance(package, Mapping) or not package.get("success", True):
        raise ValueError("package_show do STJ não retornou sucesso")
    result = package.get("result")
    if not isinstance(result, Mapping):
        raise ValueError("package_show do STJ sem result")
    resource = select_recent_resource(result.get("resources", []))
    data = fetch_json(str(resource["url"]))
    entries = records_from_json(data, resource)
    return write_catalog_file(
        output_dir,
        "stj_quarta_turma.jsonl",
        entries,
        metadata={
            "stj_entry_count": len(entries),
            "stj_package": PACKAGE_NAME,
            "stj_package_url": package_url,
            "stj_resource_name": resource.get("name"),
            "stj_resource_url": resource.get("url"),
            "stj_resource_selection": "um JSON mensal recente, máximo 10 MB",
            "stj_license": "CC BY",
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-url", default=PACKAGE_URL)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("ASSISTENTE_PRIVATE_CATALOG_DIR", "/home/ubuntu/assistente-private-catalogs")),
    )
    args = parser.parse_args(argv)
    result = import_stj(args.output_dir, args.package_url)
    print(f"STJ: {result['stj_entry_count']} ementas ({result['stj_resource_name']}); índice total: {result['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
