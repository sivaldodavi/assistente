"""Build private Quarto documents and render them to PDF with the local ABNT format."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any


EXTENSION_DIR = Path(__file__).resolve().parents[2] / "_extensions" / "abnt"
RENDER_TIMEOUT_SECONDS = 90
MAX_PDF_BYTES = 25 * 1024 * 1024
_RENDER_SLOTS = threading.BoundedSemaphore(2)
_DOCUMENT_KINDS = {
    "case_report": "case",
    "paper_project": "paper",
    "paper_final": "paper",
}


class QuartoDocumentError(ValueError):
    """The requested project/document combination is not valid."""


class QuartoUnavailableError(RuntimeError):
    """Quarto or the local format extension is unavailable."""


class QuartoBusyError(RuntimeError):
    """The renderer is at its bounded concurrency limit."""


class QuartoRenderError(RuntimeError):
    """Quarto failed or exceeded the configured resource limits."""


def _text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    # Remove control bytes that have no useful representation in a document.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value).replace("\r\n", "\n").replace("\r", "\n")


def _typst_literal(value: Any) -> str:
    """Return one escaped Typst string literal; callers never inject raw Typst."""
    return json.dumps(_text(value), ensure_ascii=False)


def _yaml_typst_scalar(value: Any) -> str:
    """Encode a Typst-escaped string as a YAML/JSON-compatible quoted scalar."""
    typst_inner = _typst_literal(value)[1:-1]
    return json.dumps(typst_inner, ensure_ascii=False)


def _markdown_text(value: Any) -> str:
    """Escape plain editor text so it cannot become Markdown, HTML, or a raw block."""
    value = _text(value)
    # Pandoc/Quarto Markdown treats backslash-escaped punctuation literally.
    return re.sub(r"([\\`*_{}\[\]<>()#+.!|~&+-])", r"\\\1", value)


def _paragraphs(value: Any) -> str:
    paragraphs = re.split(r"\n[ \t]*\n+", _text(value).strip())
    rendered = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        lines = paragraph.split("\n")
        rendered.append("  \n".join(_markdown_text(line) for line in lines))
    return "\n\n".join(rendered)


def _yaml_list(name: str, values: list[str]) -> str:
    if not values:
        return f"{name}: []"
    return f"{name}:\n" + "\n".join(f"  - {_yaml_typst_scalar(value)}" for value in values)


def _raw_typst(code: str) -> str:
    return f"```{{=typst}}\n{code.strip()}\n```\n"


def _authors(project: dict[str, Any]) -> list[str]:
    fields = project["fields"]
    return [line.strip() for line in _text(fields.get("author")).split("\n") if line.strip()]


def _brazilian_date(value: Any) -> str:
    value = _text(value).strip()
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
    return f"{match.group(3)}/{match.group(2)}/{match.group(1)}" if match else value


def _metadata(project: dict[str, Any]) -> str:
    fields = project["fields"]
    facsure = fields.get("profile") == "facsure"
    authors = _authors(project)
    institution = _text(fields.get("institution")) if facsure else ""
    course = _text(fields.get("course")) if facsure else ""
    schedule = project.get("schedule") if isinstance(project.get("schedule"), dict) else {}
    if project.get("projectType") == "paper" and fields.get("paperKind") == "final":
        delivery = schedule.get("finalDate") or fields.get("deliveryDate") or schedule.get("deliveryDate")
    else:
        delivery = fields.get("deliveryDate") or schedule.get("deliveryDate")
    details = [
        f"Disciplina: {_text(fields.get('discipline'))}" if _text(fields.get("discipline")).strip() else "",
        f"Professor(a): {_text(fields.get('teacher'))}" if _text(fields.get("teacher")).strip() else "",
        f"Turma: {_text(fields.get('classInfo'))}" if _text(fields.get("classInfo")).strip() else "",
        f"Data de entrega: {_brazilian_date(delivery)}" if _text(delivery).strip() else "",
    ]
    details = [item for item in details if item]
    title = _text(fields.get("title")).strip()
    year = _text(fields.get("year"))
    city = _text(fields.get("city"))
    subtitle = _text(fields.get("subtitle") or fields.get("subTitle"))
    metadata = [
        f"title: {_yaml_typst_scalar(title)}",
        "lang: pt-BR",
        "abnt-capa: true",
        "abnt-folha-rosto: false",
        f"abnt-instituicao: {_yaml_typst_scalar(institution)}",
        f"abnt-curso: {_yaml_typst_scalar(course)}",
        f"abnt-subtitulo: {_yaml_typst_scalar(subtitle)}",
        _yaml_list("abnt-autores", authors),
        _yaml_list("abnt-dados", details),
        f"abnt-local: {_yaml_typst_scalar(city)}",
        f"abnt-ano: {_yaml_typst_scalar(year)}",
        'abnt-numeracao: "1"',
        'abnt-numeracao-secoes: "1.1"',
        "abnt-sem-quebra-secoes: true",
        'abnt-fonte: "Liberation Sans"',
        "format: abnt-typst",
    ]
    return "---\n" + "\n".join(metadata) + "\n---\n"


def _author_notes(project: dict[str, Any]) -> list[tuple[str, str]]:
    fields = project["fields"]
    course = _text(fields.get("course")).strip() or "Direito"
    institution = _text(fields.get("institution")).strip() or "instituição de ensino"
    note = f"Discente do curso de {course} da {institution}."
    result = [(author, note) for author in _authors(project)]
    teacher = _text(fields.get("teacher")).strip()
    if teacher:
        result.append((teacher, "Docente da disciplina."))
    return result


def _typst_author_pairs(project: dict[str, Any]) -> str:
    pairs = [
        f"({_typst_literal(name)}, [#text({_typst_literal(note)})])"
        for name, note in _author_notes(project)
    ]
    return "(" + ",\n  ".join(pairs) + ("," if len(pairs) == 1 else "") + ")"


def _case_header(project: dict[str, Any]) -> str:
    fields = project["fields"]
    title = _text(fields.get("title")).strip().upper()
    discipline = _text(fields.get("discipline"))
    institution = _text(fields.get("institution"))
    note = f"Relatório de case apresentado à disciplina {discipline} da {institution}."
    return "\n".join(
        [
            '#import "_extensions/abnt/tipos/caso.typ": *',
            "#caso-cabecalho(",
            f"  titulo: {_typst_literal(title)},",
            f"  nota-titulo: [#text({_typst_literal(note)})],",
            f"  autores: {_typst_author_pairs(project)},",
            ")",
        ]
    )


def _article_header(project: dict[str, Any]) -> str:
    fields = project["fields"]
    title = _text(fields.get("title")).strip().upper()
    subtitle = _text(fields.get("subtitle") or fields.get("subTitle")).strip()
    subtitle_value = f"[#text({_typst_literal(subtitle)})]" if subtitle else "none"
    parts = [
        '#import "_extensions/abnt/tipos/artigo.typ": *',
        "#artigo-cabecalho(",
        f"  titulo: {_typst_literal(title)},",
        f"  subtitulo: {subtitle_value},",
        f"  autores: {_typst_author_pairs(project)},",
        ")",
    ]
    abstract = _text(fields.get("abstract")).strip()
    keywords = _text(fields.get("keywords")).strip()
    if abstract or keywords:
        parts.extend(
            [
                "#artigo-resumo(",
                f"  palavras: [#text({_typst_literal(keywords)})],",
                ")[",
                f"  #text({_typst_literal(abstract)})" if abstract else "  []",
                "]",
            ]
        )
    return "\n".join(parts)


def _project_identification(project: dict[str, Any]) -> str:
    fields = project["fields"]
    authors = _authors(project)
    return "\n".join(
        [
            '#import "_extensions/abnt/tipos/projeto.typ": *',
            "#pagina-identificacao-projeto(",
            f"  instituicao: {_typst_literal(fields.get('institution', '') if fields.get('profile') == 'facsure' else '')},",
            f"  titulo: {_typst_literal(_text(fields.get('title')).strip().upper())},",
            f"  periodo: {_typst_literal(fields.get('classInfo', ''))},",
            f"  disciplina: {_typst_literal(fields.get('discipline', ''))},",
            f"  professor: {_typst_literal(fields.get('teacher', ''))},",
            f"  aluno: {_typst_literal(' e '.join(authors))},",
            ")",
        ]
    )


def _reference_items(project: dict[str, Any]) -> list[str]:
    sources = project.get("sources") if isinstance(project.get("sources"), list) else []
    references = [
        _text(source.get("reference")).strip()
        for source in sources
        if isinstance(source, dict) and _text(source.get("reference")).strip()
    ]
    return sorted(set(references), key=lambda item: item.casefold())


def _bibliography(project: dict[str, Any]) -> str:
    references = _reference_items(project)
    if not references:
        return ""
    entries = "\n".join(
        f"  ref-texto({_typst_literal(reference)}, [#text({_typst_literal(reference)})]),"
        for reference in references
    )
    return "\n".join(
        [
            "#abnt-bibliografia((",
            entries,
            "), ordenar: true)",
        ]
    )


def _section(title: str, value: Any, level: int = 1) -> str:
    content = _paragraphs(value)
    if not content:
        return ""
    return f"{'#' * level} {_markdown_text(title)}\n\n{content}"


def _case_possible_solutions(fields: dict[str, Any]) -> str:
    blocks = [_paragraphs(fields.get("decisionBasis"))]
    for marker, key, ending in (("a", "decisionA", ";"), ("b", "decisionB", ".")):
        content = _text(fields.get(key)).strip()
        if not content:
            continue
        content = re.sub(r"[.;?!]\s*$", "", content).rstrip() + ending
        rendered = _paragraphs(content)
        if rendered:
            indented = rendered.replace("\n", "\n   ")
            blocks.append(f"{marker}) \u2003{indented}")
    return "\n\n".join(block for block in blocks if block)


def _case_report(project: dict[str, Any]) -> str:
    fields = project["fields"]
    criteria = project.get("criteria") if isinstance(project.get("criteria"), list) else []
    criterion_text = []
    for item in criteria:
        if not isinstance(item, dict):
            continue
        term = _text(item.get("term")).strip()
        definition = _text(item.get("definition")).strip()
        basis = _text(item.get("basis")).strip()
        if not (term or definition or basis):
            continue
        sentence = f"{term}: {definition}" if term else definition
        if basis:
            sentence += f" Base normativa ou ética: {basis}"
        criterion_text.append(sentence.strip())
    sections = [
        _section("DESCRIÇÃO DO CASO", "\n\n".join(filter(None, [_text(fields.get("facts")), _text(fields.get("problem"))]))),
        "# IDENTIFICAÇÃO E ANÁLISE DO CASO",
        _case_possible_solutions(fields),
        "## Descrição dos argumentos",
        _section(_text(fields.get("thesisATitle")).strip() or "Argumento favorável à tese A", fields.get("thesisA"), 3),
        _section(_text(fields.get("thesisBTitle")).strip() or "Argumento favorável à tese B", fields.get("thesisB"), 3),
        _section("Descrição dos critérios e valores", "\n\n".join(criterion_text), 2),
    ]
    bibliography = _bibliography(project)
    return "\n\n".join(item for item in sections if item) + ("\n\n" + _raw_typst(bibliography) if bibliography else "")


def _paper_project(project: dict[str, Any]) -> str:
    fields = project["fields"]
    objective_parts = [
        _section("Objetivo Geral", fields.get("objectiveGeneral"), 2),
    ]
    objectives = [
        _text(fields.get(f"objective{number}")).strip()
        for number in range(1, 4)
        if _text(fields.get(f"objective{number}")).strip()
    ]
    if objectives:
        objective_parts.append("## Objetivos específicos\n\n" + "\n\n".join(f"{number}. {_markdown_text(text)}" for number, text in enumerate(objectives, 1)))
    methodology = "\n\n".join(
        item for item in [
            f"Autor de metodologia adotado: {_text(fields.get('methodAuthor'))}." if _text(fields.get("methodAuthor")).strip() else "",
            f"Natureza: {_text(fields.get('nature'))}." if _text(fields.get("nature")).strip() else "",
            f"Abordagem: {_text(fields.get('approach'))}." if _text(fields.get("approach")).strip() else "",
            f"Fins: {_text(fields.get('ends'))}." if _text(fields.get("ends")).strip() else "",
            f"Procedimentos: {_text(fields.get('procedure'))}." if _text(fields.get("procedure")).strip() else "",
            _text(fields.get("instruments")),
        ] if item
    )
    sections = [
        _section("TEMA", fields.get("area")),
        _section("TÍTULO E DELIMITAÇÃO", "\n\n".join(filter(None, [_text(fields.get("delimitation")), _text(fields.get("researchContext")), _text(fields.get("researchObject"))]))),
        _section("PROBLEMA", "\n\n".join(filter(None, [_text(fields.get("problemContext")), _text(fields.get("problem"))]))),
        _section("HIPÓTESE", fields.get("hypothesis")),
        _section("JUSTIFICATIVA", fields.get("justification")),
        "# OBJETIVOS\n\n" + "\n\n".join(item for item in objective_parts if item),
        _section("REFERENCIAL TEÓRICO", fields.get("theory")),
        _section("METODOLOGIA", methodology),
    ]
    body = "\n\n".join(item for item in sections if item)
    bibliography = _bibliography(project)
    return body + ("\n\n" + _raw_typst(bibliography) if bibliography else "")


def _paper_final(project: dict[str, Any]) -> str:
    fields = project["fields"]
    sections = [_section("INTRODUÇÃO", fields.get("introduction"))]
    development = fields.get("developmentSections") if isinstance(fields.get("developmentSections"), list) else []
    for index, item in enumerate(development):
        if not isinstance(item, dict):
            continue
        title = _text(item.get("title")).strip() or f"DESENVOLVIMENTO {index + 1}"
        sections.append(_section(title, item.get("content")))
    if _text(fields.get("aiNote")).strip():
        sections.append(_section("DECLARAÇÃO SOBRE USO DE IA", fields.get("aiNote")))
    sections.append(_section("CONCLUSÃO", fields.get("conclusion")))
    body = "\n\n".join(item for item in sections if item)
    bibliography = _bibliography(project)
    return body + ("\n\n" + _raw_typst(bibliography) if bibliography else "")


def build_quarto_source(project: dict[str, Any], document_kind: str) -> str:
    """Return a .qmd document using the bundled ABNT Quarto format."""
    if not isinstance(project, dict) or not isinstance(project.get("fields"), dict):
        raise QuartoDocumentError("Projeto inválido para exportação.")
    if document_kind not in _DOCUMENT_KINDS:
        raise QuartoDocumentError("Tipo de documento inválido.")
    expected_type = _DOCUMENT_KINDS[document_kind]
    if project.get("projectType") != expected_type:
        raise QuartoDocumentError("O tipo de documento não corresponde ao projeto.")

    front_matter = _metadata(project)
    if document_kind == "case_report":
        body = _raw_typst(_case_header(project)) + "\n" + _case_report(project)
    elif document_kind == "paper_project":
        body = _raw_typst(_project_identification(project)) + "\n" + _paper_project(project)
    else:
        body = _raw_typst(_article_header(project)) + "\n" + _paper_final(project)
    return front_matter + "\n" + body.strip() + "\n"


def render_document_pdf(project: dict[str, Any], document_kind: str) -> bytes:
    """Render an isolated QMD file with the local extension and return its PDF bytes."""
    qmd = build_quarto_source(project, document_kind)
    binary = os.environ.get("QUARTO_BINARY", "quarto")
    executable = shutil.which(binary)
    if not executable or not EXTENSION_DIR.is_dir():
        raise QuartoUnavailableError("O renderizador Quarto não está disponível.")
    if not _RENDER_SLOTS.acquire(blocking=False):
        raise QuartoBusyError("Há muitas renderizações em andamento.")

    try:
        with tempfile.TemporaryDirectory(prefix="assistente-quarto-") as temp_name:
            workspace = Path(temp_name)
            (workspace / "_extensions").mkdir()
            shutil.copytree(EXTENSION_DIR, workspace / "_extensions" / "abnt")
            source_path = workspace / "document.qmd"
            output_path = workspace / "document.pdf"
            source_path.write_text(qmd, encoding="utf-8")
            home_path = workspace / "home"
            home_path.mkdir(mode=0o700)
            env = {
                "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                "HOME": str(home_path),
                "TMPDIR": str(workspace),
                "TMP": str(workspace),
                "TEMP": str(workspace),
                "LANG": os.environ.get("LANG", "C.UTF-8"),
                "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            }
            try:
                completed = subprocess.run(
                    [executable, "render", source_path.name, "--output", output_path.name],
                    cwd=workspace,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=RENDER_TIMEOUT_SECONDS,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise QuartoRenderError("A renderização excedeu o tempo limite.") from error
            except OSError as error:
                raise QuartoUnavailableError("Não foi possível iniciar o Quarto.") from error
            if completed.returncode != 0 or not output_path.is_file():
                raise QuartoRenderError("O Quarto não conseguiu renderizar este documento.")
            if output_path.stat().st_size > MAX_PDF_BYTES:
                raise QuartoRenderError("O PDF gerado excedeu o limite de tamanho.")
            pdf = output_path.read_bytes()
            if not pdf.startswith(b"%PDF-"):
                raise QuartoRenderError("O renderizador não retornou um PDF válido.")
            return pdf
    finally:
        _RENDER_SLOTS.release()
