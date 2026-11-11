/**
 * Duplicate Project Module - Assistente Acadêmico
 * Handles project duplication functionality
 */
export function initDuplicate({ form, flushSave, readJson }) {
  if (!form || !form.dataset.duplicateUrl) return;

  form.querySelector("[data-duplicate-project]")?.addEventListener("click", async () => {
    const button = form.querySelector("[data-duplicate-project]");
    const saveState = form.querySelector("[data-save-state]");
    button.disabled = true;
    if (saveState) saveState.textContent = "Duplicando projeto…";
    try {
      if (!await flushSave()) throw new Error("Salve as alterações antes de duplicar.");
      const csrf = form.querySelector("[name=csrf_token]")?.value;
      if (!csrf) throw new Error("Sessão sem proteção CSRF.");
      const response = await fetch(form.dataset.duplicateUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ revision: Number(form.dataset.revision) })
      });
      const result = await readJson(response);
      if (!response.ok) throw new Error(result.error || "Erro ao duplicar.");
      if (result.project_url) {
        if (saveState) saveState.textContent = "Projeto duplicado. Redirecionando…";
        window.location.href = result.project_url;
      } else {
        throw new Error("URL do projeto não retornada.");
      }
    } catch (error) {
      if (saveState) saveState.textContent = error.message;
      button.disabled = false;
    }
  });
}