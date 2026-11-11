const healthBadge = document.querySelector(".environment-badge");

if (healthBadge) {
  healthBadge.title = "Ambiente privado da nova aplicação";
}

function normalizeLegacyPublicHash() {
  if (!window.location || window.location.pathname !== "/") return;
  const hash = window.location.hash || "";
  const legacyPrefix = "#" + "/site";
  if (!hash.startsWith(legacyPrefix)) return;

  const section = hash.slice(legacyPrefix.length).replace(/^\/+/, "");
  const allowedSections = new Set(["como-funciona", "recursos", "demonstracao", "precos", "suporte"]);
  const nextHash = allowedSections.has(section) ? `#${section}` : "";
  if (window.history && typeof window.history.replaceState === "function") {
    window.history.replaceState(null, "", nextHash || window.location.pathname);
  } else {
    window.location.hash = nextHash;
  }
}

function appendText(parent, tagName, text, className = "") {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.appendChild(element);
  return element;
}

function readPublicDemoModels() {
  const dataNode = document.querySelector("#public-demo-data");
  if (!dataNode) return [];
  try {
    const models = JSON.parse(dataNode.textContent || "[]");
    return Array.isArray(models) ? models : [];
  } catch (_error) {
    return [];
  }
}

function closePublicDemo(dialog) {
  if (!dialog) return;
  if (typeof dialog.close === "function") {
    dialog.close();
  } else {
    dialog.removeAttribute("open");
    dialog.hidden = true;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function publicModelValue(value) {
  if (Array.isArray(value)) return value.join("\n");
  if (value && typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value ?? "");
}

function renderPublicModelField(field) {
  const value = publicModelValue(field.value);
  const label = `${field.label || "Campo"}${field.required ? " *" : ""}`;
  if (field.type === "select") {
    const selected = String(field.value ?? "");
    const options = (field.options || []).map(([option, text]) =>
      `<option value="${escapeHtml(option)}" ${String(option) === selected ? "selected" : ""}>${escapeHtml(text)}</option>`
    ).join("");
    return `<label class="public-model-field"><span>${escapeHtml(label)}</span><select disabled>${options || `<option>${escapeHtml(value || "Não preenchido neste modelo.")}</option>`}</select></label>`;
  }
  return `<label class="public-model-field"><span>${escapeHtml(label)}</span><textarea readonly rows="${field.size === "large" ? 7 : 3}">${escapeHtml(value || "Não preenchido neste modelo.")}</textarea></label>`;
}

function renderPublicModelSpecial(stage, model) {
  if (stage.custom === "criteria") {
    return `<section class="public-model-special"><h3>Critérios e valores</h3><textarea readonly rows="8">${escapeHtml(stage.criteria_text || "Não preenchido neste modelo.")}</textarea></section>`;
  }
  if (stage.custom === "sources") {
    const sources = model.workflow?.sources || [];
    return `<section class="public-model-special"><h3>Fontes registradas</h3><ol class="public-model-sources">${sources.map((source) => `<li><strong>${escapeHtml(source.category || "Fonte")}</strong><span>${escapeHtml(source.reference || "")}</span></li>`).join("")}</ol></section>`;
  }
  if (stage.custom === "development") {
    return `<section class="public-model-special"><h3>Desenvolvimento preenchido</h3>${(stage.development_sections || []).map((section) => `<div class="public-model-development"><h4>${escapeHtml(section.title || "Tópico")}</h4><textarea readonly rows="8">${escapeHtml(section.content || "")}</textarea></div>`).join("")}</section>`;
  }
  return "";
}

function renderPublicModelSections(stage) {
  return (stage.demo_sections || []).map((section) => `
    <section class="public-model-filled-section">
      <h4>${escapeHtml(section.title || "Seção preenchida")}</h4>
      ${(section.paragraphs || []).map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}
    </section>`).join("");
}

function renderPublicModelWorkflow(body, model, requestedStep = 0) {
  const stages = Array.isArray(model.stages) ? model.stages : [];
  if (!stages.length) {
    body.innerHTML = `<p class="sales-lede">Este modelo preenchido ainda não possui etapas disponíveis.</p>`;
    return;
  }
  const step = Math.max(0, Math.min(Number(requestedStep) || 0, stages.length - 1));
  const stage = stages[step];
  body.innerHTML = `
    <div class="public-model-workflow">
      <p class="public-model-note">Este é o mesmo roteiro de um trabalho preenchido, em modo somente leitura. Você pode percorrer as etapas sem alterar nenhum projeto.</p>
      <nav class="public-model-step-nav" aria-label="Etapas do modelo preenchido">
        ${stages.map((item, index) => `<button type="button" data-public-model-step="${index}" class="${index === step ? "is-current" : ""}" aria-current="${index === step ? "step" : "false"}"><span>${String(index + 1).padStart(2, "0")}</span>${escapeHtml(item.title || "Etapa")}</button>`).join("")}
      </nav>
      <article class="public-model-stage">
        <p class="sales-kicker">Etapa ${String(step + 1).padStart(2, "0")} de ${String(stages.length).padStart(2, "0")}</p>
        <h3>${escapeHtml(stage.title || "Etapa preenchida")}</h3>
        <p class="public-model-intro">${escapeHtml(stage.intro || "Confira o conteúdo preenchido nesta etapa.")}</p>
        ${stage.fields?.length ? `<div class="public-model-fields">${stage.fields.map(renderPublicModelField).join("")}</div>` : ""}
        ${renderPublicModelSpecial(stage, model)}
        ${renderPublicModelSections(stage)}
        ${stage.custom === "review" ? `<div class="public-model-review"><strong>Revisão do modelo</strong><p>O trabalho preenchido está disponível para consulta etapa por etapa e também no botão “Ler trabalho completo”.</p></div>` : ""}
        <div class="public-model-actions"><button type="button" class="button" data-public-model-step="${step - 1}" ${step === 0 ? "disabled" : ""}>Anterior</button><span>Modelo para consulta</span><button type="button" class="button button-primary" data-public-model-step="${step + 1}" ${step === stages.length - 1 ? "disabled" : ""}>Próxima etapa</button></div>
      </article>
    </div>`;
}

function renderPublicDemo(dialog, model, mode) {
  const body = document.querySelector("#public-demo-body");
  const title = document.querySelector("#public-demo-title");
  if (!dialog || !body || !title || !model) return;

  body.replaceChildren();
  title.textContent = model.title || "Demonstração";
  appendText(body, "p", model.type_label || "Modelo preenchido", "sales-kicker");
  appendText(body, "p", `Disciplina: ${model.discipline || ""}`, "sales-window-note");

  if (mode === "workflow") {
    body.dataset.modelId = model.id;
    renderPublicModelWorkflow(body, model);
  } else {
    const question = document.createElement("p");
    question.className = "sales-preview-question";
    appendText(question, "small", model.question_label || "Contexto");
    question.appendChild(document.createTextNode(model.question || ""));
    body.appendChild(question);

    for (const section of model.sections || []) {
      const article = document.createElement("section");
      appendText(article, "h3", section.title || "Seção");
      for (const paragraph of section.paragraphs || []) {
        appendText(article, "p", paragraph);
      }
      body.appendChild(article);
    }
  }

  dialog.hidden = false;
  if (typeof dialog.showModal === "function" && !dialog.open) {
    dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
}

function bindPublicDemos() {
  const dialog = document.querySelector("#public-demo-dialog");
  const models = readPublicDemoModels();
  if (!dialog || !models.length) return;
  const byId = new Map(models.map((model) => [model.id, model]));

  document.querySelectorAll("[data-model-workflow]").forEach((button) => {
    button.addEventListener("click", () => renderPublicDemo(dialog, byId.get(button.dataset.modelWorkflow), "workflow"));
  });
  document.querySelectorAll("[data-model-document]").forEach((button) => {
    button.addEventListener("click", () => renderPublicDemo(dialog, byId.get(button.dataset.modelDocument), "document"));
  });
  document.querySelectorAll("[data-demo-close]").forEach((button) => {
    button.addEventListener("click", () => closePublicDemo(dialog));
  });
  const demoBody = document.querySelector("#public-demo-body");
  demoBody?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-public-model-step]");
    if (!button || button.disabled) return;
    const model = byId.get(demoBody.dataset.modelId);
    if (model) renderPublicModelWorkflow(demoBody, model, Number(button.dataset.publicModelStep));
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closePublicDemo(dialog);
  });
  dialog.addEventListener("close", () => {
    const body = document.querySelector("#public-demo-body");
    if (body) body.replaceChildren();
  });
}

function setCopyStatus(button, message) {
  const payment = button.closest(".pix-payment");
  const status = payment && payment.querySelector("[data-pix-status]");
  if (status) status.textContent = message;
}

function fallbackCopy(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  let copied = false;
  try {
    copied = Boolean(document.execCommand("copy"));
  } catch (_error) {
    copied = false;
  }
  textarea.remove();
  return copied;
}

function bindPixCopy() {
  document.querySelectorAll("[data-pix-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const payment = button.closest(".pix-payment");
      const payload = payment && payment.querySelector(".pix-payload");
      const text = payload ? payload.textContent.trim() : "";
      if (!text) {
        setCopyStatus(button, "Código Pix indisponível.");
        return;
      }

      let copied = false;
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        try {
          await navigator.clipboard.writeText(text);
          copied = true;
        } catch (_error) {
          copied = false;
        }
      }
      if (!copied) copied = fallbackCopy(text);
      setCopyStatus(button, copied ? "Código Pix copiado." : "Não foi possível copiar. Selecione o código completo.");
    });
  });
}

normalizeLegacyPublicHash();
bindPublicDemos();
bindPixCopy();
