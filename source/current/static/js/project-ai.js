// Assistência contextual do editor. O módulo recebe as operações do autosave para não duplicar estado.
export function initEditorAi({ form, readJson, markDirty, flushSave, stages, showStep, createInlineSource, appendProjectSource }) {
  // Recuperação do fluxo de IA do editor legado: ações ficam dentro da etapa,
  // e nenhuma sugestão é aplicada sem confirmação explícita.
  const richAiResults = new Map();
  let currentAbortController = null;

  function escapeAi(value) {
    const node = document.createElement("span");
    node.textContent = String(value ?? "");
    return node.innerHTML;
  }

  function showLoading(target, message) {
    if (target) {
      target.textContent = message;
      target.dataset.loading = "true";
    }
  }

  function hideLoading(target) {
    if (target) {
      delete target.dataset.loading;
    }
  }

  function abortCurrentRequest() {
    if (currentAbortController) {
      currentAbortController.abort();
      currentAbortController = null;
    }
  }

  // Clean up on page unload
  window.addEventListener("beforeunload", abortCurrentRequest);

  function aiContextFields(stageId = "") {
    const stage = form?.querySelector(`[data-stage="${CSS.escape(stageId)}"]`);
    return [...(stage?.querySelectorAll("[data-case-field]") || [])].map((field) => field.dataset.caseField);
  }

  function applyRichField(fieldId, value) {
    if (!fieldId || !String(value).trim()) return false;
    const direct = form.querySelector(`[data-case-field="${CSS.escape(fieldId)}"]`);
    if (direct) {
      direct.value = value;
      direct.dispatchEvent(new Event("input", { bubbles: true }));
      return true;
    }
    const parts = String(fieldId).split(":");
    if (parts[0] === "criterion" && parts.length === 3) {
      const card = [...form.querySelectorAll("[data-criterion]")].find((item) => item.dataset.criterionId === parts[1]);
      const field = card?.querySelector(`[data-criterion-field="${CSS.escape(parts[2])}"]`);
      if (field) {
        field.value = value;
        field.dispatchEvent(new Event("input", { bubbles: true }));
        return true;
      }
    }
    return false;
  }

  function renderRichResponse(response, key) {
    const suggestions = (response?.suggestions || []).filter((item) => !item.declined);
    const suggestionHtml = suggestions.length ? `<div><strong>Possíveis ajustes</strong><ul class="ai-suggestion-list">${suggestions.map((item, index) => `<li class="ai-suggestion-item"><span>${escapeAi(item.text)}</span><small class="field-hint">Campo: ${escapeAi(item.field_id || "confira manualmente")}</small><div class="ai-suggestion-actions"><button type="button" class="text-button" data-rich-ai-apply="${escapeAi(key)}" data-rich-ai-index="${index}">Aplicar</button><button type="button" class="text-button" data-rich-ai-edit="${escapeAi(key)}" data-rich-ai-index="${index}">Editar e aplicar</button><button type="button" class="text-button" data-rich-ai-decline="${escapeAi(key)}" data-rich-ai-index="${index}">Ignorar</button></div></li>`).join("")}</ul></div>` : "";
    const rewriteHtml = response?.rewrite ? `<div class="ai-suggestion-item"><strong>Revisão opcional do campo</strong><p>${escapeAi(response.rewrite)}</p><button type="button" class="text-button" data-rich-ai-rewrite="${escapeAi(key)}">Substituir campo</button></div>` : "";
    const validation = response?.validation;
    const validationHtml = validation ? `<div class="ai-validation"><strong>Avaliação estruturada: ${escapeAi(validation.status || "não avaliado")}</strong>${(validation.observations || []).length ? `<ul>${validation.observations.map((item) => `<li>${escapeAi(item)}</li>`).join("")}</ul>` : ""}</div>` : "";
    const checklistHtml = (response?.checklist || []).length ? `<ul class="ai-suggestion-list">${response.checklist.map((item) => `<li class="ai-suggestion-item"><strong>${escapeAi(item.id)}</strong><span>Confiança: ${Math.round(Number(item.confidence || 0) * 100)}%</span><small>${escapeAi(item.evidence || "Sem evidência textual.")}</small></li>`).join("")}</ul>` : "";
    return `<article class="ai-response-card"><p>${escapeAi(response?.answer || "Não houve resposta textual.")}</p>${suggestionHtml}${rewriteHtml}${checklistHtml}${validationHtml}<small class="field-hint">Resposta gerada sob solicitação; confira tudo antes de usar.</small></article>`;
  }

  function renderJevResponse(analysis) {
    if (!analysis) return "";
    const items = (analysis.criteria || []).map((item) => {
      const probability = Array.isArray(item.probabilities) ? Math.max(...item.probabilities) : 0;
      return `<li class="ai-jev-item"><div><strong>${escapeAi(item.title || item.label || item.id)}</strong> <span class="ai-score">${escapeAi(item.score)} / 3</span></div><div class="ai-score-bar"><span style="width:${Math.round(probability * 100)}%"></span></div>${item.observation ? `<p>${escapeAi(item.observation)}</p>` : ""}<button type="button" class="text-button" data-jev-explain="${escapeAi(item.id)}">Entender esta observação</button></li>`;
    }).join("");
    const heading = analysis.expected_points !== undefined ? `<p><strong>${Number(analysis.expected_points).toFixed(2)} / ${Number(analysis.assessable_points || 3.5).toFixed(2)} pontos estimados.</strong></p>` : "<p>Leitura formativa da etapa; não é nota oficial.</p>";
    const grade = analysis.grade_range ? `<p><strong>Faixa provável:</strong> nível ${escapeAi(analysis.grade_range.score)} de 0 a 3.</p>` : "";
    return `<article class="ai-response-card"><h4>Resultado da avaliação</h4>${heading}${grade}<ul class="ai-jev-list">${items}</ul><small class="field-hint">A avaliação usa o texto enviado e deve ser conferida pelo estudante; não verifica automaticamente a correção jurídica das fontes.</small></article>`;
  }

  async function runRichAiAction(action, payload, target) {
    if (!target || !form?.dataset.aiActionUrl) return;
    abortCurrentRequest();
    currentAbortController = new AbortController();
    showLoading(target, "Salvando esta etapa e consultando a assistência…");
    try {
      if (!await flushSave()) throw new Error("Salve as alterações antes de pedir assistência.");
      const body = { action, project_revision: Number(form.dataset.revision), context_fields: aiContextFields(payload.stage_id), ...payload };
      const response = await fetch(form.dataset.aiActionUrl, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-Token": form.querySelector("[name=csrf_token]").value }, body: JSON.stringify(body), signal: currentAbortController.signal });
      const result = await readJson(response);
      if (!response.ok) throw new Error(result.message || "Não foi possível consultar a assistência.");
      const key = `${action}:${payload.stage_id || payload.field_id || "project"}`;
      richAiResults.set(key, result.response || result);
      target.dataset.richAiKey = key;
      target.innerHTML = renderRichResponse(result.response || result, key);
    } catch (error) {
      if (error.name !== "AbortError") {
        target.textContent = error.message;
      }
    } finally {
      hideLoading(target);
      currentAbortController = null;
    }
  }

  async function runJevExplanation(criterion, button) {
    if (!form?.dataset.jevExplanationUrl || !button) return;
    abortCurrentRequest();
    currentAbortController = new AbortController();
    button.disabled = true;
    const result = document.createElement("div");
    result.className = "ai-validation";
    showLoading(result, "Preparando explicação…");
    button.parentElement.append(result);
    try {
      if (!await flushSave()) throw new Error("Salve as alterações antes de pedir a explicação.");
      const response = await fetch(form.dataset.jevExplanationUrl, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-Token": form.querySelector("[name=csrf_token]").value }, body: JSON.stringify({ criterion }), signal: currentAbortController.signal });
      const payload = await readJson(response);
      if (!response.ok) throw new Error(payload.message || "Não foi possível explicar esta observação.");
      const explanation = payload.explanation || {};
      result.innerHTML = `<strong>Explicação</strong><p>${escapeAi(explanation.interpretation || "Não houve explicação textual.")}</p>${(explanation.next_steps || []).length ? `<ul>${explanation.next_steps.map((item) => `<li>${escapeAi(item)}</li>`).join("")}</ul>` : ""}`;
    } catch (error) {
      if (error.name !== "AbortError") {
        result.textContent = error.message;
      }
    } finally {
      hideLoading(result);
      button.disabled = false;
      currentAbortController = null;
    }
  }

  async function runJev(section, target, report = false) {
    if (!target) return;
    abortCurrentRequest();
    currentAbortController = new AbortController();
    showLoading(target, "Salvando esta etapa e calculando a avaliação…");
    try {
      if (!await flushSave()) throw new Error("Salve as alterações antes de pedir avaliação.");
      const url = report ? form.dataset.jevReportUrl : form.dataset.jevSectionUrl;
      const body = { };
      if (!report) body.section = section;
      const response = await fetch(url, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-Token": form.querySelector("[name=csrf_token]").value }, body: JSON.stringify(body), signal: currentAbortController.signal });
      const result = await readJson(response);
      if (!response.ok) throw new Error(result.message || "Não foi possível concluir a avaliação.");
      target.innerHTML = renderJevResponse(result.analysis);
    } catch (error) {
      if (error.name !== "AbortError") {
        target.textContent = error.message;
      }
    } finally {
      hideLoading(target);
      currentAbortController = null;
    }
  }

  form?.addEventListener("click", (event) => {
    const createSourceButton = event.target.closest("[data-create-source]");
    if (createSourceButton) {
      void createInlineSource(createSourceButton);
      return;
    }
    const deliveryToggle = event.target.closest("[data-toggle-delivery]");
    if (deliveryToggle) {
      const state = deliveryToggle.closest("[data-delivery-state]");
      if (!state) return;
      const delivered = state.dataset.delivered === "true";
      if (delivered) {
        state.dataset.delivered = "false";
        state.dataset.deliveredAt = "0";
        state.innerHTML = `<button type="button" class="button button-primary finalize-button" data-toggle-delivery>Marcar ${state.dataset.deliveryKey === "report" ? "relatório" : "entrega"} como entregue</button>`;
      } else {
        state.dataset.delivered = "true";
        state.dataset.deliveredAt = String(Date.now());
        state.innerHTML = `<div class="notice completion-notice"><strong>${state.dataset.deliveryKey === "report" ? "Relatório" : "Entrega"} marcado como entregue.</strong><span class="delivery-edited">Você ainda pode editar o trabalho.</span><button class="text-button" type="button" data-toggle-delivery>Desfazer marcação</button></div>`;
      }
      markDirty();
      return;
    }
    const phaseButton = event.target.closest("[data-go-phase]");
    if (phaseButton) {
      const target = stages.findIndex((stage) => stage.dataset.stagePhase === phaseButton.dataset.goPhase);
      if (target >= 0) showStep(target, true);
      return;
    }
    const inline = event.target.closest("[data-ai-inline]");
    if (inline) {
      const fieldId = inline.dataset.aiInline;
      const target = form.querySelector(`[data-ai-field-result="${CSS.escape(fieldId)}"]`);
      void runRichAiAction("review", { field_id: fieldId, stage_id: inline.closest("[data-stage]")?.dataset.stage || "" }, target);
      return;
    }
    const stageAction = event.target.closest("[data-ai-stage-action]");
    if (stageAction) {
      const stageId = stageAction.dataset.aiStageId;
      const target = form.querySelector(`[data-ai-stage-result="${CSS.escape(stageId)}"]`);
      const checklist = [...(form.querySelector(`[data-stage="${CSS.escape(stageId)}"]`)?.querySelectorAll("[data-workflow-check]") || [])].map((input) => ({ id: input.dataset.workflowCheck, label: input.closest("label")?.textContent.trim() || input.dataset.workflowCheck }));
      void runRichAiAction(stageAction.dataset.aiStageAction, { stage_id: stageId, checklist }, target);
      return;
    }
    const jevExplain = event.target.closest("[data-jev-explain]");
    if (jevExplain) {
      void runJevExplanation(jevExplain.dataset.jevExplain, jevExplain);
      return;
    }
    const jevButton = event.target.closest("[data-jev-section]");
    if (jevButton) {
      const target = jevButton.closest("[data-stage-ai]")?.querySelector("[data-ai-stage-result]");
      void runJev(jevButton.dataset.jevSection, target);
      return;
    }
    const jevReport = event.target.closest("[data-jev-report]");
    if (jevReport) {
      const target = jevReport.closest("[data-stage-ai]")?.querySelector("[data-ai-stage-result]");
      void runJev("", target, true);
      return;
    }
    const suggestionButton = event.target.closest("[data-rich-ai-apply], [data-rich-ai-edit], [data-rich-ai-decline]");
    if (suggestionButton) {
      const key = suggestionButton.dataset.richAiApply || suggestionButton.dataset.richAiEdit || suggestionButton.dataset.richAiDecline;
      const result = richAiResults.get(key);
      const index = Number(suggestionButton.dataset.richAiIndex);
      const suggestion = result?.suggestions?.[index];
      if (!suggestion) return;
      if (suggestionButton.hasAttribute("data-rich-ai-decline")) {
        suggestion.declined = true;
      } else {
        let value = suggestion.text;
        if (suggestionButton.hasAttribute("data-rich-ai-edit")) value = window.prompt("Edite a sugestão antes de aplicar:", value);
        if (value === null || value === undefined) return;
        if (!applyRichField(suggestion.field_id, value)) suggestion.notice = "O campo não está visível nesta etapa; confira a sugestão manualmente.";
        else markDirty();
      }
      const owner = suggestionButton.closest("[data-ai-stage-result], [data-ai-field-result]");
      if (owner) owner.innerHTML = renderRichResponse(result, key);
      return;
    }
    const rewrite = event.target.closest("[data-rich-ai-rewrite]");
    if (rewrite) {
      const result = richAiResults.get(rewrite.dataset.richAiRewrite);
      const fieldId = rewrite.dataset.richAiRewrite.split(":").slice(1).join(":");
      if (result?.rewrite && window.confirm("Substituir o campo pela revisão sugerida?")) {
        if (applyRichField(fieldId, result.rewrite)) markDirty();
      }
    }
  });
}
