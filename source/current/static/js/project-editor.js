/**
 * Project Editor - Main Entry Point
 * Orchestrates all editor modules: autosave, schedule, AI, JEV, PDF export, duplicate, revisions
 */

import { createAutosave } from "./autosave.js";
import { initScheduleEditor, collectSchedule } from "./project-schedule.js";
import { initEditorAi } from "./project-ai.js";
import { initPdfExport } from "./pdf-export.js";
import { initDuplicate } from "./duplicate.js";
import { initRevisions } from "./revisions.js";
import { initJevPanel } from "./jev-panel.js";

const form = document.querySelector("[data-project-editor]");

if (!form) {
  // Editor not on this page
} else {
  // Initialize autosave with payload collector
  const collectPayload = () => ({
    version: 1,
    fields: collectFields(form),
    source_ids: [...new Set([...form.querySelectorAll("[data-project-source]:checked")].map((input) => input.value))],
    criteria: collectCriteria(form),
    schedule: collectSchedule(form),
    deliveries: collectDeliveries(form),
    checks: Object.fromEntries([...form.querySelectorAll("[data-workflow-check]")].map((input) => [input.dataset.workflowCheck, input.checked])),
    development_sections: [...form.querySelectorAll("[data-development]")].map((card) => ({
      id: card.dataset.developmentId,
      title: card.querySelector("[data-development-title]").value,
      body: card.querySelector("[data-development-body]").value,
    })),
  });

  const { flushSave, save, markDirty, hasConflict } = createAutosave({
    form,
    collectPayload,
    saveUrl: form.dataset.saveUrl,
    onStateChange: (state) => { /* state changes handled by autosave */ }
  });

  async function readJson(response) {
    const text = await response.text();
    if (!text) return {};
    try {
      return JSON.parse(text);
    } catch {
      return {};
    }
  }

  // Helper functions for payload collection
  function collectFields(form) {
    const fields = Object.fromEntries([...form.querySelectorAll("[data-case-field]")].map((element) => [element.dataset.caseField, element.value]));
    const title = fields.title || form.querySelector("[data-project-title]")?.value || "";
    return { ...fields, title };
  }

  function collectCriteria(form) {
    return [...form.querySelectorAll("[data-criterion]")].map((card) => {
      const value = (key) => card.querySelector(`[data-criterion-field="${key}"]`)?.value || "";
      return { id: card.dataset.criterionId || crypto.randomUUID(), title: value("title"), definition: value("definition"), basis: value("basis") };
    });
  }

  function collectDeliveries(form) {
    return Object.fromEntries([...form.querySelectorAll("[data-delivery-state]")]
      .filter((node) => node.dataset.delivered === "true")
      .map((node) => [node.dataset.deliveryKey, { delivered: true, at: Number(node.dataset.deliveredAt || 0) }]));
  }

  // Criterion management
  function addCriterionCard() {
    const list = form.querySelector("[data-criteria-list]");
    if (!list) return;
    const card = document.createElement("fieldset");
    card.className = "criterion-card";
    card.dataset.criterion = "";
    card.dataset.criterionId = crypto.randomUUID();
    card.innerHTML = `<legend>Critério</legend><label>Nome<input data-criterion-field="title" maxlength="180"></label><label>Definição<textarea data-criterion-field="definition" maxlength="3000" rows="4"></textarea></label><label>Base ou fundamento<input data-criterion-field="basis" maxlength="1000"></label><button type="button" class="quiet-button danger" data-remove-criterion>Remover critério</button>`;
    list.append(card);
    card.querySelector("[data-criterion-field]").focus();
    markDirty();
  }

  form.querySelector("[data-add-criterion]")?.addEventListener("click", addCriterionCard);
  form.addEventListener("click", (event) => {
    if (event.target.closest("[data-remove-criterion]")) {
      event.target.closest("[data-criterion]").remove();
      markDirty();
    }
  });

  // Schedule editor
  initScheduleEditor(form, () => markDirty());

  // PDF Export (Quarto)
  initPdfExport({ form, flushSave, readJson });

  // Duplicate Project
  initDuplicate({ form, flushSave, readJson });

  // Revisions
  initRevisions({ form, readJson, setSaveState: (msg) => { const saveState = form.querySelector("[data-save-state]"); if (saveState) saveState.textContent = msg; } });

  // JEV Panel
  initJevPanel({ form, flushSave, readJson, collectPayload });

  // Export links (external links that need save first)
  form.querySelectorAll("[data-export-link]").forEach((link) => link.addEventListener("click", async (event) => {
    event.preventDefault();
    const target = link.target === "_blank" ? window.open("about:blank", "_blank") : null;
    if (!await flushSave()) { target?.close(); const saveState = form.querySelector("[data-save-state]"); if (saveState) saveState.textContent = "Salve as alterações antes de exportar."; return; }
    if (target) { target.opener = null; target.location.href = link.href; } else window.location.href = link.href;
  }));

  // Paper mode switch
  form.querySelectorAll("[data-paper-mode]").forEach((button) => button.addEventListener("click", async () => {
    const saveState = form.querySelector("[data-save-state]");
    button.disabled = true;
    try {
      if (!await flushSave()) throw new Error("Salve as alterações antes de trocar a etapa do Paper.");
      const response = await fetch(button.dataset.modeUrl, { method: "POST", headers: {"Content-Type": "application/json", "X-CSRF-Token": form.querySelector("[name=csrf_token]").value}, body: JSON.stringify({project_type: button.dataset.paperMode, revision: Number(form.dataset.revision)}) });
      if (!response.ok) throw new Error("Não foi possível trocar o roteiro. Reabra a versão do servidor.");
      window.location.hash = "";
      window.location.reload();
    } catch (error) { if (saveState) saveState.textContent = error.message; button.disabled = false; }
  }));

  // Stage navigation (keep in main as it coordinates with other modules)
  initStageNavigation(form, flushSave, markDirty);

  // Development sections
  initDevelopmentSections(form, markDirty);

  // Initialize editor AI (rich AI actions)
  initEditorAi({ form, readJson, markDirty, flushSave, stages: [...(form.querySelectorAll("[data-stage]") || [])], showStep: window.showStep, createInlineSource: window.createInlineSource, appendProjectSource: window.appendProjectSource });
}

// ============================================================================
// Stage Navigation (coordinated with other modules)
// ============================================================================
function initStageNavigation(form, flushSave, markDirty) {
  const stages = [...(form?.querySelectorAll("[data-stage]") || [])];
  const stepButtons = [...(form?.querySelectorAll("[data-step]") || [])];
  let activeStep = 0;

  window.showStep = function showStep(index, focus = false) {
    if (!stages.length) return;
    activeStep = Math.max(0, Math.min(index, stages.length - 1));
    stages.forEach((stage, i) => { stage.hidden = i !== activeStep; });
    const phase = stages[activeStep].dataset.stagePhase;
    stepButtons.forEach((button, i) => {
      button.setAttribute("aria-current", i === activeStep ? "step" : "false");
      button.classList.toggle("is-other-phase", button.dataset.stepPhase !== phase);
    });
    form.querySelectorAll("[data-phase]").forEach((button) => button.setAttribute("aria-pressed", button.dataset.phase === phase ? "true" : "false"));
    form.querySelectorAll("[data-nav-phase]").forEach((node) => node.classList.toggle("is-other-phase", node.dataset.navPhase !== phase));
    form.querySelector("[data-previous-step]").disabled = activeStep === 0;
    form.querySelector("[data-next-step]").textContent = activeStep === stages.length - 1 ? "Voltar à identificação" : "Continuar";
    history.replaceState(null, "", `#stage-${stages[activeStep].dataset.stage}`);
    updateProgress(form, stages, activeStep, stepButtons, phase);
    if (focus) {
      stages[activeStep].querySelector("h2").focus({ preventScroll: true });
      form.querySelector(".workspace").scrollIntoView({ behavior: "auto", block: "start" });
    }
  };

  function updateProgress(form, stages, activeStep, stepButtons, phase) {
    if (!stages.length) return;
    const phaseStages = stages.filter((stage) => stage.dataset.stagePhase === phase);
    const required = phaseStages.flatMap((stage) => [...stage.querySelectorAll("[data-required-field]")]);
    const done = required.filter((input) => input.value.trim()).length;
    const percent = required.length ? Math.round(done / required.length * 100) : 0;
    form.querySelector("[data-progress-count]").textContent = `${done}/${required.length} campos · ${percent}%`;
    form.querySelector("[data-progress-bar]").style.width = `${percent}%`;
    const labels = { report: "Relatório", debate: "Debate", dissertation: "Dissertação", paper_project: "Projeto de Paper", paper_final: "Paper Final" };
    form.querySelector("[data-progress-label]").textContent = `Progresso · ${labels[phase]}`;
    stages.forEach((stage, i) => {
      const inputs = [...stage.querySelectorAll("[data-required-field], [data-workflow-check]")];
      const complete = inputs.length > 0 && inputs.every((input) => input.type === "checkbox" ? input.checked : input.value.trim());
      const status = stepButtons[i].querySelector(".step-status");
      status.textContent = complete ? "✓" : "·";
      status.setAttribute("aria-label", complete ? "Etapa completa" : "Etapa incompleta");
    });
    const title = form.querySelector('[data-case-field="title"]')?.value.trim();
    const heading = document.querySelector("[data-editor-title]");
    if (heading && title) heading.textContent = title;
  }

  stepButtons.forEach((button, i) => button.addEventListener("click", () => window.showStep(i, true)));
  form?.querySelectorAll("[data-phase]").forEach((button) => button.addEventListener("click", () => window.showStep(stages.findIndex((stage) => stage.dataset.stagePhase === button.dataset.phase), true)));
  form?.querySelector("[data-previous-step]")?.addEventListener("click", () => window.showStep(activeStep - 1, true));
  form?.querySelector("[data-next-step]")?.addEventListener("click", () => window.showStep(activeStep === stages.length - 1 ? 0 : activeStep + 1, true));
  const restoredStep = stages.findIndex((stage) => `#stage-${stage.dataset.stage}` === location.hash);
  window.showStep(restoredStep >= 0 ? restoredStep : 0);
  window.addEventListener("hashchange", () => { const index = stages.findIndex((stage) => `#stage-${stage.dataset.stage}` === location.hash); if (index >= 0) window.showStep(index); });
}

// ============================================================================
// Development Sections
// ============================================================================
function initDevelopmentSections(form, markDirty) {
  form?.querySelector("[data-add-development]")?.addEventListener("click", () => {
    const list = form.querySelector("[data-development-list]");
    const card = document.createElement("fieldset");
    card.className = "development-section";
    card.dataset.development = "";
    card.dataset.developmentId = crypto.randomUUID();
    card.innerHTML = '<legend>Tópico</legend><label>Título do tópico<input data-development-title maxlength="240"></label><label>Fundamentação<textarea data-development-body data-size="large" maxlength="30000"></textarea></label><button type="button" class="text-button danger" data-remove-development>Remover tópico</button>';
    list.append(card);
    card.querySelector("input").focus();
    markDirty();
  });
  form?.addEventListener("click", (event) => {
    const remove = event.target.closest("[data-remove-development]");
    if (remove) { remove.closest("[data-development]").remove(); markDirty(); }
  });
}

// ============================================================================
// Legal Recommendations & Source Creation (keep in main for now)
// ============================================================================
function initLegalAndSources(form, readJson, markDirty, flushSave, createInlineSource, appendProjectSource) {
  function legalField(id, fallback = "") {
    return form.querySelector(`[data-case-field="${id}"]`)?.value?.trim() || fallback;
  }

  function appendProjectSource(source, checked = true) {
    const list = form.querySelector(".source-check-list");
    if (!list || !source?.id) return;
    list.querySelector(".empty-state")?.remove();
    const row = document.createElement("label");
    row.className = "check-row";
    row.innerHTML = `<input type="checkbox" data-project-source><span><strong></strong><small></small><small></small></span>`;
    const input = row.querySelector("[data-project-source]");
    input.value = source.id;
    input.checked = checked;
    row.querySelector("strong").textContent = source.title || "Fonte sem título";
    row.querySelectorAll("small")[0].textContent = source.author || "";
    row.querySelectorAll("small")[1].textContent = source.reference || "";
    list.append(row);
  }

  window.createInlineSource = async function createInlineSource(button) {
    const status = form.querySelector("[data-source-create-status]");
    const value = (name) => form.querySelector(`[data-source-create-field="${name}"]`)?.value?.trim() || "";
    const title = value("title");
    if (!title) {
      if (status) status.textContent = "Informe o título da fonte.";
      form.querySelector('[data-source-create-field="title"]')?.focus();
      return;
    }
    button.disabled = true;
    if (status) status.textContent = "Adicionando…";
    try {
      const response = await fetch(form.dataset.sourceCreateUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": form.querySelector("[name=csrf_token]").value },
        body: JSON.stringify({ title, author: value("author"), kind: value("kind"), reference: value("reference"), notes: value("notes") }),
      });
      const result = await readJson(response);
      if (!response.ok) throw new Error(result.message || "Não foi possível adicionar a fonte.");
      appendProjectSource(result.source);
      ["title", "author", "reference", "notes"].forEach((name) => {
        const field = form.querySelector(`[data-source-create-field="${name}"]`);
        if (field) field.value = "";
      });
      if (status) status.textContent = "Fonte adicionada.";
      markDirty();
    } catch (error) {
      if (status) status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  };

  function renderLegalEntry(entry, attachUrl, csrf) {
    const card = document.createElement("article");
    card.className = "legal-result-card";
    const title = document.createElement("h4");
    title.textContent = entry.title || "Fonte sem título";
    card.append(title);
    const meta = document.createElement("p");
    meta.className = "legal-result-meta";
    meta.textContent = [entry.source, entry.source_year, entry.author, entry.reference].filter(Boolean).join(" · ");
    card.append(meta);
    const why = document.createElement("p");
    why.textContent = entry.why || "Pista contextual para conferência.";
    card.append(why);
    const actions = document.createElement("div");
    actions.className = "legal-result-actions";
    const attach = document.createElement("button");
    attach.type = "button";
    attach.className = "text-button";
    attach.textContent = "Adicionar à Minha Biblioteca";
    attach.addEventListener("click", async () => {
      attach.disabled = true;
      try {
        const response = await fetch(attachUrl, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify({ source_id: entry.id }) });
        const result = await readJson(response);
        if (!response.ok) throw new Error(result.message || "Não foi possível adicionar a fonte.");
        appendProjectSource({ id: result.source_id, title: result.title, author: result.author, reference: result.reference });
        markDirty();
        attach.textContent = "Adicionada à biblioteca";
      } catch (error) {
        attach.disabled = false;
        attach.textContent = error.message;
      }
    });
    const discard = document.createElement("button");
    discard.type = "button";
    discard.className = "text-button";
    discard.textContent = "Descartar";
    discard.addEventListener("click", () => card.remove());
    actions.append(attach, discard);
    card.append(actions);
    return card;
  }

  form?.querySelector("[data-legal-recommendations]")?.addEventListener("click", async () => {
    const button = form.querySelector("[data-legal-recommendations]");
    const result = form.querySelector("[data-legal-result]");
    const problem = legalField("problem", form.dataset.legalProblem || "");
    const instructions = legalField("assignment_prompt", form.dataset.legalInstructions || "");
    const rawKeywords = form.querySelector("[data-legal-keywords]")?.value || form.dataset.legalKeywords || "";
    const keywords = rawKeywords.split(/[;,\n]/).map((item) => item.trim()).filter(Boolean).slice(0, 20);
    if (!problem) { result.textContent = "Preencha a pergunta-problema antes de pedir sugestões."; return; }
    button.disabled = true;
    result.textContent = "Consultando catálogo e assistência…";
    try {
      const response = await fetch(form.dataset.legalUrl, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-Token": form.querySelector("[name=csrf_token]").value }, body: JSON.stringify({ request_id: crypto.randomUUID(), project_revision: Number(form.dataset.revision), problem_question: problem, professor_instructions: instructions, keywords, catalog_source_ids: [] }) });
      const payload = await readJson(response);
      if (!response.ok) throw new Error(payload.message || "Não foi possível obter sugestões.");
      result.replaceChildren();
      const provider = document.createElement("p");
      provider.className = "field-hint";
      provider.textContent = "Sugestões baseadas no catálogo disponível e no contexto deste trabalho. Confira cada fonte antes de usar.";
      result.append(provider);
      const labels = { law: "Lei", jurisprudence: "Jurisprudência", doctrine: "Doutrina" };
      Object.entries(labels).forEach(([key, label]) => {
        const items = payload.recommendations?.[key] || [];
        const heading = document.createElement("h3");
        heading.textContent = `${label} (${items.length})`;
        result.append(heading);
        if (!items.length) { const empty = document.createElement("p"); empty.className = "field-hint"; empty.textContent = "Nenhuma pista encontrada neste recorte."; result.append(empty); return; }
        items.forEach((entry) => result.append(renderLegalEntry(entry, form.dataset.legalAttachUrl, form.querySelector("[name=csrf_token]").value)));
      });
      (payload.warnings || []).forEach((warning) => { const note = document.createElement("p"); note.className = "field-hint"; note.textContent = warning; result.append(note); });
    } catch (error) { result.textContent = error.message; }
    finally { button.disabled = false; }
  });
}

// Initialize legal and sources
initLegalAndSources(form, readJson, markDirty, flushSave, null, null);