/**
 * JEV Panel Module - Assistente Acadêmico
 * Handles JEV Section/Report/Explanation functionality
 */

let currentAbortController = null;

function abortCurrentRequest() {
  if (currentAbortController) {
    currentAbortController.abort();
    currentAbortController = null;
  }
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

async function callJev(form, action, payload, signal) {
  const csrf = form.querySelector("[name=csrf_token]")?.value;
  if (!csrf) throw new Error("Sessão sem proteção CSRF.");
  const response = await fetch(form.dataset.jevUrl, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ action, ...payload, revision: Number(form.dataset.revision) }),
    signal
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Erro no ${action}.`);
  return result;
}

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = String(value ?? "");
  return node.innerHTML;
}

function renderJevResponse(analysis) {
  if (!analysis) return "";
  const items = (analysis.criteria || []).map((item) => {
    const probability = Array.isArray(item.probabilities) ? Math.max(...item.probabilities) : 0;
    return `<li class="ai-jev-item"><div><strong>${escapeHtml(item.title || item.label || item.id)}</strong> <span class="ai-score">${escapeHtml(item.score)} / 3</span></div><div class="ai-score-bar"><span style="width:${Math.round(probability * 100)}%"></span></div>${item.observation ? `<p>${escapeHtml(item.observation)}</p>` : ""}<button type="button" class="text-button" data-jev-explain="${escapeHtml(item.id)}">Entender esta observação</button></li>`;
  }).join("");
  const heading = analysis.expected_points !== undefined
    ? `<p><strong>${Number(analysis.expected_points).toFixed(2)} / ${Number(analysis.assessable_points || 3.5).toFixed(2)} pontos estimados.</strong></p>`
    : "<p>Leitura formativa da etapa; não é nota oficial.</p>";
  const grade = analysis.grade_range
    ? `<p><strong>Faixa provável:</strong> nível ${escapeHtml(analysis.grade_range.score)} de 0 a 3.</p>`
    : "";
  return `<article class="ai-response-card"><h4>Resultado da avaliação</h4>${heading}${grade}<ul class="ai-jev-list">${items}</ul><small class="field-hint">A avaliação usa o texto enviado e deve ser conferida pelo estudante; não verifica automaticamente a correção jurídica das fontes.</small></article>`;
}

export function initJevPanel({ form, flushSave, readJson, collectPayload }) {
  if (!form || !form.dataset.jevUrl) return;

  const setSaveState = (msg) => {
    const saveState = form.querySelector("[data-save-state]");
    if (saveState) saveState.textContent = msg;
  };

  // JEV Section
  form.querySelector("[data-jev-section]")?.addEventListener("click", async () => {
    const button = form.querySelector("[data-jev-section]");
    const resultEl = form.querySelector("[data-jev-result]");
    const sectionSelect = form.querySelector("[data-jev-section-select]");
    const section = sectionSelect?.value;
    if (!section) { resultEl.textContent = "Selecione uma seção."; return; }
    abortCurrentRequest();
    currentAbortController = new AbortController();
    button.disabled = true;
    showLoading(resultEl, "Avaliando seção…");
    try {
      const result = await callJev(form, "section", { section, payload: collectPayload() }, currentAbortController.signal);
      resultEl.textContent = result.answer || "Sem resposta.";
      if (result.suggestions?.length) {
        const list = document.createElement("ul");
        result.suggestions.forEach(s => { const li = document.createElement("li"); li.textContent = s.text; list.append(li); });
        resultEl.append(list);
      }
    } catch (error) {
      if (error.name !== "AbortError") {
        resultEl.textContent = error.message;
      }
    } finally {
      hideLoading(resultEl);
      button.disabled = false;
      currentAbortController = null;
    }
  });

  // JEV Report
  form.querySelector("[data-jev-report]")?.addEventListener("click", async () => {
    const button = form.querySelector("[data-jev-report]");
    const resultEl = form.querySelector("[data-jev-result]");
    abortCurrentRequest();
    currentAbortController = new AbortController();
    button.disabled = true;
    showLoading(resultEl, "Gerando relatório JEV completo…");
    try {
      const result = await callJev(form, "report", { payload: collectPayload() }, currentAbortController.signal);
      resultEl.innerHTML = renderJevResponse(result.analysis);
    } catch (error) {
      if (error.name !== "AbortError") {
        resultEl.textContent = error.message;
      }
    } finally {
      hideLoading(resultEl);
      button.disabled = false;
      currentAbortController = null;
    }
  });

  // JEV Explanation
  form.querySelector("[data-jev-explanation]")?.addEventListener("click", async () => {
    const button = form.querySelector("[data-jev-explanation]");
    const resultEl = form.querySelector("[data-jev-result]");
    const criterionSelect = form.querySelector("[data-jev-criterion-select]");
    const criterion = criterionSelect?.value;
    if (!criterion) { resultEl.textContent = "Selecione um critério."; return; }
    abortCurrentRequest();
    currentAbortController = new AbortController();
    button.disabled = true;
    showLoading(resultEl, "Gerando explicação DeepSeek…");
    try {
      const result = await callJev(form, "explanation", { criterion, payload: collectPayload() }, currentAbortController.signal);
      resultEl.textContent = result.answer || "Sem resposta.";
    } catch (error) {
      if (error.name !== "AbortError") {
        resultEl.textContent = error.message;
      }
    } finally {
      hideLoading(resultEl);
      button.disabled = false;
      currentAbortController = null;
    }
  });
}