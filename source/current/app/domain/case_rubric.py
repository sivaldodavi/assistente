"""Rubrica e checklists do case usados pela IA e pela revisão."""

AI_CASE_RUBRIC = {
    "case_description": {
        "title": "Descrição do caso e decisões possíveis",
        "max_points": 0.5,
        "instructions": (
            "Score this 0.5-point criterion using the official FACSUR case-report rubric only: "
            "whether the topic is legally delimited and specific, the case narrative makes the "
            "relevant characters, context and legal conflict clear, the legal problem is "
            "objective, and possible decisions can be identified. Do not reduce the score for "
            "optional advice in the student's supplementary guide, such as requiring the final "
            "sentence to be an interrogative, using a particular section order, or adding a "
            "separate conceptual subsection, unless the professor's instructions for this "
            "assignment explicitly require it. Do not insist on a fixed Thesis A-versus-B "
            "dichotomy when the report describes an open case; assess whether it identifies "
            "the legal issue and relevant possible positions. Do not decide which position is "
            "legally correct."
        ),
    },
    "legal_writing_foundation": {
        "title": "Redação jurídica e fundamentação",
        "max_points": 2.5,
        "instructions": (
            "Score this 2.5-point criterion against the official FACSUR case-report rubric. "
            "Insufficient performance includes missing legal foundation, doctrine, or possible "
            "decisions. Partial performance includes superficial sources, citations without a "
            "clear relation to the case, or jurisprudence mentioned without explaining its "
            "connection. Adequate performance requires a clear case narrative and legal "
            "problem, at least three relevant works visibly used, direct identification of "
            "applicable legal provisions, and decisions/arguments coherent with the case. "
            "Count only distinct works identifiable in the supplied argument text; the "
            "reference list and library catalog are not supplied, so do not claim that a work "
            "belongs to the FACSUR Virtual Library or verify that any source exists, is current, "
            "or legally accurate. Do not assess the later debate or individual dissertation's "
            "final choice as part of the report-stage criterion. The student's supplementary "
            "guide includes optional ways to improve the work; do not lower this score for not "
            "following them, including using four works with two per thesis, reaching a suggested "
            "page count, writing exclusively in third person, following a particular thesis "
            "opening/development/closing pattern, integrating every source in each paragraph, "
            "or commenting after every quotation, unless the professor's assignment expressly "
            "requires a specific item. If useful, identify such points as optional suggestions "
            "separate from the rubric score. Do not infer page count or formatting from plain text."
        ),
    },
    "criteria_and_values": {
        "title": "Critérios e valores",
        "max_points": 0.5,
        "instructions": (
            "Score this 0.5-point criterion using the official FACSUR case-report rubric only: "
            "whether the possible legal solution is coherent and justified by normative "
            "criteria or legal values. A separate, comprehensive glossary defining every "
            "technical term is an optional improvement in the student's supplementary guide, "
            "not a score requirement unless the professor's instructions for this assignment "
            "explicitly require it. Do not require definitions for ordinary legal vocabulary. "
            "Do not verify the legal correctness of concepts or sources."
        ),
    },
}

DEEPSEEK_EVIDENCE_LABELS = {
    "case_description": {
        "case_facts": "Fatos do caso",
        "legal_question": "Pergunta jurídica",
        "possible_decision_a": "Decisão possível A",
        "possible_decision_b": "Decisão possível B",
    },
    "legal_writing_foundation": {
        "case_facts": "Fatos do caso",
        "legal_question": "Pergunta jurídica",
        "conceptual_basis": "Base conceitual",
        "thesis_a_title": "Título da tese A",
        "thesis_a_argument": "Tese A",
        "thesis_b_title": "Título da tese B",
        "thesis_b_argument": "Tese B",
    },
    "criteria_and_values": {
        "thesis_a_argument": "Argumentação da tese A",
        "thesis_b_argument": "Argumentação da tese B",
        "criteria_and_values": "Critérios e valores",
    },
}

AI_CASE_GRADE_RANGES = [
    "0 — 0.00 to 0.87 of the 3.50 assessable content points.",
    "1 — 0.88 to 1.75 of the 3.50 assessable content points.",
    "2 — 1.76 to 2.62 of the 3.50 assessable content points.",
    "3 — 2.63 to 3.50 of the 3.50 assessable content points.",
]

AI_CASE_GRADE_QUESTION = {
    "title": "Faixa de pontuação provável do conteúdo",
    "instructions": (
        "Estimate the most likely point range for this FACSUR case report using only its "
        "three assessable content criteria: case description/possible decisions (0.5), legal "
        "writing/foundation (2.5), and criteria/values (0.5), total 3.5 points. Select 0 for "
        "0.00-0.87, 1 for 0.88-1.75, 2 for 1.76-2.62, or 3 for 2.63-3.50. These are equal "
        "technical bands for an indicative estimate, not cutoffs defined by the manual; "
        "the per-criterion 0-3 probability scale is also an internal estimate, not an official "
        "grading scale. Follow only the official rubric when estimating points. Do not include "
        "optional improvements from supplementary guides in the score. "
        "Do not include the separate 0.5 formal/ABNT criterion, debate, or final dissertation. "
        "This scoring call must not draft or rewrite any part of the work. Never invent legal "
        "authorities or claim this is an official grade. Base the estimate on the supplied report "
        "content only."
    ),
}

AI_CASE_SCORE_LEVELS = [
    "0 — Insuficiente: the criterion is absent or the text shows a substantial deficiency.",
    "1 — Partial, closer to insufficient: some evidence exists, but major gaps remain. This is an internal estimate, not a separate level in the official rubric.",
    "2 — Partial, closer to adequate: substantial evidence exists, with relevant gaps remaining. This is an internal estimate, not a separate level in the official rubric.",
    "3 — Adequado: the supplied text substantially meets the criterion described in the manual.",
]

AI_CASE_PROBABILITY_THRESHOLD = 0.7

AI_CASE_CHECKLIST_LEVELS = [
    "This is a formative self-review of the selected checklist item, not the professor's official grade. Assess only the exact item being checked; do not turn optional style or structure suggestions into requirements.",
    "0 — The supplied text contains no evidence that this checklist item is met.",
    "1 — Weak evidence: the item appears mostly unmet or materially incomplete.",
    "2 — Partial evidence: some requirements are met, but relevant gaps remain.",
    "3 — Clear evidence in the supplied text that this checklist item is met.",
]

AI_CASE_CHECKLISTS = {
    "case_description": {
        "title": "Descrição do caso",
        "fields": ("assignment_prompt", "case_facts", "legal_question"),
        "checks": {
            "facts-neutral": {
                "label": "Mantive a descrição sem antecipar solução ou julgamento.",
                "instructions": "Assess only whether the facts narrative itself presents events neutrally without arguing for a legal outcome. Do not treat ordinary factual selection as bias. This is a formative writing suggestion, not an official grading requirement unless the professor expressly requires it.",
            },
            "facts-relevant": {
                "label": "Apresentei quem, o que, contexto e conflito e cortei o que não altera o caso.",
                "instructions": "Assess whether the supplied narrative identifies relevant actors, events, context and the dispute, and appears focused on facts connected to the legal question. Do not require facts absent from the source prompt. Treat cutting every nonessential detail as a writing suggestion, not a separate official score requirement.",
            },
            "problem-question": {
                "label": "A seção termina com uma pergunta jurídica clara, não respondível apenas com sim ou não.",
                "instructions": "Assess whether the legal problem is clearly phrased and connected to the supplied facts. A literal question mark, open-question phrasing, or this exact placement at the end is a suggested presentation technique, not a score requirement unless the professor expressly requires it.",
            },
            "facts-original": {
                "label": "Reescrevi os fatos com minhas próprias palavras, sem copiar o enunciado.",
                "instructions": (
                    "The guide requires an original facts narrative in the student's own words. "
                    "Use the professor's text in assignment_prompt as the comparison source only "
                    "when it includes the original case narrative. If it contains only general "
                    "instructions or no source narrative, do not infer what the original said and "
                    "mark the comparison as uncertain. Assess only distinctive wording that appears "
                    "copied, not whether the underlying "
                    "facts or legal problem are the same. Ignore unavoidable overlap such as names, "
                    "dates, legal terms, statutory language, facts necessary to describe the dispute, "
                    "and short common phrases. Similar meaning with genuinely different wording is "
                    "paraphrase, not copying. If wording is common, legally prescribed, or ambiguous, "
                    "choose an uncertain/partial level. Never accuse the student of plagiarism or "
                    "provide a plagiarism percentage; assess only textual evidence in these two texts."
                ),
            },
        },
    },
    "case_decisions": {
        "title": "Decisões possíveis",
        "fields": (
            "case_facts",
            "legal_question",
            "conceptual_basis",
            "possible_decision_a",
            "possible_decision_b",
        ),
        "checks": {
            "decisions-clear": {
                "label": "As duas decisões possíveis estão formuladas com clareza.",
                "instructions": "Assess whether possible decisions are clearly identifiable and stated as legal outcomes rather than repetitions of facts. A separate conceptual subsection or a fixed a/b layout is optional unless the professor expressly requires it. Do not demand a fixed two-thesis format if the supplied report identifies the case as open.",
            },
            "decisions-balanced": {
                "label": "As alternativas têm peso jurídico comparável.",
                "instructions": "Compare whether the alternatives are presented as plausible positions with reasonably comparable framing, without deciding which is legally correct. For a case identified as open, assess whether competing lines are explored without prematurely declaring a winner.",
            },
            "decisions-neutral": {
                "label": "A base conceitual e a apresentação não indicam uma preferência.",
                "instructions": "As a formative suggestion, assess whether the presentation of alternatives is reasonably balanced and avoids prejudging the outcome. This is not a separate official grading requirement unless the professor expressly requires it.",
            },
        },
    },
    "thesis_a": {
        "title": "Argumentação da tese A",
        "fields": (
            "case_facts",
            "legal_question",
            "conceptual_basis",
            "thesis_a_title",
            "thesis_a_argument",
        ),
        "checks": {
            "thesis-a-integrated": {
                "label": "Entrelacei legislação, doutrina e jurisprudência na argumentação.",
                "instructions": "As a formative suggestion, assess whether legislation, doctrine, and jurisprudence support the argument and relate to the case. The official rubric's three-or-more-work threshold applies to the whole report and cannot be checked from this single-thesis excerpt; do not require a fixed number of works in this section or two per thesis. Interweaving every source type in each paragraph is optional. Do not claim works belong to the FACSUR Virtual Library or verify existence, currency, or legal accuracy.",
            },
            "thesis-a-comment": {
                "label": "Expliquei com palavras próprias a relevância das citações para o caso.",
                "instructions": "As a formative suggestion, assess whether the student explains how cited law, doctrine, and judicial holdings relate to the case. Commentary after every direct quotation is not a separate official grading requirement unless the professor expressly requires it.",
            },
            "thesis-a-neutral": {
                "label": "Mantive a análise equilibrada e redigida em terceira pessoa.",
                "instructions": "As a formative suggestion, note first-person phrasing or opportunities to present the argument fairly. Exclusive third-person writing is not a separate official grading requirement unless the professor expressly requires it. Do not penalize ordinary attribution of arguments to parties. The report should not be required to choose the final winning position if that belongs to a later dissertation.",
            },
        },
    },
    "thesis_b": {
        "title": "Argumentação da tese B",
        "fields": (
            "case_facts",
            "legal_question",
            "conceptual_basis",
            "thesis_b_title",
            "thesis_b_argument",
        ),
        "checks": {
            "thesis-b-integrated": {
                "label": "Entrelacei legislação, doutrina e jurisprudência na argumentação.",
                "instructions": "As a formative suggestion, assess whether legislation, doctrine, and jurisprudence support the argument and relate to the case. The official rubric's three-or-more-work threshold applies to the whole report and cannot be checked from this single-thesis excerpt; do not require a fixed number of works in this section or two per thesis. Interweaving every source type in each paragraph is optional. Do not claim works belong to the FACSUR Virtual Library or verify existence, currency, or legal accuracy.",
            },
            "thesis-b-comment": {
                "label": "Expliquei com palavras próprias a relevância das citações para o caso.",
                "instructions": "As a formative suggestion, assess whether the student explains how cited law, doctrine, and judicial holdings relate to the case. Commentary after every direct quotation is not a separate official grading requirement unless the professor expressly requires it.",
            },
            "thesis-b-neutral": {
                "label": "Mantive a análise equilibrada e redigida em terceira pessoa.",
                "instructions": "As a formative suggestion, note first-person phrasing or opportunities to present the argument fairly. Exclusive third-person writing is not a separate official grading requirement unless the professor expressly requires it. Do not penalize ordinary attribution of arguments to parties. The report should not be required to choose the final winning position if that belongs to a later dissertation.",
            },
        },
    },
    "criteria_and_values": {
        "title": "Critérios e valores",
        "fields": ("thesis_a_argument", "thesis_b_argument", "criteria_and_values"),
        "checks": {
            "criteria-defined": {
                "label": "Defini os conceitos técnicos relevantes e indiquei o fundamento de cada definição.",
                "instructions": "As a formative suggestion, assess whether listed concepts have clear definitions and a stated normative or ethical basis. A separate glossary defining every term is optional unless the professor expressly requires it.",
            },
            "criteria-covered": {
                "label": "Conferi se os termos técnicos usados nas teses estão explicados nesta seção.",
                "instructions": "As a formative suggestion, compare important case-specific concepts in the arguments with those explained in this section. A comprehensive glossary is optional unless the professor expressly requires one. Ignore ordinary legal vocabulary."
            },
        },
    },
}

AI_CASE_UNASSESSABLE_CHECKS = {
    "case_description": ("facts-original",),
    "case_decisions": (),
    "thesis_a": ("thesis-a-length",),
    "thesis_b": ("thesis-b-length",),
    "criteria_and_values": (),
}
