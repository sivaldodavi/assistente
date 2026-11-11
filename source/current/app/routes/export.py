from flask import Blueprint, Response, abort, request

from ..auth import current_account_id, login_required
from ..services.export import ExportUnavailable, build_project_html, render_pdf
from ..store.projects import get_project
from ..store.sources import list_sources


export_bp = Blueprint("export", __name__)


@export_bp.get("/projects/<project_id>/export")
@login_required
def project_export(project_id):
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)
    if project['project_type'] == 'case':
        phase = request.args.get('phase', 'report')
        if phase not in {'report', 'debate', 'dissertation'}:
            abort(400, description='Documento inválido.')
        project['export_phase'] = phase
    source_ids = set(project.get("source_ids", []))
    sources = [source for source in list_sources(current_account_id()) if source["id"] in source_ids]
    export_format = request.args.get("format", "html")
    if export_format == "html":
        return Response(build_project_html(project, sources), mimetype="text/html")
    if export_format == "pdf":
        try:
            pdf = render_pdf(project, sources)
        except ExportUnavailable as error:
            abort(503, description=str(error))
        except Exception:
            abort(503, description="Não foi possível gerar o PDF neste momento.")
        return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": "attachment; filename=assistente-academico.pdf"})
    abort(400, description="Formato de exportação inválido.")
