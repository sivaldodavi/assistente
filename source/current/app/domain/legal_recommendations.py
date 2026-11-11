from __future__ import annotations

import re
from uuid import UUID


MAX_PROBLEM = 4000
MAX_INSTRUCTIONS = 12000
MAX_KEYWORDS = 20
MAX_KEYWORD = 80
MAX_SOURCE_IDS = 30
MAX_RESULTS_PER_KIND = 5
_KIND_TO_CATEGORY = {"legislation": "law", "case-law": "jurisprudence", "book": "doctrine"}
_CATEGORY_TO_KIND = {value: key for key, value in _KIND_TO_CATEGORY.items()}
_UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")


def _text(value: object, limit: int, name: str, required: bool = False) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise ValueError(f"{name} inválido")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{name} obrigatório")
    if len(value) > limit:
        raise ValueError(f"{name} grande demais")
    return value


def normalize_request(body: object) -> dict:
    if not isinstance(body, dict):
        raise ValueError("pedido inválido")
    request_id = body.get("request_id")
    if not isinstance(request_id, str) or not _UUID_RE.fullmatch(request_id):
        raise ValueError("request_id inválido")
    try:
        request_id = str(UUID(request_id))
    except ValueError as error:
        raise ValueError("request_id inválido") from error
    revision = body.get("project_revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError("project_revision inválida")
    keywords = body.get("keywords", [])
    if not isinstance(keywords, list) or len(keywords) > MAX_KEYWORDS:
        raise ValueError("keywords inválidas")
    clean_keywords = []
    for keyword in keywords:
        value = _text(keyword, MAX_KEYWORD, "keyword", required=True)
        if value not in clean_keywords:
            clean_keywords.append(value)
    source_ids = body.get("catalog_source_ids", [])
    if not isinstance(source_ids, list) or len(source_ids) > MAX_SOURCE_IDS:
        raise ValueError("fontes de catálogo inválidas")
    clean_source_ids = []
    for source_id in source_ids:
        value = _text(source_id, 160, "source_id", required=True)
        if value not in clean_source_ids:
            clean_source_ids.append(value)
    return {
        "request_id": request_id,
        "project_revision": revision,
        "problem_question": _text(body.get("problem_question"), MAX_PROBLEM, "pergunta-problema", required=True),
        "professor_instructions": _text(body.get("professor_instructions"), MAX_INSTRUCTIONS, "instruções do professor"),
        "keywords": clean_keywords,
        "catalog_source_ids": clean_source_ids,
    }


def category_for_kind(kind: str) -> str | None:
    return _KIND_TO_CATEGORY.get(kind)


def kind_for_category(category: str) -> str | None:
    return _CATEGORY_TO_KIND.get(category)


def validate_candidates(entries: list[dict]) -> list[dict]:
    clean = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source_id = entry.get("id")
        kind = entry.get("kind")
        title = entry.get("title")
        if not isinstance(source_id, str) or not source_id or source_id in seen:
            continue
        if kind not in _KIND_TO_CATEGORY or not isinstance(title, str) or not title.strip():
            continue
        seen.add(source_id)
        clean.append({
            "id": source_id,
            "kind": kind,
            "title": title[:500],
            "reference": str(entry.get("reference") or "")[:1000],
            "author": str(entry.get("author") or "")[:500],
            "abstract": str(entry.get("abstract") or entry.get("ementa") or "")[:4000],
            "source_year": entry.get("source_year") if isinstance(entry.get("source_year"), int) else None,
            "source": str(entry.get("source") or "")[:500],
            "link": entry.get("link") if isinstance(entry.get("link"), str) and entry["link"].startswith("https://") else "",
        })
    return clean


def validate_result(result: object, candidates: list[dict]) -> dict:
    if not isinstance(result, dict) or set(result) - {"law", "jurisprudence", "doctrine", "warnings"}:
        raise ValueError("resposta de recomendação inválida")
    by_id = {entry["id"]: entry for entry in candidates}
    output = {"law": [], "jurisprudence": [], "doctrine": []}
    used = set()
    for category in output:
        items = result.get(category, [])
        if not isinstance(items, list) or len(items) > MAX_RESULTS_PER_KIND:
            raise ValueError("lista de recomendações inválida")
        expected_kind = kind_for_category(category)
        for item in items:
            if not isinstance(item, dict) or set(item) != {"source_id", "why", "rank"}:
                raise ValueError("item de recomendação inválido")
            source_id = item["source_id"]
            why = item["why"]
            rank = item["rank"]
            if source_id not in by_id or source_id in used or by_id[source_id]["kind"] != expected_kind:
                raise ValueError("fonte recomendada não pertence ao catálogo permitido")
            if not isinstance(why, str) or not why.strip() or len(why) > 600:
                raise ValueError("justificativa inválida")
            if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= MAX_RESULTS_PER_KIND:
                raise ValueError("posição inválida")
            used.add(source_id)
            output[category].append({"source_id": source_id, **by_id[source_id], "why": why.strip(), "rank": rank})
    warnings = result.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(item, str) or len(item) > 300 for item in warnings):
        raise ValueError("avisos inválidos")
    return {"recommendations": output, "warnings": warnings[:5]}


__all__ = [
    "MAX_RESULTS_PER_KIND",
    "category_for_kind",
    "normalize_request",
    "validate_candidates",
    "validate_result",
]
