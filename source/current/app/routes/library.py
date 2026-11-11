from flask import Blueprint, abort, redirect, render_template, request, url_for

from ..auth import current_account_id, login_required, require_csrf
from ..store.sources import create_source, delete_source, list_sources, update_source


library_bp = Blueprint("library", __name__)

SOURCE_KIND_LABELS = {
    "book": "Livro",
    "article": "Artigo",
    "legislation": "Legislação",
    "case_law": "Jurisprudência",
    "website": "Site",
    "other": "Outro",
}


def _render_home(*, saved: str = "", editing_id: str = ""):
    account_id = current_account_id()
    return render_template(
        "library/home.html",
        sources=list_sources(account_id),
        source_kind_labels=SOURCE_KIND_LABELS,
        saved=saved,
        editing_id=editing_id,
    )


@library_bp.get("/library")
@login_required
def home():
    return _render_home(saved=request.args.get("saved", ""))


@library_bp.post("/library/sources")
@login_required
@require_csrf
def add_source():
    title = request.form.get("title", "").strip()
    if not title:
        abort(400, description="Informe o título da fonte.")
    create_source(
        current_account_id(),
        title,
        request.form.get("author", ""),
        request.form.get("kind", "other"),
        request.form.get("reference", ""),
        request.form.get("notes", ""),
    )
    return redirect(url_for("library.home", saved="source"))


@library_bp.get("/library/sources/<source_id>/edit")
@login_required
def edit_source(source_id):
    source = next(
        (item for item in list_sources(current_account_id()) if item["id"] == source_id),
        None,
    )
    if source is None:
        abort(404)
    return _render_home(editing_id=source_id)


@library_bp.post("/library/sources/<source_id>")
@library_bp.post("/library/sources/<source_id>/edit")
@login_required
@require_csrf
def save_source(source_id):
    title = request.form.get("title", "").strip()
    if not title:
        abort(400, description="Informe o título da fonte.")
    if not update_source(
        current_account_id(),
        source_id,
        title,
        request.form.get("author", ""),
        request.form.get("kind", "other"),
        request.form.get("reference", ""),
        request.form.get("notes", ""),
    ):
        abort(404)
    return redirect(url_for("library.home", saved="source-updated"))


@library_bp.post("/library/sources/<source_id>/delete")
@login_required
@require_csrf
def delete_source_route(source_id):
    if not delete_source(current_account_id(), source_id):
        abort(404)
    return redirect(url_for("library.home", saved="source-deleted"))


@library_bp.delete("/library/sources/<source_id>")
@login_required
@require_csrf
def delete_source_http(source_id):
    if not delete_source(current_account_id(), source_id):
        abort(404)
    return ("", 204)
