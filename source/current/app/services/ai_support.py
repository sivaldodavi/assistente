"""Suporte independente às ações de IA e ao contrato IA -> JEV.

Este módulo não grava conteúdo de projeto nem escolhe fontes por heurística local.
A validação de pertinência é sempre delegada ao provedor JEV recebido pelo servidor.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit


PROJECT_AI_ACTIONS = {
    "review",
    "chat",
    "checklist",
    "proposal_chat",
    "suggest_problem",
    "suggest_theses",
    "case_structure",
    "research",
    "review_criteria",
    "review_references",
    "review_development",
    "debate_coach",
}

SUGGESTION_ACTIONS = {
    "proposal_chat",
    "suggest_problem",
    "suggest_theses",
    "case_structure",
    "review_criteria",
    "review_references",
    "review_development",
}

REQUEST_ID_ACTIONS = SUGGESTION_ACTIONS | {"research", "debate_coach"}

# These are the IDs used by the current frontend.  The aliases below are kept
# because imported/older paper payloads may use paperProblem/paperHypothesis.
_CASE_FIELDS = {
    "proposal_chat": ("problem", "decision_basis", "decision_a", "decision_b", "thesis_a_title", "thesis_a", "thesis_b_title", "thesis_b"),
    "suggest_problem": ("problem",),
    "suggest_theses": ("thesis_a_title", "thesis_a", "thesis_b_title", "thesis_b"),
    "case_structure": ("facts", "problem", "decision_basis", "decision_a", "decision_b"),
    "review_criteria": ("criteria",),
}
_PAPER_FIELDS = {
    "proposal_chat": (
        "problem", "problem_context", "hypothesis", "research_object",
        "objective_general", "introduction", "conclusion",
    ),
    "suggest_problem": ("problem", "problem_context", "research_object"),
    "suggest_theses": ("hypothesis", "objective_general"),
    "case_structure": (
        "research_object", "problem", "problem_context", "hypothesis",
        "objective_general",
    ),
    "review_criteria": ("criteria",),
}

_UNSAFE_SUGGESTION_FIELD_IDS = {
    "author", "institution", "course", "discipline", "teacher", "classInfo",
    "deliveryDate", "city", "year", "profile", "paperKind", "sources", "references",
    "email", "account", "account_id", "project_id", "owner", "session", "csrf_token",
}
_SAFE_DIRECT_FIELD = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


# Criteria are deliberately different per flow. JEV receives the proposal and
# suggestion, never only the candidate text, and its observation is requested
# as textual evidence rather than synthesized locally.
JEV_SUGGESTION_CRITERIA = {
    "proposal_chat": (
        ("proposal_fit", "A resposta atende à proposta do professor e ao pedido do aluno."),
        ("academic_direction", "A direção sugerida é acadêmica, delimitada e executável."),
        ("authorship", "A resposta preserva a autoria do aluno e não redige o trabalho inteiro."),
    ),
    "suggest_problem": (
        ("proposal_fit", "A pergunta-problema responde ao recorte e à proposta do professor."),
        ("clarity", "A pergunta é clara, investigável e não se resolve apenas com sim ou não."),
        ("scope", "O recorte é viável e não promete uma conclusão sem pesquisa."),
    ),
    "suggest_theses": (
        ("proposal_fit", "As teses são pertinentes à proposta e ao problema fornecido."),
        ("argumentability", "As teses admitem argumentos jurídicos ou acadêmicos verificáveis."),
        ("balance", "As alternativas são distinguíveis e apresentadas sem impor uma resposta."),
    ),
    "case_structure": (
        ("proposal_fit", "A estrutura atende à proposta e ao tipo de projeto informado."),
        ("completeness", "Os campos sugeridos cobrem a direção necessária sem inventar fatos."),
        ("coherence", "A sequência sugerida é coerente com a pergunta e com as decisões possíveis."),
    ),
    "review_criteria": (
        ("proposal_fit", "A revisão dos critérios é pertinente à proposta do professor."),
        ("traceability", "Cada observação pode ser conferida no material fornecido."),
        ("actionability", "As sugestões orientam uma revisão sem substituir a autoria."),
    ),
    "review_references": (
        ("proposal_fit", "A orientação de referências é pertinente à proposta e ao tema."),
        ("traceability", "A revisão não inventa obra, lei, artigo ou processo."),
        ("actionability", "A indicação ajuda o aluno a conferir fontes reais por conta própria."),
    ),
    "review_development": (
        ("proposal_fit", "A revisão do desenvolvimento é pertinente à proposta do professor."),
        ("coherence", "As observações conectam desenvolvimento, problema e argumentos."),
        ("authorship", "A resposta orienta a revisão sem produzir o trabalho completo."),
    ),
}


@dataclass(frozen=True)
class ValidationResult:
    """Resultado estruturado derivado exclusivamente do retorno validado do JEV."""

    status: str
    observations: list[str]
    proposal_present: bool

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "observations": list(self.observations),
            "proposal_present": self.proposal_present,
        }


def is_new_action(action: object) -> bool:
    return isinstance(action, str) and action in SUGGESTION_ACTIONS


def suggestion_field_ids(
    action: str,
    project_type: str = "case",
    project_context: dict | None = None,
    *,
    source_ids: object = None,
    development_ids: object = None,
    criterion_ids: object = None,
) -> tuple[str, ...]:
    """Return only IDs that the actual project/frontend can address.

    ``project_context`` is the saved field map.  When present, aliases are
    resolved by retaining the ID that really exists (for example
    ``paperProblem`` instead of inventing ``problem``).  Dynamic forms such as
    sources/development/criteria are returned only with their saved IDs.
    """
    if action not in SUGGESTION_ACTIONS:
        return ()
    project_context = project_context if isinstance(project_context, dict) else None
    candidates = (_PAPER_FIELDS if project_type == "paper" else _CASE_FIELDS).get(action, ())
    if action == "review_references":
        values = source_ids if isinstance(source_ids, (list, tuple, set)) else ()
        result = tuple(
            f"source:{value}" for value in values
            if isinstance(value, str) and value and ":" not in value
        )
    elif action == "review_development":
        values = development_ids if isinstance(development_ids, (list, tuple, set)) else ()
        result = tuple(
            field_id
            for value in values
            if isinstance(value, str) and value and ":" not in value
            for field_id in (f"development:{value}", f"developmentText:{value}")
        )
    elif action == "review_criteria":
        values = criterion_ids if isinstance(criterion_ids, (list, tuple, set)) else ()
        result = tuple(
            f"criterion:{value}:{property_name}"
            for value in values
            if isinstance(value, str) and value and ":" not in value
            for property_name in ("term", "definition", "basis")
        )
    elif project_context is None:
        result = tuple(candidates)
    else:
        result = tuple(field_id for field_id in candidates if field_id in project_context)
    return tuple(field_id for field_id in result if field_id not in _UNSAFE_SUGGESTION_FIELD_IDS)


def normalize_request_id(value: object) -> str | None:
    """Aceita somente UUID textual para idempotência de uma ação IA."""
    if not isinstance(value, str):
        return None
    import uuid

    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None
    return str(parsed)


def validate_suggestion_items(
    action: str,
    suggestions: object,
    *,
    project_type: str = "case",
    project_context: dict | None = None,
    source_ids: object = None,
    development_ids: object = None,
    criterion_ids: object = None,
) -> list[dict[str, str]]:
    if not isinstance(suggestions, list) or len(suggestions) > 20:
        raise ValueError("suggestions inválidas")
    allowed = set(
        suggestion_field_ids(
            action,
            project_type,
            project_context,
            source_ids=source_ids,
            development_ids=development_ids,
            criterion_ids=criterion_ids,
        )
    )
    result = []
    seen = set()
    for item in suggestions:
        if not isinstance(item, dict) or set(item) != {"field_id", "text"}:
            raise ValueError("suggestion inválida")
        field_id = item["field_id"]
        text = item["text"]
        if (
            not isinstance(field_id, str)
            or field_id not in allowed
            or field_id in seen
            or field_id in _UNSAFE_SUGGESTION_FIELD_IDS
            or not isinstance(text, str)
            or not text.strip()
            or len(text) > 2000
        ):
            raise ValueError("suggestion inválida")
        if ":" not in field_id and not _SAFE_DIRECT_FIELD.fullmatch(field_id):
            raise ValueError("suggestion inválida")
        seen.add(field_id)
        result.append({"field_id": field_id, "text": text.strip()})
    return result


def proposal_text(context: dict) -> str:
    value = context.get("assignment_prompt", "")
    return value.strip() if isinstance(value, str) else ""


def suggestion_validation_from_jev(
    action: str, context: dict, answers: dict
) -> ValidationResult:
    """Converte respostas score reais do JEV em status de UX.

    Não cria evidência local: somente observações textuais retornadas pelo JEV
    são expostas. A ausência de proposta impede o rótulo ``adequado`` mesmo
    quando clareza foi avaliada.
    """
    criteria = JEV_SUGGESTION_CRITERIA.get(action)
    if not criteria or not isinstance(answers, dict):
        raise ValueError("respostas JEV ausentes")
    observations = []
    scores = []
    for criterion_id, _title in criteria:
        answer = answers.get(criterion_id)
        if not isinstance(answer, dict):
            raise ValueError("critério JEV ausente")
        score = answer.get("score")
        confidence = answer.get("confidence")
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0 <= score <= 3
            or isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
        ):
            raise ValueError("score JEV inválido")
        scores.append(score)
        observation = answer.get("observation")
        if isinstance(observation, str) and observation.strip():
            observations.append(observation.strip())
        else:
            observations.append(
                f"O JEV não retornou observação textual para o critério {criterion_id}; "
                "confira a evidência no texto antes de aplicar a sugestão."
            )
    proposal_present = bool(proposal_text(context))
    if not proposal_present:
        observations.append(
            "A proposta do professor não foi fornecida. Esclareça a atividade para avaliar adequação."
        )
        status = "nao_avaliado"
    else:
        status = "adequado" if min(scores) >= 2 else "revisar"
    return ValidationResult(status, observations, proposal_present)


def validate_safe_web_request(value: object) -> dict | None:
    """Valida uma capacidade web opcional sem aceitar URL arbitrária."""
    if value in (None, False):
        return None
    if value is True:
        raise ValueError("a busca web exige backend permitido")
    if not isinstance(value, dict) or value.get("enabled") is not True:
        raise ValueError("configuração de busca web inválida")
    query = value.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("consulta web inválida")
    domains = value.get("allowed_domains", [])
    if not isinstance(domains, list) or not domains or any(
        not isinstance(domain, str) or not domain.strip() for domain in domains
    ):
        raise ValueError("domínios web permitidos ausentes")
    normalized = []
    for domain in domains:
        hostname = domain.strip().casefold().rstrip(".")
        if "/" in hostname or ":" in hostname or "@" in hostname:
            raise ValueError("domínio web inválido")
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if address is not None and (
            address.is_private or address.is_loopback or address.is_link_local
        ):
            raise ValueError("domínio web privado")
        normalized.append(hostname)
    return {"query": query.strip(), "allowed_domains": normalized}


def validate_backend_url(url: object, allowed_domains: list[str]) -> str:
    """Confere URL retornada por backend: HTTPS, host permitido e não privado."""
    if not isinstance(url, str):
        raise ValueError("URL web inválida")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL web insegura")
    hostname = parsed.hostname.casefold().rstrip(".")
    if not any(hostname == domain or hostname.endswith("." + domain) for domain in allowed_domains):
        raise ValueError("URL fora da lista permitida")
    try:
        addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise ValueError("host web indisponível") from error
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("URL aponta para rede privada")
    return url


def research_entries_as_references(entries: object) -> list[dict]:
    """Conserva somente metadados e IDs retornados pelo catálogo local."""
    if not isinstance(entries, list):
        raise ValueError("catálogo inválido")
    references = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise ValueError("entrada de catálogo inválida")
        reference = {
            key: entry[key]
            for key in ("id", "kind", "title", "reference", "author", "abstract", "source_year", "source")
            if key in entry and entry[key] is not None
        }
        references.append(reference)
    return references
