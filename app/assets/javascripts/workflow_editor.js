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
    card.querySelector("[data-buy-package]").dataset.requestId = "";
    card.querySelector("[data-buy-package]").disabled = false;
    card.querySelector("[data-buy-package]").textContent = "Gerar Pix";
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

      document.addEventListener("click", (event) => {
        const filterButton = event.target.closest("[data-project-filter]");
        const viewButton = event.target.closest("[data-project-view-button]");
        const page = document.querySelector(".projects-page[data-project-view]");
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
          if (emptyMessage) {
            emptyMessage.hidden = Boolean(page.querySelector("[data-project-card]:not([hidden])"));
          }
        }

        if (viewButton) {
          page.dataset.projectView = viewButton.dataset.projectViewButton;
          page.querySelectorAll("[data-project-view-button]").forEach((button) => {
            button.setAttribute("aria-pressed", String(button === viewButton));
          });
        }
      });

      document.querySelectorAll("dialog[data-settings-dialog][open]").forEach((dialog) => {
        if (typeof dialog.showModal !== "function") return;
        dialog.addEventListener("cancel", (event) => {
          event.preventDefault();
          window.location.assign(dialog.dataset.closeHref);
        });
        dialog.close();
        dialog.showModal();
      });

      const projectsPage = document.querySelector(".projects-page[data-project-view]");
      if (projectsPage && window.matchMedia("(max-width: 720px)").matches) {
        projectsPage.dataset.projectView = "list";
        projectsPage.querySelectorAll("[data-project-view-button]").forEach((button) => {
          button.setAttribute("aria-pressed", String(button.dataset.projectViewButton === "list"));
        });
      }
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
    purchaseButton.textContent = "Pix gerado";
    status.textContent = "Use o QR Code ou o código Pix para concluir o pagamento.";
  } catch (error) {
    status.textContent = error.message || "Não foi possível gerar o Pix. Tente novamente.";
    purchaseButton.disabled = false;
  }
});

document.addEventListener("click", async (event) => {
  const actionButton = event.target.closest("[data-ai-action]");
  const jevButton = event.target.closest("[data-jev-section-action], [data-jev-report]");
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
    const text = document.createElement("p");
    text.textContent = suggestion.text;
    item.append(text);

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
  heading.textContent = analysis.section ? "Resultado da etapa" : "Resultado do relatório";
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
}
