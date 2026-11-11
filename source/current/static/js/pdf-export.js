/**
 * PDF Export Module - Assistente Acadêmico
 * Handles Quarto PDF export functionality
 */
export function initPdfExport({ form, flushSave, readJson }) {
  if (!form || !form.dataset.exportQuartoUrl) return;

  form.querySelectorAll("[data-export-quarto]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      const saveState = form.querySelector("[data-save-state]");
      if (saveState) saveState.textContent = "Gerando PDF via Quarto…";
      try {
        if (!await flushSave()) throw new Error("Salve as alterações antes de exportar.");
        const csrf = form.querySelector("[name=csrf_token]")?.value;
        if (!csrf) throw new Error("Sessão sem proteção CSRF.");
        const response = await fetch(form.dataset.exportQuartoUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
          body: JSON.stringify({ revision: Number(form.dataset.revision) })
        });
        const result = await readJson(response);
        if (!response.ok) throw new Error(result.error || "Erro ao gerar PDF.");
        if (result.download_url) {
          window.open(result.download_url, "_blank");
          if (saveState) saveState.textContent = "PDF gerado com sucesso.";
        } else {
          throw new Error("URL de download não retornada.");
        }
      } catch (error) {
        if (saveState) saveState.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });
  });
}