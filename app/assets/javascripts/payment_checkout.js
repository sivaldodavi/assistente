(() => {
  const root = document.querySelector("[data-checkout]");
  if (!root) return;

  const money = (cents) => (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const emptyState = root.querySelector("[data-checkout-empty]");
  const details = root.querySelector("[data-checkout-details]");
  const itemLine = root.querySelector("[data-checkout-item]");
  const totalLine = root.querySelector("[data-checkout-total]");
  const buy = root.querySelector("[data-buy-package]");
  const status = root.querySelector("[data-payment-status]");
  const output = root.querySelector("[data-payment-result]");
  const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || "";

  const selectedCard = () => root.querySelector("input[data-package-option]:checked")?.closest("[data-package-card]");

  function setLocked(locked) {
    root.querySelectorAll("input[data-package-option], [data-package-quantity], [data-step]").forEach((element) => {
      element.disabled = locked;
    });
  }

  // Qualquer mudança de escolha descarta o Pix anterior: cada combinação gera um pedido novo.
  function update() {
    buy.dataset.requestId = "";
    buy.disabled = false;
    output.replaceChildren();
    status.textContent = "";

    const card = selectedCard();
    if (!card) {
      emptyState.hidden = false;
      details.hidden = true;
      return;
    }
    const field = card.querySelector("[data-package-quantity]");
    const quantity = Math.min(99, Math.max(1, Number(field.value) || 1));
    field.value = quantity;
    const amount = Number(card.dataset.priceCents) * quantity;

    emptyState.hidden = true;
    details.hidden = false;
    itemLine.textContent = quantity > 1 ? `${card.dataset.label} × ${quantity}` : card.dataset.label;
    totalLine.textContent = money(amount);
    buy.textContent = `Gerar Pix — ${money(amount)}`;
  }

  function renderPix(result) {
    output.replaceChildren();
    const amount = document.createElement("p");
    amount.textContent = `Total: ${money(result.amount_cents)}`;
    output.append(amount);

    if (result.qr_code_base64) {
      const image = document.createElement("img");
      image.className = "payment-qr";
      image.alt = "QR Code Pix";
      image.src = `data:image/png;base64,${result.qr_code_base64}`;
      output.append(image);
    }
    if (result.pix_copy_code) {
      const code = document.createElement("pre");
      code.dataset.pixCopyCode = "";
      code.textContent = result.pix_copy_code;
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "button button-secondary";
      copy.dataset.copyPix = "";
      copy.textContent = "Copiar código Pix";
      output.append(code, copy);
    }
    const check = document.createElement("button");
    check.type = "button";
    check.className = "button button-secondary";
    check.dataset.checkPayment = "";
    check.dataset.orderId = result.order_id;
    check.textContent = "Consultar pagamento";
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "text-button";
    reset.dataset.newPurchase = "";
    reset.textContent = "Iniciar outra compra";
    output.append(check, reset);
  }

  async function purchase() {
    const card = selectedCard();
    if (!card) return;
    buy.disabled = true;
    status.textContent = "Registrando pedido Pix…";
    if (!buy.dataset.requestId) buy.dataset.requestId = globalThis.crypto?.randomUUID?.() || "";
    if (!buy.dataset.requestId) {
      status.textContent = "Este navegador não conseguiu gerar um identificador seguro. Atualize-o para continuar.";
      buy.disabled = false;
      return;
    }
    try {
      const response = await fetch("/payments", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
        body: JSON.stringify({
          package_code: card.dataset.packageCard,
          quantity: Number(card.querySelector("[data-package-quantity]").value),
          request_id: buy.dataset.requestId
        })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.message || "Não foi possível gerar o Pix.");
      renderPix(result);
      setLocked(true);
      buy.textContent = "Pix gerado";
      status.textContent = "Use o QR Code ou o código Pix para concluir o pagamento.";
    } catch (error) {
      status.textContent = error.message || "Não foi possível gerar o Pix. Tente novamente.";
      buy.disabled = false;
    }
  }

  root.addEventListener("change", (event) => {
    if (event.target.closest("input[data-package-option], [data-package-quantity]")) update();
  });

  root.addEventListener("click", async (event) => {
    const step = event.target.closest("[data-step]");
    if (step) {
      event.preventDefault();
      const field = step.closest("[data-package-card]").querySelector("[data-package-quantity]");
      field.value = Math.min(99, Math.max(1, (Number(field.value) || 1) + Number(step.dataset.step)));
      update();
      return;
    }
    if (event.target.closest("[data-buy-package]")) return purchase();
    if (event.target.closest("[data-new-purchase]")) {
      setLocked(false);
      update();
      return;
    }
    if (event.target.closest("[data-copy-pix]")) {
      const value = root.querySelector("[data-pix-copy-code]").textContent;
      try {
        await navigator.clipboard.writeText(value);
        status.textContent = "Código Pix copiado.";
      } catch {
        status.textContent = "Não foi possível copiar. Selecione e copie o código Pix.";
      }
      return;
    }
    const check = event.target.closest("[data-check-payment]");
    if (check) {
      check.disabled = true;
      try {
        const response = await fetch(`/payments/${encodeURIComponent(check.dataset.orderId)}`, {
          credentials: "same-origin",
          headers: { Accept: "application/json" }
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.message || "Não foi possível consultar o pedido.");
        status.textContent = result.status === "approved"
          ? "Pagamento confirmado. Seus créditos foram liberados."
          : `Status do pagamento: ${result.status}.`;
      } catch (error) {
        status.textContent = error.message || "Não foi possível consultar o pedido.";
      } finally {
        check.disabled = false;
      }
    }
  });

  update();
})();
