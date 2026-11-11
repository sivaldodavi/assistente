"""TypedDict contracts for domain models - Assistente Acadêmico.

This module provides type-safe contracts for all domain data structures,
enabling static type checking and improving maintainability.
"""
from __future__ import annotations

from typing import TypedDict, Optional, Literal
try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired
from uuid import UUID


# =============================================================================
# Project Types
# =============================================================================

ProjectType = Literal["case", "paper_project", "paper_final"]
ProjectPhase = Literal["report", "debate", "dissertation", "paper_project", "paper_final"]


class ProjectFieldRules(TypedDict):
    limit: int
    required: NotRequired[bool]


class ProjectFields(TypedDict):
    """Base project fields that can appear in any project type."""
    title: str
    institution: str
    course: str
    city: str
    assignment_prompt: str
    # Case-specific fields
    facts: str
    problem: str
    decision_basis: str
    decision_a: str
    decision_b: str
    thesis_a_title: str
    thesis_a: str
    thesis_b_title: str
    thesis_b: str
    criteria: str
    # Paper-specific fields
    research_object: str
    problem_context: str
    hypothesis: str
    objective_general: str
    introduction: str
    conclusion: str
    abstract: str
    keywords: str
    development: str


class CriterionDict(TypedDict):
    id: str
    title: str
    definition: str
    basis: str


class DevelopmentSectionDict(TypedDict):
    id: str
    title: str
    body: str


class SourceDict(TypedDict):
    id: str
    title: str
    author: str
    kind: str
    reference: str
    notes: str


class DeliveryDict(TypedDict):
    delivered: bool
    at: int


class DeliveriesDict(TypedDict):
    report: NotRequired[DeliveryDict]
    dissertation: NotRequired[DeliveryDict]
    paper_project: NotRequired[DeliveryDict]
    paper_final: NotRequired[DeliveryDict]


class WorkflowCheckDict(TypedDict):
    """Dictionary of workflow check IDs to their completed state."""
    pass


class ProjectPayload(TypedDict):
    """Complete project payload for autosave and API operations."""
    version: int
    fields: ProjectFields
    source_ids: list[str]
    criteria: list[CriterionDict]
    schedule: dict
    deliveries: DeliveriesDict
    checks: WorkflowCheckDict
    development_sections: list[DevelopmentSectionDict]


# =============================================================================
# AI Action Types
# =============================================================================

AIActionName = Literal[
    "review", "chat", "checklist", "proposal_chat", "suggest_problem",
    "suggest_theses", "case_structure", "research", "review_criteria",
    "review_references", "review_development", "debate_coach"
]

SuggestionActionName = Literal[
    "proposal_chat", "suggest_problem", "suggest_theses", "case_structure",
    "review_criteria", "review_references", "review_development"
]


class AISuggestionItem(TypedDict):
    field_id: str
    text: str
    declined: NotRequired[bool]
    notice: NotRequired[str]


class AIChecklistItem(TypedDict):
    id: str
    confidence: float
    evidence: str


class AIResponse(TypedDict):
    answer: str
    suggestions: list[AISuggestionItem]
    rewrite: str
    checklist: list[AIChecklistItem]


class AIContext(TypedDict):
    """Context sent to AI providers."""
    action: AIActionName
    message: str
    instruction: str
    messages: list[dict]
    field_id: str
    project_type: ProjectType
    project_context: dict
    source_ids: list[str]
    development_ids: list[str]
    criterion_ids: list[str]
    checklist: list[dict]
    evidence_fields: list[str]
    selected_text: NotRequired[str]
    search_web: NotRequired[bool]
    assignment_prompt: str
    title: str
    case_facts: str
    legal_question: str
    conceptual_basis: str
    possible_decision_a: str
    possible_decision_b: str
    thesis_a_title: str
    thesis_a_argument: str
    thesis_b_title: str
    thesis_b_argument: str
    criteria_and_values: str
    research_object: str
    problem_context: str
    hypothesis: str
    objective_general: str
    introduction: str
    conclusion: str
    abstract: str
    keywords: str
    development: str
    fields: dict
    sources: NotRequired[list[SourceDict]]


# =============================================================================
# JEV Types
# =============================================================================

class JEVScoreAnswer(TypedDict):
    score: int
    confidence: float
    probabilities: list[float]
    observation: str


class JEVCriterionResult(TypedDict):
    id: str
    label: str
    score: int
    confidence: float
    probabilities: list[float]
    observation: str


class JEVSectionResult(TypedDict):
    model: str
    section: str
    criteria: list[JEVCriterionResult]
    probability_threshold: float
    unassessed_checks: list[str]
    usage: dict


class JEVReportResult(TypedDict):
    model: str
    criteria: list[JEVCriterionResult]
    expected_points: float
    assessable_points: float
    grade_range: dict
    probability_threshold: float
    unassessed_points: float
    usage: dict


class JEVValidationResult(TypedDict):
    status: Literal["adequado", "revisar", "nao_avaliado"]
    observations: list[str]
    proposal_present: bool


class JEVExplanation(TypedDict):
    interpretation: str
    evidence: list[str]
    next_steps: list[str]
    model: str
    provider: str


# =============================================================================
# Provider Types
# =============================================================================

ProviderName = Literal["deepseek", "gemini", "jev"]

class ProviderUsage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    prompt_cache_hit_tokens: NotRequired[int]


class ProviderResponse(TypedDict):
    model: str
    result: dict
    usage: ProviderUsage
    provider: ProviderName
    fallback_reason: NotRequired[str]


# =============================================================================
# Research Catalog Types
# =============================================================================

CatalogKind = Literal["legislation", "case-law", "book"]

class CatalogEntry(TypedDict):
    id: str
    kind: CatalogKind
    title: str
    reference: str
    author: str
    abstract: str
    source_year: int
    source: str
    link: NotRequired[str]


class CatalogSearchResult(TypedDict):
    entries: list[CatalogEntry]


# =============================================================================
# Account/Sharing Types
# =============================================================================

class AccountProfile(TypedDict):
    id: str
    email: str
    name: str
    avatar_url: str
    terms_accepted: bool
    ai_consent: bool
    sharing_allow_admin_view: bool
    sharing_allow_admin_comments: bool
    sharing_inherit_default: bool
    deletion_request_pending: bool
    ai_analysis_limit: int
    deepseek_explanation_limit: int
    project_credits: int
    project_consumed: int


class ProjectSharingPreferences(TypedDict):
    allow_admin_view: bool
    allow_admin_comments: bool
    inherit_account_default: bool


# =============================================================================
# Rate Limiting Types
# =============================================================================

RateLimitAction = Literal[
    "project_create", "ai_analysis", "ai_jev_section", "ai_jev_report",
    "ai_jev_explanation", "legal_recommendations", "pdf_export", "duplicate"
]

class RateLimitInfo(TypedDict):
    limit: int
    window_seconds: int
    current: int
    remaining: int
    reset_at: int