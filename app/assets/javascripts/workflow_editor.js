(() => {
  const shell = document.querySelector(".app-shell");
  const sidebar = document.querySelector("#app-sidebar");
  const toggle = document.querySelector("[data-sidebar-toggle]");
  const backdrop = document.querySelector("[data-sidebar-backdrop]");
  if (!shell || !sidebar || !toggle || !backdrop) return;

  const mobile = window.matchMedia("(max-width: 720px)");
  shell.classList.add("sidebar-ready");
  const label = toggle.querySelector("[data-sidebar-toggle-label]");
  const setExpanded = (expanded) => {
    toggle.setAttribute("aria-expanded", String(expanded));
    toggle.setAttribute("aria-label", mobile.matches
      ? (expanded ? "Fechar menu" : "Abrir menu")
      : (expanded ? "Ocultar navegação" : "Mostrar navegação"));
    if (label) label.textContent = mobile.matches
      ? (expanded ? "Fechar menu" : "Abrir menu")
      : (expanded ? "Ocultar navegação" : "Mostrar navegação");
    backdrop.hidden = !mobile.matches || !expanded;
  };
  const applyViewport = () => {
    if (mobile.matches) {
      shell.classList.remove("is-sidebar-collapsed");
      sidebar.classList.remove("is-open");
      setExpanded(false);
    } else {
      sidebar.classList.remove("is-open");
      let collapsed = false;
      try {
        collapsed = localStorage.getItem("academic-sidebar-collapsed") === "true";
      } catch {
        collapsed = false;
      }
      shell.classList.toggle("is-sidebar-collapsed", collapsed);
      setExpanded(!collapsed);
    }
  };
  const closeMobile = () => {
    sidebar.classList.remove("is-open");
    setExpanded(false);
    toggle.focus();
  };

  toggle.addEventListener("click", () => {
    if (mobile.matches) {
      const expanded = !sidebar.classList.contains("is-open");
      sidebar.classList.toggle("is-open", expanded);
      setExpanded(expanded);
    } else {
      const collapsed = !shell.classList.contains("is-sidebar-collapsed");
      shell.classList.toggle("is-sidebar-collapsed", collapsed);
      try {
        localStorage.setItem("academic-sidebar-collapsed", String(collapsed));
      } catch {
        // The layout still works for this page when storage is unavailable.
      }
      setExpanded(!collapsed);
    }
  });
  backdrop.addEventListener("click", closeMobile);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && mobile.matches && sidebar.classList.contains("is-open")) closeMobile();
  });
  mobile.addEventListener("change", applyViewport);
  applyViewport();
})();

function updatePackageButton(card) {
  const button = card.querySelector("[data-buy-package]");
  const quantity = card.querySelector("[data-package-quantity]");
  if (!button || !quantity) return;
  const priceCents = Number(card.dataset.priceCents);
  const count = Number(quantity.value);
  if (!Number.isSafeInteger(priceCents) || !Number.isSafeInteger(count)) return;

  const amount = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" })
    .format((priceCents * count) / 100);
  button.textContent = `Gerar Pix — ${amount}`;
}

document.addEventListener("click", (event) => {
  document.querySelectorAll(".profile-menu[open]").forEach((menu) => {
    if (!menu.contains(event.target)) menu.open = false;
  });
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  const menu = document.querySelector(".profile-menu[open]");
  if (!menu) return;
  menu.open = false;
  menu.querySelector("summary").focus();
});

document.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-collection-add]");
  if (addButton) {
    const section = addButton.closest(".collection-section");
    const list = section.querySelector("[data-collection-list]");
    const template = section.querySelector("[data-collection-template]");
    const limit = Number(list.dataset.collectionLimit);
    if (list.children.length >= limit) {
      addButton.disabled = true;
      return;
    }

    const index = Number(list.dataset.nextIndex);
    const fragment = template.content.cloneNode(true);
    fragment.querySelectorAll("[name]").forEach((input) => {
      input.name = input.name.replaceAll("INDEX_PLACEHOLDER", String(index));
    });
    list.append(fragment);
    list.dataset.nextIndex = String(index + 1);
    addButton.disabled = list.children.length >= limit;
    return;
  }

  const removeButton = event.target.closest("[data-collection-remove]");
  if (removeButton) {
    const section = removeButton.closest(".collection-section");
    removeButton.closest("[data-collection-item]").remove();
    const list = section.querySelector("[data-collection-list]");
    const add = section.querySelector("[data-collection-add]");
    add.disabled = list.children.length < Number(list.dataset.collectionLimit) ? false : true;
  }
});

document.addEventListener("click", async (event) => {
  const purchaseButton = event.target.closest("[data-buy-package]");
  const newPurchaseButton = event.target.closest("[data-new-purchase]");
  const statusButton = event.target.closest("[data-check-payment]");
  const copyButton = event.target.closest("[data-copy-pix]");

  if (newPurchaseButton) {
    const card = newPurchaseButton.closest("[data-package-card]");
    card.querySelector("[data-package-quantity]").disabled = false;
    card.querySelector("[data-buy-package]").dataset.requestId = "";
    card.querySelector("[data-buy-package]").disabled = false;
    updatePackageButton(card);
    card.querySelector("[data-payment-result]").replaceChildren();
    card.querySelector("[data-payment-status]").textContent = "";
    return;
  }

  if (copyButton) {
    const card = copyButton.closest("[data-package-card]");
    const value = card.querySelector("[data-pix-copy-code]").textContent;
    try {
      await navigator.clipboard.writeText(value);
      card.querySelector("[data-payment-status]").textContent = "Código Pix copiado.";
    } catch {
      card.querySelector("[data-payment-status]").textContent = "Não foi possível copiar. Selecione e copie o código Pix.";
    }
    return;
  }

  if (statusButton) {
    const card = statusButton.closest("[data-package-card]");
    const status = card.querySelector("[data-payment-status]");
    statusButton.disabled = true;
    try {
      const response = await fetch(`/payments/${encodeURIComponent(statusButton.dataset.orderId)}`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      });

      const result = await response.json();
      if (!response.ok) throw new Error(result.message || "Não foi possível consultar o pedido.");
      status.textContent = result.status === "approved" ? "Pagamento confirmado. Seus créditos foram liberados." : `Status do pagamento: ${result.status}.`;
    } catch (error) {
      status.textContent = error.message || "Não foi possível consultar o pedido.";
    } finally {
      statusButton.disabled = false;
    }
    return;
  }

  if (!purchaseButton) return;
  const card = purchaseButton.closest("[data-package-card]");
  const status = card.querySelector("[data-payment-status]");
  purchaseButton.disabled = true;
  status.textContent = "Registrando pedido Pix…";
  if (!purchaseButton.dataset.requestId) {
    purchaseButton.dataset.requestId = globalThis.crypto?.randomUUID?.() || "";
  }
  if (!purchaseButton.dataset.requestId) {
    status.textContent = "Este navegador não conseguiu gerar um identificador seguro. Atualize-o para continuar.";
    purchaseButton.disabled = false;
    return;
  }

  try {
    const response = await fetch("/payments", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      },
      body: JSON.stringify({
        package_code: purchaseButton.dataset.buyPackage,
        quantity: Number(card.querySelector("[data-package-quantity]").value),
        request_id: purchaseButton.dataset.requestId
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "Não foi possível gerar o Pix.");

    const output = card.querySelector("[data-payment-result]");
    output.replaceChildren();
    const heading = document.createElement("h3");
    heading.textContent = "Pedido Pix criado";
    const amount = document.createElement("p");
    amount.textContent = `Total: ${(result.amount_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}`;
    output.append(heading, amount);
    if (result.qr_code_base64) {
      const image = document.createElement("img");
      image.className = "payment-qr";
      image.alt = "QR Code Pix";
      image.src = `data:image/png;base64,${result.qr_code_base64}`;
      output.append(image);
    }
    if (result.pix_copy_code) {
      const label = document.createElement("p");
      label.textContent = "Pix copia e cola:";
      const code = document.createElement("pre");
      code.dataset.pixCopyCode = "";
      code.textContent = result.pix_copy_code;
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "button button-secondary";
      copy.dataset.copyPix = "";
      copy.textContent = "Copiar código Pix";
      output.append(label, code, copy);
    }
    const check = document.createElement("button");
    check.type = "button";
    check.className = "button button-secondary";
    check.dataset.checkPayment = "";
    check.dataset.orderId = result.order_id;
    check.textContent = "Consultar pagamento";
    output.append(check);

    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "text-button";
    reset.dataset.newPurchase = "";
    reset.textContent = "Iniciar outra compra";
    output.append(reset);
    card.querySelector("[data-package-quantity]").disabled = true;
    purchaseButton.textContent = "Pix gerado";
    status.textContent = "Use o QR Code ou o código Pix para concluir o pagamento.";
  } catch (error) {
    status.textContent = error.message || "Não foi possível gerar o Pix. Tente novamente.";
    purchaseButton.disabled = false;
  }
});

document.addEventListener("change", (event) => {
  const quantity = event.target.closest("[data-package-quantity]");
  if (quantity) updatePackageButton(quantity.closest("[data-package-card]"));

  const mode = event.target.closest("[data-studio-mode]");
  if (!mode) return;
  const root = mode.closest("[data-project-studio]");
  const guided = mode.value === "guided";
  root.querySelectorAll("[data-guided-only]").forEach((element) => {
    element.hidden = !guided;
  });
  root.querySelector("[data-studio-source-field]").hidden = guided;
});

document.addEventListener("click", (event) => {
  const filterButton = event.target.closest("[data-project-filter]");
  const viewButton = event.target.closest("[data-project-view-button]");
  const row = event.target.closest("[data-project-row]");
  const page = document.querySelector(".projects-page[data-project-view]");

  if (row && !event.target.closest("a, button, input, select")) {
    row.querySelector("a[href]")?.click();
    return;
  }
  if (!page) return;

  if (filterButton) {
    const filter = filterButton.dataset.projectFilter;
    page.querySelectorAll("[data-project-filter]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button === filterButton));
    });
    page.querySelectorAll("[data-project-card]").forEach((card) => {
      card.hidden = filter !== "all" && card.dataset.projectKind !== filter;
    });
    page.querySelectorAll("[data-project-column]").forEach((column) => {
      const visibleCards = column.querySelectorAll(".project-board-items > [data-project-card]:not([hidden])");
      column.querySelector("[data-column-count]").textContent = String(visibleCards.length);
      column.hidden = visibleCards.length === 0;
    });
    const emptyMessage = page.querySelector("[data-project-filter-empty]");
    if (emptyMessage) emptyMessage.hidden = Boolean(page.querySelector("[data-project-card]:not([hidden])"));
  }

  if (viewButton) {
    page.dataset.projectView = viewButton.dataset.projectViewButton;
    page.querySelectorAll("[data-project-view-button]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button === viewButton));
    });
  }
});

document.addEventListener("keydown", (event) => {
  const row = event.target.closest?.("[data-project-row]");
  if (!row || event.target.closest("a, button, input, select") || (event.key !== "Enter" && event.key !== " ")) return;
  event.preventDefault();
  row.querySelector("a[href]")?.click();
});

document.addEventListener("click", async (event) => {
  const actionButton = event.target.closest("[data-ai-action]");
  const jevButton = event.target.closest("[data-jev-section-action], [data-jev-report], [data-jev-assessment]");
  if (!actionButton && !jevButton) return;

  const panel = event.target.closest("[data-ai-panel]");
  if (!panel) return;

  const button = actionButton || jevButton;
  const status = panel.querySelector(actionButton ? "[data-ai-status]" : "[data-jev-status]");
  const output = panel.querySelector(actionButton ? "[data-ai-response]" : "[data-jev-response]");
  if (!output) return;

  button.disabled = true;
  output.replaceChildren();
  if (status) status.textContent = "Consultando o serviço de IA…";
  try {
    let url;
    let payload;
    if (actionButton) {
      url = panel.dataset.actionUrl;
      payload = {
        action: actionButton.dataset.aiAction,
        message: panel.querySelector("[data-ai-message]").value,
        project_revision: Number(panel.dataset.projectRevision)
      };
    } else if (jevButton.matches("[data-jev-report]")) {
      url = panel.dataset.jevReportUrl;
      payload = {};
    } else if (jevButton.matches("[data-jev-assessment]")) {
      const assistPanel = panel.querySelector(".assist-panel");
      if (assistPanel) {
        assistPanel.open = true;
        if (!window.matchMedia("(max-width: 720px)").matches) {
          assistPanel.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
      url = panel.dataset.jevAssessmentUrl;
      payload = {
        stage: jevButton.dataset.jevAssessmentStage,
        project_revision: Number(panel.dataset.projectRevision)
      };
    } else {
      url = panel.dataset.jevSectionUrl;
      payload = { section: panel.querySelector("[data-jev-section-select]").value };
    }

    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "Não foi possível concluir a análise.");

    if (actionButton) {
      renderAiResponse(output, result.response);
    } else {
      renderJevAnalysis(output, result.analysis);
    }
    if (status) status.textContent = "Análise concluída.";
  } catch (error) {
    output.textContent = error.message || "Não foi possível conectar ao serviço de IA.";
    if (status) status.textContent = "A análise não foi concluída.";
  } finally {
    button.disabled = false;
  }
});

function renderAiResponse(output, response) {
  const answer = document.createElement("p");
  answer.textContent = response.answer;
  output.append(answer);

  response.suggestions.forEach((suggestion) => {
    const item = document.createElement("div");
    item.className = "assist-suggestion";
    const origin = document.createElement("p");
    origin.className = "field-hint";
    origin.textContent = "Sugestão gerada por IA. Revise e edite antes de usar.";
    const text = document.createElement("p");
    text.textContent = suggestion.text;
    item.append(origin, text);

    const field = document.getElementById(`project_fields_${suggestion.field_id}`);
    if (field) {
      const apply = document.createElement("button");
      apply.type = "button";
      apply.className = "button button-secondary";
      apply.textContent = "Usar sugestão neste campo";
      apply.addEventListener("click", () => {
        field.value = suggestion.text;
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.focus();
      });
      item.append(apply);
    }
    output.append(item);
  });
}

function renderJevAnalysis(output, analysis) {
  const heading = document.createElement("h5");
  heading.textContent = {
    case_report: "Resultado do relatório do Case",
    case_dissertation: "Resultado da dissertação do Case",
    paper_project: "Resultado do Projeto de Paper",
    paper_final: "Resultado do Paper Final"
  }[analysis.stage] || (analysis.section ? "Resultado da etapa" : "Resultado do relatório");
  output.append(heading);

  (analysis.criteria || []).forEach((criterion) => {
    const item = document.createElement("article");
    item.className = "jev-criterion";
    const title = document.createElement("h5");
    title.textContent = criterion.title || criterion.label || criterion.id;
    const score = document.createElement("p");
    score.textContent = `Pontuação indicativa: ${criterion.score}/3 · confiança ${Math.round((criterion.confidence || 0) * 100)}%`;
    const observation = document.createElement("p");
    observation.textContent = criterion.observation || "Sem observação.";
    item.append(title, score, observation);
    output.append(item);
  });

  if (analysis.grade_range) {
    const grade = document.createElement("p");
    grade.textContent = `Faixa provável: ${analysis.grade_range.score}/3 · conteúdo estimado em ${analysis.expected_points}/${analysis.assessable_points} pontos`;
    output.append(grade);
  }

  if (analysis.expected_points !== undefined) {
    const points = document.createElement("p");
    points.textContent = `Subtotal indicativo: ${analysis.expected_points}/${analysis.assessable_points} pontos`;
    output.append(points);
  }
  if (analysis.points_discrepancy) {
    const note = document.createElement("p");
    note.className = "field-hint";
    note.textContent = `Os critérios publicados somam ${analysis.assessable_points} pontos, embora a etapa seja declarada como ${analysis.declared_points}. Nenhum ponto ausente foi estimado.`;
    output.append(note);
  }
  if (analysis.unassessed_points > 0) {
    const note = document.createElement("p");
    note.className = "field-hint";
    note.textContent = `${analysis.unassessed_points} ponto de formatação não é estimado a partir de texto simples; a avaliação do debate também não é inferida.`;
    output.append(note);
  }
}

document.addEventListener("submit", async (event) => {
  const form = event.target.closest("[data-studio-request]");
  if (!form) return;

  event.preventDefault();
  await requestStudioSuggestions(form.closest("[data-project-studio]"), form, false);
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-studio-continue]");
  if (!button) return;

  const root = button.closest("[data-project-studio]");
  const form = root.querySelector("[data-studio-request]");
  await requestStudioSuggestions(root, form, true);
});

document.addEventListener("click", (event) => {
  const guideSuggestion = event.target.closest("[data-guide-prompt]");
  const studioSuggestion = event.target.closest("[data-studio-prompt-suggestion]");
  const suggestion = guideSuggestion || studioSuggestion;
  if (suggestion) {
    const root = suggestion.closest("main");
    const input = root.querySelector(guideSuggestion ? "#question" : "[data-studio-prompt]");
    input.value = suggestion.dataset.guidePrompt || suggestion.dataset.studioPromptSuggestion;
    input.focus();
  }
});

document.addEventListener("change", (event) => {
  const select = event.target.closest("[data-preview-select]");
  if (!select) return;

  const link = select.closest(".export-controls").querySelector("[data-preview-link]");
  link.href = select.value;
});

document.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-studio-create-form]");
  if (!form) return;

  const root = form.closest("[data-project-studio]");
  const selected = [...root.querySelectorAll("[data-studio-accept]:checked")];
  if (!selected.length) {
    event.preventDefault();
    root.querySelector("[data-studio-status]").textContent = "Selecione ao menos um campo revisado para criar o projeto.";
    return;
  }

  form.querySelectorAll("[data-studio-generated-field]").forEach((input) => input.remove());
  selected.forEach((checkbox) => {
    const card = checkbox.closest("[data-studio-field-card]");
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = `project[fields][${checkbox.value}]`;
    input.value = card.querySelector("[data-studio-field-text]").value;
    input.dataset.studioGeneratedField = "true";
    form.append(input);
  });
  root.querySelector("[data-studio-create-type]").value = root.querySelector("[data-studio-project-type]").value;
});

document.addEventListener("submit", (event) => {
  const form = event.target.closest("#project-editor");
  if (!form) return;

  const button = event.submitter;
  if (!button) return;
  if (button.name) {
    const submittedValue = document.createElement("input");
    submittedValue.type = "hidden";
    submittedValue.name = button.name;
    submittedValue.value = button.value;
    form.append(submittedValue);
  }
  button.disabled = true;
  button.textContent = "Salvando…";
});

async function requestStudioSuggestions(root, form, continuation) {
  if (!root || !form) return;
  const status = root.querySelector("[data-studio-status]");
  const results = root.querySelector("[data-studio-results]");
  const projectType = form.querySelector("[data-studio-project-type]").value;
  const mode = form.querySelector("[data-studio-mode]").value;
  const prompt = mode === "guided" ? form.querySelector("[data-studio-prompt]").value.trim() : "";
  const sourceText = mode === "import" ? form.querySelector("[data-studio-source]").value.trim() : "";
  let userMessage = prompt;

  if (continuation) {
    const answers = [...root.querySelectorAll("[data-studio-question-input]")].map((input) => {
      const question = input.closest("[data-studio-question]").querySelector("[data-studio-question-label]").textContent;
      return `${question}\n${input.value.trim()}`;
    }).filter((answer) => answer.trim().length > 0);
    if (!answers.length) {
      status.textContent = "Responda ao menos uma pergunta para continuar.";
      return;
    }
    userMessage = answers.join("\n\n");
  } else if (!prompt && !sourceText) {
    status.textContent = "Descreva sua ideia ou cole um texto para organizar.";
    return;
  }

  const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
  if (submitButton) submitButton.disabled = true;
  root.querySelector("[data-studio-continue]").disabled = true;
  status.textContent = "Preparando uma proposta...";
  captureStudioFields(root);
  const messages = [...(root._studioMessages || []), { role: "user", content: userMessage }];

  try {
    const response = await fetch(root.dataset.draftUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      },
      body: JSON.stringify({
        project_type: projectType,
        mode,
        prompt: root.dataset.studioStarted ? "" : prompt,
        source_text: sourceText,
        messages
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "Não foi possível gerar uma proposta.");

    root.dataset.studioStarted = "true";
    root._studioMessages = [...messages, { role: "assistant", content: result.response.answer }];
    root._studioSuggestions ||= new Map();
    result.response.suggestions.forEach((suggestion) => {
      const previous = root._studioSuggestions.get(suggestion.field_id);
      const edited = previous && previous.currentText !== previous.originalText;
      root._studioSuggestions.set(suggestion.field_id, {
        ...suggestion,
        originalText: suggestion.text,
        currentText: edited ? previous.currentText : suggestion.text,
        selected: previous?.selected === true
      });
    });
    results.hidden = false;
    renderStudioThread(root, root._studioMessages);
    renderStudioQuestions(root, result.response.questions);
    renderStudioFields(root);
    form.querySelector("[data-studio-project-type]").disabled = true;
    form.querySelector("[data-studio-mode]").disabled = true;
    status.textContent = "Proposta pronta. Revise as sugestões antes de criar o projeto.";
  } catch (error) {
    status.textContent = error.message || "Não foi possível conectar ao serviço de IA.";
  } finally {
    if (submitButton) submitButton.disabled = false;
    root.querySelector("[data-studio-continue]").disabled = false;
  }
}

function renderStudioThread(root, messages) {
  const thread = root.querySelector("[data-studio-thread]");
  thread.replaceChildren();
  messages.forEach((message) => addChatMessage(thread, message.role, message.content));
}

function renderStudioQuestions(root, questions) {
  const section = root.querySelector("[data-studio-questions-section]");
  const container = root.querySelector("[data-studio-questions]");
  container.replaceChildren();
  section.hidden = !questions.length;
  questions.forEach((question) => {
    const item = document.createElement("div");
    item.className = "field studio-question";
    item.dataset.studioQuestion = "true";
    const label = document.createElement("label");
    label.textContent = question.prompt;
    label.dataset.studioQuestionLabel = "true";
    const input = document.createElement("textarea");
    input.className = "text-control";
    input.rows = 3;
    input.maxLength = 2000;
    input.dataset.studioQuestionInput = "true";
    item.append(label, input);
    container.append(item);
  });
}

function renderStudioFields(root) {
  const section = root.querySelector("[data-studio-suggestions-section]");
  const container = root.querySelector("[data-studio-suggestions]");
  const suggestions = [...root._studioSuggestions.values()];
  container.replaceChildren();
  section.hidden = !suggestions.length;
  suggestions.forEach((suggestion) => {
    const card = document.createElement("article");
    card.className = "studio-suggestion";
    card.dataset.studioFieldCard = "true";
    card.dataset.studioFieldId = suggestion.field_id;
    const title = document.createElement("h3");
    title.textContent = suggestion.label;
    const origin = document.createElement("p");
    origin.className = "field-hint";
    origin.textContent = suggestion.origin === "from_user_input"
      ? "A IA classificou esta proposta como apoiada no material fornecido; confira se a correspondência está correta."
      : "Sugestão gerada pela IA; confira fatos e fundamentos antes de usar.";
    const input = document.createElement("textarea");
    input.className = "text-control";
    input.rows = 5;
    input.maxLength = suggestion.limit;
    input.value = suggestion.currentText ?? suggestion.text;
    input.dataset.studioFieldText = "true";
    const acceptLabel = document.createElement("label");
    acceptLabel.className = "studio-accept";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = suggestion.field_id;
    checkbox.checked = suggestion.selected === true;
    checkbox.dataset.studioAccept = "true";
    const acceptText = document.createElement("span");
    acceptText.textContent = "Incluir este campo no novo projeto";
    acceptLabel.append(checkbox, acceptText);
    card.append(title, origin, input, acceptLabel);
    container.append(card);
  });
}

function captureStudioFields(root) {
  if (!root._studioSuggestions) return;
  root.querySelectorAll("[data-studio-field-card]").forEach((card) => {
    const suggestion = root._studioSuggestions.get(card.dataset.studioFieldId);
    if (!suggestion) return;

    suggestion.currentText = card.querySelector("[data-studio-field-text]").value;
    suggestion.selected = card.querySelector("[data-studio-accept]").checked;
  });
}

function setupAssistPanel() {
  const panel = document.querySelector(".assist-panel");
  const backdrop = document.querySelector("[data-assist-backdrop]");
  if (!panel || !backdrop || panel.dataset.sheetReady) return;

  panel.dataset.sheetReady = "true";
  const summary = panel.querySelector("summary");
  const closeButton = panel.querySelector("[data-assist-close]");
  const mobile = window.matchMedia("(max-width: 720px)");
  let wasMobileOpen = false;

  const sync = (focusPanel = false) => {
    const mobileOpen = mobile.matches && panel.open;
    summary.setAttribute("aria-expanded", String(panel.open));
    panel.classList.toggle("is-mobile-open", mobileOpen);
    backdrop.hidden = !mobileOpen;
    document.body.classList.toggle("assist-sheet-open", mobileOpen);
    if (mobileOpen) {
      panel.setAttribute("role", "dialog");
      panel.setAttribute("aria-modal", "true");
      panel.setAttribute("aria-labelledby", "assist-panel-title");
      if (focusPanel) closeButton.focus();
    } else {
      panel.removeAttribute("role");
      panel.removeAttribute("aria-modal");
      panel.removeAttribute("aria-labelledby");
      if (wasMobileOpen && !panel.open) summary.focus();
    }
    wasMobileOpen = mobileOpen;
  };
  const close = () => {
    panel.open = false;
    summary.focus();
  };

  panel.addEventListener("toggle", () => sync(panel.open));
  mobile.addEventListener("change", () => sync());
  closeButton.addEventListener("click", close);
  backdrop.addEventListener("click", close);
  panel.addEventListener("keydown", (event) => {
    if (!mobile.matches || !panel.open) return;
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...panel.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )].filter((element) => element.getClientRects().length > 0);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  sync();
}

function setupChat() {
  const root = document.querySelector("[data-chat]");
  if (!root || root.dataset.chatReady) return;

  root.dataset.chatReady = "true";
  root._chatMessages = [];
  const form = root.querySelector("[data-chat-form]");
  const input = root.querySelector("[data-chat-input]");
  const messages = root.querySelector("[data-chat-messages]");
  const status = root.querySelector("[data-chat-status]");
  const submit = form.querySelector('button[type="submit"]');

  root.addEventListener("click", (event) => {
    const suggestion = event.target.closest("[data-chat-suggestion]");
    if (!suggestion) return;
    input.value = suggestion.dataset.chatSuggestion;
    input.focus();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    messages.querySelector(".chat-empty")?.remove();
    addChatMessage(messages, "user", message);
    input.value = "";
    submit.disabled = true;
    status.textContent = "Pensando…";
    try {
      const response = await fetch(root.dataset.chatUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({
          project_id: root.dataset.projectId,
          scope: root.dataset.scope,
          message,
          messages: root._chatMessages
        })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.message || "Não foi possível enviar a pergunta.");

      root._chatMessages.push({ role: "user", content: message });
      root._chatMessages.push({ role: "assistant", content: result.answer });
      root._chatMessages = root._chatMessages.slice(-12);
      addChatMessage(messages, "assistant", result.answer);
      status.textContent = "Resposta recebida.";
    } catch (error) {
      input.value = message;
      addChatMessage(messages, "assistant", error.message || "Não foi possível conectar ao serviço de IA.");
      status.textContent = "A pergunta não foi enviada.";
    } finally {
      submit.disabled = false;
      input.focus();
    }
  });
}

function addChatMessage(container, role, content) {
  const message = document.createElement("article");
  message.className = `chat-message chat-message-${role}`;
  message.setAttribute("aria-label", role === "user" ? "Sua mensagem" : "Resposta");
  const body = document.createElement("p");
  body.textContent = content;
  message.append(body);
  container.append(message);
  container.scrollTop = container.scrollHeight;
}

function initializePageInteractions() {
  document.querySelectorAll(".flash:not([data-flash-ready])").forEach((flash) => {
    flash.dataset.flashReady = "true";
    const close = document.createElement("button");
    close.type = "button";
    close.className = "flash-close";
    close.setAttribute("aria-label", "Fechar mensagem");
    close.textContent = "×";
    close.addEventListener("click", () => flash.remove());
    flash.append(close);
    if (flash.classList.contains("flash-notice")) {
      window.setTimeout(() => flash.remove(), 6000);
    }
  });

  const projectsPage = document.querySelector(".projects-page[data-project-view]");
  if (projectsPage && window.matchMedia("(max-width: 720px)").matches) {
    projectsPage.dataset.projectView = "list";
    projectsPage.querySelectorAll("[data-project-view-button]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.projectViewButton === "list"));
    });
  }
  document.querySelectorAll("[data-package-card]").forEach(updatePackageButton);
  document.querySelectorAll("[data-studio-mode]").forEach((mode) => {
    const guided = mode.value === "guided";
    const root = mode.closest("[data-project-studio]");
    root.querySelectorAll("[data-guided-only]").forEach((element) => {
      element.hidden = !guided;
    });
    root.querySelector("[data-studio-source-field]").hidden = guided;
  });
  setupChat();
  setupAssistPanel();
}

document.addEventListener("DOMContentLoaded", initializePageInteractions);
document.addEventListener("turbo:load", initializePageInteractions);
