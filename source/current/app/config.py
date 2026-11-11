"""Centralized configuration constants - Assistente Acadêmico.

All magic strings, numbers, and configuration values are defined here
to improve maintainability and avoid duplication.
"""
from __future__ import annotations

import os
from pathlib import Path

# =============================================================================
# Application Constants
# =============================================================================

APP_NAME = "Assistente Acadêmico"
APP_VERSION = "2.0.0"

# =============================================================================
# Database Constants
# =============================================================================

DB_SCHEMA_VERSION = 12
DB_WAL_MODE = True
DB_BUSY_TIMEOUT = 5000  # ms

# =============================================================================
# Project Constants
# =============================================================================

PROJECT_TYPES = ("case", "paper_project", "paper_final")
PROJECT_PHASES = ("report", "debate", "dissertation", "paper_project", "paper_final")

# Field limits
FIELD_LIMITS = {
    "title": 240,
    "institution": 160,
    "course": 160,
    "city": 160,
    "assignment_prompt": 12000,
    "facts": 16000,
    "problem": 5000,
    "decision_basis": 12000,
    "decision_a": 6000,
    "decision_b": 6000,
    "thesis_a_title": 240,
    "thesis_a": 16000,
    "thesis_b_title": 240,
    "thesis_b": 16000,
    "criteria": 12000,
    "research_object": 5000,
    "problem_context": 8000,
    "hypothesis": 8000,
    "objective_general": 5000,
    "introduction": 16000,
    "conclusion": 16000,
    "abstract": 8000,
    "keywords": 1000,
    "development": 30000,
    "criterion_title": 180,
    "criterion_definition": 3000,
    "criterion_basis": 1000,
    "development_title": 240,
    "development_body": 30000,
    "source_title": 240,
    "source_author": 240,
    "source_reference": 500,
    "source_notes": 2000,
}

# Maximum counts
MAX_CRITERIA = 40
MAX_DEVELOPMENT_SECTIONS = 20
MAX_SOURCES = 60
MAX_SUGGESTIONS = 4
MAX_CHECKLIST_ITEMS = 30
MAX_AI_MESSAGES = 12

# =============================================================================
# AI Provider Constants
# =============================================================================

# Timeouts (seconds) - configurable via environment variables
DEFAULT_PROVIDER_TIMEOUT = int(os.environ.get("PROVIDER_TIMEOUT", "30"))
DEFAULT_DEEPSEEK_TIMEOUT = int(os.environ.get("DEEPSEEK_TIMEOUT", "30"))
DEFAULT_GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "30"))
DEFAULT_JEV_TIMEOUT = int(os.environ.get("JEV_TIMEOUT", "60"))

# API endpoints
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

GEMINI_API_URL = os.environ.get("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

TYPESAFE_API_URL = os.environ.get("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone")
TYPESAFE_MODEL = os.environ.get("TYPESAFE_MODEL", "jev-latest")

# Token limits
PROJECT_AI_MAX_OUTPUT_TOKENS = int(os.environ.get("PROJECT_AI_MAX_OUTPUT_TOKENS", "2200"))
PROJECT_AI_REVIEW_MAX_TOKENS = int(os.environ.get("PROJECT_AI_REVIEW_MAX_TOKENS", "1400"))

# Fallback configuration
FALLBACK_ERROR_CODES = {
    "provider_busy",
    "provider_unreachable",
    "provider_auth",
    "provider_quota",
    "secret_unavailable",
    "secret_invalid",
    "invalid_response",
    "response_too_large",
}

# =============================================================================
# JEV Constants
# =============================================================================

JEV_SECTIONS = ("case_description", "case_decisions", "thesis_a", "thesis_b", "criteria_and_values")

# Score levels
JEV_SCORE_LEVELS = {
    0: "Insuficiente",
    1: "Parcial (mais próximo do insuficiente)",
    2: "Parcial (mais próximo do adequado)",
    3: "Adequado",
}

JEV_CHECKLIST_LEVELS = {
    0: "Sem evidência",
    1: "Evidência fraca",
    2: "Evidência parcial",
    3: "Evidência clara",
}

# Probability threshold for JEV assessments
JEV_PROBABILITY_THRESHOLD = 0.7

# Grade ranges (points out of 3.5)
JEV_GRADE_RANGES = [
    (0, 0.00, 0.87),
    (1, 0.88, 1.75),
    (2, 1.76, 2.62),
    (3, 2.63, 3.50),
]

# =============================================================================
# Rate Limiting Constants
# =============================================================================

RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour window
_RATE_LIMIT_MAX_KEYS = 10000  # Max keys in memory before cleanup

RATE_LIMITS = {
    "project_create": 10,
    "ai_analysis": 50,
    "ai_jev_section": 30,
    "ai_jev_report": 10,
    "ai_jev_explanation": 20,
    "legal_recommendations": 20,
    "pdf_export": 30,
    "duplicate": 5,
}

# Detailed rate limit config (for new granular rate limiting)
RATE_LIMIT_ACTIONS = {
    "project_create": {"limit": 10, "window": 3600},
    "ai_analysis": {"limit": 50, "window": 3600},
    "ai_jev_section": {"limit": 30, "window": 3600},
    "ai_jev_report": {"limit": 10, "window": 3600},
    "ai_jev_explanation": {"limit": 20, "window": 3600},
    "legal_recommendations": {"limit": 20, "window": 3600},
    "pdf_export": {"limit": 30, "window": 3600},
    "duplicate": {"limit": 5, "window": 3600},
}

# =============================================================================
# File/Export Constants
# =============================================================================

# PDF Export
QUARTO_EXPORT_TIMEOUT = 300  # seconds
MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB

# Account Export (LGPD)
EXPORT_MAX_FILES = 100
EXPORT_MAX_SIZE = 100 * 1024 * 1024  # 100 MB

# =============================================================================
# Session/Auth Constants
# =============================================================================

SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE = 30 * 24 * 3600  # 30 days
CSRF_TOKEN_LENGTH = 32
PKCE_CODE_VERIFIER_LENGTH = 64

# =============================================================================
# Security Headers
# =============================================================================

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://api.deepseek.com https://generativelanguage.googleapis.com https://api.typesafe.ai; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
}

# =============================================================================
# Google OAuth Constants
# =============================================================================

GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_OAUTH_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_OAUTH_SCOPES = ["openid", "email", "profile"]

# =============================================================================
# Quarto/Typst Constants
# =============================================================================

QUARTO_CLI = os.environ.get("QUARTO_CLI", "quarto")
TYPST_CLI = os.environ.get("TYPST_CLI", "typst")
QUARTO_PROJECT_DIR = Path(os.environ.get("QUARTO_PROJECT_DIR", "/tmp/quarto_projects"))
QUARTO_OUTPUT_DIR = Path(os.environ.get("QUARTO_OUTPUT_DIR", "/tmp/quarto_output"))

# ABNT extension
QUARTO_ABNT_EXTENSION = "abnt"

# =============================================================================
# Notification Constants
# =============================================================================

NOTIFICATION_KINDS = (
    "project_created",
    "project_shared",
    "comment_added",
    "ai_analysis_complete",
    "pdf_export_ready",
    "admin_message",
)

NOTIFICATION_MAX_RETRIES = 5
NOTIFICATION_RETRY_DELAY = 300  # seconds
NOTIFICATION_MAX_DELAY = 86400  # 24 hours

# =============================================================================
# Admin/Plans Constants
# =============================================================================

DEFAULT_PLAN = "free"
PLAN_CODES = ("free", "basic", "pro", "institutional")

PLAN_LABELS = {
    "free": "Grátis",
    "basic": "Básico",
    "pro": "Profissional",
    "institutional": "Institucional",
}

MAX_ACCOUNT_LIMIT = 1000  # Maximum number of accounts per instance

PLAN_LIMITS = {
    "free": {"projects": 3, "ai_analysis": 10, "deepseek_explanation": 5, "pdf_exports": 5},
    "basic": {"projects": 10, "ai_analysis": 50, "deepseek_explanation": 20, "pdf_exports": 20},
    "pro": {"projects": 50, "ai_analysis": 200, "deepseek_explanation": 100, "pdf_exports": 100},
    "institutional": {"projects": -1, "ai_analysis": -1, "deepseek_explanation": -1, "pdf_exports": -1},
}

# =============================================================================
# Legal Recommendations Constants
# =============================================================================

LEGAL_CATALOG_KINDS = ("legislation", "case-law", "book")
LEGAL_SEARCH_LIMIT = 8
LEGAL_MAX_KEYWORDS = 20
LEGAL_MAX_RECOMMENDATIONS = 10

# =============================================================================
# Revision Constants
# =============================================================================

REVISION_RETENTION_DAYS = 30
MAX_REVISIONS_PER_PROJECT = 100

# =============================================================================
# Deletion Request Constants
# =============================================================================

DELETION_REQUEST_STATUSES = ("pending", "accepted", "rejected")
DELETION_REQUEST_EXPIRY_DAYS = 30

# =============================================================================
# Pagination
# =============================================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100