import http.client
import io
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

import server


def project(title):
    return {
        "version": 2,
        "projectType": "case",
        "fields": {
            "title": title,
            "author": "Nome que não deve ser enviado",
            "assignmentPrompt": "Proposta do professor para orientar o trabalho.",
            "originalCasePrompt": "Enunciado original opcional.",
            "facts": "Fatos relevantes do caso para contextualizar a questão.",
            "problem": "Qual solução jurídica é adequada diante desses fatos?",
            "decisionBasis": "Base conceitual do caso.",
            "thesisATitle": "Tese A",
            "thesisA": "Argumentação da tese A com fatos, regra e conclusão. " * 4,
            "thesisBTitle": "Tese B",
            "thesisB": "Argumentação da tese B com fatos, regra e conclusão. " * 4,
        },
        "sources": [],
        "criteria": [],
        "checks": {},
        "currentStep": 0,
        "finalized": False,
    }


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.previous_store = server.STORE
        cls.previous_cookie_secure = server.COOKIE_SECURE
        cls.previous_public_dir = server.PUBLIC_DIR
        server.COOKIE_SECURE = True
        server.STORE = server.Store(Path(cls.temp_dir.name) / "api.sqlite3")
        server.PUBLIC_DIR = Path(__file__).resolve().parents[1] / "public"
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.address = cls.httpd.server_address

    def setUp(self):
        self.code_a, self.code_b = server.STORE.issue_batch(2)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()
        server.STORE = cls.previous_store
        server.COOKIE_SECURE = cls.previous_cookie_secure
        server.PUBLIC_DIR = cls.previous_public_dir
        cls.temp_dir.cleanup()

    def request(self, method, path, payload=None, cookie=None):
        connection = http.client.HTTPConnection(*self.address)
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if cookie:
            headers["Cookie"] = cookie
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        data = response.read()
        try:
            result = json.loads(data) if data else None
        except json.JSONDecodeError:
            result = data
        set_cookie = response.getheader("Set-Cookie")
        status = response.status
        connection.close()
        return status, result, set_cookie

    def login(self, code):
        status, result, set_cookie = self.request("POST", "/api/login", {"code": code})
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("SameSite=Strict", set_cookie)
        self.assertIn("Secure", set_cookie)
        return set_cookie.split(";", 1)[0], result

    @staticmethod
    def jev_response():
        return {
            "model": "jev-test",
            "answers": {
                question_id: {
                    "type": "score",
                    "score": 2.25,
                    "confidence": 0.8,
                    "probabilities": {"0": 0.05, "1": 0.15, "2": 0.4, "3": 0.4},
                }
                for question_id in [*server.AI_CASE_RUBRIC, "grade_range"]
            },
            "usage": {"input_tokens": 420, "output_tokens": 0},
        }

    @classmethod
    def jev_analysis(cls):
        criteria = [
            {
                "id": question_id,
                "title": definition["title"],
                "max_points": definition["max_points"],
                "score": 2.25,
                "confidence": 0.8,
                "probabilities": [0.05, 0.15, 0.4, 0.4],
            }
            for question_id, definition in server.AI_CASE_RUBRIC.items()
        ]
        return {
            "model": "jev-test",
            "input_tokens": 420,
            "criteria": criteria,
            "expected_points": 1.75,
            "assessable_points": 3.5,
            "grade_range": {
                "title": server.AI_CASE_GRADE_QUESTION["title"],
                "score": 2,
                "confidence": 0.8,
                "probabilities": [0.05, 0.15, 0.4, 0.4],
            },
            "probability_threshold": 0.6,
            "unassessed_points": 0.5,
        }

    @staticmethod
    def deepseek_response():
        return {
            "model": "deepseek-flash-test",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "interpretation": "O resultado indica atendimento parcial, com lacunas relevantes.",
                                "evidence": [
                                    {
                                        "field": "Tese A",
                                        "observation": "O argumento apresenta fundamentos, mas sua conexão com o caso pode ficar mais clara.",
                                    }
                                ],
                                "next_steps": [
                                    "Confira como cada fundamento se relaciona ao problema jurídico delimitado."
                                ],
                            }
                        )
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 1200,
                "completion_tokens": 80,
                "prompt_cache_hit_tokens": 900,
            },
        }

    @staticmethod
    def jev_section_response(section):
        check_ids = server.AI_CASE_CHECKLISTS[section]["checks"]
        if section == "case_description":
            check_ids = [check_id for check_id in check_ids if check_id != "facts-original"]
        return {
            "model": "jev-test",
            "input_tokens": 180,
            "section": section,
            "criteria": [
                {
                    "id": check_id,
                    "label": server.AI_CASE_CHECKLISTS[section]["checks"][check_id]["label"],
                    "score": 2,
                    "confidence": 0.8,
                    "probabilities": [0.05, 0.15, 0.4, 0.4],
                }
                for check_id in check_ids
            ],
            "probability_threshold": 0.6,
            "unassessed_checks": [],
        }

    def test_login_creates_http_only_cookie_without_returning_code(self):
        cookie, result = self.login(self.code_a)
        self.assertTrue(result["account"]["active"])
        self.assertNotIn("code", result)
        status, session, _ = self.request("GET", "/api/session", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertTrue(session["account"]["active"])

    def test_public_app_and_api_are_served_from_the_same_origin(self):
        status, _, _ = self.request("GET", "/")
        self.assertEqual(status, 200)
        status, _, _ = self.request("GET", "/js/main.js")
        self.assertEqual(status, 200)

    def test_project_routes_require_session_and_isolate_accounts(self):
        status, _, _ = self.request("GET", "/api/projects")
        self.assertEqual(status, 401)
        cookie_a, _ = self.login(self.code_a)
        cookie_b, _ = self.login(self.code_b)
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": project("Trabalho A")}, cookie_a
        )
        self.assertEqual(status, 201)
        status, opened, _ = self.request(
            "GET", f"/api/projects/{created['id']}", cookie=cookie_a
        )
        self.assertEqual(status, 200)
        status, updated, _ = self.request(
            "PUT",
            f"/api/projects/{created['id']}",
            {"project": project("Versão A"), "revision": opened["revision"]},
            cookie_a,
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["revision"], 2)
        status, conflict, _ = self.request(
            "PUT",
            f"/api/projects/{created['id']}",
            {"project": project("Versão desatualizada"), "revision": opened["revision"]},
            cookie_a,
        )
        self.assertEqual(status, 409)
        self.assertEqual(conflict["error"], "project_conflict")
        status, _, _ = self.request(
            "GET", f"/api/projects/{created['id']}", cookie=cookie_b
        )
        self.assertEqual(status, 404)

    def test_expired_license_keeps_read_access_but_rejects_edits(self):
        cookie, _ = self.login(self.code_a)
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": project("Trabalho preservado")}, cookie
        )
        self.assertEqual(status, 201)
        account = server.STORE.account_by_code(self.code_a)
        with server.STORE.connect() as connection:
            connection.execute(
                "UPDATE accounts SET expires_at = 1 WHERE id = ?",
                (account["id"],),
            )
        status, _, _ = self.request("GET", f"/api/projects/{created['id']}", cookie=cookie)
        self.assertEqual(status, 200)
        status, result, _ = self.request(
            "PUT",
            f"/api/projects/{created['id']}",
            {"project": project("Edição bloqueada"), "revision": 1},
            cookie,
        )
        self.assertEqual(status, 403)
        self.assertEqual(result["error"], "license_expired")

    def test_case_analysis_uses_saved_report_and_returns_rubric_estimate(self):
        cookie, _ = self.login(self.code_a)
        report = project("Case")
        report["sources"] = [{"reference": "Fonte cadastrada que não deve ser enviada"}]
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": report}, cookie
        )
        self.assertEqual(status, 201)
        with patch("server.typesafe_api_key", return_value="test-key"), patch(
            "server.call_jev", return_value=self.jev_analysis()
        ) as call:
            status, result, _ = self.request(
                "POST",
                f"/api/projects/{created['id']}/analyze-case-report",
                {},
                cookie,
            )
        self.assertEqual(status, 200)
        self.assertEqual(result["usage"], {"limit": 5, "used": 1, "remaining": 4})
        self.assertEqual(len(result["analysis"]["criteria"]), 3)
        self.assertEqual(result["analysis"]["assessable_points"], 3.5)
        self.assertEqual(result["analysis"]["unassessed_points"], 0.5)
        self.assertEqual(result["analysis"]["grade_range"]["confidence"], 0.8)
        state = call.call_args.args[0]
        self.assertIn("Argumentação da tese A", state["thesis_a_argument"])
        self.assertIn("Argumentação da tese B", state["thesis_b_argument"])
        self.assertNotIn("Nome que não deve ser enviado", json.dumps(state))
        self.assertNotIn("Fonte cadastrada que não deve ser enviada", json.dumps(state))
        self.assertNotIn("Enunciado original opcional", json.dumps(state))
        self.assertEqual(server.STORE.account_by_code(self.code_a)["ai_analysis_used"], 1)

    def test_case_analysis_rejects_paper_final_on_both_jev_routes_without_quota_use(self):
        cookie, _ = self.login(self.code_a)
        paper = project("Paper")
        paper["projectType"] = "paper"
        paper["fields"]["paperKind"] = "final"
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": paper}, cookie
        )
        self.assertEqual(status, 201)
        with patch("server.call_jev") as call:
            for endpoint, body in [
                ("analyze-case-report", {}),
                ("analyze-case-section", {"section": "case_description"}),
            ]:
                with self.subTest(endpoint=endpoint):
                    status, result, _ = self.request(
                        "POST",
                        f"/api/projects/{created['id']}/{endpoint}",
                        body,
                        cookie,
                    )
                    self.assertEqual(status, 400)
                    self.assertEqual(result["error"], "case_analysis_only")
        call.assert_not_called()
        self.assertEqual(server.STORE.account_by_code(self.code_a)["ai_analysis_used"], 0)

    def test_deepseek_route_sends_only_selected_criterion_and_records_token_metadata(self):
        server.STORE.update_account(self.code_a, deepseek_explanation_limit=1)
        cookie, _ = self.login(self.code_a)
        report = project("Case")
        report["sources"] = [{"reference": "Referência privada que não deve ser enviada"}]
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": report}, cookie
        )
        self.assertEqual(status, 201)
        provider_response = json.dumps(self.deepseek_response()).encode()
        with patch("server.deepseek_api_key", return_value="deepseek-test-key"), patch(
            "server.urlopen", return_value=io.BytesIO(provider_response)
        ) as request_mock:
            status, result, _ = self.request(
                "POST",
                f"/api/projects/{created['id']}/explain-case-criterion",
                {
                    "criterion": "legal_writing_foundation",
                    "jev_result": {
                        "score": 2.25,
                        "confidence": 0.8,
                        "probabilities": [0.05, 0.15, 0.4, 0.4],
                    },
                    "whole_report": "This untrusted field must be ignored.",
                },
                cookie,
            )
        self.assertEqual(status, 200)
        self.assertEqual(
            result["usage"], {"limit": 1, "used": 1, "remaining": 0}
        )
        explanation = result["explanation"]
        self.assertEqual(explanation["input_tokens"], 1200)
        self.assertEqual(explanation["output_tokens"], 80)
        self.assertEqual(explanation["cache_hit_input_tokens"], 900)
        self.assertEqual(explanation["estimated_cost_usd"], 0.000456)
        self.assertNotIn("whole_report", explanation)
        request = request_mock.call_args.args[0]
        request_body = json.loads(request.data)
        self.assertEqual(request.full_url, server.DEEPSEEK_API_URL)
        self.assertEqual(request.get_header("Authorization"), "Bearer deepseek-test-key")
        self.assertEqual(request_body["model"], server.DEEPSEEK_MODEL)
        self.assertEqual(request_body["response_format"], {"type": "json_object"})
        self.assertEqual(request_body["max_tokens"], 650)
        self.assertEqual(request_body["thinking"], {"type": "disabled"})
        self.assertIn("Tese A", request_body["messages"][1]["content"])
        self.assertNotIn("Nome que não deve ser enviado", request.data.decode())
        self.assertNotIn("Referência privada", request.data.decode())
        self.assertNotIn("Enunciado original opcional", request.data.decode())
        self.assertNotIn("whole_report", request.data.decode())
        account = server.STORE.account_by_code(self.code_a)
        self.assertEqual(account["deepseek_explanation_used"], 1)
        self.assertEqual(account["ai_analysis_used"], 0)
        with server.STORE.connect() as connection:
            usage_row = connection.execute(
                "SELECT criterion_id, input_tokens, output_tokens, "
                "cache_hit_input_tokens, estimated_cost_usd FROM deepseek_usage"
            ).fetchone()
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(deepseek_usage)")
            }
        self.assertEqual(
            tuple(usage_row),
            ("legal_writing_foundation", 1200, 80, 900, 0.000456),
        )
        self.assertNotIn("prompt", columns)
        self.assertNotIn("response", columns)

    def test_deepseek_route_rejects_paper_final_and_exhausted_quota_without_provider_call(self):
        server.STORE.update_account(self.code_a, deepseek_explanation_limit=0)
        cookie, _ = self.login(self.code_a)
        paper = project("Paper")
        paper["projectType"] = "paper"
        paper["fields"]["paperKind"] = "final"
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": paper}, cookie
        )
        self.assertEqual(status, 201)
        with patch("server.call_deepseek_explanation") as call:
            status, result, _ = self.request(
                "POST",
                f"/api/projects/{created['id']}/explain-case-criterion",
                {
                    "criterion": "case_description",
                    "jev_result": {
                        "score": 2,
                        "confidence": 0.8,
                        "probabilities": [0.05, 0.15, 0.4, 0.4],
                    },
                },
                cookie,
            )
        self.assertEqual(status, 400)
        self.assertEqual(result["error"], "case_analysis_only")
        call.assert_not_called()
        self.assertEqual(server.STORE.account_by_code(self.code_a)["deepseek_explanation_used"], 0)

    def test_deepseek_client_uses_json_mode_and_rejects_unbounded_output(self):
        provider_response = json.dumps(self.deepseek_response()).encode()
        context = {
            "criterion": {
                "id": "legal_writing_foundation",
                "title": "Redação jurídica e fundamentação",
                "max_points": 2.5,
            },
            "jev_result": {"score": 2, "confidence": 0.8, "probabilities": [0.05, 0.15, 0.4, 0.4]},
            "evidence": {"thesis_a_argument": "Trecho curto"},
            "evidence_fields": ["Tese A"],
        }
        with patch("server.urlopen", return_value=io.BytesIO(provider_response)) as request_mock:
            result = server.call_deepseek_explanation(context, "private-test-key")
        self.assertEqual(result["model"], "deepseek-flash-test")
        self.assertAlmostEqual(result["estimated_cost_usd"], 0.000456)
        self.assertEqual(request_mock.call_args.args[0].get_header("Authorization"), "Bearer private-test-key")

        invalid_explanations = [
            {"interpretation": "x" * 701, "evidence": [], "next_steps": []},
            {
                "interpretation": "Curta.",
                "evidence": [{"field": "Tese A", "observation": "x" * 201}],
                "next_steps": [],
            },
            {
                "interpretation": "Curta.",
                "evidence": [],
                "next_steps": ["x" * 151],
            },
            {
                "interpretation": "Curta.",
                "evidence": [
                    {"field": "Tese A", "observation": "Evidência."},
                    {"field": "Tese A", "observation": "Mais evidência."},
                    {"field": "Tese A", "observation": "Outra evidência."},
                ],
                "next_steps": [],
            },
        ]
        for content in invalid_explanations:
            malformed = self.deepseek_response()
            malformed["choices"][0]["message"]["content"] = json.dumps(content)
            with self.subTest(content=content), patch(
                "server.urlopen",
                return_value=io.BytesIO(json.dumps(malformed).encode()),
            ):
                with self.assertRaises(server.ApiError) as error:
                    server.call_deepseek_explanation(context, "private-test-key")
                self.assertEqual(error.exception.code, "deepseek_invalid_response")

    def test_project_assistant_endpoint_supports_paper_final_and_records_only_usage_metadata(self):
        server.STORE.update_account(self.code_a, deepseek_explanation_limit=1)
        cookie, _ = self.login(self.code_a)
        paper = project("Paper final")
        paper["projectType"] = "paper"
        paper["fields"]["paperKind"] = "final"
        paper["fields"]["assignmentPrompt"] = "Proposta oficial da atividade."
        paper["fields"]["introduction"] = "Introdução para análise."
        paper["sources"] = [{"reference": "Referência que não deve ser enviada"}]
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": paper}, cookie
        )
        self.assertEqual(status, 201)
        response = {
            "model": "assistant-test",
            "reply": "A introdução apresenta o tema, mas pode explicitar melhor o problema.",
            "evidence": "O texto apresenta o tema, mas não formula uma pergunta de pesquisa.",
            "suggestions": [{"point": "Problema pouco explícito.", "action": "Conecte a pergunta ao recorte do tema."}],
            "rewrite": "Versão sugerida da introdução.",
            "checklist": [],
            "input_tokens": 300,
            "output_tokens": 60,
            "cache_hit_input_tokens": 100,
            "estimated_cost_usd": 0.000162,
        }
        with patch("server.deepseek_api_key", return_value="private-test-key"), patch(
            "server.call_project_assistant", return_value=response
        ) as call:
            status, result, _ = self.request(
                "POST",
                f"/api/projects/{created['id']}/assistant",
                {"action": "review", "field_id": "introduction"},
                cookie,
            )
        self.assertEqual(status, 200)
        self.assertEqual(result["response"], response)
        self.assertEqual(result["usage"], {"limit": 1, "used": 1, "remaining": 0})
        context = call.call_args.args[0]
        serialized = json.dumps(context, ensure_ascii=False)
        self.assertEqual(context["field"]["text"], "Introdução para análise.")
        self.assertIn("Proposta oficial", serialized)
        self.assertNotIn("Nome que não deve ser enviado", serialized)
        self.assertNotIn("Referência que não deve ser enviada", serialized)
        with server.STORE.connect() as connection:
            usage = connection.execute(
                "SELECT criterion_id, input_tokens, output_tokens FROM deepseek_usage "
                "WHERE project_id = ?",
                (created["id"],),
            ).fetchone()
        self.assertEqual(tuple(usage), ("assistant:review", 300, 60))

    def test_project_assistant_provider_returns_validated_bounded_feedback(self):
        content = {
            "reply": "A ideia está clara; o recorte temporal ainda precisa aparecer.",
            "evidence": "O título nomeia o tema, mas não informa período ou delimitação.",
            "suggestions": [{"point": "O período está ausente.", "action": "Informe o intervalo que será pesquisado."}],
            "rewrite": "O impacto de X entre 2020 e 2025.",
            "checklist": [],
        }
        provider_response = {
            "model": server.DEEPSEEK_MODEL,
            "choices": [{"message": {"content": json.dumps(content)}}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 90, "prompt_cache_hit_tokens": 100},
        }
        with patch(
            "server.urlopen",
            return_value=io.BytesIO(json.dumps(provider_response).encode()),
        ) as request_mock:
            result = server.call_project_assistant(
                {
                    "action": "review",
                    "assignment_prompt": "Delimite o tema.",
                    "project_context": {"problem": "Qual o impacto de X?"},
                    "field": {"id": "title", "text": "Impacto de X"},
                    "checklist": [],
                },
                "private-test-key",
            )
        self.assertEqual(result["reply"], content["reply"])
        self.assertEqual(result["evidence"], content["evidence"])
        self.assertEqual(result["rewrite"], content["rewrite"])
        body = json.loads(request_mock.call_args.args[0].data)
        self.assertEqual(body["max_tokens"], server.PROJECT_AI_MAX_OUTPUT_TOKENS)
        self.assertNotIn("jev", body["messages"][0]["content"].lower())

    def test_deepseek_payment_error_is_reported_as_actionable(self):
        payment_error = HTTPError(
            server.DEEPSEEK_API_URL,
            402,
            "Payment Required",
            {},
            io.BytesIO(b""),
        )
        with patch("server.urlopen", side_effect=payment_error):
            with self.assertRaises(server.ApiError) as error:
                server.call_deepseek_explanation(
                    {
                        "criterion": {"title": "Critério"},
                        "jev_result": {
                            "score": 2,
                            "confidence": 0.8,
                            "probabilities": [0.05, 0.15, 0.4, 0.4],
                        },
                        "evidence": {},
                        "evidence_fields": [],
                    },
                    "private-test-key",
                )
        self.assertEqual(error.exception.status, 402)
        self.assertEqual(error.exception.code, "deepseek_payment_required")
        self.assertIn("saldo", str(error.exception))

    def test_section_checklist_analysis_uses_only_its_saved_content_and_consumes_one_unit(self):
        cookie, _ = self.login(self.code_a)
        report = project("Case")
        report["sources"] = [{"reference": "Referência privada que não deve ser enviada"}]
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": report}, cookie
        )
        self.assertEqual(status, 201)
        analysis = self.jev_section_response("case_description")
        with patch("server.typesafe_api_key", return_value="test-key"), patch(
            "server.call_jev", return_value=analysis
        ) as call:
            status, result, _ = self.request(
                "POST",
                f"/api/projects/{created['id']}/analyze-case-section",
                {"section": "case_description"},
                cookie,
            )
        self.assertEqual(status, 200)
        self.assertEqual(result["usage"], {"limit": 5, "used": 1, "remaining": 4})
        self.assertEqual(result["analysis"]["unassessed_checks"], [])
        state, api_key, section = call.call_args.args
        self.assertEqual(api_key, "test-key")
        self.assertEqual(section, "case_description")
        self.assertIn("Fatos relevantes", state["case_facts"])
        self.assertIn("Enunciado original", state["original_case_prompt"])
        self.assertNotIn("thesis_a_argument", state)
        self.assertNotIn("Nome que não deve ser enviado", json.dumps(state))
        self.assertNotIn("Referência privada", json.dumps(state))
        self.assertEqual(server.STORE.account_by_code(self.code_a)["ai_analysis_used"], 1)

    def test_unassessable_reference_checklist_is_rejected_without_quota_use(self):
        cookie, _ = self.login(self.code_a)
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": project("Case")}, cookie
        )
        self.assertEqual(status, 201)
        status, result, _ = self.request(
            "POST",
            f"/api/projects/{created['id']}/analyze-case-section",
            {"section": "references"},
            cookie,
        )
        self.assertEqual(status, 400)
        self.assertEqual(result["error"], "invalid_analysis_section")
        self.assertEqual(server.STORE.account_by_code(self.code_a)["ai_analysis_used"], 0)

    def test_jev_section_client_sends_only_matching_checklist_questions(self):
        check_ids = [
            check_id for check_id in server.AI_CASE_CHECKLISTS["case_description"]["checks"]
        ]
        response = {
            "model": "jev-test",
            "answers": {
                check_id: {
                    "type": "score",
                    "score": 2,
                    "confidence": 0.8,
                    "probabilities": {"0": 0.05, "1": 0.15, "2": 0.4, "3": 0.4},
                }
                for check_id in check_ids
            },
            "usage": {"input_tokens": 180},
        }
        body = json.dumps(response).encode()
        state = {
            "case_facts": "Narrativa do aluno",
            "legal_question": "Pergunta do caso",
            "original_case_prompt": "Enunciado recebido",
        }
        with patch("server.urlopen", return_value=io.BytesIO(body)) as request_mock:
            result = server.call_jev(state, "private-test-key", "case_description")
        request_body = json.loads(request_mock.call_args.args[0].data)
        self.assertEqual(
            set(request_body["questions"]),
            {"facts-neutral", "facts-relevant", "problem-question", "facts-original"},
        )
        self.assertIn("Enunciado recebido", json.dumps(request_body["state"]))
        self.assertEqual(result["section"], "case_description")
        self.assertEqual(len(result["criteria"]), 4)
        self.assertEqual(result["unassessed_checks"], [])

    def test_jev_skips_originality_question_when_original_prompt_is_absent(self):
        check_ids = [
            check_id for check_id in server.AI_CASE_CHECKLISTS["case_description"]["checks"]
            if check_id != "facts-original"
        ]
        response = {
            "model": "jev-test",
            "answers": {
                check_id: {
                    "type": "score",
                    "score": 2,
                    "confidence": 0.8,
                    "probabilities": {"0": 0.05, "1": 0.15, "2": 0.4, "3": 0.4},
                }
                for check_id in check_ids
            },
            "usage": {"input_tokens": 120},
        }
        with patch("server.urlopen", return_value=io.BytesIO(json.dumps(response).encode())) as request_mock:
            analysis = server.call_jev(
                {"case_facts": "Narrativa", "legal_question": "Problema"},
                "private-test-key",
                "case_description",
            )
        request_body = json.loads(request_mock.call_args.args[0].data)
        self.assertNotIn("facts-original", request_body["questions"])
        self.assertEqual(analysis["unassessed_checks"], ["facts-original"])

    def test_jev_client_sends_typed_questions_to_the_fixed_provider_endpoint(self):
        provider_response = json.dumps(self.jev_response()).encode()
        with patch("server.urlopen", return_value=io.BytesIO(provider_response)) as request_mock:
            result = server.call_jev({"thesis_text": "texto da tese"}, "private-test-key")
        request = request_mock.call_args.args[0]
        request_body = json.loads(request.data)
        self.assertEqual(request.full_url, server.TYPESAFE_API_URL)
        self.assertEqual(request.get_header("Authorization"), "Bearer private-test-key")
        self.assertEqual(request_body["model"], server.TYPESAFE_MODEL)
        self.assertEqual(len(request_body["questions"]), 4)
        self.assertEqual(result["input_tokens"], 420)
        self.assertEqual(len(result["criteria"]), 3)
        self.assertIn("grade_range", request_body["questions"])
        self.assertEqual(result["assessable_points"], 3.5)
        self.assertEqual(result["unassessed_points"], 0.5)
        self.assertEqual(result["grade_range"]["probabilities"], [0.05, 0.15, 0.4, 0.4])
        self.assertAlmostEqual(result["expected_points"], 2.36)
        request_state = request_body["state"]
        self.assertNotIn("sources", request_state)
        writing_instructions = request_body["questions"]["legal_writing_foundation"][
            "instructions"
        ]
        self.assertIn("at least three relevant works visibly used", writing_instructions)
        self.assertIn("four works with two per thesis", writing_instructions)
        self.assertIn("do not lower this score", writing_instructions)
        self.assertIn("Do not infer page count or formatting", writing_instructions)
        self.assertIn("Do not assess the later debate", writing_instructions)
        description_instructions = request_body["questions"]["case_description"]["instructions"]
        self.assertIn("open case", description_instructions)
        self.assertIn("optional advice", description_instructions)
        criteria_instructions = request_body["questions"]["criteria_and_values"]["instructions"]
        self.assertIn("optional improvement", criteria_instructions)
        grade_instructions = request_body["questions"]["grade_range"]["instructions"]
        self.assertIn("Follow only the official rubric", grade_instructions)
        self.assertIn("must not draft or rewrite any part", grade_instructions)

    def test_checklist_prompts_are_formative_and_separate_optional_guidance(self):
        self.assertIn("formative self-review", server.AI_CASE_CHECKLIST_LEVELS[0])
        integrated_sources = server.AI_CASE_CHECKLISTS["thesis_a"]["checks"][
            "thesis-a-integrated"
        ]["instructions"]
        self.assertIn(
            "cannot be checked from this single-thesis excerpt", integrated_sources
        )
        self.assertIn(
            "do not require a fixed number of works in this section", integrated_sources
        )
        self.assertIn(
            "Interweaving every source type in each paragraph is optional",
            integrated_sources,
        )
        glossary = server.AI_CASE_CHECKLISTS["criteria_and_values"]["checks"][
            "criteria-defined"
        ]["instructions"]
        self.assertIn("optional unless the professor expressly requires it", glossary)

    def test_jev_client_rejects_malformed_score_responses(self):
        response = self.jev_response()
        response["answers"]["case_description"]["probabilities"]["3"] = 9
        malformed_responses = [
            response,
            [],
            {**self.jev_response(), "usage": []},
        ]
        for malformed_response in malformed_responses:
            with self.subTest(response=type(malformed_response).__name__):
                body = json.dumps(malformed_response).encode()
                with patch("server.urlopen", return_value=io.BytesIO(body)):
                    with self.assertRaises(server.ApiError) as error:
                        server.call_jev({"thesis_text": "texto"}, "private-test-key")
                self.assertEqual(error.exception.code, "ai_invalid_response")

    def test_provider_failure_still_consumes_one_reserved_analysis(self):
        cookie, _ = self.login(self.code_a)
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": project("Case")}, cookie
        )
        self.assertEqual(status, 201)
        with patch("server.typesafe_api_key", return_value="test-key"), patch(
            "server.call_jev",
            side_effect=server.ApiError(503, "ai_provider_busy", "Tente novamente."),
        ):
            status, result, _ = self.request(
                "POST",
                f"/api/projects/{created['id']}/analyze-case-report",
                {},
                cookie,
            )
        self.assertEqual(status, 503)
        self.assertEqual(result["error"], "ai_provider_busy")
        self.assertEqual(server.STORE.account_by_code(self.code_a)["ai_analysis_used"], 1)

    def test_missing_provider_key_consumes_requested_analysis(self):
        cookie, _ = self.login(self.code_a)
        status, created, _ = self.request(
            "POST", "/api/projects", {"project": project("Case")}, cookie
        )
        self.assertEqual(status, 201)
        with patch(
            "server.typesafe_api_key",
            side_effect=server.ApiError(503, "ai_unavailable", "Not configured."),
        ):
            status, result, _ = self.request(
                "POST",
                f"/api/projects/{created['id']}/analyze-case-report",
                {},
                cookie,
            )
        self.assertEqual(status, 503)
        self.assertEqual(result["error"], "ai_unavailable")
        self.assertEqual(server.STORE.account_by_code(self.code_a)["ai_analysis_used"], 1)


if __name__ == "__main__":
    unittest.main()
