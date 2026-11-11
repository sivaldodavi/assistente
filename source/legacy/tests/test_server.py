import contextlib
import io
import json
import tempfile
import unittest
import stat
from pathlib import Path
from unittest.mock import patch

import server
from server import ApiError, Store


def project(title="Projeto de teste", project_type="case"):
    return {
        "version": 2,
        "projectType": project_type,
        "fields": {
            "title": title,
            "author": "Nome que não deve ser enviado",
            "assignmentPrompt": "Proposta do professor para orientar o trabalho.",
            "originalCasePrompt": "Enunciado original opcional do professor.",
            "facts": "Fatos relevantes do caso apresentado para contextualizar a análise.",
            "problem": "Qual é a solução jurídica adequada diante dos fatos narrados?",
            "decisionBasis": "Base conceitual pertinente ao problema.",
            "thesisATitle": "Tese A",
            "thesisA": "Argumentação da tese A. " * 8,
            "thesisBTitle": "Tese B",
            "thesisB": "Argumentação da tese B. " * 8,
        },
        "sources": [],
        "criteria": [],
        "checks": {},
        "currentStep": 0,
        "finalized": False,
    }


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp_dir.name) / "app.sqlite3")
        self.first_code, self.second_code = self.store.issue_batch(2, days=7, project_limit=1)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_codes_are_random_and_only_their_hashes_are_stored(self):
        account = self.store.account_by_code(self.first_code)
        self.assertIsNotNone(account)
        self.assertNotEqual(account["code_hash"], self.first_code)
        self.assertEqual(len(self.store.list_accounts()), 2)

    def test_owner_account_has_no_license_project_or_analysis_limits(self):
        start = 1_800_000_000
        self.store.create_owner_account("TESTOWNER22", start)
        account = self.store.account_by_code("testowner22")
        self.assertIsNotNone(account)
        self.assertTrue(account["owner"])
        self.assertNotEqual(account["code_hash"], "TESTOWNER22")
        self.assertTrue(Store.license_active(account, start + 100 * 365 * 24 * 60 * 60))
        summary = self.store.account_summary(
            account, start + 100 * 365 * 24 * 60 * 60
        )
        self.assertTrue(summary["unlimited"])
        self.assertTrue(summary["active"])
        self.assertIsNone(summary["expires_at"])
        self.assertIsNone(summary["project_limit"])
        self.assertIsNone(summary["ai_analysis_limit"])
        self.assertIsNone(summary["ai_analysis_remaining"])
        self.assertIsNone(summary["deepseek_explanation_limit"])
        self.assertIsNone(summary["deepseek_explanation_remaining"])

        with self.store.connect() as connection:
            connection.execute(
                "UPDATE accounts SET project_limit = 1, ai_analysis_limit = 1, expires_at = 1 WHERE id = ?",
                (account["id"],),
            )
        first_project_id = self.store.create_project(account, project("Case A"), start + 1)
        second_project_id = self.store.create_project(account, project("Case B"), start + 2)
        first_state, first_usage = self.store.reserve_case_analysis(
            account["id"], first_project_id, start + 3
        )
        second_state, second_usage = self.store.reserve_case_analysis(
            account["id"], second_project_id, start + 4
        )
        self.assertIn("case_facts", first_state)
        self.assertIn("case_facts", second_state)
        self.assertIsNone(first_usage["limit"])
        self.assertIsNone(first_usage["remaining"])
        self.assertIsNone(second_usage["remaining"])
        self.assertEqual(second_usage["used"], 2)

    def test_owner_code_must_be_custom_alphanumeric_and_unique(self):
        with self.assertRaises(ValueError):
            self.store.create_owner_account("SHORT")
        self.store.create_owner_account("TESTOWNER22")
        with self.assertRaises(ValueError):
            self.store.create_owner_account("TESTOWNER22")

    def test_create_owner_command_confirms_code_without_printing_it(self):
        with (
            patch("server.Store", return_value=self.store),
            patch("server.getpass.getpass", side_effect=["TESTOWNER22", "TESTOWNER22"]),
            patch("builtins.print") as print_mock,
        ):
            self.assertEqual(server.admin_main(["create-owner"]), 0)
        self.assertIsNotNone(self.store.account_by_code("TESTOWNER22"))
        self.assertEqual(print_mock.call_args.args[0], "Conta do proprietário criada.")
        self.assertNotIn("TESTOWNER22", str(print_mock.call_args))

    def test_create_owner_command_rejects_mismatched_confirmation(self):
        error_output = io.StringIO()
        with (
            patch("server.Store", return_value=self.store),
            patch("server.getpass.getpass", side_effect=["TESTOWNER22", "DIFFERENT22"]),
            contextlib.redirect_stderr(error_output),
        ):
            self.assertEqual(server.admin_main(["create-owner"]), 1)
        self.assertIn("Os códigos não coincidem.", error_output.getvalue())
        self.assertIsNone(self.store.account_by_code("TESTOWNER22"))

    def test_account_list_identifies_owner_and_unlimited_quotas(self):
        self.store.create_owner_account("TESTOWNER22")
        with (
            patch("server.Store", return_value=self.store),
            patch("builtins.print") as print_mock,
        ):
            self.assertEqual(server.admin_main(["list"]), 0)
        owner_line = next(
            call.args[0]
            for call in print_mock.call_args_list
            if "proprietário" in call.args[0]
        )
        self.assertIn("projetos=ilimitados", owner_line)
        self.assertIn("jev=0/ilimitadas", owner_line)
        self.assertIn("deepseek=0/ilimitadas", owner_line)

    def test_initial_batch_can_issue_one_hundred_seven_day_single_project_codes(self):
        codes = self.store.issue_batch(100, days=7, project_limit=1)
        self.assertEqual(len(codes), 100)
        self.assertEqual(len(set(codes)), 100)
        self.assertTrue(all(code.startswith("ROTE-") for code in codes))
        self.assertTrue(all(self.store.account_by_code(code)["default_days"] == 7 for code in codes))
        self.assertTrue(all(self.store.account_by_code(code)["project_limit"] == 1 for code in codes))
        self.assertTrue(all(self.store.account_by_code(code)["ai_analysis_limit"] == 5 for code in codes))
        self.assertTrue(
            all(
                self.store.account_by_code(code)["deepseek_explanation_limit"] == 5
                for code in codes
            )
        )

    def test_analysis_quota_is_atomic_and_resets_when_license_is_renewed(self):
        start = 1_800_000_000
        self.store.update_account(self.first_code, ai_analysis_limit=1)
        account = self.store.activate_code(self.first_code, start)
        project_id = self.store.create_project(account, project(), start + 1)
        state, usage = self.store.reserve_case_analysis(account["id"], project_id, start + 2)
        self.assertEqual(usage, {"limit": 1, "used": 1, "remaining": 0})
        self.assertEqual(state["thesis_a_argument"], project()["fields"]["thesisA"])
        self.assertNotIn("author", state)
        with self.assertRaises(ApiError) as quota_error:
            self.store.reserve_case_analysis(account["id"], project_id, start + 3)
        self.assertEqual(quota_error.exception.code, "ai_quota_exhausted")

        self.store.extend_account(self.first_code, 7, start + 4)
        renewed = self.store.account_by_code(self.first_code)
        self.assertEqual(renewed["ai_analysis_used"], 0)

    def test_deepseek_explanation_quota_is_independent_and_resets_on_renewal(self):
        start = 1_800_000_000
        self.store.update_account(self.first_code, deepseek_explanation_limit=1)
        account = self.store.activate_code(self.first_code, start)
        case = project()
        case["sources"] = [{"reference": "PRIVATE SOURCE LIST"}]
        case["criteria"] = [
            {
                "term": "Proporcionalidade",
                "definition": "Adequação, necessidade e proporcionalidade estrita.",
                "basis": "Base conceitual.",
            }
        ]
        project_id = self.store.create_project(account, case, start + 1)
        context, usage = self.store.reserve_deepseek_explanation(
            account["id"],
            project_id,
            "legal_writing_foundation",
            {"score": 2.25, "confidence": 0.8, "probabilities": [0.05, 0.15, 0.4, 0.4]},
            start + 2,
        )
        serialized = json.dumps(context, ensure_ascii=False)
        self.assertEqual(usage, {"limit": 1, "used": 1, "remaining": 0})
        self.assertIn("Argumentação da tese A", serialized)
        self.assertNotIn("Nome que não deve ser enviado", serialized)
        self.assertNotIn("PRIVATE SOURCE LIST", serialized)
        self.assertNotIn("Proporcionalidade", serialized)
        with self.assertRaises(ApiError) as quota_error:
            self.store.reserve_deepseek_explanation(
                account["id"],
                project_id,
                "legal_writing_foundation",
                {"score": 2, "confidence": 0.8, "probabilities": [0.05, 0.15, 0.4, 0.4]},
                start + 3,
            )
        self.assertEqual(quota_error.exception.code, "deepseek_quota_exhausted")
        current = self.store.account_by_code(self.first_code)
        self.assertEqual(current["ai_analysis_used"], 0)
        self.assertEqual(current["deepseek_explanation_used"], 1)

        self.store.extend_account(self.first_code, 7, start + 4)
        renewed = self.store.account_by_code(self.first_code)
        self.assertEqual(renewed["deepseek_explanation_used"], 0)

    def test_deepseek_explanation_rejects_papers_and_invalid_jev_results_without_quota(self):
        self.store.update_account(self.first_code, project_limit=2)
        account = self.store.activate_code(self.first_code, 1_800_000_000)
        paper_id = self.store.create_project(
            account, project("Paper", "paper"), 1_800_000_001
        )
        with self.assertRaises(ApiError) as paper_error:
            self.store.reserve_deepseek_explanation(
                account["id"],
                paper_id,
                "case_description",
                {"score": 2, "confidence": 0.8, "probabilities": [0.05, 0.15, 0.4, 0.4]},
                1_800_000_002,
            )
        self.assertEqual(paper_error.exception.code, "case_analysis_only")
        case_id = self.store.create_project(
            account, project("Case"), 1_800_000_003
        )
        with self.assertRaises(ApiError) as result_error:
            self.store.reserve_deepseek_explanation(
                account["id"],
                case_id,
                "case_description",
                {"score": float("nan"), "confidence": 0.8, "probabilities": [0.05, 0.15, 0.4, 0.4]},
                1_800_000_004,
            )
        self.assertEqual(result_error.exception.code, "invalid_jev_result")
        stored = self.store.account_by_code(self.first_code)
        self.assertEqual(stored["deepseek_explanation_used"], 0)

    def test_project_assistant_uses_prompt_without_identity_or_reference_list_and_supports_paper_final(self):
        start = 1_800_000_000
        self.store.update_account(self.first_code, deepseek_explanation_limit=1)
        account = self.store.activate_code(self.first_code, start)
        paper = project("Paper final", "paper")
        paper["fields"]["paperKind"] = "final"
        paper["fields"]["assignmentPrompt"] = "Analise o tema e responda ao problema proposto."
        paper["fields"]["introduction"] = "Esta é a introdução do paper."
        paper["fields"]["developmentSections"] = [
            {"id": "section-one", "title": "Fundamentação", "content": "Argumentação do tópico."}
        ]
        paper["sources"] = [{"reference": "REFERÊNCIA PRIVADA"}]
        project_id = self.store.create_project(account, paper, start + 1)
        context, usage = self.store.reserve_project_ai(
            account["id"],
            project_id,
            {"action": "review", "field_id": "developmentText:section-one"},
            start + 2,
        )
        serialized = json.dumps(context, ensure_ascii=False)
        self.assertEqual(usage, {"limit": 1, "used": 1, "remaining": 0})
        self.assertEqual(context["project_type"], "paper")
        self.assertEqual(context["field"]["text"], "Argumentação do tópico.")
        self.assertIn("assignment_prompt", context)
        self.assertIn("introduction", context["project_context"])
        self.assertNotIn("Nome que não deve ser enviado", serialized)
        self.assertNotIn("REFERÊNCIA PRIVADA", serialized)
        with self.assertRaises(ApiError) as quota_error:
            self.store.reserve_project_ai(
                account["id"], project_id, {"action": "chat", "messages": [{"role": "user", "content": "Pergunta"}]}, start + 3
            )
        self.assertEqual(quota_error.exception.code, "deepseek_quota_exhausted")

    def test_project_assistant_requires_assignment_prompt_and_respects_context_selection(self):
        start = 1_800_000_000
        self.store.update_account(self.first_code, deepseek_explanation_limit=2)
        account = self.store.activate_code(self.first_code, start)
        case = project("Case")
        del case["fields"]["assignmentPrompt"]
        project_id = self.store.create_project(account, case, start + 1)
        with self.assertRaises(ApiError) as prompt_error:
            self.store.reserve_project_ai(
                account["id"],
                project_id,
                {"action": "review", "field_id": "facts"},
                start + 2,
            )
        self.assertEqual(prompt_error.exception.code, "assignment_prompt_required")
        self.assertEqual(self.store.account_by_code(self.first_code)["deepseek_explanation_used"], 0)

        case["fields"]["assignmentPrompt"] = "Proposta do professor."
        self.store.update_project(account, project_id, case, 1, start + 3)
        context, _ = self.store.reserve_project_ai(
            account["id"],
            project_id,
            {
                "action": "chat",
                "context_fields": [],
                "messages": [{"role": "user", "content": "Como posso delimitar?"}],
            },
            start + 4,
        )
        self.assertEqual(context["project_context"], {})
        self.assertEqual(context["development_topics"], [])
        self.assertEqual(context["assignment_prompt"], "Proposta do professor.")

    def test_case_analysis_sends_only_report_content_not_identity_or_reference_list(self):
        account = self.store.activate_code(self.first_code, 1_800_000_000)
        case = project()
        case["sources"] = [{"reference": "PRIVATE SOURCE LIST"}]
        case["criteria"] = [{"term": "Proporcionalidade", "definition": "Adequação, necessidade e proporcionalidade estrita.", "basis": "Base conceitual."}]
        project_id = self.store.create_project(account, case, 1_800_000_001)
        state, usage = self.store.reserve_case_analysis(account["id"], project_id, 1_800_000_002)
        serialized = str(state)
        self.assertIn("Fatos relevantes do caso", serialized)
        self.assertIn("Proporcionalidade", serialized)
        self.assertNotIn("Nome que não deve ser enviado", serialized)
        self.assertNotIn("PRIVATE SOURCE LIST", serialized)
        self.assertEqual(usage["used"], 1)

    def test_case_analysis_rejects_papers_without_spending_quota(self):
        account = self.store.activate_code(self.first_code, 1_800_000_000)
        paper_id = self.store.create_project(
            account, project("Paper", "paper"), 1_800_000_001
        )
        with self.assertRaises(ApiError) as error:
            self.store.reserve_case_analysis(account["id"], paper_id, 1_800_000_002)
        self.assertEqual(error.exception.code, "case_analysis_only")
        self.assertEqual(self.store.account_by_code(self.first_code)["ai_analysis_used"], 0)

    def test_section_analysis_sends_only_matching_fields_and_original_prompt_when_relevant(self):
        account = self.store.activate_code(self.first_code, 1_800_000_000)
        case = project()
        case["sources"] = [{"reference": "PRIVATE SOURCE LIST"}]
        project_id = self.store.create_project(account, case, 1_800_000_001)
        state, usage = self.store.reserve_case_analysis(
            account["id"], project_id, 1_800_000_002, section="case_description"
        )
        self.assertEqual(
            set(state),
            {"assignment_prompt", "case_facts", "legal_question", "original_case_prompt"},
        )
        self.assertIn("Enunciado original", state["original_case_prompt"])
        self.assertNotIn("PRIVATE SOURCE LIST", str(state))
        self.assertNotIn("Argumentação da tese A", str(state))
        self.assertEqual(usage["used"], 1)

        case["fields"]["originalCasePrompt"] = ""
        self.store.update_project(account, project_id, case, 1, 1_800_000_003)
        state, _ = self.store.reserve_case_analysis(
            account["id"], project_id, 1_800_000_004, section="case_description"
        )
        self.assertNotIn("original_case_prompt", state)

    def test_unassessable_section_is_rejected_without_spending_quota(self):
        account = self.store.activate_code(self.first_code, 1_800_000_000)
        project_id = self.store.create_project(account, project(), 1_800_000_001)
        with self.assertRaises(ApiError) as error:
            self.store.reserve_case_analysis(
                account["id"], project_id, 1_800_000_002, section="references"
            )
        self.assertEqual(error.exception.code, "invalid_analysis_section")
        self.assertEqual(self.store.account_by_code(self.first_code)["ai_analysis_used"], 0)

    def test_case_assessment_requires_professor_prompt_without_consuming_quota(self):
        account = self.store.activate_code(self.first_code, 1_800_000_000)
        case = project()
        del case["fields"]["assignmentPrompt"]
        project_id = self.store.create_project(account, case, 1_800_000_001)
        with self.assertRaises(ApiError) as error:
            self.store.reserve_case_analysis(account["id"], project_id, 1_800_000_002)
        self.assertEqual(error.exception.code, "assignment_prompt_required")
        self.assertEqual(self.store.account_by_code(self.first_code)["ai_analysis_used"], 0)

    def test_license_starts_on_first_use_and_expires_after_seven_days(self):
        start = 1_800_000_000
        account = self.store.activate_code(self.first_code, start)
        self.assertEqual(account["activated_at"], start)
        self.assertEqual(account["expires_at"], start + 7 * 24 * 60 * 60)
        same_account = self.store.activate_code(self.first_code, start + 100)
        self.assertEqual(same_account["activated_at"], start)

    def test_project_limit_and_account_isolation_are_enforced(self):
        account = self.store.activate_code(self.first_code, 1_800_000_000)
        project_id = self.store.create_project(account, project(), 1_800_000_001)
        with self.assertRaises(ApiError) as quota_error:
            self.store.create_project(account, project("Segundo"), 1_800_000_002)
        self.assertEqual(quota_error.exception.code, "project_limit")

        other = self.store.activate_code(self.second_code, 1_800_000_000)
        with self.assertRaises(ApiError) as isolation_error:
            self.store.get_project(other["id"], project_id)
        self.assertEqual(isolation_error.exception.status, 404)

    def test_expired_accounts_can_read_but_not_change_projects(self):
        start = 1_800_000_000
        account = self.store.activate_code(self.first_code, start)
        project_id = self.store.create_project(account, project(), start + 1)
        expired_at = start + 7 * 24 * 60 * 60
        self.assertEqual(self.store.get_project(account["id"], project_id)["project"]["fields"]["title"], "Projeto de teste")
        with self.assertRaises(ApiError) as error:
            self.store.update_project(account, project_id, project("Editado"), 1, expired_at)
        self.assertEqual(error.exception.code, "license_expired")

    def test_stale_revision_cannot_overwrite_another_device_edit(self):
        start = 1_800_000_000
        account = self.store.activate_code(self.first_code, start)
        project_id = self.store.create_project(account, project(), start + 1)
        revision = self.store.update_project(account, project_id, project("Nova versão"), 1, start + 2)
        self.assertEqual(revision, 2)
        with self.assertRaises(ApiError) as error:
            self.store.update_project(account, project_id, project("Versão antiga"), 1, start + 3)
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(
            self.store.get_project(account["id"], project_id)["project"]["fields"]["title"],
            "Nova versão",
        )

    def test_renewal_extends_expiry_and_code_rotation_invalidates_old_code(self):
        start = 1_800_000_000
        account = self.store.activate_code(self.first_code, start)
        self.store.extend_account(self.first_code, 7, start + 3 * 24 * 60 * 60)
        renewed = self.store.account_by_code(self.first_code)
        self.assertEqual(renewed["expires_at"], account["expires_at"] + 7 * 24 * 60 * 60)
        replacement = self.store.rotate_code(self.first_code)
        self.assertIsNone(self.store.account_by_code(self.first_code))
        self.assertEqual(self.store.account_by_code(replacement)["id"], account["id"])

    def test_revoked_code_cannot_create_a_new_session(self):
        self.store.set_revoked(self.first_code, True)
        with self.assertRaises(ApiError) as error:
            self.store.activate_code(self.first_code)
        self.assertEqual(error.exception.code, "invalid_code")

    def test_account_data_is_retained_when_license_expires(self):
        start = 1_800_000_000
        account = self.store.activate_code(self.first_code, start)
        project_id = self.store.create_project(account, project(), start + 1)
        summary = self.store.account_summary(account, start + 8 * 24 * 60 * 60)
        self.assertFalse(summary["active"])
        self.assertEqual(summary["project_count"], 1)
        self.assertEqual(self.store.get_project(account["id"], project_id)["id"], project_id)

    def test_backup_is_private_and_contains_the_database(self):
        self.store.issue_batch(1)
        destination = Path(self.temp_dir.name) / "backup" / "copy.sqlite3"
        backup = self.store.backup(destination)
        self.assertTrue(backup.is_file())
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        copy = Store(backup)
        self.assertEqual(len(copy.list_accounts()), 3)


if __name__ == "__main__":
    unittest.main()
