import os
from uuid import uuid4

from flask import Blueprint, abort, jsonify, request

from ..auth import current_account_id, login_required, require_csrf
from ..domain.case_rubric import AI_CASE_CHECKLISTS
from ..domain.legal_recommendations import normalize_request
from ..services.assistant import ALLOWED_FIELDS, build_jev_validation, build_messages, validate_result
from ..services.legal_recommendations import recommend
from ..services.providers import DeepSeekClient, GeminiClient, JevClient, ProviderError, load_secret
from ..services.ai_support import JEV_SUGGESTION_CRITERIA, PROJECT_AI_ACTIONS, SUGGESTION_ACTIONS, normalize_request_id
from ..services.ai_workflows import (
    action_context,
    action_messages,
    jev_questions,
    jev_state,
    legacy_state,
    normalize_jev_result,
    normalized_jev_suggestion,
    validate_action_result,
)
from ..store.accounts import get_account
from ..store.ai_usage import UsageError, finish_usage, record_provider_usage, refund_usage, reserve_usage
from ..store.projects import get_project
from ..store.sources import create_source, list_sources
from ..services.research import ResearchUnavailable, entries_by_ids, search_catalog


ai_bp = Blueprint("ai", __name__)


def _ai_account():
    account = get_account(current_account_id())
    if account is None:
        abort(401)
    if not account["terms_accepted"]:
        return None, (jsonify({"error": "terms_required", "message": "Aceite os termos antes de usar a assistência."}), 403)
    if not account["ai_consent"]:
        return None, (jsonify({"error": "ai_consent_required", "message": "Autorize o uso de IA no perfil antes de pedir assistência."}), 403)
    return account, None


def _request_id(body: dict) -> str:
    # SEMPRE gerar server-side; ignorar cliente para evitar colisão/DoS
    normalized = normalize_request_id(str(uuid4()))
    if normalized is None:
        raise ValueError("request_id inválido")
    return normalized


def _deepseek_for_action():
    return DeepSeekClient(
        load_secret("DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY_FILE", "/run/secrets/deepseek_api_key"),
        api_url=os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        timeout=int(os.environ.get("DEEPSEEK_TIMEOUT", "30")),
    )


def _gemini_for_action():
    return GeminiClient(
        load_secret("GEMINI_API_KEY", "GEMINI_API_KEY_FILE", "/run/secrets/gemini_api_key"),
        api_url=os.environ.get("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"),
        model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        timeout=int(os.environ.get("GEMINI_TIMEOUT", "30")),
    )


_FALLBACK_ERROR_CODES = {
    "provider_busy",
    "provider_unreachable",
    "provider_auth",
    "provider_quota",
    "secret_unavailable",
    "secret_invalid",
    "invalid_response",
    "response_too_large",
}


def _fallback_allowed(error):
    return isinstance(error, ProviderError) and error.code in _FALLBACK_ERROR_CODES


def _complete_with_fallback(messages, validator, max_tokens):
    first_error = None
    try:
        client = _deepseek_for_action()
        response = client.complete_json(messages, max_tokens=max_tokens)
        validator(response.get("result"))
        response["provider"] = "deepseek"
        return response
    except (ProviderError, OSError) as deepseek_error:
        if isinstance(deepseek_error, ProviderError) and not _fallback_allowed(deepseek_error):
            raise
        first_error = deepseek_error if isinstance(deepseek_error, ProviderError) else ProviderError("provider_unreachable", "Não foi possível conectar ao DeepSeek.", 503, retryable=True)
    except (ValueError, TypeError) as deepseek_error:
        first_error = ProviderError("invalid_response", "A resposta DeepSeek não respeitou o contrato estruturado.", 502, retryable=True)
    try:
        client = _gemini_for_action()
        response = client.complete_json(messages, max_tokens=max_tokens)
        validator(response.get("result"))
        response["provider"] = "gemini"
        response["fallback_reason"] = first_error.code if first_error else "invalid_response"
        return response
    except (ValueError, TypeError) as error:
        raise ProviderError("invalid_response", "DeepSeek e Gemini não respeitaram o contrato estruturado.", 502, retryable=True) from error
    except ProviderError as error:
        raise error from first_error


def _complete_action(context):
    return _complete_with_fallback(
        action_messages(context),
        lambda result: validate_action_result(result, context),
        int(os.environ.get("PROJECT_AI_MAX_OUTPUT_TOKENS", "2200")),
    )


def _jev_analysis(project, section=None):
    key = load_secret("TYPESAFE_API_KEY", "TYPESAFE_API_KEY_FILE", "/run/secrets/typesafe_api_key")
    client = JevClient(
        key,
        api_url=os.environ.get("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone"),
        model=os.environ.get("TYPESAFE_MODEL", "jev-latest"),
        timeout=int(os.environ.get("JEV_TIMEOUT", "60")),
    )
    raw = client.score(jev_state(project), jev_questions(section))
    return normalize_jev_result(raw, section), raw


@ai_bp.post("/projects/<project_id>/ai/action")
@login_required
@require_csrf
def action(project_id):
    account, error_response = _ai_account()
    if error_response:
        return error_response
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)
    body = request.get_json(silent=True) or {}
    action_name = body.get("action")
    if action_name not in PROJECT_AI_ACTIONS or action_name == "research":
        return jsonify({"error": "invalid_ai_action", "message": "Ação de assistência inválida."}), 400
    if action_name == "debate_coach" and project.get("project_type") != "case":
        return jsonify({"error": "invalid_ai_action", "message": "O apoio ao debate só existe no Case."}), 400
    if action_name == "review" and body.get("field_id") not in ALLOWED_FIELDS:
        return jsonify({"error": "invalid_ai_request", "message": "Campo não permitido."}), 400
    try:
        request_id = _request_id(body)
        if body.get("project_revision") is not None and int(body["project_revision"]) != int(project["revision"]):
            return jsonify({"error": "stale_project_revision", "revision": project["revision"]}), 409
        context = action_context(project, action_name, body, sources=list_sources(current_account_id()))
        reserve_usage(current_account_id(), project_id, request_id, action_name)
        provider_response = _complete_action(context)
        result = validate_action_result(provider_response.get("result"), context)
        result.update({"action": action_name, "model": provider_response.get("model", ""), "provider": provider_response.get("provider", "deepseek")})
        if provider_response.get("fallback_reason"):
            result["fallback_reason"] = provider_response["fallback_reason"]
        record_provider_usage(request_id, result["provider"], f"assistant:{action_name}", result["model"] or "unknown", "complete", provider_response.get("usage"))
        if action_name in SUGGESTION_ACTIONS and result["suggestions"]:
            try:
                jev_key = load_secret("TYPESAFE_API_KEY", "TYPESAFE_API_KEY_FILE", "/run/secrets/typesafe_api_key")
                jev_client = JevClient(jev_key, api_url=os.environ.get("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone"), model=os.environ.get("TYPESAFE_MODEL", "jev-latest"), timeout=int(os.environ.get("JEV_TIMEOUT", "60")))
                suggestion_state = legacy_state(project, sources=list_sources(current_account_id()))
                suggestion_state["action"] = action_name
                suggestion_state["suggestion"] = result["answer"]
                jev_raw = jev_client.score(suggestion_state, {
                    criterion_id: {"type": "score", "instructions": title, "criteria": ["0", "1", "2", "3"]}
                    for criterion_id, title in JEV_SUGGESTION_CRITERIA[action_name]
                })
                result["validation"] = normalized_jev_suggestion(action_name, context, jev_raw)
                record_provider_usage(request_id, "jev", f"suggestion:{action_name}", jev_raw.get("model", "jev-latest"), "complete", jev_raw.get("usage"))
            except ProviderError:
                result["validation"] = {"status": "nao_avaliado", "observations": ["O JEV não está disponível agora; confira a sugestão manualmente."], "proposal_present": bool(context.get("assignment_prompt"))}
        finish_usage(request_id)
        return jsonify({"ok": True, "request_id": request_id, "response": result})
    except UsageError as error:
        return jsonify({"error": error.code, "message": str(error)}), error.status
    except (ValueError, TypeError) as error:
        try:
            refund_usage(request_id)
        except Exception:
            pass
        return jsonify({"error": "invalid_ai_request", "message": str(error)}), 400
    except ProviderError as error:
        try:
            refund_usage(request_id)
        except Exception:
            pass
        return jsonify({"error": error.code, "message": str(error)}), error.status


@ai_bp.post("/projects/<project_id>/ai/jev-section")
@login_required
@require_csrf
def jev_section(project_id):
    account, error_response = _ai_account()
    if error_response:
        return error_response
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)
    body = request.get_json(silent=True) or {}
    section = body.get("section")
    try:
        request_id = _request_id(body)
        if section not in {"case_description", "case_decisions", "thesis_a", "thesis_b", "criteria_and_values"}:
            raise ValueError("etapa JEV inválida")
        reserve_usage(current_account_id(), project_id, request_id, f"jev:{section}")
        analysis, raw = _jev_analysis(project, section)
        record_provider_usage(request_id, "jev", f"case-section:{section}", analysis["model"], "complete", raw.get("usage"))
        finish_usage(request_id)
        return jsonify({"ok": True, "request_id": request_id, "analysis": analysis})
    except UsageError as error:
        return jsonify({"error": error.code, "message": str(error)}), error.status
    except (ValueError, TypeError) as error:
        try:
            refund_usage(request_id)
        except Exception:
            pass
        return jsonify({"error": "invalid_ai_request", "message": str(error)}), 400
    except ProviderError as error:
        try:
            refund_usage(request_id)
        except Exception:
            pass
        return jsonify({"error": error.code, "message": str(error)}), error.status


@ai_bp.post("/projects/<project_id>/ai/jev-report")
@login_required
@require_csrf
def jev_report(project_id):
    account, error_response = _ai_account()
    if error_response:
        return error_response
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)
    body = request.get_json(silent=True) or {}
    try:
        request_id = _request_id(body)
        reserve_usage(current_account_id(), project_id, request_id, "jev:case_report")
        analysis, raw = _jev_analysis(project)
        record_provider_usage(request_id, "jev", "case-report", analysis["model"], "complete", raw.get("usage"))
        finish_usage(request_id)
        return jsonify({"ok": True, "request_id": request_id, "analysis": analysis})
    except UsageError as error:
        return jsonify({"error": error.code, "message": str(error)}), error.status
    except (ValueError, TypeError) as error:
        try:
            refund_usage(request_id)
        except Exception:
            pass
        return jsonify({"error": "invalid_ai_request", "message": str(error)}), 400
    except ProviderError as error:
        try:
            refund_usage(request_id)
        except Exception:
            pass
        return jsonify({"error": error.code, "message": str(error)}), error.status


@ai_bp.post("/projects/<project_id>/ai/jev-explanation")
@login_required
@require_csrf
def jev_explanation(project_id):
    account, error_response = _ai_account()
    if error_response:
        return error_response
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)
    body = request.get_json(silent=True) or {}
    criterion = body.get("criterion")
    field_map = {
        "case_description": ["assignment_prompt", "facts", "problem"],
        "legal_writing_foundation": ["assignment_prompt", "facts", "problem", "thesis_a", "thesis_b"],
        "criteria_and_values": ["assignment_prompt", "thesis_a", "thesis_b", "criteria"],
        "grade_range": ["assignment_prompt", "facts", "problem", "thesis_a", "thesis_b"],
    }
    checklist_ids = {check_id for definition in AI_CASE_CHECKLISTS.values() for check_id in definition["checks"]}
    if not isinstance(criterion, str) or (criterion not in field_map and criterion not in checklist_ids):
        return jsonify({"error": "invalid_criterion", "message": "Critério JEV inválido."}), 400
    try:
        request_id = _request_id(body)
        context = action_context(
            project,
            "review",
            {
                "field_id": criterion,
                "context_fields": field_map.get(criterion, ["assignment_prompt", "facts", "problem", "thesis_a", "thesis_b", "criteria"]),
                "instruction": "Explique esta observação JEV com base na evidência enviada, indique o que o estudante deve conferir e não transforme a estimativa em nota oficial.",
            },
            sources=list_sources(current_account_id()),
        )
        context["jev_result"] = body.get("jev_result") if isinstance(body.get("jev_result"), dict) else {}
        reserve_usage(current_account_id(), project_id, request_id, f"jev-explanation:{criterion}")
        provider_response = _complete_action(context)
        result = validate_action_result(provider_response.get("result"), context)
        explanation = {
            "interpretation": result["answer"],
            "evidence": [],
            "next_steps": [item["text"] for item in result.get("suggestions", [])][:2],
            "model": provider_response.get("model", ""),
            "provider": provider_response.get("provider", "deepseek"),
        }
        record_provider_usage(request_id, explanation["provider"], f"jev-explanation:{criterion}", explanation["model"] or "unknown", "complete", provider_response.get("usage"))
        finish_usage(request_id)
        return jsonify({"ok": True, "request_id": request_id, "explanation": explanation})
    except UsageError as error:
        return jsonify({"error": error.code, "message": str(error)}), error.status
    except (ValueError, TypeError) as error:
        try:
            refund_usage(request_id)
        except Exception:
            pass
        return jsonify({"error": "invalid_ai_request", "message": str(error)}), 400
    except ProviderError as error:
        try:
            refund_usage(request_id)
        except Exception:
            pass
        return jsonify({"error": error.code, "message": str(error)}), error.status


@ai_bp.post("/projects/<project_id>/ai/review")
@login_required
@require_csrf
def review(project_id):
    account = get_account(current_account_id())
    if account is None:
        abort(401)
    if not account["ai_consent"]:
        return jsonify({"error": "ai_consent_required", "message": "Autorize o uso de IA no perfil antes de pedir assistência."}), 403
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)
    body = request.get_json(silent=True) or {}
    field_id = body.get("field_id")
    instruction = body.get("instruction", "")
    if field_id not in ALLOWED_FIELDS or not isinstance(instruction, str) or not instruction.strip():
        return jsonify({"error": "invalid_ai_request"}), 400
    try:
        response = _complete_with_fallback(
            build_messages(project, field_id, instruction),
            lambda result: validate_result(result),
            int(os.environ.get("PROJECT_AI_MAX_OUTPUT_TOKENS", "1400")),
        )
        result = validate_result(response["result"])
    except ProviderError as error:
        return jsonify({"error": error.code, "message": str(error)}), error.status
    except (KeyError, ValueError):
        return jsonify({"error": "ai_invalid_response", "message": "A assistência retornou uma resposta inesperada."}), 502
    return jsonify({"ok": True, "field_id": field_id, **result})


@ai_bp.post("/projects/<project_id>/ai/validate")
@login_required
@require_csrf
def validate(project_id):
    account = get_account(current_account_id())
    if account is None:
        abort(401)
    if not account["ai_consent"]:
        return jsonify({"error": "ai_consent_required", "message": "Autorize o uso de IA no perfil antes de pedir validação."}), 403
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)
    body = request.get_json(silent=True) or {}
    try:
        state, questions = build_jev_validation(project, body.get("field_id", "problem"))
        key = load_secret("TYPESAFE_API_KEY", "TYPESAFE_API_KEY_FILE", "/run/secrets/typesafe_api_key")
        client = JevClient(key, api_url=os.environ.get("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone"), model=os.environ.get("TYPESAFE_MODEL", "jev-latest"), timeout=int(os.environ.get("JEV_TIMEOUT", "60")))
        result = client.score(state, questions)
    except ProviderError as error:
        return jsonify({"error": error.code, "message": str(error)}), error.status
    except ValueError:
        return jsonify({"error": "invalid_ai_request"}), 400
    return jsonify({"ok": True, **result})


@ai_bp.post("/projects/<project_id>/ai/legal-recommendations")
@login_required
@require_csrf
def legal_recommendations(project_id):
    account = get_account(current_account_id())
    if account is None:
        abort(401)
    if not account["terms_accepted"]:
        return jsonify({"error": "terms_required", "message": "Aceite os termos antes de pedir recomendações."}), 403
    if not account["ai_consent"]:
        return jsonify({"error": "ai_consent_required", "message": "Autorize o uso de IA no perfil antes de pedir recomendações."}), 403
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)
    try:
        payload = normalize_request(request.get_json(silent=True) or {})
    except ValueError as error:
        return jsonify({"error": "invalid_ai_request", "message": str(error)}), 400
    if payload["project_revision"] != project["revision"]:
        return jsonify({"error": "stale_project_revision", "revision": project["revision"]}), 409
    try:
        if payload["catalog_source_ids"]:
            candidates = entries_by_ids(payload["catalog_source_ids"])
            if len(candidates) != len(payload["catalog_source_ids"]):
                return jsonify({"error": "invalid_catalog_source", "message": "Uma fonte não pertence ao catálogo disponível."}), 400
        else:
            query = " ".join([payload["problem_question"], *payload["keywords"]]).strip()
            candidates = []
            for kind in ("legislation", "case-law", "book"):
                candidates.extend(search_catalog(query, kind=kind, limit=8)["entries"])
    except ResearchUnavailable:
        return jsonify({"error": "catalog_unavailable", "message": "O catálogo jurídico não está disponível no momento."}), 503
    if not candidates:
        return jsonify({
            "ok": True,
            "request_id": payload["request_id"],
            "provider": {"name": "none", "model": "", "fallback_used": False, "fallback_reason": None},
            "recommendations": {"law": [], "jurisprudence": [], "doctrine": []},
            "coverage": {"candidate_count": 0, "by_kind": {"legislation": 0, "case-law": 0, "book": 0}, "scope": "catálogo jurídico local; pista inicial"},
            "warnings": ["Nenhum candidato foi encontrado neste recorte do catálogo."],
        })
    try:
        reserve_usage(current_account_id(), project_id, payload["request_id"], "legal_recommendations")
    except UsageError as error:
        return jsonify({"error": error.code, "message": str(error)}), error.status

    def record(provider, model, status, usage):
        record_provider_usage(payload["request_id"], provider, "legal_recommendations", model or "unknown", status, usage)

    try:
        result = recommend(
            payload,
            project,
            candidates,
            deepseek_factory=lambda: DeepSeekClient(
                load_secret("DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY_FILE", "/run/secrets/deepseek_api_key"),
                api_url=os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                timeout=int(os.environ.get("DEEPSEEK_TIMEOUT", "30")),
            ),
            gemini_factory=lambda: GeminiClient(
                load_secret("GEMINI_API_KEY", "GEMINI_API_KEY_FILE", "/run/secrets/gemini_api_key"),
                api_url=os.environ.get("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"),
                model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                timeout=int(os.environ.get("GEMINI_TIMEOUT", "30")),
            ),
            record_attempt=record,
        )
        finish_usage(payload["request_id"])
        return jsonify({"ok": True, "request_id": payload["request_id"], **result})
    except ProviderError as error:
        refund_usage(payload["request_id"])
        return jsonify({"error": error.code, "message": str(error)}), error.status


@ai_bp.post("/projects/<project_id>/ai/legal-recommendations/attach")
@login_required
@require_csrf
def attach_catalog_source(project_id):
    if get_project(current_account_id(), project_id) is None:
        abort(404)
    body = request.get_json(silent=True) or {}
    source_id = body.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        return jsonify({"error": "invalid_catalog_source"}), 400
    try:
        entries = entries_by_ids([source_id])
    except ResearchUnavailable:
        return jsonify({"error": "catalog_unavailable", "message": "O catálogo jurídico não está disponível no momento."}), 503
    if not entries:
        return jsonify({"error": "invalid_catalog_source"}), 404
    entry = entries[0]
    kind = {"case-law": "case_law", "legislation": "legislation", "book": "book"}.get(entry.get("kind"), "other")
    reference = entry.get("reference") or entry.get("source") or ""
    notes = "Fonte adicionada a partir do catálogo jurídico. Confira os dados antes de citar."
    if entry.get("link"):
        notes += " Origem: " + entry["link"]
    personal_id = create_source(current_account_id(), entry.get("title", "Fonte jurídica"), entry.get("author", ""), kind, reference, notes)
    return jsonify({"ok": True, "source_id": personal_id, "title": entry.get("title", "Fonte jurídica"), "author": entry.get("author", ""), "reference": reference})
